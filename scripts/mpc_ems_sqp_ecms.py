#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mpc_ems_sqp_ecms.py — SQP-ECMS 混合：MPC 框架 + ECMS 目标函数 + SQP 序列优化

标准 ECMS:    瞬时决策，无预测，60 点网格枚举
SQP-ECMS:     N_p 步预测，SQP 序列优化，ECMS 风格目标函数

目标函数（只有三个项，比 MPC 的 8 个权重参数简洁得多）：
  min  Σ [ m_H2(P_fc[i]) + s × |P_bat[i]| / 3600 ]  +  β × (SOC_end - SOC_ref)²

用法：
    python scripts/mpc_ems_sqp_ecms.py                          # WLTC
    python scripts/mpc_ems_sqp_ecms.py --cycle nedc             # NEDC
    python scripts/mpc_ems_sqp_ecms.py --all                    # 全部
    python scripts/mpc_ems_sqp_ecms.py --np 5                   # 更短的预测时域
"""

import os, sys, time
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.optimize import minimize, differential_evolution

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
from mpc_ems_optimized import mpc_step_soc, soc_equivalent_h2
from day9_ecms_ems import S_FACTOR_DEFAULT, S0_ADAPTIVE, KP_ADAPTIVE

SOC_REF = 0.6

# ====================================================================
# SQP-ECMS 代价函数
# ====================================================================
def cost_fn_ecms_seq(control_seq, p_load_pred, soc_k, dt, s_factor, beta_term,
                     p_fc_prev, w_pfc_slew):
    """
    ECMS 风格代价函数（序列版）

    控制序列 u = [P_fc(0), ..., P_fc(N_p-1)]
    代价 = Σ ECMS瞬时代价 + 终端SOC惩罚 + 爬坡惩罚
    """
    control_seq = np.asarray(control_seq)
    horizon = len(control_seq)
    soc_pred = soc_k
    J = 0.0

    for i in range(horizon):
        p_fc_i = control_seq[i]
        p_load_i = p_load_pred[i]
        p_bat_i = p_load_i - p_fc_i
        h2_i = fc_hydrogen_flow(p_fc_i)

        # 爬坡惩罚（上一步→当前步的变化）
        slew_prev = p_fc_prev if i == 0 else control_seq[i - 1]
        J += w_pfc_slew * (p_fc_i - slew_prev) ** 2

        # ECMS 核心：实际氢耗 + 等效氢耗
        J += h2_i * dt
        J += s_factor * abs(p_bat_i) / 3600.0 * dt

        # 状态转移
        soc_pred_next = mpc_step_soc(soc_pred, p_fc_i, p_load_i)
        if soc_pred_next is None:
            return 1e15
        soc_pred = soc_pred_next

    # 终端 SOC 惩罚
    J += beta_term * (soc_pred - SOC_REF) ** 2
    return J


# ====================================================================
# 代价函数 wrapper（用于 minimize 的 lambda 兼容）
# ====================================================================
def make_cost_fn(static_args):
    """返回一个只接受 control_seq 的闭包"""
    def fn(seq):
        return cost_fn_ecms_seq(seq, *static_args)
    return fn


# ====================================================================
# 计算代价函数在某个点的精确梯度（解析-数值混合）
# ====================================================================
def cost_with_grad(control_seq, *static_args):
    """计算代价 + 数值梯度（用于提供 jac 给 SQP，减少迭代次数）"""
    seq = np.asarray(control_seq)
    f0 = cost_fn_ecms_seq(seq, *static_args)
    eps = 0.01
    grad = np.zeros_like(seq)
    for i in range(len(seq)):
        seq_plus = seq.copy()
        seq_plus[i] += eps
        fp = cost_fn_ecms_seq(seq_plus, *static_args)
        grad[i] = (fp - f0) / eps
    return f0, grad


# ====================================================================
# SQP-ECMS 仿真
# ====================================================================
def sqp_ecms_sim(P_load, SOC_0=0.6, N_p=8,
                 s_factor=S0_ADAPTIVE, beta_term=3000.0,
                 w_pfc_slew=0.0005, adaptive=True, Kp=KP_ADAPTIVE,
                 use_gradient=True):
    """
    SQP-ECMS 混合仿真

    参数
    ----------
    N_p : int — 预测时域（短时域 5-10 即可，ECMS 本身是瞬时的）
    s_factor : float — 等效因子基准值 [g/kWh]
    beta_term : float — 终端 SOC 惩罚系数
    adaptive : bool — 是否自适应调整 s
    use_gradient : bool — 是否提供解析梯度给 SQP
    """
    N = len(P_load)
    SOC = np.zeros(N + 1)
    P_fc = np.zeros(N)
    P_bat = np.zeros(N)
    m_H2 = np.zeros(N)
    s_hist = np.zeros(N)

    SOC[0] = SOC_0

    mode = 'adaptive' if adaptive else 'fixed'
    grad_str = '+grad' if use_gradient else ''
    print(f'[SQP-ECMS] N_p={N_p}, s₀={s_factor}, β={beta_term}, mode={mode}{grad_str}')
    print(f'[SQP-ECMS] 开始仿真... ({N} 步)')

    step_times = []

    for k in range(N):
        t_start = time.perf_counter()
        soc_k = SOC[k]
        horizon = min(N_p, N - k)
        p_load_pred = P_load[k: k + horizon]
        p_fc_prev = P_fc[k - 1] if k > 0 else np.clip(P_load[k], PFC_MIN, PFC_MAX)

        # ── 自适应等效因子 ──
        if adaptive:
            s_k = s_factor * (1 + Kp * (SOC_REF - soc_k))
            s_k = np.clip(s_k, 50.0, 350.0)
        else:
            s_k = s_factor
        s_hist[k] = s_k

        # ── 初始猜测 ──
        x0 = np.clip(p_load_pred.copy(), PFC_MIN, PFC_MAX)
        # 更稳定：先跑一个 1D 粗网格找到好的恒定 P_fc
        coarse = np.linspace(PFC_MIN, PFC_MAX, 8)
        J_c = np.array([
            cost_fn_ecms_seq(np.full(horizon, p), p_load_pred, soc_k, DT, s_k,
                             beta_term, p_fc_prev, w_pfc_slew)
            for p in coarse
        ])
        best_const = coarse[J_c.argmin()]
        # 混合：70% 最优恒定 + 30% 负荷跟随
        x0 = 0.7 * np.full(horizon, best_const) + 0.3 * x0

        static_args = (p_load_pred, soc_k, DT, s_k, beta_term, p_fc_prev, w_pfc_slew)

        # ── SQP 求解（提供梯度加速收敛） ──
        if use_gradient:
            res = minimize(
                cost_with_grad, x0, args=static_args,
                method='SLSQP',
                jac=True,  # cost_with_grad 返回 (f, grad)
                bounds=[(PFC_MIN, PFC_MAX)] * horizon,
                options={'maxiter': 60, 'ftol': 1e-10, 'eps': 0.05},
            )
        else:
            res = minimize(
                cost_fn_ecms_seq, x0, args=static_args,
                method='SLSQP',
                bounds=[(PFC_MIN, PFC_MAX)] * horizon,
                options={'maxiter': 60, 'ftol': 1e-10, 'eps': 0.05},
            )

        best_seq = res.x if res.success else x0
        best_p_fc = best_seq[0]

        # ── 执行 ──
        P_fc[k] = np.clip(best_p_fc, PFC_MIN, PFC_MAX)
        P_bat[k] = P_load[k] - P_fc[k]
        m_H2[k] = fc_hydrogen_flow(P_fc[k]) * DT
        soc_next = mpc_step_soc(soc_k, P_fc[k], P_load[k])
        SOC[k + 1] = soc_k if soc_next is None else soc_next

        t_elapsed = time.perf_counter() - t_start
        step_times.append(t_elapsed)

        if k % 300 == 0:
            print(f'  step {k}/{N}  s={s_k:.0f}  P_fc[0]={best_p_fc:.2f}  '
                  f'iters={res.nit:2d}  cost={res.fun:.3f}')

    raw_h2_kg = np.cumsum(m_H2)[-1] / 1000
    h2_eq_kg = soc_equivalent_h2(raw_h2_kg, SOC[-1], soc_ref=SOC_REF, s_factor=s_factor)
    avg_time = np.mean(step_times) * 1000

    print(f'[SQP-ECMS] 完成！H2_raw={raw_h2_kg:.4f} kg, SOC_end={SOC[-1]:.3f}, '
          f'H2_eq={h2_eq_kg:.4f} kg')
    print(f'[SQP-ECMS] 平均每步耗时: {avg_time:.1f} ms')

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
        'fc_efficiency': fc_efficiency(P_fc),
        's_history': s_hist,
        'avg_step_time_ms': avg_time,
        'config': {'N_p': N_p, 's_factor': s_factor,
                   'beta_term': beta_term, 'adaptive': adaptive, 'Kp': Kp},
    }


# ====================================================================
# 标准 ECMS（供对比，从 day9_ecms_ems 直接调用）
# ====================================================================
def run_std_ecms(P_load, s_factor=S0_ADAPTIVE, Kp=KP_ADAPTIVE, adaptive=True):
    if adaptive:
        from day9_ecms_ems import ecms_adaptive
        return ecms_adaptive(P_load, s_0=s_factor, Kp=Kp)
    else:
        from day9_ecms_ems import ecms_sim
        return ecms_sim(P_load, s_factor=s_factor)


# ====================================================================
# 对比图
# ====================================================================
def plot_comparison(t, P_load, dp, ecms, sqp_ecms, cycle_name='wltc'):
    t_min = t / 60
    fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True)

    c = {'DP': 'g', 'A-ECMS': 'orange', 'SQP-ECMS': 'r'}
    ls_ = {'DP': '--', 'A-ECMS': '-.', 'SQP-ECMS': '-'}

    items = [('DP', dp)]
    if ecms: items.append(('A-ECMS', ecms))
    if sqp_ecms: items.append(('SQP-ECMS', sqp_ecms))

    # (1) P_fc
    ax = axes[0]
    ax.fill_between(t_min, 0, P_load, alpha=0.10, color='gray', label='Load')
    for name, res in items:
        h2 = res.get('H2_raw_kg', res['m_H2_cumul_kg'][-1])
        ax.plot(t_min, res['P_fc_kW'], color=c[name], linestyle=ls_[name],
                lw=0.8, label=f'{name} ({h2:.3f} kg)')
    ax.set_ylabel('P_fc (kW)'); ax.legend(fontsize=7, ncol=2); ax.grid(True, alpha=0.3)
    ax.set_title(f'{cycle_name.upper()} — DP vs A-ECMS vs SQP-ECMS')

    # (2) SOC
    ax = axes[1]
    for name, res in items:
        se = res.get('SOC_end', res['SOC'][-1])
        ax.plot(t_min, res['SOC'], color=c[name], linestyle=ls_[name],
                lw=0.8, label=f'{name} (end={se:.3f})')
    ax.axhline(y=SOC_REF, color='gray', ls=':', alpha=0.5)
    ax.set_ylabel('SOC'); ax.set_ylim(0.2, 0.9); ax.legend(fontsize=7); ax.grid(True, alpha=0.3)

    # (3) 累计氢耗
    ax = axes[2]
    for name, res in items:
        ax.plot(t_min, res['m_H2_cumul_kg'], color=c[name], linestyle=ls_[name],
                lw=0.8, label=f'{name} ({res["m_H2_cumul_kg"][-1]:.3f} kg)')
    ax.set_ylabel('Cumul. H₂ (kg)'); ax.legend(fontsize=7); ax.grid(True, alpha=0.3)

    # (4) s 变化（仅 SQP-ECMS）
    ax = axes[3]
    if sqp_ecms and 's_history' in sqp_ecms and sqp_ecms['s_history'] is not None:
        ax.plot(t_min, sqp_ecms['s_history'], 'r-', lw=0.8,
                label=f's(t), mean={sqp_ecms["s_history"].mean():.0f}')
        ax.axhline(y=sqp_ecms['config']['s_factor'], color='gray', ls=':', alpha=0.5)
        ax.set_ylabel('s (g/kWh)'); ax.legend(fontsize=7); ax.set_xlabel('Time (min)')
        ax.grid(True, alpha=0.3)
    else:
        ax.axis('off')

    plt.tight_layout()
    p = os.path.join(RESULTS_DIR, f'DP_AECMS_SQPECMS_{cycle_name}.png')
    plt.savefig(p, dpi=150, bbox_inches='tight'); print(f'[图] {p}'); plt.close()


# ====================================================================
# 主程序
# ====================================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='SQP-ECMS 混合')
    parser.add_argument('--cycle', choices=['wltc', 'nedc', 'cltc'], default='wltc')
    parser.add_argument('--np', type=int, default=8, help='预测时域 (default: 8)')
    parser.add_argument('--s', type=float, default=S0_ADAPTIVE)
    parser.add_argument('--beta', type=float, default=3000.0, help='终端 SOC 惩罚')
    parser.add_argument('--no-adaptive', action='store_true')
    parser.add_argument('--no-gradient', action='store_true', help='不提供梯度')
    parser.add_argument('--all', action='store_true')
    args = parser.parse_args()

    cycles = ['wltc', 'nedc', 'cltc'] if args.all else [args.cycle]

    for cycle in cycles:
        print('\n' + '=' * 60)
        print(f'  工况: {cycle.upper()}, N_p={args.np}')
        print('=' * 60)

        t, v = load_drive_cycle(cycle)
        P_load = vehicle_power(v, DT)

        # DP
        print(f'\n[1/4] DP...')
        from day8_dp_ems import backward_dp, forward_rollout
        J, pi = backward_dp(P_load)
        dp = forward_rollout(P_load, pi)

        # 标准 A-ECMS
        print(f'\n[2/4] A-ECMS 基准...')
        t0 = time.perf_counter()
        ecms = run_std_ecms(P_load, args.s,
                            adaptive=not args.no_adaptive)
        t_ecms = time.perf_counter() - t0

        # SQP-ECMS
        print(f'\n[3/4] SQP-ECMS (N_p={args.np})...')
        t0 = time.perf_counter()
        sqp_e = sqp_ecms_sim(P_load, N_p=args.np, s_factor=args.s,
                              beta_term=args.beta,
                              adaptive=not args.no_adaptive,
                              use_gradient=not args.no_gradient)
        t_sqp = time.perf_counter() - t0

        # 输出
        print('\n' + '=' * 60)
        print(f'  {"指标":<28} {"A-ECMS":>13} {"SQP-ECMS":>13}')
        print('=' + '-' * 54 + '=')
        dp_H2 = dp['m_H2_cumul_kg'][-1]
        rows = [
            ('总氢耗 raw (kg)', f'{ecms["m_H2_cumul_kg"][-1]:.4f}',
             f'{sqp_e["H2_raw_kg"]:.4f}'),
            ('相对 DP 差距', f'{(ecms["m_H2_cumul_kg"][-1]/dp_H2-1)*100:+.2f}%',
             f'{(sqp_e["H2_raw_kg"]/dp_H2-1)*100:+.2f}%'),
            ('SOC_end', f'{ecms["SOC"][-1]:.4f}', f'{sqp_e["SOC_end"]:.4f}'),
            ('SOC 修正氢耗 (kg)', f'{soc_equivalent_h2(ecms["m_H2_cumul_kg"][-1], ecms["SOC"][-1]):.4f}',
             f'{sqp_e["H2_eq_kg"]:.4f}'),
            ('FC 平均效率', f'{fc_efficiency(ecms["P_fc_kW"]).mean():.2%}',
             f'{sqp_e["fc_efficiency"].mean():.2%}'),
            ('总耗时 (s)', f'{t_ecms:.2f}', f'{t_sqp:.1f}'),
        ]
        for r in rows:
            print(f'  {r[0]:<28} {r[1]:>13} {r[2]:>13}')
        print('=' + '=' * 54 + '=')
        print(f'  N_p={args.np}, s₀={args.s}, β={args.beta}')

        plot_comparison(t, P_load, dp, ecms, sqp_e, cycle)

    print(f'\n[OK] 完成！')


if __name__ == '__main__':
    main()
