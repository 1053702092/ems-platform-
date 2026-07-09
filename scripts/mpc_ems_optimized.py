# -*- coding: utf-8 -*-
"""
mpc_ems_optimized.py — MPC 优化版模型预测控制在燃料电池 EMS 能量管理中的应用
功能：在原 mpc_ems.py 基础上加入 SOC 软约束、终点 SOC 欠差惩罚、FC 功率变化惩罚

用法：
    python scripts/mpc_ems_optimized.py                    # 跑 WLTC 优化版 MPC 仿真
    python scripts/mpc_ems_optimized.py --cycle nedc       # 跑 NEDC
    python scripts/mpc_ems_optimized.py --np 30            # 预测时域 N_p=30
    python scripts/mpc_ems_optimized.py --compare           # MPC vs DP vs ECMS vs Rule 四方法对比

依赖：numpy, pandas, matplotlib
复用：day8_dp_ems.py 的 vehicle_power / state_transition / fc_hydrogen_flow
"""

import os, sys, argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PROJECT_ROOT, 'results')
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, 'scripts')
sys.path.insert(0, SCRIPTS_DIR)

# 从 day8_dp_ems 复用核心组件
from day8_dp_ems import (
    fc_hydrogen_flow, fc_efficiency, vehicle_power, state_transition,
    load_drive_cycle, run_rule_controller,
    SOC_MIN, SOC_MAX, PFC_MIN, PFC_MAX,
    N_SOC, N_PFC, DT, LHV_H2, PFC_EFF_BP, ETA_FC,
    SOC_BP, OCV_LU, Q_BAT, R_INT,
)

# 从 day9_ecms_ems 复用常量
# 注意：N_PFC 在 day8 中表示 DP 网格密度（60），不是 ECMS 网格密度（也是 60）
# 统一用 N_PFC_GRID = 60 表示 P_fc 搜索网格数

# ====================================================================
# MPC 参数
# ====================================================================
N_P_DEFAULT = 50          # 预测时域（prediction horizon）
S_MPC = 130.0             # 等效因子（energy balancing penalty）
W_SOC = 1200.0            # SOC 维持惩罚权重
BETA_TERM = 5000.0        # 滚动终端 SOC 惩罚系数 β
SOC_DEADBAND = 0.015      # SOC_ref 附近的小死区，避免过度抖动
SOC_SOFT_MIN = 0.57       # 软下限：防止靠透支电池换低原始氢耗
W_SOC_LOW = 20000.0       # 低 SOC 软约束惩罚
SOC_FINAL_TOL = 0.01      # 真实工况终点允许的 SOC 欠差
W_FINAL_SOC = 80000.0     # 真实终点 SOC 不足惩罚
W_PFC_SLEW = 0.001        # 燃料电池功率变化惩罚，保护 FC 寿命/抑制跳变
PFC_GRID = np.linspace(PFC_MIN, PFC_MAX, N_PFC)  # 控制搜索网格
SOC_REF = 0.6             # 目标 SOC

# ====================================================================
# 1. 预计算氢耗网格（加速）
# ====================================================================
H2_GRID = fc_hydrogen_flow(PFC_GRID)  # g/s, shape (N_PFC,)


# ====================================================================
# 2. 单步仿真（用于 MPC 预测内循环）
# ====================================================================
def mpc_step_soc(soc_k, p_fc, p_load_k, dt=DT):
    """
    单步 MPC 状态转移（与 day8_dp_ems.state_transition 相同，
    但返回 float 而非 array，避免逐步 array 开销）
    """
    p_bat = p_load_k - p_fc
    v_oc = np.interp(soc_k, SOC_BP, OCV_LU)
    p_w = p_bat * 1000.0

    delta = v_oc ** 2 - 4 * R_INT * p_w
    if delta < 0:
        # 物理不可行：交给上层候选筛选，不能用 clip 掩盖成可行解。
        return None

    i = (v_oc - np.sqrt(delta)) / (2 * R_INT)
    i = np.clip(i, -300, 300)
    soc_next = soc_k - i / (Q_BAT * 3600) * dt
    if not np.isfinite(soc_next) or soc_next < SOC_MIN or soc_next > SOC_MAX:
        return None #数值稳定性检查
    return soc_next


def soc_equivalent_h2(raw_h2_kg, soc_end, soc_ref=SOC_REF, s_factor=S_MPC):
    """
    将终端 SOC 偏差折算成等效氢耗，便于 charge-sustaining 公平比较。

    约定：SOC_end < soc_ref 代表多用了电池能量，应加回等效氢耗；
    SOC_end > soc_ref 代表保留了更多电池能量，等效氢耗可扣减。
    这是报告层面的可比性指标，不替代真实氢耗。 理解成最终氢耗的等效加减
    """
    delta_soc = soc_ref - soc_end
    e_bat_kwh = Q_BAT * np.mean(OCV_LU) * delta_soc / 1000.0
    return raw_h2_kg + s_factor * e_bat_kwh / 1000.0


def soc_tracking_penalty(soc, is_terminal, is_route_end,
                         w_soc=W_SOC, beta_term=BETA_TERM,
                         soc_ref=SOC_REF, soc_deadband=SOC_DEADBAND,
                         soc_soft_min=SOC_SOFT_MIN, w_soc_low=W_SOC_LOW,
                         soc_final_tol=SOC_FINAL_TOL, w_final_soc=W_FINAL_SOC):
    """
    SOC 维持代价。

    设计目标：
    1. 日常滚动窗口内，让 SOC 不要长期低于参考值；
    2. 真实工况终点附近，强制避免用终端 SOC 透支换低原始氢耗；
    3. 保留 deadband，避免控制器为极小 SOC 偏差频繁抖动。
    """
    abs_dev = abs(soc - soc_ref)
    excess = max(abs_dev - soc_deadband, 0.0)
    penalty = w_soc * excess ** 2 * DT

    low_gap = max(soc_soft_min - soc, 0.0)  #soc小于0.57运行
    penalty += w_soc_low * low_gap ** 2 * DT

    if is_terminal:
        penalty += beta_term * excess ** 2

    if is_route_end:
        final_shortfall = max((soc_ref - soc_final_tol) - soc, 0.0)
        penalty += w_final_soc * final_shortfall ** 2

    return penalty


# ====================================================================
# 3. MPC 仿真（网格搜索法）
# ====================================================================
def mpc_sim(P_load, SOC_0=0.6, N_p=N_P_DEFAULT, w_soc=W_SOC,
            beta_term=BETA_TERM, soc_ref=SOC_REF, s_factor=S_MPC,
            soc_deadband=SOC_DEADBAND, soc_soft_min=SOC_SOFT_MIN,
            w_soc_low=W_SOC_LOW, soc_final_tol=SOC_FINAL_TOL,
            w_final_soc=W_FINAL_SOC, w_pfc_slew=W_PFC_SLEW):
    """
    MPC 仿真 — 网格搜索 + receding horizon

    在每个时刻 k：
      1. 取未来 N_p 步的功率预测（已知工况：直接取真实值）
      2. 枚举 P_fc_grid，对每个候选 P_fc 向前仿真 N_p 步
      3. 累计代价 = Σ 氢耗 + 等效电池能量 + SOC软约束 + β_term × 滚动终端惩罚
      4. 选最优 P_fc，执行第一步

    Parameters
    ----------
    P_load : array (N,) — 功率需求 [kW]
    SOC_0  : float — 初始 SOC
    N_p    : int — 预测时域
    w_soc  : float — SOC 维持惩罚权重
    beta_term : float — 终端 SOC 惩罚系数
    s_factor : float — 电池功率等效氢耗因子 [g/kWh]
    soc_soft_min : float — SOC 软下限，低于该值会快速加罚
    w_pfc_slew : float — 燃料电池功率变化惩罚系数

    Returns
    -------
    dict — 仿真结果
    """
    N = len(P_load)
    SOC = np.zeros(N + 1)
    P_fc = np.zeros(N)
    P_bat = np.zeros(N)
    m_H2 = np.zeros(N)

    SOC[0] = SOC_0

    print(f'[MPC] N_p={N_p}, s={s_factor}, w_soc={w_soc}, β_term={beta_term}, '
          f'soft_min={soc_soft_min}, slew={w_pfc_slew}, grid={N_PFC}')
    print(f'[MPC] 开始仿真... ({N} 步)')

    for k in range(N):
        soc_k = SOC[k]

        # ── 预测工况 ──
        horizon = min(N_p, N - k)  #末尾区间取不到np则缩小预测区间
        p_load_pred = P_load[k : k + horizon]

        # ── 枚举所有候选控制 ──
        J_best = np.inf
        best_j = None
        p_fc_prev = P_fc[k - 1] if k > 0 else np.clip(P_load[k], PFC_MIN, PFC_MAX)

        for j in range(N_PFC):
            p_fc_cand = PFC_GRID[j]
            h2_cand = H2_GRID[j]  # g/s

            # 向前仿真 horizon 步
            soc_pred = soc_k
            J_total = 0.0
            J_total += w_pfc_slew * (p_fc_cand - p_fc_prev) ** 2

            for i in range(horizon):
                p_load_i = p_load_pred[i]
                p_bat_i = p_load_i - p_fc_cand

                # 单步氢耗
                J_total += h2_cand * DT

                # ★ 关键修正：等效能量平衡惩罚
                #   MPC 只优化氢耗会导致"过度依赖电池放电"（因为电池不直接烧氢）
                #   必须把电池 SOC 消耗折算成等效氢耗代价
                #   原理：用电 = 以后烧更多氢，等价于 s × |P_bat|/3600 [g/s]
                J_total += s_factor * abs(p_bat_i) / 3600.0 * DT

                # 向前一步 SOC。不可行候选直接剔除，避免边界 clip 带来"免费能量"。
                soc_pred_next = mpc_step_soc(soc_pred, p_fc_cand, p_load_i)
                if soc_pred_next is None:
                    J_total = np.inf
                    break
                soc_pred = soc_pred_next

                # SOC 维持/终端软约束：重点抑制终端 SOC 透支。
                is_terminal = i == horizon - 1
                is_route_end = k + i + 1 >= N
                J_total += soc_tracking_penalty(
                    soc_pred,
                    is_terminal=is_terminal,
                    is_route_end=is_route_end,
                    w_soc=w_soc,
                    beta_term=beta_term,
                    soc_ref=soc_ref,
                    soc_deadband=soc_deadband,
                    soc_soft_min=soc_soft_min,
                    w_soc_low=w_soc_low,
                    soc_final_tol=soc_final_tol,
                    w_final_soc=w_final_soc,
                )

            if J_total < J_best:
                J_best = J_total
                best_j = j

        # ── 执行最优控制的第 1 步 ──
        if best_j is None:
            one_step_feasible = []
            for j, p_fc_cand in enumerate(PFC_GRID):
                soc_next = mpc_step_soc(soc_k, p_fc_cand, P_load[k])
                if soc_next is not None:
                    one_step_feasible.append((abs(soc_next - soc_ref), j))
            if one_step_feasible:
                best_j = min(one_step_feasible)[1]
            else:
                best_j = int(np.argmin(np.abs(PFC_GRID - np.clip(P_load[k], PFC_MIN, PFC_MAX))))

        P_fc[k] = PFC_GRID[best_j]
        P_bat[k] = P_load[k] - P_fc[k]
        m_H2[k] = fc_hydrogen_flow(P_fc[k]) * DT
        soc_next = mpc_step_soc(soc_k, P_fc[k], P_load[k])
        SOC[k + 1] = soc_k if soc_next is None else soc_next

        if k % 300 == 0:
            print(f'  MPC step {k}/{N}')

    # 记录终端 SOC
    raw_h2_kg = np.cumsum(m_H2)[-1] / 1000
    h2_eq_kg = soc_equivalent_h2(raw_h2_kg, SOC[-1], soc_ref=soc_ref, s_factor=s_factor)
    print(f'[MPC] 完成，H2_raw={raw_h2_kg:.4f} kg, SOC_end={SOC[-1]:.3f}, '
          f'H2_eq={h2_eq_kg:.4f} kg')

    # 后处理：计算 FC 效率等
    p_fc_arr = P_fc
    eff_arr = fc_efficiency(p_fc_arr)

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
        },
    }


# ====================================================================
# 4. N_p 敏感性分析
# ====================================================================
def mpc_n_p_scan(P_load, N_p_values=None, SOC_0=0.6, **mpc_kwargs):
    """
    扫描不同 N_p 下的氢耗，分析预测时域的影响

    Parameters
    ----------
    P_load : array (N,)
    N_p_values : list of int — 要扫描的 N_p 值
    Returns
    -------
    DataFrame — N_p, H2_total, SOC_end
    """
    if N_p_values is None:
        N_p_values = [10, 20, 30, 50, 80, 120, 200]

    print(f'\n[MPC N_p 扫描] 范围: {N_p_values}')
    results = []

    for n_p in N_p_values:
        if n_p > len(P_load):
            continue

        res = mpc_sim(P_load, SOC_0=SOC_0, N_p=n_p, **mpc_kwargs)
        results.append({
            'N_p': n_p,
            'H2_kg': res['H2_raw_kg'],
            'SOC_end': res['SOC_end'],
            'H2_eq_kg': res['H2_eq_kg'],
        })
        print(f'  N_p={n_p:4d}: H2={res["H2_raw_kg"]:.4f} kg, '
              f'SOC_end={res["SOC_end"]:.3f}, '
              f'H2_eq={res["H2_eq_kg"]:.4f} kg')

    return pd.DataFrame(results)


# ====================================================================
# 5. 四方法对比可视化
# ====================================================================
def plot_four_way(t, v, P_load, rule, dp, ecms, mpc_result, cycle_name='wltc'):
    """
    四种方法（Rule / DP / ECMS / MPC）五合一对比图

    复用 day8_dp_ems.plot_comparison 的布局风格
    """
    t_min = t / 60

    fig, axes = plt.subplots(5, 1, figsize=(16, 14), sharex=True)

    colors = {'Rule': 'orange', 'DP': 'g', 'ECMS': 'b', 'MPC': 'r'}
    linestyles = {'Rule': '--', 'DP': '-', 'ECMS': '-.', 'MPC': ':'}

    # (1) 速度 + SOC 对比
    ax = axes[0]
    ax.plot(t_min, v, 'b-', linewidth=0.8, alpha=0.4, label='Speed (km/h)')
    ax.set_ylabel('Speed (km/h)', color='b')
    ax2 = ax.twinx()
    for name in ['Rule', 'DP', 'ECMS', 'MPC']:
        r = {'Rule': rule, 'DP': dp, 'ECMS': ecms, 'MPC': mpc_result}[name]
        ls = linestyles[name]
        c = colors[name]
        if ls == '-':
            lw = 1.3
        elif ls == '--':
            lw = 0.8
        else:
            lw = 1.0
        ax2.plot(t_min, r['SOC'], color=c, linewidth=lw, linestyle=ls, label=name)
    ax2.set_ylabel('SOC')
    ax2.set_ylim(0.2, 0.9)
    ax.set_title(f'{cycle_name.upper()} — Rule vs DP vs ECMS vs MPC Comparison')
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=7, ncol=4)
    ax.grid(True, alpha=0.3)

    # (2) 功率分配对比（只画 MPC + DP + Load）
    ax = axes[1]
    ax.fill_between(t_min, 0, P_load, alpha=0.15, color='gray', label='Load')
    ax.plot(t_min, dp['P_fc_kW'], 'g-', linewidth=1.0, label='DP FC')
    ax.plot(t_min, mpc_result['P_fc_kW'], 'r-', linewidth=1.0, label='MPC FC')
    ax.fill_between(t_min, 0, mpc_result['P_bat_kW'],
                    where=mpc_result['P_bat_kW'] > 0,
                    alpha=0.3, color='green', label='MPC Bat Discharge')
    ax.fill_between(t_min, 0, mpc_result['P_bat_kW'],
                    where=mpc_result['P_bat_kW'] < 0,
                    alpha=0.3, color='orange', label='MPC Bat Charge')
    ax.set_ylabel('Power (kW)')
    ax.legend(loc='upper right', fontsize=7, ncol=3)
    ax.grid(True, alpha=0.3)

    # (3) SOC 对比
    ax = axes[2]
    for name in ['Rule', 'DP', 'ECMS', 'MPC']:
        r = {'Rule': rule, 'DP': dp, 'ECMS': ecms, 'MPC': mpc_result}[name]
        ax.plot(t_min, r['SOC'], color=colors[name], linewidth=1.0,
                linestyle=linestyles[name], label=name)
    ax.axhline(y=SOC_REF, color='gray', linestyle=':', alpha=0.5, label=f'SOC_ref={SOC_REF}')
    ax.set_ylabel('SOC')
    ax.set_ylim(0.2, 0.9)
    ax.legend(loc='lower right', fontsize=7)
    ax.grid(True, alpha=0.3)

    # (4) 累计氢耗对比
    ax = axes[3]
    for name in ['Rule', 'DP', 'ECMS', 'MPC']:
        r = {'Rule': rule, 'DP': dp, 'ECMS': ecms, 'MPC': mpc_result}[name]
        h2 = r['m_H2_cumul_kg'][-1]
        ax.plot(t_min, r['m_H2_cumul_kg'], color=colors[name], linewidth=1.0,
                linestyle=linestyles[name], label=f'{name} ({h2:.3f} kg)')
    ax.set_ylabel('Cumul. H₂ (kg)')
    ax.legend(loc='upper left', fontsize=7)
    ax.grid(True, alpha=0.3)

    # (5) FC 效率直方图
    ax = axes[4]
    bins = np.linspace(0, 0.6, 25)
    for name in ['Rule', 'DP', 'ECMS', 'MPC']:
        r = {'Rule': rule, 'DP': dp, 'ECMS': ecms, 'MPC': mpc_result}[name]
        eff = r['fc_efficiency'] if 'fc_efficiency' in r else fc_efficiency(r['P_fc_kW'])
        ax.hist(eff, bins=bins, alpha=0.4, color=colors[name],
                label=f'{name} (mean={eff.mean():.1%})')
    ax.set_xlabel('FC Efficiency')
    ax.set_ylabel('Count')
    ax.legend(loc='upper right', fontsize=7)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    png_path = os.path.join(RESULTS_DIR, f'FourWay_compare_optimized_{cycle_name}.png')
    plt.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f'[图] {png_path}')
    plt.close()


# ====================================================================
# 6. 指标打印
# ====================================================================
def print_four_way_metrics(rule, dp, ecms, mpc_result, P_load):
    """打印四种方法的对比指标"""
    print()
    print('=' * 70)
    print(f'  {"指标":<22} {"规则控制器":>12} {"DP":>12} {"ECMS":>12} {"MPC":>12}')
    print('=' * 70)

    rule_H2 = rule['m_H2_cumul_kg'][-1]
    dp_H2 = dp['m_H2_cumul_kg'][-1]
    ecms_H2 = ecms['m_H2_cumul_kg'][-1]
    mpc_H2 = mpc_result['m_H2_cumul_kg'][-1]

    rule_SOC_end = rule['SOC'][-1]
    dp_SOC_end = dp['SOC'][-1]
    ecms_SOC_end = ecms['SOC'][-1]
    mpc_SOC_end = mpc_result.get('SOC_end', mpc_result['SOC'][-1])
    rule_H2_eq = soc_equivalent_h2(rule_H2, rule_SOC_end)
    dp_H2_eq = soc_equivalent_h2(dp_H2, dp_SOC_end)
    ecms_H2_eq = soc_equivalent_h2(ecms_H2, ecms_SOC_end)
    mpc_H2_eq = soc_equivalent_h2(mpc_H2, mpc_SOC_end)

    rule_eff = fc_efficiency(rule['P_fc_kW'])
    dp_eff = dp.get('fc_efficiency', fc_efficiency(dp['P_fc_kW']))
    ecms_eff = ecms.get('fc_efficiency', fc_efficiency(ecms['P_fc_kW']))
    mpc_eff = mpc_result.get('fc_efficiency', fc_efficiency(mpc_result['P_fc_kW']))

    rows = [
        ('总氢耗 (kg)', f'{rule_H2:.4f}', f'{dp_H2:.4f}', f'{ecms_H2:.4f}', f'{mpc_H2:.4f}'),
        ('SOC 初值→终值', f'0.60→{rule_SOC_end:.3f}', f'0.60→{dp_SOC_end:.3f}',
         f'0.60→{ecms_SOC_end:.3f}', f'0.60→{mpc_SOC_end:.3f}'),
        ('SOC修正氢耗 (kg)', f'{rule_H2_eq:.4f}', f'{dp_H2_eq:.4f}',
         f'{ecms_H2_eq:.4f}', f'{mpc_H2_eq:.4f}'),
        ('FC 平均效率', f'{rule_eff.mean():.1%}', f'{dp_eff.mean():.1%}',
         f'{ecms_eff.mean():.1%}', f'{mpc_eff.mean():.1%}'),
        ('FC 最大功率 (kW)', f'{rule["P_fc_kW"].max():.1f}', f'{dp["P_fc_kW"].max():.1f}',
         f'{ecms["P_fc_kW"].max():.1f}', f'{mpc_result["P_fc_kW"].max():.1f}'),
        ('总能量需求 (kWh)', f'{np.trapezoid(P_load, dx=DT)/3600:.2f}', '', '', ''),
    ]

    for row in rows:
        print(f'  {row[0]:<22} {row[1]:>12} {row[2]:>12} {row[3]:>12} {row[4]:>12}')
    print('=' * 70)
    print()

    # 相对 DP 的差距
    print('  相对 DP 的氢耗差距:')
    print(f'    Rule:  +{(rule_H2 - dp_H2) / dp_H2 * 100:.1f}%')
    print(f'    ECMS:  +{(ecms_H2 - dp_H2) / dp_H2 * 100:.1f}%')
    print(f'    MPC:   +{(mpc_H2 - dp_H2) / dp_H2 * 100:.1f}%')
    print('  相对 DP 的 SOC 修正氢耗差距:')
    print(f'    Rule:  {(rule_H2_eq - dp_H2_eq) / dp_H2_eq * 100:+.1f}%')
    print(f'    ECMS:  {(ecms_H2_eq - dp_H2_eq) / dp_H2_eq * 100:+.1f}%')
    print(f'    MPC:   {(mpc_H2_eq - dp_H2_eq) / dp_H2_eq * 100:+.1f}%')
    print('=' * 70)


# ====================================================================
# 7. N_p 敏感性图
# ====================================================================
def plot_np_sensitivity(np_df, dp_H2, cycle_name='wltc'):
    """绘制 N_p 敏感性曲线"""
    t_min_vals = np.arange(len(np_df))

    fig, ax = plt.subplots(2, 1, figsize=(10, 8), sharex=False)

    # (1) 氢耗 vs N_p
    ax1 = ax[0]
    ax1.plot(np_df['N_p'], np_df['H2_kg'], 'ro-', linewidth=1.5, markersize=6, label='MPC raw')
    if 'H2_eq_kg' in np_df.columns:
        ax1.plot(np_df['N_p'], np_df['H2_eq_kg'], 'mo--', linewidth=1.2, markersize=5, label='MPC SOC-corrected')
    ax1.axhline(y=dp_H2, color='g', linestyle='--', linewidth=1.0, label=f'DP ({dp_H2:.4f} kg)')
    ax1.set_xlabel('N_p (prediction horizon)')
    ax1.set_ylabel('Total H₂ (kg)')
    ax1.set_title(f'{cycle_name.upper()} — MPC N_p Sensitivity')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # (2) SOC_end vs N_p
    ax2 = ax[1]
    ax2.plot(np_df['N_p'], np_df['SOC_end'], 'bo-', linewidth=1.5, markersize=6)
    ax2.axhline(y=SOC_REF, color='gray', linestyle=':', linewidth=1.0, label=f'SOC_ref={SOC_REF}')
    ax2.set_xlabel('N_p (prediction horizon)')
    ax2.set_ylabel('SOC_end')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    png_path = os.path.join(RESULTS_DIR, f'MPC_np_sensitivity_optimized_{cycle_name}.png')
    plt.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f'[图] {png_path}')
    plt.close()


# ====================================================================
# 8. 主程序
# ====================================================================
def main():
    parser = argparse.ArgumentParser(description='MPC 优化版模型预测控制 EMS 仿真')
    parser.add_argument('--cycle', choices=['wltc', 'nedc', 'cltc'], default='wltc')
    parser.add_argument('--np', type=int, default=N_P_DEFAULT, help=f'预测时域 (default: {N_P_DEFAULT})')
    parser.add_argument('--s-factor', type=float, default=S_MPC, help=f'电池功率等效氢耗因子 g/kWh (default: {S_MPC})')
    parser.add_argument('--w-soc', type=float, default=W_SOC, help=f'SOC 维持惩罚权重 (default: {W_SOC})')
    parser.add_argument('--beta-term', type=float, default=BETA_TERM, help=f'滚动终端 SOC 惩罚 (default: {BETA_TERM})')
    parser.add_argument('--soc-soft-min', type=float, default=SOC_SOFT_MIN, help=f'SOC 软下限 (default: {SOC_SOFT_MIN})')
    parser.add_argument('--w-soc-low', type=float, default=W_SOC_LOW, help=f'低 SOC 软约束惩罚 (default: {W_SOC_LOW})')
    parser.add_argument('--soc-final-tol', type=float, default=SOC_FINAL_TOL, help=f'真实终点允许 SOC 欠差 (default: {SOC_FINAL_TOL})')
    parser.add_argument('--w-final-soc', type=float, default=W_FINAL_SOC, help=f'真实终点 SOC 不足惩罚 (default: {W_FINAL_SOC})')
    parser.add_argument('--w-pfc-slew', type=float, default=W_PFC_SLEW, help=f'FC 功率变化惩罚 (default: {W_PFC_SLEW})')
    parser.add_argument('--scan', action='store_true', help='跑 N_p 敏感性扫描')
    parser.add_argument('--compare', action='store_true', help='四方法对比')
    parser.add_argument('--plot-only', action='store_true', help='只看已有结果')
    args = parser.parse_args()

    cycle = args.cycle
    n_p = args.np
    mpc_kwargs = {
        's_factor': args.s_factor,
        'w_soc': args.w_soc,
        'beta_term': args.beta_term,
        'soc_soft_min': args.soc_soft_min,
        'w_soc_low': args.w_soc_low,
        'soc_final_tol': args.soc_final_tol,
        'w_final_soc': args.w_final_soc,
        'w_pfc_slew': args.w_pfc_slew,
    }

    print('=' * 55)
    print('  MPC 优化版模型预测控制 EMS 仿真')
    print(f'  工况: {cycle.upper()}, N_p: {n_p}')
    print('=' * 55)

    # 1. 加载工况
    t, v = load_drive_cycle(cycle)
    P_load = vehicle_power(v, DT)
    N = len(t)
    print(f'  功率需求范围: {P_load.min():.1f} ~ {P_load.max():.1f} kW')

    # 2. 规则控制器（baseline）
    print(f'\n[1/4] 规则控制器...')
    rule = run_rule_controller(P_load)

    # 3. DP（全局最优基准）
    print(f'\n[2/4] DP 后向 Rollout...')
    # 从 day8_dp_ems 直接导入
    sys.path.insert(0, SCRIPTS_DIR)
    from day8_dp_ems import backward_dp, forward_rollout
    J, pi = backward_dp(P_load)
    dp = forward_rollout(P_load, pi)

    # 4. ECMS（作为对比）
    if args.compare:
        print(f'\n[3/4] ECMS (标准 s=130)...')
        from day9_ecms_ems import ecms_sim
        S_FACTOR_DEFAULT = 130.0  # 修正后的最优值
        ecms = ecms_sim(P_load, SOC_0=0.6, s_factor=S_FACTOR_DEFAULT)
        ecms['fc_efficiency'] = fc_efficiency(ecms['P_fc_kW'])
    else:
        ecms = None

    # 5. MPC
    print(f'\n[3/4 if compare else 2/4] MPC (N_p={n_p})...')
    mpc_result = mpc_sim(P_load, SOC_0=0.6, N_p=n_p, **mpc_kwargs)

    # 6. 打印指标
    print(f'\n[4/4] 对比结果:')
    if args.compare and ecms is not None:
        print_four_way_metrics(rule, dp, ecms, mpc_result, P_load)
        # 四方法对比图
        plot_four_way(t, v, P_load, rule, dp, ecms, mpc_result, cycle)
    else:
        # 只画 MPC + DP + Rule
        print()
        print('=' * 55)
        print(f'  {"指标":<22} {"规则控制器":>12} {"DP":>12} {"MPC":>12}')
        print('=' * 55)
        rule_H2 = rule['m_H2_cumul_kg'][-1]
        dp_H2 = dp['m_H2_cumul_kg'][-1]
        mpc_H2 = mpc_result['m_H2_cumul_kg'][-1]
        rows = [
            ('总氢耗 (kg)', f'{rule_H2:.4f}', f'{dp_H2:.4f}', f'{mpc_H2:.4f}'),
            ('SOC 初值→终值', f'0.60→{rule["SOC"][-1]:.3f}', f'0.60→{dp["SOC"][-1]:.3f}', f'0.60→{mpc_result["SOC_end"]:.3f}'),
            ('SOC修正氢耗 (kg)',
             f'{soc_equivalent_h2(rule_H2, rule["SOC"][-1]):.4f}',
             f'{soc_equivalent_h2(dp_H2, dp["SOC"][-1]):.4f}',
             f'{mpc_result["H2_eq_kg"]:.4f}'),
            ('FC 平均效率', f'{fc_efficiency(rule["P_fc_kW"]).mean():.1%}',
             f'{fc_efficiency(dp["P_fc_kW"]).mean():.1%}',
             f'{fc_efficiency(mpc_result["P_fc_kW"]).mean():.1%}'),
        ]
        for row in rows:
            print(f'  {row[0]:<22} {row[1]:>12} {row[2]:>12} {row[3]:>12}')
        print('=' * 55)
        # 三方法对比图
        if not args.plot_only:
            t_min = t / 60
            fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True)
            ax = axes[0]
            ax.plot(t_min, v, 'b-', linewidth=0.8, alpha=0.4, label='Speed')
            ax.set_ylabel('Speed (km/h)')
            ax2 = ax.twinx()
            for name, r, c, ls in [('Rule', rule, 'orange', '--'),
                                     ('DP', dp, 'g', '-'),
                                     ('MPC', mpc_result, 'r', ':')]:
                ax2.plot(t_min, r['SOC'], color=c, linewidth=1.0, linestyle=ls, label=name)
            ax2.set_ylabel('SOC')
            ax2.set_ylim(0.2, 0.9)
            ax.legend(loc='upper right', fontsize=8)
            ax.set_title(f'{cycle.upper()} — Rule vs DP vs MPC')
            ax.grid(True, alpha=0.3)

            ax = axes[1]
            ax.fill_between(t_min, 0, P_load, alpha=0.15, color='gray', label='Load')
            ax.plot(t_min, dp['P_fc_kW'], 'g-', linewidth=1.0, label='DP FC')
            ax.plot(t_min, mpc_result['P_fc_kW'], 'r-', linewidth=1.0, label='MPC FC')
            ax.set_ylabel('Power (kW)')
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)

            ax = axes[2]
            ax.plot(t_min, rule['SOC'], 'orange', linewidth=1.0, linestyle='--', label='Rule')
            ax.plot(t_min, dp['SOC'], 'g-', linewidth=1.0, label='DP')
            ax.plot(t_min, mpc_result['SOC'], 'r-', linewidth=1.0, linestyle=':', label='MPC')
            ax.set_ylabel('SOC')
            ax.set_ylim(0.2, 0.9)
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)

            ax = axes[3]
            for name, r, c, ls in [('Rule', rule, 'orange', '--'),
                                     ('DP', dp, 'g', '-'),
                                     ('MPC', mpc_result, 'r', ':')]:
                h2 = r['m_H2_cumul_kg'][-1]
                ax.plot(t_min, r['m_H2_cumul_kg'], color=c, linewidth=1.0,
                        linestyle=ls, label=f'{name} ({h2:.3f} kg)')
            ax.set_ylabel('Cumul. H₂ (kg)')
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)

            plt.tight_layout()
            png_path = os.path.join(RESULTS_DIR, f'MPC_optimized_vs_DP_Rule_{cycle}_np{n_p}.png')
            plt.savefig(png_path, dpi=150, bbox_inches='tight')
            print(f'[图] {png_path}')
            plt.close()

    # 7. 保存 MPC 结果
    df_mpc = pd.DataFrame({
        'time': mpc_result['time'],
        'speed_kmh': v,
        'P_load_kW': P_load,
        'P_fc_kW': mpc_result['P_fc_kW'],
        'P_bat_kW': mpc_result['P_bat_kW'],
        'SOC': mpc_result['SOC'],
        'm_H2_cumul_kg': mpc_result['m_H2_cumul_kg'],
        'H2_eq_kg': mpc_result['H2_eq_kg'],
    })
    csv_path = os.path.join(RESULTS_DIR, f'mpc_ems_optimized_{cycle}_np{n_p}.csv')
    df_mpc.to_csv(csv_path, index=False)
    print(f'[保存] {csv_path}')

    summary = {
        'cycle': cycle,
        'N_p': n_p,
        'H2_raw_kg': mpc_result['H2_raw_kg'],
        'SOC_end': mpc_result['SOC_end'],
        'SOC_delta_ref_minus_end': SOC_REF - mpc_result['SOC_end'],
        'H2_eq_kg': mpc_result['H2_eq_kg'],
        **mpc_result['config'],
    }
    summary_path = os.path.join(RESULTS_DIR, f'mpc_ems_optimized_{cycle}_np{n_p}_summary.csv')
    pd.DataFrame([summary]).to_csv(summary_path, index=False)
    print(f'[保存] {summary_path}')

    # 8. N_p 敏感性扫描
    if args.scan:
        print(f'\n[MPC N_p 敏感性扫描]')
        np_df = mpc_n_p_scan(P_load, N_p_values=[10, 20, 30, 50, 80, 120, 200], **mpc_kwargs)
        np_df.to_csv(os.path.join(RESULTS_DIR, f'MPC_np_sensitivity_optimized_{cycle}.csv'), index=False)
        plot_np_sensitivity(np_df, dp['m_H2_cumul_kg'][-1], cycle)

    print(f'\n[OK] MPC 仿真完成！')
    print(f'   结果: {csv_path}')


if __name__ == '__main__':
    main()
