#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mpc_ems_sqp_seq.py — MPC + SQP 全时域控制序列优化

与单变量 SQP 版（mpc_ems_sqp.py）的核心区别：

  单变量 SQP:   优化 1 个变量 P_fc（在整个时域内保持恒定）
  序列 SQP:     优化 N_p 个变量 [P_fc(k), ..., P_fc(k+N_p-1)]（每步独立）

这是"教科书级"的 MPC：在每个时间步求解一个完整的 Np 步优化问题，
但只执行第 1 步，然后滚动到下一时刻。

网格枚举无法处理此问题（60^N_p 组合爆炸），SQP 是可行方案。

用法：
    python scripts/mpc_ems_sqp_seq.py                            # WLTC
    python scripts/mpc_ems_sqp_seq.py --cycle nedc               # NEDC
    python scripts/mpc_ems_sqp_seq.py --np 20                    # 预测时域
    python scripts/mpc_ems_sqp_seq.py --all                       # 所有工况
    python scripts/mpc_ems_sqp_seq.py --benchmark                 # 三方对比（DP/单变量SQP/序列SQP）
"""

import os, sys, time
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.optimize import minimize

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PROJECT_ROOT, 'results')
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, 'scripts')
sys.path.insert(0, SCRIPTS_DIR)

from day8_dp_ems import (
    fc_hydrogen_flow, fc_efficiency, vehicle_power, state_transition,
    load_drive_cycle, run_rule_controller,
    SOC_MIN, SOC_MAX, PFC_MIN, PFC_MAX,
    N_SOC, N_PFC, DT, LHV_H2, PFC_EFF_BP, ETA_FC,
    SOC_BP, OCV_LU, Q_BAT, R_INT,
)
from mpc_ems_optimized import (
    N_P_DEFAULT, S_MPC, W_SOC, BETA_TERM, SOC_DEADBAND,
    SOC_SOFT_MIN, W_SOC_LOW, SOC_FINAL_TOL, W_FINAL_SOC, W_PFC_SLEW,
    SOC_REF, PFC_GRID, H2_GRID,
    mpc_step_soc, soc_tracking_penalty, soc_equivalent_h2,
)


# ====================================================================
# 代价函数（序列版）
# ====================================================================
def cost_fn_seq(control_seq, p_load_pred, soc_k, dt, s_factor, w_pfc_slew,
                p_fc_prev, soc_ref, soc_deadband, soc_soft_min,
                w_soc, w_soc_low, beta_term, soc_final_tol, w_final_soc,
                is_route_end):
    """
    序列版代价函数

    control_seq : array (N_p,) — 整个预测时域的控制序列
    其余参数与单变量版本一致
    """
    control_seq = np.asarray(control_seq)
    horizon = len(control_seq)
    soc_pred = soc_k
    J = 0.0

    p_fc_prev_local = p_fc_prev  # 第 0 步的"上一步"

    for i in range(horizon):
        p_fc_i = control_seq[i]
        p_load_i = p_load_pred[i]
        p_bat_i = p_load_i - p_fc_i
        h2_i = fc_hydrogen_flow(p_fc_i)

        # ── 爬坡惩罚（对上一步/上一控制步） ──
        slew_prev = p_fc_prev_local
        J += w_pfc_slew * (p_fc_i - slew_prev) ** 2
        p_fc_prev_local = p_fc_i  # 下一步的"上一步"就是当前 P_fc

        # ── 氢耗 ──
        J += h2_i * dt

        # ── 等效电池能量 ──
        J += s_factor * abs(p_bat_i) / 3600.0 * dt

        # ── SOC 前向仿真 ──
        soc_pred_next = mpc_step_soc(soc_pred, p_fc_i, p_load_i)
        if soc_pred_next is None:
            return 1e15
        soc_pred = soc_pred_next

        # ── SOC 惩罚 ──
        is_terminal = (i == horizon - 1)
        J += soc_tracking_penalty(
            soc_pred, is_terminal=is_terminal, is_route_end=is_route_end,
            w_soc=w_soc, beta_term=beta_term, soc_ref=soc_ref,
            soc_deadband=soc_deadband, soc_soft_min=soc_soft_min,
            w_soc_low=w_soc_low, soc_final_tol=soc_final_tol,
            w_final_soc=w_final_soc,
        )

    return J


# ====================================================================
# MPC 仿真 — 序列 SQP
# ====================================================================
def mpc_sim_sqp_seq(P_load, SOC_0=0.6, N_p=N_P_DEFAULT,
                    w_soc=W_SOC, beta_term=BETA_TERM, soc_ref=SOC_REF,
                    s_factor=S_MPC, soc_deadband=SOC_DEADBAND,
                    soc_soft_min=SOC_SOFT_MIN, w_soc_low=W_SOC_LOW,
                    soc_final_tol=SOC_FINAL_TOL, w_final_soc=W_FINAL_SOC,
                    w_pfc_slew=W_PFC_SLEW,
                    seq_maxiter=80, ftol=1e-6, eps=0.05):
    """
    MPC 仿真 — 全时域控制序列优化

    Parameters 与 mpc_sim / mpc_sim_sqp 完全兼容。

    新增参数
    ----------
    seq_maxiter : int — 每步 SQP 最大迭代次数（N_p 维需要更多）
    ftol : float — 相对代价收敛容差
    eps : float — 有限差分梯度步长 [kW]
    """
    N = len(P_load)
    SOC = np.zeros(N + 1)
    P_fc = np.zeros(N)
    P_bat = np.zeros(N)
    m_H2 = np.zeros(N)

    SOC[0] = SOC_0

    print(f'[MPC-SQP-SEQ] N_p={N_p}, s={s_factor}, w_soc={w_soc}, β_term={beta_term}')
    print(f'[MPC-SQP-SEQ] 优化维度: {N_p} 维（全时域控制序列）')
    print(f'[MPC-SQP-SEQ] 开始仿真... ({N} 步)')

    step_times = []

    for k in range(N):
        t_start = time.perf_counter()
        soc_k = SOC[k]
        horizon = min(N_p, N - k)
        p_load_pred = P_load[k: k + horizon]
        p_fc_prev = P_fc[k - 1] if k > 0 else np.clip(P_load[k], PFC_MIN, PFC_MAX)
        is_route_end = (k + horizon >= N)

        # ── 第一步：1D 粗网格筛选 + SQP，找最佳恒定 P_fc ──
        static_args = (p_load_pred, soc_k, DT, s_factor, w_pfc_slew,
                       p_fc_prev, soc_ref, soc_deadband, soc_soft_min,
                       w_soc, w_soc_low, beta_term, soc_final_tol, w_final_soc,
                       is_route_end)

        N_COARSE = 10
        coarse_grid = np.linspace(PFC_MIN, PFC_MAX, N_COARSE)
        J_coarse = np.array([cost_fn_seq(np.full(horizon, p), *static_args)
                             for p in coarse_grid])
        best_const_pfc = coarse_grid[J_coarse.argmin()]

        # SQP 精炼恒定 P_fc
        res_1d = minimize(
            lambda p: cost_fn_seq(np.full(horizon, p[0]), *static_args),
            np.array([best_const_pfc]),
            method='SLSQP', bounds=[(PFC_MIN, PFC_MAX)],
            options={'maxiter': 15, 'ftol': 1e-4, 'eps': 0.05},
        )
        const_pfc = res_1d.x[0] if res_1d.success else best_const_pfc

        # ── 第二步：用恒定最优作为初始序列，SQP 逐点精炼 ──
        x0 = np.full(horizon, const_pfc)

        res = minimize(
            cost_fn_seq, x0,
            args=static_args,
            method='SLSQP',
            bounds=[(PFC_MIN, PFC_MAX)] * horizon,
            options={'maxiter': seq_maxiter, 'ftol': ftol, 'eps': eps},
        )

        best_seq = res.x if res.success else x0
        best_p_fc = best_seq[0]

        # ── 执行第 1 步 ──
        P_fc[k] = np.clip(best_p_fc, PFC_MIN, PFC_MAX)
        P_bat[k] = P_load[k] - P_fc[k]
        m_H2[k] = fc_hydrogen_flow(P_fc[k]) * DT
        soc_next = mpc_step_soc(soc_k, P_fc[k], P_load[k])
        SOC[k + 1] = soc_k if soc_next is None else soc_next

        t_elapsed = time.perf_counter() - t_start
        step_times.append(t_elapsed)

        if k % 300 == 0:
            seq_var = np.std(best_seq)  # 序列的波动幅度
            print(f'  SEQ step {k}/{N}  iters={res.nit:3d}  '
                  f'P_fc[0]={best_p_fc:.2f}  σ_seq={seq_var:.2f}  '
                  f'cost={res.fun:.2f}')

    # ── 汇总 ──
    raw_h2_kg = np.cumsum(m_H2)[-1] / 1000
    h2_eq_kg = soc_equivalent_h2(raw_h2_kg, SOC[-1], soc_ref=soc_ref, s_factor=s_factor)
    avg_time = np.mean(step_times) * 1000

    print(f'[MPC-SQP-SEQ] 完成！H2_raw={raw_h2_kg:.4f} kg, SOC_end={SOC[-1]:.3f}, '
          f'H2_eq={h2_eq_kg:.4f} kg')
    print(f'[MPC-SQP-SEQ] 平均每步耗时: {avg_time:.1f} ms')

    eff_arr = fc_efficiency(P_fc)

    return {
        'time': np.arange(N),
        'SOC': SOC[:N],
        'SOC_end': SOC[-1],
        'P_fc_kW': P_fc,
        'P_bat_kW': P_bat,
        'm_H2_g': m_H2,
        'm_H2_cumul_kg': np.cumsum(m_H2) / 1000,
        'H2_raw_kg': raw_h2_kg,
        'H2_eq_kg': h2_eq_kg,
        'fc_efficiency': eff_arr,
        'step_times_ms': step_times,
        'avg_step_time_ms': avg_time,
        'solver': 'SQP-SEQ',
        'config': {
            'N_p': N_p,
            's_factor': s_factor,
            'w_soc': w_soc,
            'beta_term': beta_term,
            'solver': 'SQP-SEQ',
        },
    }


# ====================================================================
# 三方对比图（DP / 单变量SQP / 序列SQP）
# ====================================================================
def plot_three_way(t, P_load, dp_result, sqp_result, seq_result, cycle_name='wltc'):
    """DP vs 单变量SQP vs 序列SQP 对比"""
    t_min = t / 60

    fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True)

    colors = {'DP': 'g', 'SQP': 'b', 'SQP-SEQ': 'r'}
    ls = {'DP': '--', 'SQP': '-.', 'SQP-SEQ': '-'}

    # (1) P_fc
    ax = axes[0]
    ax.fill_between(t_min, 0, P_load, alpha=0.10, color='gray', label='Load')
    for name, res in [('DP', dp_result), ('SQP', sqp_result), ('SQP-SEQ', seq_result)]:
        h2_str = res.get('H2_raw_kg', res['m_H2_cumul_kg'][-1])
        ax.plot(t_min, res['P_fc_kW'], color=colors[name], linestyle=ls[name],
                linewidth=0.8, label=f'{name} ({h2_str:.3f} kg)')
    ax.set_ylabel('P_fc (kW)')
    ax.legend(fontsize=7, ncol=2)
    ax.grid(True, alpha=0.3)
    ax.set_title(f'{cycle_name.upper()} — DP vs SQP (1D) vs SQP-SEQ (Np-D)')

    # (2) SOC
    ax = axes[1]
    for name, res in [('DP', dp_result), ('SQP', sqp_result), ('SQP-SEQ', seq_result)]:
        soc_end = res.get('SOC_end', res['SOC'][-1])
        ax.plot(t_min, res['SOC'], color=colors[name], linestyle=ls[name],
                linewidth=0.8, label=f'{name} (end={soc_end:.3f})')
    ax.axhline(y=SOC_REF, color='gray', linestyle=':', alpha=0.5)
    ax.set_ylabel('SOC')
    ax.set_ylim(0.2, 0.9)
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)

    # (3) 累计氢耗
    ax = axes[2]
    for name, res in [('DP', dp_result), ('SQP', sqp_result), ('SQP-SEQ', seq_result)]:
        ax.plot(t_min, res['m_H2_cumul_kg'], color=colors[name], linestyle=ls[name],
                linewidth=0.8, label=f'{name} ({res["m_H2_cumul_kg"][-1]:.3f} kg)')
    ax.set_ylabel('Cumul. H₂ (kg)')
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)

    # (4) 每步耗时对比
    ax = axes[3]
    for name, res in [('SQP', sqp_result), ('SQP-SEQ', seq_result)]:
        times = res.get('step_times_ms', [])
        if len(times) > 0:
            ax.plot(t_min[:len(times)], times, color=colors[name],
                    linestyle=ls[name], linewidth=0.6,
                    label=f'{name} avg={np.mean(times):.1f}ms')
    ax.set_ylabel('Step time (ms)')
    ax.set_xlabel('Time (min)')
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    png_path = os.path.join(RESULTS_DIR, f'DP_vs_SQP_vs_SEQ_{cycle_name}.png')
    plt.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f'[图] {png_path}')
    plt.close()


# ====================================================================
# 主程序
# ====================================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='MPC SQP 序列优化')
    parser.add_argument('--cycle', choices=['wltc', 'nedc', 'cltc'], default='wltc')
    parser.add_argument('--np', type=int, default=20,
                        help='预测时域（注意：序列优化 N_p 越大越慢）')
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--benchmark', action='store_true', default=True,
                        help='三方对比（DP + 单变量SQP + 序列SQP）')
    args = parser.parse_args()

    cycles = ['wltc', 'nedc', 'cltc'] if args.all else [args.cycle]

    for cycle in cycles:
        print('\n' + '=' * 60)
        print(f'  工况: {cycle.upper()}, N_p={args.np}')
        print('=' * 60)

        # 加载工况
        t, v = load_drive_cycle(cycle)
        P_load = vehicle_power(v, DT)
        N = len(t)
        print(f'  功率范围: {P_load.min():.1f} ~ {P_load.max():.1f} kW')

        # DP 基准
        print(f'\n[1/3] DP 全局最优...')
        from day8_dp_ems import backward_dp, forward_rollout
        J, pi = backward_dp(P_load)
        dp = forward_rollout(P_load, pi)

        # 单变量 SQP 基准
        print(f'\n[2/3] 单变量 SQP (1D)...')
        from mpc_ems_sqp import mpc_sim_sqp
        t0 = time.perf_counter()
        sqp_res = mpc_sim_sqp(P_load, SOC_0=0.6, N_p=args.np)
        t_sqp = time.perf_counter() - t0

        # 序列 SQP
        print(f'\n[3/3] 序列 SQP ({args.np}D)...')
        t0 = time.perf_counter()
        seq_res = mpc_sim_sqp_seq(P_load, SOC_0=0.6, N_p=args.np)
        t_seq = time.perf_counter() - t0

        # 对比输出
        print('\n' + '=' * 60)
        print(f'  {"指标":<28} {"SQP 1D":>13} {"SQP SEQ":>13}')
        print('=' + '-' * 54 + '=')
        rows = [
            ('总氢耗 raw (kg)', f'{sqp_res["H2_raw_kg"]:.4f}',
             f'{seq_res["H2_raw_kg"]:.4f}'),
            ('SOC_end', f'{sqp_res["SOC_end"]:.4f}',
             f'{seq_res["SOC_end"]:.4f}'),
            ('SOC 修正氢耗 (kg)', f'{sqp_res["H2_eq_kg"]:.4f}',
             f'{seq_res["H2_eq_kg"]:.4f}'),
            ('FC 平均效率', f'{sqp_res["fc_efficiency"].mean():.2%}',
             f'{seq_res["fc_efficiency"].mean():.2%}'),
            ('FC 最大功率 (kW)', f'{sqp_res["P_fc_kW"].max():.2f}',
             f'{seq_res["P_fc_kW"].max():.2f}'),
            ('总耗时 (s)', f'{t_sqp:.1f}',
             f'{t_seq:.1f}'),
            ('平均每步 (ms)', f'{t_sqp/N*1000:.1f}',
             f'{t_seq/N*1000:.1f}'),
        ]
        for row in rows:
            print(f'  {row[0]:<28} {row[1]:>13} {row[2]:>13}')
        print('=' + '=' * 54 + '=')

        # 相对 DP
        dp_H2 = dp['m_H2_cumul_kg'][-1]
        dp_H2eq = soc_equivalent_h2(dp_H2, dp['SOC'][-1])
        print(f'\n  相对 DP 差距 (raw H₂ / SOC修正):')
        print(f'    SQP 1D:   raw {sqp_res["H2_raw_kg"]/dp_H2-1:+.2%}  '
              f'eq {sqp_res["H2_eq_kg"]/dp_H2eq-1:+.2%}')
        print(f'    SQP SEQ:  raw {seq_res["H2_raw_kg"]/dp_H2-1:+.2%}  '
              f'eq {seq_res["H2_eq_kg"]/dp_H2eq-1:+.2%}')

        # 对比图
        plot_three_way(t, P_load, dp, sqp_res, seq_res, cycle)

    print(f'\n[OK] 全部完成！结果保存在 {RESULTS_DIR}/DP_vs_SQP_vs_SEQ_*.png')


if __name__ == '__main__':
    main()
