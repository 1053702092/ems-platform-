# -*- coding: utf-8 -*-
"""
mpc_ems.py — MPC 模型预测控制在燃料电池 EMS 能量管理中的应用
功能：网格搜索 MPC + 已知工况预测 + 与 DP/ECMS/Rule 对比

用法：
    python scripts/mpc_ems.py                    # 跑 WLTC MPC 仿真
    python scripts/mpc_ems.py --cycle nedc       # 跑 NEDC
    python scripts/mpc_ems.py --np 30            # 预测时域 N_p=30
    python scripts/mpc_ems.py --compare           # MPC vs DP vs ECMS vs Rule 四方法对比

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
W_SOC = 500.0             # SOC 维持惩罚权重（终端区域）
BETA_TERM = 1000.0        # 终端 SOC 惩罚系数 β
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
        # 物理不可行：保持当前 SOC（数值恢复）
        return np.clip(soc_k, SOC_MIN, SOC_MAX)

    i = (v_oc - np.sqrt(delta)) / (2 * R_INT)
    i = np.clip(i, -300, 300)
    soc_next = soc_k - i / (Q_BAT * 3600) * dt
    return np.clip(soc_next, SOC_MIN, SOC_MAX)

# ====================================================================
# 3. MPC 仿真（网格搜索法）
# ====================================================================
def mpc_sim(P_load, SOC_0=0.6, N_p=N_P_DEFAULT, w_soc=W_SOC,
            beta_term=BETA_TERM, soc_ref=SOC_REF):
    """
    MPC 仿真 — 网格搜索 + receding horizon

    在每个时刻 k：
      1. 取未来 N_p 步的功率预测（已知工况：直接取真实值）
      2. 枚举 P_fc_grid，对每个候选 P_fc 向前仿真 N_p 步
      3. 累计代价 = Σ 氢耗 + w_soc × Σ SOC惩罚 + β_term × 终端惩罚
      4. 选最优 P_fc，执行第一步

    Parameters
    ----------
    P_load : array (N,) — 功率需求 [kW]
    SOC_0  : float — 初始 SOC
    N_p    : int — 预测时域
    w_soc  : float — SOC 维持惩罚权重
    beta_term : float — 终端 SOC 惩罚系数

    Returns
    -------
    dict — 仿真结果
    """
    N = len(P_load)
    SOC = np.zeros(N + 1)
    P_fc = np.zeros(N)
    P_bat = np.zeros(N)
    m_H2 = np.zeros(N)
    SOC_pred_history = []  # 记录每步的预测 SOC 轨迹（用于分析）

    SOC[0] = SOC_0

    # 终端 SOC 惩罚开始生效的步数（最后 30%）
    penalty_start = int(N * 0.7)

    print(f'[MPC] N_p={N_p}, w_soc={w_soc}, β_term={beta_term}, grid={N_PFC}')
    print(f'[MPC] 开始仿真... ({N} 步)')

    for k in range(N):
        soc_k = SOC[k]

        # ── 预测工况 ──
        horizon = min(N_p, N - k)
        p_load_pred = P_load[k : k + horizon]   #因为已知的工况，预测值变成真实值

        # ── 枚举所有候选控制 ──
        J_best = np.inf
        best_j = 0

        for j in range(N_PFC):
            p_fc_cand = PFC_GRID[j]
            h2_cand = H2_GRID[j]  # g/s

            # 向前仿真 horizon 步
            soc_pred = soc_k
            J_total = 0.0

            for i in range(horizon):
                p_load_i = p_load_pred[i]
                p_bat_i = p_load_i - p_fc_cand #p-fc当前在区间内是恒定不变的

                # 单步氢耗
                J_total += h2_cand * DT

                # ★ 关键修正：等效能量平衡惩罚
                #   MPC 只优化氢耗会导致"过度依赖电池放电"（因为电池不直接烧氢）
                #   必须把电池 SOC 消耗折算成等效氢耗代价
                #   原理：用电 = 以后烧更多氢，等价于 s × |P_bat|/3600 [g/s]
                J_total += S_MPC * abs(p_bat_i) / 3600.0 * DT

                # 向前一步 SOC
                soc_pred = mpc_step_soc(soc_pred, p_fc_cand, p_load_i)

                # SOC 维持惩罚（仅在偏离 > 0.05 时触发）
                soc_dev = soc_pred - soc_ref
                if abs(soc_dev) > 0.05:
                    J_total += W_SOC * soc_dev ** 2 * DT

                # 终端 SOC 惩罚（仅在最后一步）
                if i == horizon - 1 and k >= penalty_start:
                    J_total += beta_term * (soc_pred - soc_ref) ** 2

            if J_total < J_best:
                J_best = J_total
                best_j = j

        # ── 执行最优控制的第 1 步 ──
        P_fc[k] = PFC_GRID[best_j]
        P_bat[k] = P_load[k] - P_fc[k]
        m_H2[k] = fc_hydrogen_flow(P_fc[k]) * DT
        SOC[k + 1] = mpc_step_soc(soc_k, P_fc[k], P_load[k])

        if k % 300 == 0:
            print(f'  MPC step {k}/{N}')

    # 记录终端 SOC
    print(f'[MPC] 完成，SOC_end = {SOC[-1]:.3f}')

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
        'fc_efficiency': eff_arr,
    }

# ====================================================================
# 4. N_p 敏感性分析
# ====================================================================
def mpc_n_p_scan(P_load, N_p_values=None, SOC_0=0.6):
    """
    扫描不同 N_p 下的氢耗，分析预测时域的影响

    Parameters
    ----------
    P_load : array (N,)
    N_p_values : list of int — 要扫描的 N_p 值
    Returns
    -------
    DataFrame — N_p, H2_total, SOC_end
     N_p 敏感性分析揭示了 MPC 的核心权衡：
     更长的预测时域 = 更好的性能 + 更多的计算量。实际应用中需找到"够好"而非"最好"的 N_p。
    """
    if N_p_values is None:
        N_p_values = [10, 20, 30, 50, 80, 120, 200]

    print(f'\n[MPC N_p 扫描] 范围: {N_p_values}')
    results = []

    for n_p in N_p_values:
        if n_p > len(P_load):
            continue

        res = mpc_sim(P_load, SOC_0=SOC_0, N_p=n_p)
        results.append({
            'N_p': n_p,
            'H2_kg': res['m_H2_cumul_kg'][-1],
            'SOC_end': res['SOC_end'],
        })
        print(f'  N_p={n_p:4d}: H2={res["m_H2_cumul_kg"][-1]:.4f} kg, SOC_end={res["SOC_end"]:.3f}')

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
    png_path = os.path.join(RESULTS_DIR, f'FourWay_compare_{cycle_name}.png')
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
    mpc_SOC_end = mpc_result['SOC'][-1]

    rule_eff = fc_efficiency(rule['P_fc_kW'])
    dp_eff = dp.get('fc_efficiency', fc_efficiency(dp['P_fc_kW']))
    ecms_eff = ecms.get('fc_efficiency', fc_efficiency(ecms['P_fc_kW']))
    mpc_eff = mpc_result.get('fc_efficiency', fc_efficiency(mpc_result['P_fc_kW']))

    rows = [
        ('总氢耗 (kg)', f'{rule_H2:.4f}', f'{dp_H2:.4f}', f'{ecms_H2:.4f}', f'{mpc_H2:.4f}'),
        ('SOC 初值→终值', f'0.60→{rule_SOC_end:.3f}', f'0.60→{dp_SOC_end:.3f}',
         f'0.60→{ecms_SOC_end:.3f}', f'0.60→{mpc_SOC_end:.3f}'),
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
    ax1.plot(np_df['N_p'], np_df['H2_kg'], 'ro-', linewidth=1.5, markersize=6)
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
    png_path = os.path.join(RESULTS_DIR, f'MPC_np_sensitivity_{cycle_name}.png')
    plt.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f'[图] {png_path}')
    plt.close()


# ====================================================================
# 8. 主程序
# ====================================================================
def main():
    parser = argparse.ArgumentParser(description='MPC 模型预测控制 EMS 仿真')
    parser.add_argument('--cycle', choices=['wltc', 'nedc', 'cltc'], default='wltc')
    parser.add_argument('--np', type=int, default=N_P_DEFAULT, help=f'预测时域 (default: {N_P_DEFAULT})')
    parser.add_argument('--scan', action='store_true', help='跑 N_p 敏感性扫描')
    parser.add_argument('--compare', action='store_true', help='四方法对比')
    parser.add_argument('--plot-only', action='store_true', help='只看已有结果')
    args = parser.parse_args()

    cycle = args.cycle
    n_p = args.np

    print('=' * 55)
    print('  MPC 模型预测控制 EMS 仿真')
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
    mpc_result = mpc_sim(P_load, SOC_0=0.6, N_p=n_p)

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
            png_path = os.path.join(RESULTS_DIR, f'MPC_vs_DP_Rule_{cycle}_np{n_p}.png')
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
    })
    csv_path = os.path.join(RESULTS_DIR, f'mpc_ems_{cycle}_np{n_p}.csv')
    df_mpc.to_csv(csv_path, index=False)
    print(f'[保存] {csv_path}')

    # 8. N_p 敏感性扫描
    if args.scan:
        print(f'\n[MPC N_p 敏感性扫描]')
        np_df = mpc_n_p_scan(P_load, N_p_values=[10, 20, 30, 50, 80, 120, 200])
        np_df.to_csv(os.path.join(RESULTS_DIR, f'MPC_np_sensitivity_{cycle}.csv'), index=False)
        plot_np_sensitivity(np_df, dp['m_H2_cumul_kg'][-1], cycle)

    print(f'\n[OK] MPC 仿真完成！')
    print(f'   结果: {csv_path}')


if __name__ == '__main__':
    main()
