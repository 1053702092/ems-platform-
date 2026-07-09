#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mpc_ems_sqp.py — MPC + SQP 序列二次规划求解器

核心区别：
  网格搜索（原版）：        60次枚举 × N_p步前向仿真  → 离散最优
  SQP（本文件）：     scipy.optimize.minimize(SLSQP) → 连续最优

优点：
  • 连续空间搜索，不受网格分辨率限制
  • 对 1D 问题，函数调用次数约 10-20 次（vs 60 网格枚举）
  • 很容易扩展到同时优化 P_fc 序列（P_fc[0]...P_fc[N_p-1]）

用法：
    python scripts/mpc_ems_sqp.py                                # WLTC 对比
    python scripts/mpc_ems_sqp.py --cycle nedc                   # NEDC
    python scripts/mpc_ems_sqp.py --np 30                        # 预测时域
    python scripts/mpc_ems_sqp.py --all                          # 所有工况
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

# 复用已调优的 MPC 参数
from mpc_ems_optimized import (
    N_P_DEFAULT, S_MPC, W_SOC, BETA_TERM, SOC_DEADBAND,
    SOC_SOFT_MIN, W_SOC_LOW, SOC_FINAL_TOL, W_FINAL_SOC, W_PFC_SLEW,
    SOC_REF, PFC_GRID, H2_GRID,
    mpc_step_soc, soc_tracking_penalty, soc_equivalent_h2,
    plot_four_way, print_four_way_metrics,
)


# ====================================================================
# SQP 代价函数
# ====================================================================
def cost_fn_sqp(p_fc_cand, p_load_pred, soc_k, dt, s_factor, w_pfc_slew,
                p_fc_prev, soc_ref, soc_deadband, soc_soft_min,
                w_soc, w_soc_low, beta_term, soc_final_tol, w_final_soc,
                is_route_end):
    """
    SQP 代价函数（连续版）
    与网格搜索的代价完全一致，但 fc_hydrogen_flow 是连续计算而非查表
    """
    # minimize 传进来的是 shape (1,) 数组
    p_fc_cand = p_fc_cand.item()
    h2_cand = fc_hydrogen_flow(p_fc_cand)  # 连续，不查离散网格

    horizon = len(p_load_pred)
    soc_pred = soc_k
    J = w_pfc_slew * (p_fc_cand - p_fc_prev) ** 2  # 爬坡惩罚

    for i in range(horizon):
        p_load_i = p_load_pred[i]
        p_bat_i = p_load_i - p_fc_cand

        # 氢耗
        J += h2_cand * dt
        # 等效电池能量
        J += s_factor * abs(p_bat_i) / 3600.0 * dt

        # SOC 前向仿真
        soc_pred_next = mpc_step_soc(soc_pred, p_fc_cand, p_load_i)
        if soc_pred_next is None:
            return 1e15  # 大惩罚而非 np.inf（梯度需要连续值）
        soc_pred = soc_pred_next

        # SOC 维持 / 终端惩罚
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
# MPC 仿真 — SQP 版
# ====================================================================
def mpc_sim_sqp(P_load, SOC_0=0.6, N_p=N_P_DEFAULT,
                w_soc=W_SOC, beta_term=BETA_TERM, soc_ref=SOC_REF,
                s_factor=S_MPC, soc_deadband=SOC_DEADBAND,
                soc_soft_min=SOC_SOFT_MIN, w_soc_low=W_SOC_LOW,
                soc_final_tol=SOC_FINAL_TOL, w_final_soc=W_FINAL_SOC,
                w_pfc_slew=W_PFC_SLEW,
                sqp_maxiter=30, fallback_grid=True):
    """
    MPC 仿真 — SQP (SLSQP) 优化器 + receding horizon

    参数与 mpc_sim（网格搜索版）完全兼容，便于 A/B 对比。

    新增参数
    ----------
    sqp_maxiter : int — SQP 最大迭代次数
    fallback_grid : bool — SQP 失败时是否回退到网格搜索

    Returns
    -------
    dict — 与 mpc_sim 完全相同的输出格式
    """
    N = len(P_load)
    SOC = np.zeros(N + 1)
    P_fc = np.zeros(N)
    P_bat = np.zeros(N)
    m_H2 = np.zeros(N)

    SOC[0] = SOC_0

    print(f'[MPC-SQP] N_p={N_p}, s={s_factor}, w_soc={w_soc}, β_term={beta_term}')
    print(f'[MPC-SQP] SQP maxiter={sqp_maxiter}, fallback_grid={fallback_grid}')
    print(f'[MPC-SQP] 开始仿真... ({N} 步)')

    step_times = []

    for k in range(N):
        t_start = time.perf_counter()
        soc_k = SOC[k]
        horizon = min(N_p, N - k)
        p_load_pred = P_load[k: k + horizon]
        p_fc_prev = P_fc[k - 1] if k > 0 else np.clip(P_load[k], PFC_MIN, PFC_MAX)
        is_route_end = (k + horizon >= N)

        # ── 粗网格筛选 + SQP 精炼 ──
        #   先跑 10 个粗网格点找较好区域，避免 P_fc=0 的局部极小
        static_args = (p_load_pred, soc_k, DT, s_factor, w_pfc_slew,
                       p_fc_prev, soc_ref, soc_deadband, soc_soft_min,
                       w_soc, w_soc_low, beta_term, soc_final_tol, w_final_soc,
                       is_route_end)

        N_COARSE = 10
        coarse_grid = np.linspace(PFC_MIN, PFC_MAX, N_COARSE)
        J_coarse = np.array([cost_fn_sqp(p, *static_args) for p in coarse_grid])
        best_coarse_idx = np.argmin(J_coarse)
        best_coarse_pfc = coarse_grid[best_coarse_idx]
        best_coarse_cost = J_coarse[best_coarse_idx]

        # SQP 从粗网格最优出发精炼
        res = minimize(
            cost_fn_sqp, np.array([best_coarse_pfc]),
            args=static_args,
            method='SLSQP',
            bounds=[(PFC_MIN, PFC_MAX)],
            options={'maxiter': sqp_maxiter, 'ftol': 1e-4, 'eps': 0.05},
        )

        if res.success and res.fun < best_coarse_cost:
            best_p_fc = res.x[0]
        else:
            best_p_fc = best_coarse_pfc  # 回退到粗网格最优

        # ── 极端回退：SQP+粗网格都失败 → 全网格搜 ──
        if fallback_grid:
            try_feas = mpc_step_soc(soc_k, best_p_fc, P_load[k])
            if try_feas is None:
                J_best = np.inf
                best_j = None
                for j in range(N_PFC):
                    p_cand = PFC_GRID[j]
                    J = cost_fn_sqp(p_cand, *static_args)
                    if J < J_best:
                        J_best = J
                        best_j = j
                if best_j is not None:
                    best_p_fc = PFC_GRID[best_j]

        # ── 执行 ──
        P_fc[k] = np.clip(best_p_fc, PFC_MIN, PFC_MAX)
        P_bat[k] = P_load[k] - P_fc[k]
        m_H2[k] = fc_hydrogen_flow(P_fc[k]) * DT
        soc_next = mpc_step_soc(soc_k, P_fc[k], P_load[k])
        SOC[k + 1] = soc_k if soc_next is None else soc_next

        t_elapsed = time.perf_counter() - t_start
        step_times.append(t_elapsed)

        if k % 300 == 0:
            print(f'  SQP step {k}/{N}  iters={res.nit:2d}  '
                  f'P_fc={best_p_fc:.2f}  cost={res.fun:.3f}')

    # ── 汇总 ──
    raw_h2_kg = np.cumsum(m_H2)[-1] / 1000
    h2_eq_kg = soc_equivalent_h2(raw_h2_kg, SOC[-1], soc_ref=soc_ref, s_factor=s_factor)
    avg_time = np.mean(step_times) * 1000

    print(f'[MPC-SQP] 完成！H2_raw={raw_h2_kg:.4f} kg, SOC_end={SOC[-1]:.3f}, '
          f'H2_eq={h2_eq_kg:.4f} kg')
    print(f'[MPC-SQP] 平均每步耗时: {avg_time:.1f} ms')

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
        'config': {
            'N_p': N_p,
            's_factor': s_factor,
            'w_soc': w_soc,
            'beta_term': beta_term,
            'soc_deadband': soc_deadband,
            'soc_soft_min': soc_soft_min,
            'w_soc_low': w_soc_low,
            'soc_final_tol': soc_final_tol,
            'w_final_soc': w_final_soc,
            'w_pfc_slew': w_pfc_slew,
            'solver': 'SQP',
            'sqp_maxiter': sqp_maxiter,
        },
    }


# ====================================================================
# 对比可视化：网格 MPC vs SQP MPC vs DP
# ====================================================================
def plot_grid_vs_sqp(t, P_load, grid_result, sqp_result, dp_result,
                     cycle_name='wltc'):
    """Grid MPC vs SQP MPC 一对一对比 + DP 基准"""
    t_min = t / 60
    N = len(t)

    fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True)

    # (1) P_fc 轨迹对比
    ax = axes[0]
    ax.fill_between(t_min, 0, P_load, alpha=0.10, color='gray', label='Load')
    ax.plot(t_min, dp_result['P_fc_kW'], 'g-', linewidth=0.8, alpha=0.6, label='DP (最优基准)')
    ax.plot(t_min, grid_result['P_fc_kW'], 'b-', linewidth=0.8, label=f'Grid MPC  ({grid_result["H2_raw_kg"]:.3f} kg)')
    ax.plot(t_min, sqp_result['P_fc_kW'], 'r-', linewidth=0.8, label=f'SQP MPC  ({sqp_result["H2_raw_kg"]:.3f} kg)')
    ax.set_ylabel('P_fc (kW)')
    ax.legend(fontsize=7, ncol=2)
    ax.grid(True, alpha=0.3)
    ax.set_title(f'{cycle_name.upper()} — Grid MPC vs SQP MPC （DP 基准）')

    # (2) SOC 轨迹对比
    ax = axes[1]
    ax.plot(t_min, dp_result['SOC'], 'g-', linewidth=1.0, alpha=0.6, label='DP')
    ax.plot(t_min, grid_result['SOC'], 'b--', linewidth=1.0, label=f'Grid (SOC_end={grid_result["SOC_end"]:.3f})')
    ax.plot(t_min, sqp_result['SOC'], 'r-', linewidth=1.0, label=f'SQP (SOC_end={sqp_result["SOC_end"]:.3f})')
    ax.axhline(y=SOC_REF, color='gray', linestyle=':', alpha=0.5, label=f'SOC_ref={SOC_REF}')
    ax.set_ylabel('SOC')
    ax.set_ylim(0.2, 0.9)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # (3) 累计氢耗对比
    ax = axes[2]
    ax.plot(t_min, dp_result['m_H2_cumul_kg'], 'g-', linewidth=1.0, alpha=0.6,
            label=f'DP ({dp_result["m_H2_cumul_kg"][-1]:.3f} kg)')
    ax.plot(t_min, grid_result['m_H2_cumul_kg'], 'b--', linewidth=1.0,
            label=f'Grid ({grid_result["m_H2_cumul_kg"][-1]:.3f} kg)')
    ax.plot(t_min, sqp_result['m_H2_cumul_kg'], 'r-', linewidth=1.0,
            label=f'SQP ({sqp_result["m_H2_cumul_kg"][-1]:.3f} kg)')
    ax.set_ylabel('Cumul. H₂ (kg)')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # (4) P_fc 分布直方图
    ax = axes[3]
    bins = np.linspace(PFC_MIN, PFC_MAX, 31)
    ax.hist(dp_result['P_fc_kW'], bins=bins, alpha=0.3, color='g', label='DP')
    ax.hist(grid_result['P_fc_kW'], bins=bins, alpha=0.4, color='b', label='Grid MPC')
    ax.hist(sqp_result['P_fc_kW'], bins=bins, alpha=0.4, color='r', label='SQP MPC')
    ax.set_xlabel('P_fc (kW)')
    ax.set_ylabel('Count')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    png_path = os.path.join(RESULTS_DIR, f'Grid_vs_SQP_{cycle_name}.png')
    plt.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f'[图] {png_path}')
    plt.close()


# ====================================================================
# 主程序
# ====================================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='MPC SQP 求解器对比')
    parser.add_argument('--cycle', choices=['wltc', 'nedc', 'cltc'], default='wltc')
    parser.add_argument('--np', type=int, default=N_P_DEFAULT)
    parser.add_argument('--all', action='store_true', help='跑所有工况')
    args = parser.parse_args()

    cycles = ['wltc', 'nedc', 'cltc'] if args.all else [args.cycle]

    for cycle in cycles:
        print('\n' + '=' * 60)
        print(f'  工况: {cycle.upper()}, N_p={args.np}')
        print('=' * 60)

        # 1. 加载工况
        t, v = load_drive_cycle(cycle)
        P_load = vehicle_power(v, DT)
        N = len(t)
        print(f'  功率范围: {P_load.min():.1f} ~ {P_load.max():.1f} kW')

        # 2. DP 基准
        print(f'\n[1/3] DP 全局最优...')
        from day8_dp_ems import backward_dp, forward_rollout
        J, pi = backward_dp(P_load)
        dp = forward_rollout(P_load, pi)

        # 3. Grid MPC
        print(f'\n[2/3] Grid MPC (N_p={args.np})...')
        # 直接从 mpc_ems_optimized 跑（避免重复 import main）
        from mpc_ems_optimized import mpc_sim as mpc_sim_grid
        mpc_kwargs = {}
        t0 = time.perf_counter()
        grid_res = mpc_sim_grid(P_load, SOC_0=0.6, N_p=args.np, **mpc_kwargs)
        grid_time = time.perf_counter() - t0

        # 4. SQP MPC
        print(f'\n[3/3] SQP MPC (N_p={args.np})...')
        t0 = time.perf_counter()
        sqp_res = mpc_sim_sqp(P_load, SOC_0=0.6, N_p=args.np)
        sqp_time = time.perf_counter() - t0

        # 5. 对比打印
        print('\n' + '=' * 60)
        print(f'  {"指标":<28} {"Grid MPC":>13} {"SQP MPC":>13}')
        print('=' + '-' * 58 + '=')
        rows = [
            ('总氢耗 raw (kg)', f'{grid_res["H2_raw_kg"]:.4f}',
             f'{sqp_res["H2_raw_kg"]:.4f}'),
            ('SOC_end', f'{grid_res["SOC_end"]:.4f}',
             f'{sqp_res["SOC_end"]:.4f}'),
            ('SOC 修正氢耗 (kg)', f'{grid_res["H2_eq_kg"]:.4f}',
             f'{sqp_res["H2_eq_kg"]:.4f}'),
            ('FC 平均效率', f'{grid_res["fc_efficiency"].mean():.2%}',
             f'{sqp_res["fc_efficiency"].mean():.2%}'),
            ('FC 最大功率 (kW)', f'{grid_res["P_fc_kW"].max():.2f}',
             f'{sqp_res["P_fc_kW"].max():.2f}'),
            ('总耗时 (s)', f'{grid_time:.1f}',
             f'{sqp_time:.1f}'),
            ('平均每步 (ms)', f'{grid_time/N*1000:.1f}',
             f'{sqp_time/N*1000:.1f}'),
        ]
        for row in rows:
            print(f'  {row[0]:<28} {row[1]:>13} {row[2]:>13}')
        print('=' + '=' * 58 + '=')

        # 相对 DP 差距
        dp_H2 = dp['m_H2_cumul_kg'][-1]
        dp_H2eq = soc_equivalent_h2(dp_H2, dp['SOC'][-1])
        grid_H2eq = grid_res['H2_eq_kg']
        sqp_H2eq = sqp_res['H2_eq_kg']
        print(f'\n  相对 DP 差距:')
        print(f'    Grid MPC raw: +{(grid_res["H2_raw_kg"] - dp_H2) / dp_H2 * 100:+.2f}%  '
              f'eq: +{(grid_H2eq - dp_H2eq) / dp_H2eq * 100:+.2f}%')
        print(f'    SQP  MPC raw: +{(sqp_res["H2_raw_kg"] - dp_H2) / dp_H2 * 100:+.2f}%  '
              f'eq: +{(sqp_H2eq - dp_H2eq) / dp_H2eq * 100:+.2f}%')

        # 6. 对比图
        plot_grid_vs_sqp(t, P_load, grid_res, sqp_res, dp, cycle)

    print(f'\n[OK] 全部完成！结果保存在 {RESULTS_DIR}/Grid_vs_SQP_*.png')


if __name__ == '__main__':
    main()
