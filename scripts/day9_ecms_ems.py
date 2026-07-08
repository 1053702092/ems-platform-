# -*- coding: utf-8 -*-
"""
ecms_ems.py — ECMS 等效消耗最小化策略 EMS 能量管理
功能：标准 ECMS + 自适应 ECMS + 参数扫描 + 与 DP 对比

用法：
    python scripts/ecms_ems.py                    # 跑 WLTC 标准 ECMS
    python scripts/ecms_ems.py --adaptive          # 跑自适应 ECMS
    python scripts/ecms_ems.py --scan              # 参数扫描（s=120~250）
    python scripts/ecms_ems.py --cycle nedc        # 跑 NEDC
    python scripts/ecms_ems.py --compare           # ECMS vs DP vs Rule 三方法对比

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
    N_PFC, DT, LHV_H2, PFC_EFF_BP, ETA_FC,
    SOC_BP, OCV_LU, Q_BAT, R_INT,
    RESULTS_DIR as DP_RESULTS_DIR,
)

# ====================================================================
# ECMS 参数 
# ====================================================================
SOC_REF = 0.6
# ── 标准 ECMS 等效因子（用 abs 修正后，s 在 50-250 范围合理） ──
S_FACTOR_DEFAULT = 160.0    # 基准等效因子 [g/kWh]
S_FACTOR_MIN = 50.0         # 扫描下限
S_FACTOR_MAX = 300.0        # 扫描上限
S_FACTOR_STEP = 10.0        # 扫描步长

# ── A-ECMS 自适应参数 ──
KP_ADAPTIVE = 3.0           # 自适应比例增益（SOC 偏差的反馈强度）
S0_ADAPTIVE = 160.0         # 自适应基准等效因子（≈DP 反推最优值）
S_ADAPTIVE_MIN = 50.0       # 等效因子下限（不等于放电时仍有效）
S_ADAPTIVE_MAX = 350.0      # 等效因子上限

# 终端 SOC 惩罚（辅助 SOC 维持，仅在末端生效）
PENALTY_START_RATIO = 0.7   # 从 70% 步数开始加终端惩罚
PENALTY_COEFF = 500.0       # SOC 偏差惩罚系数

PFC_GRID = np.linspace(PFC_MIN, PFC_MAX, N_PFC)
H2_GRID = fc_hydrogen_flow(PFC_GRID)  # 预计算氢耗网格


# ====================================================================
# 1. 标准 ECMS（恒定等效因子）
# ====================================================================
def ecms_sim(P_load, SOC_0=0.6, s_factor=S_FACTOR_DEFAULT):
    """
    标准 ECMS 仿真 — 恒定等效因子

    Parameters
    ----------
    P_load : array (N,) — 功率需求 [kW]
    SOC_0  : float — 初始 SOC
    s_factor : float — 等效因子 [g/kWh]

    -------
    dict — 仿真结果（SOC, P_fc, P_bat, m_H2, s_history=None）
    """
    N = len(P_load)
    SOC = np.zeros(N + 1)
    P_fc = np.zeros(N)
    P_bat = np.zeros(N)
    m_H2 = np.zeros(N)

    SOC[0] = SOC_0

    for k in range(N):
        # ── 瞬时优化：计算所有候选控制的等效氢耗 ──
        H_fc = H2_GRID                              # 实际氢耗 [g/s]
        P_bat_candidates = P_load[k] - PFC_GRID   
        # 候选电池功率 [kW]（正=放电，负=充电）
        # ★ 修正：用 abs(P_bat) 确保充放电都产生正成本，避免充电时等效氢耗虚假降低
        #   单位：s [g/kWh] × |P_bat| [kW] ÷ 3600 → g/s
        H_eq = H_fc + s_factor * np.abs(P_bat_candidates) / 3600.0
        #s 的单位是 g/kWh，P_bat 的单位是 kW，相乘得 g/h，再除以 3600 得到 g/s。
        # ── SOC 约束筛选（预计算所有候选的下一时刻 SOC）──
        soc_next_all = state_transition(SOC[k], PFC_GRID, P_load[k], DT)

        # ── 终端 SOC 惩罚：后段辅助 SOC 维持 ──
        penalty_start = int(N * PENALTY_START_RATIO) #只在70%之后生效
        if k >= penalty_start:
            # SOC 偏离惩罚：高 SOC 时放电（P_fc 小），低 SOC 时充电（P_fc 大）
            soc_dev = SOC[k] - SOC_REF
            if soc_dev > 0.05:
                # SOC 偏高：额外惩罚大 P_fc（充电会进一步推高 SOC）
                penalty = PENALTY_COEFF * soc_dev**2 * (PFC_GRID / PFC_MAX) / 3600.0
            elif soc_dev < -0.05:
                # SOC 偏低：额外惩罚小 P_fc（放电会进一步拉低 SOC）
                penalty = PENALTY_COEFF * soc_dev**2 * (1 - PFC_GRID / PFC_MAX) / 3600.0
            else:
                penalty = 0.0
            H_eq += penalty

        # SOC 约束筛选
        feasible = [j for j in range(N_PFC)
                    if SOC_MIN + 0.01 <= soc_next_all[j] <= SOC_MAX - 0.01]

        if feasible:
            best_j = min(feasible, key=lambda j: H_eq[j]) #返回Heq最小值对应的key
            P_fc[k] = PFC_GRID[best_j]
        else:
            # 无可行解 fallback：取中点
            P_fc[k] = np.clip(P_load[k] * 0.5, PFC_MIN, PFC_MAX)

        # ── 状态更新 ──
        P_bat[k] = P_load[k] - P_fc[k]
        m_H2[k] = fc_hydrogen_flow(P_fc[k]) * DT
        SOC[k + 1] = state_transition(SOC[k], P_fc[k], P_load[k], DT)

    return {
        'SOC': SOC[:N],
        'P_fc_kW': P_fc,
        'P_bat_kW': P_bat,
        'm_H2_g': m_H2,
        'm_H2_cumul_kg': np.cumsum(m_H2) / 1000,
        's_history': None,  # 标准 ECMS 无自适应历史
    }


# ====================================================================
# 2. 自适应 ECMS（SOC 反馈调整等效因子）
# ====================================================================
def ecms_adaptive(P_load, SOC_0=0.6, s_0=S0_ADAPTIVE, Kp=KP_ADAPTIVE,
                  SOC_ref=SOC_REF, s_min=S_ADAPTIVE_MIN, s_max=S_ADAPTIVE_MAX):
    """
    自适应 ECMS — SOC 反馈调整等效因子

    s(k) = s_0 * (1 + Kp * (SOC_ref - SOC(k)))

    Parameters
    ----------
    P_load  : array (N,)
    SOC_0   : float
    s_0     : float — 基准等效因子 [g/kWh]
    Kp      : float — 自适应强度（SOC_ref - SOC 的系数）
    SOC_ref : float — 目标 SOC
    s_min   : float — 等效因子下限
    s_max   : float — 等效因子上限

    Returns
    -------
    dict — 仿真结果 + s_history
    """
    N = len(P_load)
    SOC = np.zeros(N + 1)
    P_fc = np.zeros(N)
    P_bat = np.zeros(N)
    m_H2 = np.zeros(N)
    s_hist = np.zeros(N)

    SOC[0] = SOC_0

    for k in range(N):
        # ── SOC 反馈自适应等效因子 ──
        s_k = s_0 * (1 + Kp * (SOC_ref - SOC[k]))
        s_k = np.clip(s_k, s_min, s_max)
        s_hist[k] = s_k

        # ── 瞬时优化（同标准 ECMS，但用自适应 s_k） ──
        H_fc = H2_GRID
        P_bat_candidates = P_load[k] - PFC_GRID
        # ★ 用 abs(P_bat) 修正
        H_eq = H_fc + s_k * np.abs(P_bat_candidates) / 3600.0

        # ── SOC 约束筛选（预计算）──
        soc_next_all = state_transition(SOC[k], PFC_GRID, P_load[k], DT)

        # ── 终端 SOC 惩罚 ──
        penalty_start = int(N * PENALTY_START_RATIO)
        if k >= penalty_start:
            soc_dev = SOC[k] - SOC_REF
            if soc_dev > 0.05:
                penalty = PENALTY_COEFF * soc_dev**2 * (PFC_GRID / PFC_MAX) / 3600.0
            elif soc_dev < -0.05:
                penalty = PENALTY_COEFF * soc_dev**2 * (1 - PFC_GRID / PFC_MAX) / 3600.0
            else:
                penalty = 0.0
            H_eq += penalty

        # SOC 约束筛选
        feasible = [j for j in range(N_PFC)
                    if SOC_MIN + 0.01 <= soc_next_all[j] <= SOC_MAX - 0.01]

        if feasible:
            best_j = min(feasible, key=lambda j: H_eq[j])
            P_fc[k] = PFC_GRID[best_j]
        else:  #没有合适的取负载的一半
            P_fc[k] = np.clip(P_load[k] * 0.5, PFC_MIN, PFC_MAX)

        P_bat[k] = P_load[k] - P_fc[k]
        m_H2[k] = fc_hydrogen_flow(P_fc[k]) * DT
        SOC[k + 1] = state_transition(SOC[k], P_fc[k], P_load[k], DT)

    return {
        'SOC': SOC[:N],
        'P_fc_kW': P_fc,
        'P_bat_kW': P_bat,
        'm_H2_g': m_H2,
        'm_H2_cumul_kg': np.cumsum(m_H2) / 1000,
        's_history': s_hist,
    }


# ====================================================================
# 3. 参数扫描 — 找最优等效因子
# ====================================================================
def scan_s_factor(P_load, SOC_0=0.6, cycle_name='wltc'):
    """
    扫描 s ∈ [120, 250]，找最优等效因子

    Returns
    -------
    pd.DataFrame — s 值、氢耗、SOC终值、FC平均效率
    np.arange   隔五个生成一个值一共31个值
    """
    s_values = np.arange(S_FACTOR_MIN, S_FACTOR_MAX + 1, S_FACTOR_STEP)
    results = []

    for s in s_values:
        res = ecms_sim(P_load, SOC_0, s_factor=s)
        eff = fc_efficiency(res['P_fc_kW'])
        results.append({
            's_factor': s,
            'H2_kg': res['m_H2_cumul_kg'][-1],
            'SOC_end': res['SOC'][-1],
            'FC_eff_mean': eff.mean(),
            'FC_eff_gt50': (eff > 0.50).mean(),
        })

    df = pd.DataFrame(results)
    csv_path = os.path.join(RESULTS_DIR, f'ecms_scan_{cycle_name}.csv')
    df.to_csv(csv_path, index=False)
    print(f'[保存] 扫描结果: {csv_path}')
    print_scan_summary(df, cycle_name)
    return df
    #扫描 s 对不同 SOC 的影响，找到氢耗最低且 SOC_end 接近 0.6 的 s。

def print_scan_summary(df, cycle_name='wltc'):
    """打印扫描结果摘要表格"""
    print(f'\n{"="*60}')
    print(f'  ECMS 等效因子扫描结果 — {cycle_name.upper()}')
    print(f'{"="*60}')
    print(f'  {"s(g/kWh)":>10}  {"H2(kg)":>10}  {"SOC_end":>8}  {"FC_eff":>8}  {"FC>50%":>8}')
    print(f'  {"-"*48}')
    for _, r in df.iterrows():
        print(f'  {r["s_factor"]:>10.0f}  {r["H2_kg"]:>10.4f}  {r["SOC_end"]:>8.3f}  '
              f'{r["FC_eff_mean"]:>8.1%}  {r["FC_eff_gt50"]:>7.1%}')
    best = df.loc[df['H2_kg'].idxmin()]
    print(f'  {"-"*48}')
    print(f'  ★ 最优: s={best["s_factor"]:.0f} g/kWh, H2={best["H2_kg"]:.4f} kg, '
          f'SOC_end={best["SOC_end"]:.3f}')
    print(f'{"="*60}\n')


def find_best_s(df):
    """从扫描结果中找最优 s（氢耗最低且 SOC_end ≈ 0.6）"""
    # 先按氢耗排序
    df_sorted = df.sort_values('H2_kg')

    # 在氢耗最低的 5 个中找 SOC_end 最接近 0.6 的
    top5 = df_sorted.head(5)
    top5['soc_dev'] = (top5['SOC_end'] - SOC_REF).abs()
    best = top5.loc[top5['soc_dev'].idxmin()]
    return best


# ====================================================================
# 4. 加载 DP 基准结果
# ====================================================================
def load_dp_results(cycle_name='wltc'):
    """加载已有的 DP 结果 CSV"""
    csv_path = os.path.join(RESULTS_DIR, f'dp_ems_{cycle_name}.csv')
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f'DP 结果未找到: {csv_path}\n请先运行 python scripts/dp_ems.py --cycle {cycle_name}')
    df = pd.read_csv(csv_path)
    return {
        'time': df['time'].values,
        'SOC': df['SOC'].values,
        'P_fc_kW': df['P_fc_kW'].values,
        'P_bat_kW': df['P_bat_kW'].values,
        'm_H2_cumul_kg': df['m_H2_cumul_kg'].values,
    }


def load_rule_results(cycle_name='wltc'):
    """加载已有规则控制器结果"""
    csv_path = os.path.join(RESULTS_DIR, f'Day7_ems_sim_{cycle_name}.csv')
    if not os.path.exists(csv_path):
        return None
    df = pd.read_csv(csv_path)
    return {
        'time': df['time'].values,
        'SOC': df['SOC'].values,
        'P_fc_kW': df['P_fc_kW'].values,
        'P_bat_kW': df['P_bat_kW'].values,
        'm_H2_cumul_kg': np.cumsum(fc_hydrogen_flow(df['P_fc_kW'].values) * DT) / 1000,
    }


# ====================================================================
# 5. 对比图
# ====================================================================
def plot_ecms_comparison(t, v, P_load, rule, dp, ecms, ecms_adp=None,
                         cycle_name='wltc', best_s=None):
    """五合一对比图：Rule vs DP vs ECMS（+ A-ECMS）"""
    t_min = t / 60
    n_panels = 6 if ecms_adp else 5
    fig, axes = plt.subplots(n_panels, 1, figsize=(14, 14), sharex=True)

    def panel_speed_soc(ax):
        ax.plot(t_min, v, 'b-', linewidth=0.8, alpha=0.5, label='Speed')
        ax.set_ylabel('Speed (km/h)', color='b')
        ax2 = ax.twinx()
        if rule:
            ax2.plot(t_min, rule['SOC'], 'orange', lw=0.8, ls='--', label='Rule SOC')
        ax2.plot(t_min, dp['SOC'], 'g-', lw=1.2, label='DP SOC')
        ax2.plot(t_min, ecms['SOC'], 'r-', lw=1.0, ls='-.', label='ECMS SOC')
        if ecms_adp:
            ax2.plot(t_min, ecms_adp['SOC'], 'purple', lw=1.0, ls=':', label='A-ECMS SOC')
        ax2.axhline(y=SOC_REF, color='gray', ls=':', alpha=0.5, label=f'SOC_ref={SOC_REF}')
        ax2.set_ylabel('SOC')
        ax2.set_ylim(0.2, 0.9)
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=7, ncol=3)
        ax.grid(True, alpha=0.3)

    def panel_power(ax):
        ax.fill_between(t_min, 0, P_load, alpha=0.1, color='gray', label='Load')
        if rule:
            ax.plot(t_min, rule['P_fc_kW'], 'orange', lw=0.7, ls='--', label='Rule FC')
        ax.plot(t_min, dp['P_fc_kW'], 'g-', lw=1.0, label='DP FC')
        ax.plot(t_min, ecms['P_fc_kW'], 'r-', lw=1.0, ls='-.', label='ECMS FC')
        if ecms_adp:
            ax.plot(t_min, ecms_adp['P_fc_kW'], 'purple', lw=0.9, ls=':', label='A-ECMS FC')
        ax.fill_between(t_min, 0, ecms['P_bat_kW'], where=ecms['P_bat_kW'] > 0,
                        alpha=0.2, color='green', label='ECMS Bat+')
        ax.fill_between(t_min, 0, ecms['P_bat_kW'], where=ecms['P_bat_kW'] < 0,
                        alpha=0.2, color='orange', label='ECMS Bat-')
        ax.set_ylabel('Power (kW)')
        ax.legend(loc='upper right', fontsize=6, ncol=4)
        ax.grid(True, alpha=0.3)

    def panel_soc_detail(ax):
        if rule:
            ax.plot(t_min, rule['SOC'], 'orange', lw=0.8, ls='--', label='Rule')
        ax.plot(t_min, dp['SOC'], 'g-', lw=1.2, label='DP')
        ax.plot(t_min, ecms['SOC'], 'r-', lw=1.0, ls='-.', label='ECMS')
        if ecms_adp:
            ax.plot(t_min, ecms_adp['SOC'], 'purple', lw=1.0, ls=':', label='A-ECMS')
        ax.axhline(y=SOC_REF, color='gray', ls=':', alpha=0.5)
        ax.set_ylabel('SOC')
        ax.set_ylim(0.2, 0.9)
        ax.legend(loc='lower right', fontsize=7)
        ax.grid(True, alpha=0.3)

    def panel_h2(ax):
        if rule:
            ax.plot(t_min, rule['m_H2_cumul_kg'], 'orange', lw=0.8, ls='--',
                    label=f'Rule ({rule["m_H2_cumul_kg"][-1]:.4f} kg)')
        ax.plot(t_min, dp['m_H2_cumul_kg'], 'g-', lw=1.2,
                label=f'DP ({dp["m_H2_cumul_kg"][-1]:.4f} kg)')
        ax.plot(t_min, ecms['m_H2_cumul_kg'], 'r-', lw=1.0, ls='-.',
                label=f'ECMS ({ecms["m_H2_cumul_kg"][-1]:.4f} kg)')
        if ecms_adp:
            ax.plot(t_min, ecms_adp['m_H2_cumul_kg'], 'purple', lw=1.0, ls=':',
                    label=f'A-ECMS ({ecms_adp["m_H2_cumul_kg"][-1]:.4f} kg)')
        ax.set_ylabel('Cumul. H₂ (kg)')
        ax.legend(loc='upper left', fontsize=7)
        ax.grid(True, alpha=0.3)

    def panel_eff(ax):
        rule_eff = fc_efficiency(rule['P_fc_kW']) if rule else None
        dp_eff = fc_efficiency(dp['P_fc_kW'])
        ecms_eff = fc_efficiency(ecms['P_fc_kW'])
        bins = np.linspace(0, 0.6, 25)
        if rule_eff is not None:
            ax.hist(rule_eff, bins=bins, alpha=0.4, color='orange', label=f'Rule ({rule_eff.mean():.1%})')
        ax.hist(dp_eff, bins=bins, alpha=0.4, color='green', label=f'DP ({dp_eff.mean():.1%})')
        ax.hist(ecms_eff, bins=bins, alpha=0.4, color='red', label=f'ECMS ({ecms_eff.mean():.1%})')
        if ecms_adp:
            adp_eff = fc_efficiency(ecms_adp['P_fc_kW'])
            ax.hist(adp_eff, bins=bins, alpha=0.4, color='purple', label=f'A-ECMS ({adp_eff.mean():.1%})')
        ax.set_xlabel('FC Efficiency')
        ax.set_ylabel('Count')
        ax.legend(loc='upper right', fontsize=7)
        ax.grid(True, alpha=0.3)

    def panel_s_factor(ax):
        """自适应 ECMS 的等效因子变化曲线（仅在 A-ECMS 存在时显示）"""
        if ecms_adp and ecms_adp['s_history'] is not None:
            ax.plot(t_min, ecms_adp['s_history'], 'purple', lw=1.2, label='s(t)')
            ax.axhline(y=S0_ADAPTIVE, color='gray', ls='--', alpha=0.5, label=f's₀={S0_ADAPTIVE}')
            ax.set_ylabel('Equivalence Factor s [g/kWh]')
            ax.set_title('A-ECMS: Adaptive Equivalence Factor')
            ax.legend(loc='upper right', fontsize=7)
            ax.grid(True, alpha=0.3)
        else:
            ax.axis('off')

    panel_speed_soc(axes[0])
    panel_power(axes[1])
    panel_soc_detail(axes[2])
    panel_h2(axes[3])
    panel_eff(axes[4])
    if ecms_adp:
        panel_s_factor(axes[5])

    title = (f'ECMS vs DP vs Rule — {cycle_name.upper()} (s={best_s:.0f} g/kWh)'
             if best_s else f'ECMS vs DP vs Rule — {cycle_name.upper()}')
    fig.suptitle(title, fontsize=14, fontweight='bold', y=0.98)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    png_path = os.path.join(RESULTS_DIR, f'ECMS_compare_{cycle_name}.png')
    plt.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f'[图] {png_path}')
    plt.close()


def plot_s_scan(df, cycle_name='wltc'):
    """等效因子扫描结果图"""
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))

    # 氢耗 vs s
    ax = axes[0]
    ax.plot(df['s_factor'], df['H2_kg'], 'b-o', markersize=3)
    ax.set_xlabel('Equivalence Factor s [g/kWh]')
    ax.set_ylabel('Total H₂ (kg)')
    ax.set_title('Hydrogen Consumption vs s')
    ax.grid(True, alpha=0.3)
    best_idx = df['H2_kg'].idxmin()
    ax.axvline(x=df.loc[best_idx, 's_factor'], color='r', ls='--', alpha=0.5,
               label=f"min at s={df.loc[best_idx, 's_factor']:.0f}")
    ax.legend(fontsize=8)

    # SOC 终值 vs s
    ax = axes[1]
    ax.plot(df['s_factor'], df['SOC_end'], 'g-o', markersize=3)
    ax.axhline(y=SOC_REF, color='gray', ls=':', alpha=0.7, label=f'SOC_ref={SOC_REF}')
    ax.set_xlabel('Equivalence Factor s [g/kWh]')
    ax.set_ylabel('SOC End')
    ax.set_title('SOC End Value vs s')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # FC 效率 vs s
    ax = axes[2]
    ax.plot(df['s_factor'], df['FC_eff_mean'] * 100, 'r-o', markersize=3)  
    ax.set_xlabel('Equivalence Factor s [g/kWh]')
    ax.set_ylabel('FC Avg Efficiency (%)')
    ax.set_title('FC Efficiency vs s')
    ax.grid(True, alpha=0.3)

    plt.suptitle(f'ECMS Parameter Scan — {cycle_name.upper()}', fontsize=12, fontweight='bold')
    plt.tight_layout()
    png_path = os.path.join(RESULTS_DIR, f'ecms_s_scan_{cycle_name}.png')
    plt.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f'[图] {png_path}')
    plt.close()


# ====================================================================
# 6. 指标打印
# ====================================================================
def print_metrics(rule, dp, ecms, ecms_adp=None, P_load=None):
    """打印四方法对比指标"""
    print()
    print('=' * 70)
    header = f'  {"指标":<22} {"Rule":>10} {"DP":>10} {"ECMS":>10}'
    print(header)
    if ecms_adp:
        print(f'  {"":<22} {"":>10} {"":>10} {"A-ECMS":>10}')
    print('-' * 70)

    def get_eff(res):
        return fc_efficiency(res['P_fc_kW'])

    rows = [
        ('总氢耗 (kg)',
         rule['m_H2_cumul_kg'][-1] if rule else np.nan,
         dp['m_H2_cumul_kg'][-1],
         ecms['m_H2_cumul_kg'][-1],
         ecms_adp['m_H2_cumul_kg'][-1] if ecms_adp else np.nan),
        ('SOC 终值',
         rule['SOC'][-1] if rule else np.nan,
         dp['SOC'][-1],
         ecms['SOC'][-1],
         ecms_adp['SOC'][-1] if ecms_adp else np.nan),
        ('FC 平均效率',
         get_eff(rule).mean() if rule else np.nan,
         get_eff(dp).mean(),
         get_eff(ecms).mean(),
         get_eff(ecms_adp).mean() if ecms_adp else np.nan),
        ('FC >50% 占比',
         (get_eff(rule) > 0.50).mean() if rule else np.nan,
         (get_eff(dp) > 0.50).mean(),
         (get_eff(ecms) > 0.50).mean(),
         (get_eff(ecms_adp) > 0.50).mean() if ecms_adp else np.nan),
    ]

    for name, r, d, e, ea in rows:
        fmt = f'  {name:<22} {r:>10.4f} {d:>10.4f} {e:>10.4f}'
        if ecms_adp:
            fmt += f' {ea:>10.4f}'
        print(fmt)
    print('=' * 70)
    print()


# ====================================================================
# 7. 主程序
# ====================================================================
def main():
    parser = argparse.ArgumentParser(description='ECMS 能量管理策略仿真')
    parser.add_argument('--cycle', choices=['wltc', 'nedc', 'cltc'], default='wltc')
    parser.add_argument('--adaptive', action='store_true', help='启用自适应 ECMS')
    parser.add_argument('--scan', action='store_true', help='参数扫描：s ∈ [120, 250]')
    parser.add_argument('--compare', action='store_true', help='ECMS vs DP vs Rule 对比')
    parser.add_argument('--s-factor', type=float, default=S_FACTOR_DEFAULT, help='等效因子值')
    parser.add_argument('--Kp', type=float, default=KP_ADAPTIVE, help='自适应 Kp')
    parser.add_argument('--s0', type=float, default=S0_ADAPTIVE, help='自适应基准 s₀')
    args = parser.parse_args()

    cycle = args.cycle

    print('=' * 55)
    print('  ECMS 等效消耗最小化策略')
    print(f'  工况: {cycle.upper()}')
    if args.adaptive:
        print(f'  模式: 自适应 ECMS (s0={args.s0}, Kp={args.Kp})')
    else:
        print(f'  模式: 标准 ECMS (s={args.s_factor})')
    print('=' * 55)

    # 1. 加载工况
    t, v = load_drive_cycle(cycle)
    P_load = vehicle_power(v, DT)
    N = len(t)
    print(f'  功率需求: {P_load.min():.1f} ~ {P_load.max():.1f} kW')

    # 2. ECMS 仿真
    if args.scan:
        print(f'\n[扫描] s ∈ [{S_FACTOR_MIN}, {S_FACTOR_MAX}], 步长 {S_FACTOR_STEP}...')
        df_scan = scan_s_factor(P_load, cycle_name=cycle)
        best = find_best_s(df_scan)
        print(f'\n[最优] s = {best["s_factor"]:.0f} g/kWh')
        print(f'      氢耗 = {best["H2_kg"]:.4f} kg,  SOC_end = {best["SOC_end"]:.3f}')
        plot_s_scan(df_scan, cycle)

    elif args.compare:
        print(f'\n[对比] 运行三方法...')
        # Rule
        print('  [1/3] 规则控制器...')
        rule = load_rule_results(cycle) or run_rule_controller(P_load)
        # DP
        print('  [2/3] DP...')
        dp = load_dp_results(cycle)
        # ECMS (先用最优 s)
        df_scan = scan_s_factor(P_load, cycle_name=cycle)
        best = find_best_s(df_scan)
        best_s = best['s_factor']
        print(f'  [3/3] ECMS (s={best_s:.0f})...')
        ecms = ecms_sim(P_load, s_factor=best_s)
        # A-ECMS：用命令行 s₀，不依赖扫描最优 s
        s0_use = args.s0 if args.adaptive else best_s
        ecms_adp = ecms_adaptive(P_load, s_0=s0_use, Kp=args.Kp) if args.adaptive else None
        # 打印指标
        print_metrics(rule, dp, ecms, ecms_adp)
        # 绘图
        plot_ecms_comparison(t, v, P_load, rule, dp, ecms, ecms_adp, cycle, best_s)
        # 保存 ECMS 结果
        df_ecms = pd.DataFrame({
            'time': np.arange(N), 'speed_kmh': v, 'P_load_kW': P_load,
            'P_fc_kW': ecms['P_fc_kW'], 'P_bat_kW': ecms['P_bat_kW'],
            'SOC': ecms['SOC'], 'm_H2_cumul_kg': ecms['m_H2_cumul_kg'],
        })
        csv_path = os.path.join(RESULTS_DIR, f'ecms_ems_{cycle}.csv')
        df_ecms.to_csv(csv_path, index=False)
        print(f'[保存] {csv_path}')

    else:
        # 单跑 ECMS
        print(f'\n[仿真] ECMS...')
        ecms = ecms_adaptive(P_load, s_0=args.s0, Kp=args.Kp) if args.adaptive else ecms_sim(P_load, s_factor=args.s_factor)
        eff = fc_efficiency(ecms['P_fc_kW'])
        print(f'  总氢耗: {ecms["m_H2_cumul_kg"][-1]:.4f} kg')
        print(f'  SOC: {ecms["SOC"][0]:.3f} → {ecms["SOC"][-1]:.3f}')
        print(f'  FC 平均效率: {eff.mean():.1%}')
        print(f'  FC >50% 占比: {(eff > 0.50).mean():.1%}')
        # 绘图
        dp = load_dp_results(cycle)
        rule = load_rule_results(cycle)
        plot_ecms_comparison(t, v, P_load, rule, dp, ecms, None, cycle)
        # 保存
        df_ecms = pd.DataFrame({
            'time': np.arange(N), 'speed_kmh': v, 'P_load_kW': P_load,
            'P_fc_kW': ecms['P_fc_kW'], 'P_bat_kW': ecms['P_bat_kW'],
            'SOC': ecms['SOC'], 'm_H2_cumul_kg': ecms['m_H2_cumul_kg'],
        })
        csv_path = os.path.join(RESULTS_DIR, f'ecms_ems_{cycle}.csv')
        df_ecms.to_csv(csv_path, index=False)
        print(f'[保存] {csv_path}')

    print(f'\n[OK] ECMS 仿真完成！')


if __name__ == '__main__':
    main()
