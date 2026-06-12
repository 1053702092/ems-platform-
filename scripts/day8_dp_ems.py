# -*- coding: utf-8 -*-
"""
dp_ems.py — DP 动态规划 EMS 能量管理
功能：后向 DP + 前向 Rollout + 规则控制器对比

用法：
    python scripts/dp_ems.py                    # 跑 WLTC DP 仿真
    python scripts/dp_ems.py --cycle nedc       # 跑 NEDC
    python scripts/dp_ems.py --plot-only        # 只看已有对比图

依赖：numpy, pandas, matplotlib
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

# ====================================================================
# 0. 参数
# ====================================================================
# 车辆参数
MASS = 1500
G = 9.81
F_R = 0.015
RHO = 1.225
CD = 0.32
AREA = 2.2
ETA_DRIVE = 0.90

# 电池参数
Q_BAT = 50          # Ah
V_NOM = 350         # V
R_INT = 0.05        # Ohm
SOC_MIN, SOC_MAX = 0.2, 0.9
SOC_BP = np.array([0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9, 1.0])
OCV_LU = np.array([320, 330, 338, 345, 352, 358, 362, 368, 380])

# FC 参数
PFC_MIN, PFC_MAX = 0, 30       # kW
LHV_H2 = 120e6                 # J/kg
PFC_EFF_BP = np.array([0, 2, 5, 8, 10, 15, 20, 25, 30])
ETA_FC     = np.array([0, 0.28, 0.40, 0.48, 0.50, 0.55, 0.53, 0.48, 0.40])

# DP 网格参数
N_SOC = 150
N_PFC = 60
SOC_REF = 0.6
ALPHA = 100.0        # SOC 维持惩罚系数（值越大 SOC 越稳）
BETA = 10000.0       # 终端 SOC 惩罚系数
DT = 1.0             # 时间步长 (s)

# ====================================================================
# 1. FC 氢耗模型
# ====================================================================
def fc_efficiency(P_fc):
    """FC 效率曲线查表 插值"""
    return np.interp(P_fc, PFC_EFF_BP, ETA_FC)

def fc_hydrogen_flow(P_fc):
    """
    P_fc : float or array (kW)
    return: mdot_H2 (g/s)   
    氢气流速计算
    """
    is_scalar = np.isscalar(P_fc)
    P_fc = np.atleast_1d(np.asarray(P_fc, dtype=float))
    eta = fc_efficiency(P_fc)
    with np.errstate(divide='ignore', invalid='ignore'):
        mdot = P_fc * 1000 / (eta * LHV_H2) * 1000
    mdot[~np.isfinite(mdot)] = 0
    mdot[P_fc == 0] = 0
    return float(mdot[0]) if is_scalar else mdot

# ====================================================================
# 2. 车辆动力学 & 电池模型（从 run_ems_simulation.py 移植）
# ====================================================================
def vehicle_power(v_kmh, dt=1.0):
    """车速 -> 功率需求 [kW]
    •v_ms = v_kmh / 3.6 — 车速单位换算，km/h 转 m/s
    •中心差分求加速度：a[k] = (v[k+1] - v[k-1]) / (2×dt)，比前后向差分更精确
    •np.clip(a, -3, 3) — 加速度限幅，防止噪声导致不合理的加速度值
    •nF_rr/F_aero/F_inertia — 三力模型：滚动阻力+空气阻力+惯性力
    •P_load = max(P_wheel / η / 1000, 0) — 传动效率折算后取正（无再生制动）
    •v < 0.5 km/h 时功率归零 — 停车状态下功率需求为 0
    """
    v_ms = v_kmh / 3.6
    a = np.zeros_like(v_ms)
    a[1:-1] = (v_ms[2:] - v_ms[:-2]) / (2 * dt)
    a[0] = (v_ms[1] - v_ms[0]) / dt
    a[-1] = (v_ms[-1] - v_ms[-2]) / dt
    a = np.clip(a, -3, 3)
    F_rr = MASS * G * F_R
    F_aero = 0.5 * RHO * CD * AREA * v_ms ** 2
    F_inertia = MASS * a
    P_wheel = (F_rr + F_aero + F_inertia) * v_ms
    P_load = np.maximum(P_wheel / ETA_DRIVE / 1000, 0)
    P_load[v_kmh < 0.5] = 0
    return P_load

def state_transition(SOC_k, P_fc, P_load_k, dt=1.0):
    """
    单步状态转移（标量或向量）
    SOC_k: float, P_fc: array, P_load_k: float
    return: SOC_{k+1} (同 P_fc 形状)，clip 到 [SOC_MIN, SOC_MAX]
    电池soc的变化，判断当前soc值是否需要更新怎么更新
    """
    is_scalar = np.isscalar(P_fc)
    P_fc = np.atleast_1d(np.asarray(P_fc, dtype=float))
    P_bat = P_load_k - P_fc
    V_oc = np.interp(SOC_k, SOC_BP, OCV_LU)

    SOC_next = np.full_like(P_fc, SOC_k)  # 默认 SOC 不变
    #两步循环，第一步先判断pbat有没soc更新的必要，然后判断delta看看符合求解规则不
    mask_large = np.abs(P_bat) >= 0.01
    if mask_large.any():
        P_w = P_bat[mask_large] * 1000
        Delta = V_oc**2 - 4 * R_INT * P_w
        valid = Delta >= 0
        valid_indices = np.where(mask_large)[0][valid]
        if len(valid_indices) > 0:
            I = (V_oc - np.sqrt(Delta[valid])) / (2 * R_INT)
            I = np.clip(I, -300, 300)
            SOC_next[valid_indices] = SOC_k - I / (Q_BAT * 3600) * dt
        # Delta<0 的保持默认值 SOC_k（物理上不可行，但数值上可恢复）

    SOC_next = np.clip(SOC_next, SOC_MIN, SOC_MAX)
    return float(SOC_next[0]) if is_scalar else SOC_next

def battery_model_vectorized(P_bat_kW, SOC_init, dt=1.0):
    """向量化电池模型（用于规则控制器对比）"""
    n = len(P_bat_kW)
    SOC = np.zeros(n)
    soc = SOC_init
    for i in range(n):
        V_oc = np.interp(soc, SOC_BP, OCV_LU)
        P_w = P_bat_kW[i] * 1000
        if abs(P_w) < 10:
            I = 0.0
        else:
            Delta = V_oc**2 - 4 * R_INT * P_w
            if Delta < 0:
                # 物理不可行：保持当前 SOC 不变（不重置）
                SOC[i] = soc
                continue
            I = (V_oc - np.sqrt(Delta)) / (2 * R_INT)
            I = np.clip(I, -300, 300)
        soc_change = -I / (Q_BAT * 3600) * dt
        soc = np.clip(soc + soc_change, 0.05, 0.95)
        SOC[i] = soc
    return SOC

# ====================================================================
# 3. 载荷工况数据
# ====================================================================
def load_drive_cycle(name='wltc'):
    csv_map = {'wltc': 'wltc_cycle.csv', 'nedc': 'nedc_cycle.csv', 'cltc': 'cltc_cycle.csv'}
    csv_path = os.path.join(RESULTS_DIR, csv_map.get(name, 'wltc_cycle.csv'))
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f'工况数据未找到: {csv_path}\n请先运行: python scripts/download_drive_cycles.py')
    df = pd.read_csv(csv_path)
    t = df['time'].values
    v = df['speed_kmh'].values
    print(f'[载入] {name.upper()} 工况: {len(t)} 点, {t[-1]:.0f}s')
    return t, v

# ====================================================================
# 4. 后向 DP
# ====================================================================
def backward_dp(P_load, SOC_0=0.6):
    """
    后向 DP（向量化内层循环）
    P_load : array (N,)
    return: J_table, policy_table
    J[k][i] = min_{p_fc} [ g(p_fc) + α×(SOC_next-SOC_ref)² + J[k+1][lookup(SOC_next)] ]
    """
    N = len(P_load) #N=1800
    SOC_GRID = np.linspace(SOC_MIN, SOC_MAX, N_SOC)
    PFC_GRID = np.linspace(PFC_MIN, PFC_MAX, N_PFC)

    J = np.zeros((N + 1, N_SOC))  #J[k][i] = "时刻 k、SOC状态i时，到终点最少还要花多少代价"
    pi = np.zeros((N, N_SOC))  #pi[k][i] = "时刻 k、SOC状态i时，应该输出多少FC功率"

    # 预计算氢耗（PFC_GRID -> H2_flow, 向量化）
    H2_flow_grid = fc_hydrogen_flow(PFC_GRID)  # g/s, shape (N_PFC,)

    # 终端惩罚   偏离soc=0.6受到的惩罚
    J[N, :] = BETA * (SOC_GRID - SOC_0) ** 2

    print(f'[后向 DP] 开始... (N={N}, N_SOC={N_SOC}, N_PFC={N_PFC})')
    for k in range(N - 1, -1, -1):   #总共1800s的工况
        P_load_k = P_load[k]
        J_next_k = J[k + 1, :]

        for i in range(N_SOC):   # 网格数=150
            soc = SOC_GRID[i]

            # 向量化：一次算所有 PFC_GRID 的 SOC_next  一次试完60种FC功率
            SOC_next_all = state_transition(soc, PFC_GRID, P_load_k, DT)

            # 找出可行的控制（SOC_next 在范围内）
            feasible = (SOC_next_all >= SOC_MIN) & (SOC_next_all <= SOC_MAX)
            #feasible 是布尔数组
            if not feasible.any():
                # 没有可行控制 → 此状态不可达，设置无穷大代价
                J[k, i] = np.inf
                pi[k, i] = np.nan
                continue

            # 单步代价：仅氢耗
            g = H2_flow_grid * DT

            # 未来价值：J + SOC 惩罚放 SOC_next 上（即对"控制结果"而非"当前状态"罚）
            J_future = np.interp(SOC_next_all[feasible], SOC_GRID, J_next_k)
            J_future += ALPHA * (SOC_next_all[feasible] - SOC_REF) ** 2

            # 总代价
            total = np.full(N_PFC, np.inf)
            total[feasible] = g[feasible] + J_future #这一时刻 未来的J值已经确定

            # 取最小
            min_idx = np.argmin(total)
            J[k, i] = total[min_idx]
            pi[k, i] = PFC_GRID[min_idx]

        if k % 300 == 0:
            pct = (N - k) / N * 100
            print(f'  DP 后向: k={k}/{N} ({pct:.0f}%)')

    print('[后向 DP] 完成')
    return J, pi

# ====================================================================
# 5. 前向 Rollout
# ====================================================================
def forward_rollout(P_load, pi, SOC_0=0.6):
    """
    前向 Rollout — 查策略表仿真
    return: dict
    """
    N = len(P_load)
    SOC_GRID = np.linspace(SOC_MIN, SOC_MAX, N_SOC)

    SOC = np.zeros(N + 1)
    P_FC = np.zeros(N)
    P_BAT = np.zeros(N)
    M_H2 = np.zeros(N)   # g

    SOC[0] = SOC_0

    print('[前向 Rollout] 开始...')
    for k in range(N):
        pfc = float(np.interp(SOC[k], SOC_GRID, pi[k, :]))
        pfc = np.clip(pfc, PFC_MIN, PFC_MAX)

        pbat = P_load[k] - pfc
        SOC[k + 1] = state_transition(SOC[k], pfc, P_load[k], DT)
        M_H2[k] = fc_hydrogen_flow(pfc) * DT

        P_FC[k] = pfc
        P_BAT[k] = pbat

    print('[前向 Rollout] 完成')
    return {
        'time': np.arange(N),
        'SOC': SOC[:N],
        'P_fc_kW': P_FC,
        'P_bat_kW': P_BAT,
        'm_H2_g': M_H2,
        'm_H2_cumul_kg': np.cumsum(M_H2) / 1000,
    }

# ====================================================================
# 6. 规则控制器（用于对比）
# ====================================================================
def run_rule_controller(P_load, SOC_0=0.6):
    """运行规则控制器，返回仿真结果 dict"""
    params = {
        'P_fc_min': 3, 'P_fc_max': 25, 'P_fc_peak': 30,
        'SOC_min': 0.3, 'SOC_low': 0.4, 'SOC_high': 0.8, 'SOC_max': 0.9,
    }
    p = params
    N = len(P_load)

    P_fc = np.zeros(N)
    soc = SOC_0
    SOC = np.zeros(N)
    M_H2 = np.zeros(N)

    for k in range(N):
        pl = P_load[k]

        if pl < 1.0:
            if soc < p['SOC_max']:
                P_fc[k] = p['P_fc_min']
            else:
                P_fc[k] = 0
        elif soc < p['SOC_low']:
            charge_pwr = max(0, 1.0 - soc / p['SOC_low']) * 10
            P_fc[k] = min(max(pl + charge_pwr, p['P_fc_min']), p['P_fc_max'])
        elif soc > p['SOC_high']:
            P_fc[k] = max(pl - 10, p['P_fc_min'])
            P_fc[k] = min(P_fc[k], p['P_fc_max'])
        else:
            if pl <= p['P_fc_min']:
                P_fc[k] = p['P_fc_min']
            elif pl <= p['P_fc_max']:
                P_fc[k] = pl
            else:
                P_fc[k] = p['P_fc_max']

        P_bat_k = pl - P_fc[k]
        soc = state_transition(soc, P_fc[k], pl, DT)
        M_H2[k] = fc_hydrogen_flow(P_fc[k]) * DT
        SOC[k] = soc

    return {
        'time': np.arange(N),
        'SOC': SOC,
        'P_fc_kW': P_fc,
        'P_bat_kW': pl - P_fc,
        'm_H2_g': M_H2,
        'm_H2_cumul_kg': np.cumsum(M_H2) / 1000,
    }

# ====================================================================
# 7. 对比图
# ====================================================================
def plot_comparison(t, v, P_load, rule, dp, cycle_name='wltc'):
    """规则 vs DP 五合一对比图"""
    t_min = t / 60  # s -> min

    fig, axes = plt.subplots(5, 1, figsize=(14, 12), sharex=True)

    # (1) 速度 + SOC 对比
    ax = axes[0]
    ax.plot(t_min, v, 'b-', linewidth=0.8, alpha=0.5, label='Speed (km/h)')
    ax.set_ylabel('Speed (km/h)', color='b')
    ax2 = ax.twinx()
    ax2.plot(t_min, rule['SOC'], 'orange', linewidth=0.8, linestyle='--', label='Rule SOC')
    ax2.plot(t_min, dp['SOC'], 'g-', linewidth=1.2, label='DP SOC')
    ax2.set_ylabel('SOC')
    ax2.set_ylim(0.2, 0.9)
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=8, ncol=3)
    ax.set_title(f'{cycle_name.upper()} Drive Cycle — Rule vs DP Comparison')
    ax.grid(True, alpha=0.3)

    # (2) 功率分配对比
    ax = axes[1]
    ax.fill_between(t_min, 0, P_load, alpha=0.15, color='gray', label='Load')
    ax.plot(t_min, rule['P_fc_kW'], 'orange', linewidth=0.8, linestyle='--', label='Rule FC')
    ax.plot(t_min, dp['P_fc_kW'], 'r-', linewidth=1.0, label='DP FC')
    ax.fill_between(t_min, 0, dp['P_bat_kW'], where=dp['P_bat_kW'] > 0,
                    alpha=0.3, color='green', label='DP Bat Discharge')
    ax.fill_between(t_min, 0, dp['P_bat_kW'], where=dp['P_bat_kW'] < 0,
                    alpha=0.3, color='orange', label='DP Bat Charge')
    ax.set_ylabel('Power (kW)')
    ax.legend(loc='upper right', fontsize=7, ncol=4)
    ax.grid(True, alpha=0.3)

    # (3) SOC 对比
    ax = axes[2]
    ax.plot(t_min, rule['SOC'], 'orange', linewidth=1.0, linestyle='--', label='Rule')
    ax.plot(t_min, dp['SOC'], 'g-', linewidth=1.2, label='DP')
    ax.axhline(y=SOC_REF, color='gray', linestyle=':', alpha=0.5, label=f'SOC_ref={SOC_REF}')
    ax.set_ylabel('SOC')
    ax.set_ylim(0.2, 0.9)
    ax.legend(loc='lower right', fontsize=8)
    ax.grid(True, alpha=0.3)

    # (4) 累计氢耗对比
    ax = axes[3]
    ax.plot(t_min, rule['m_H2_cumul_kg'], 'orange', linewidth=1.0, linestyle='--', label=f'Rule ({rule["m_H2_cumul_kg"][-1]:.3f} kg)')
    ax.plot(t_min, dp['m_H2_cumul_kg'], 'g-', linewidth=1.2, label=f'DP ({dp["m_H2_cumul_kg"][-1]:.3f} kg)')
    ax.set_ylabel('Cumul. H₂ (kg)')
    ax.legend(loc='upper left', fontsize=8)
    ax.grid(True, alpha=0.3)

    # (5) FC 效率分布直方图
    ax = axes[4]
    rule_eff = fc_efficiency(rule['P_fc_kW'])
    dp_eff = fc_efficiency(dp['P_fc_kW'])
    bins = np.linspace(0, 0.6, 25)
    ax.hist(rule_eff, bins=bins, alpha=0.5, color='orange', label=f'Rule (mean={rule_eff.mean():.1%})')
    ax.hist(dp_eff, bins=bins, alpha=0.5, color='green', label=f'DP (mean={dp_eff.mean():.1%})')
    ax.set_xlabel('FC Efficiency')
    ax.set_ylabel('Count')
    ax.legend(loc='upper right', fontsize=8)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    png_path = os.path.join(RESULTS_DIR, f'DP_vs_Rule_{cycle_name}.png')
    plt.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f'[图] {png_path}')
    plt.close()

# ====================================================================
# 8. 主程序
# ====================================================================
def print_metrics(rule, dp, P_load):
    """打印对比指标"""
    print()
    print('=' * 60)
    print(f'  {"指标":<25} {"规则控制器":>12} {"DP":>12} {"改善":>10}')
    print('=' * 60)

    rule_H2 = rule['m_H2_cumul_kg'][-1]
    dp_H2 = dp['m_H2_cumul_kg'][-1]
    impr_H2 = (rule_H2 - dp_H2) / rule_H2 * 100

    rule_SOC_end = rule['SOC'][-1]
    dp_SOC_end = dp['SOC'][-1]

    rule_eff = fc_efficiency(rule['P_fc_kW'])
    dp_eff = fc_efficiency(dp['P_fc_kW'])

    rows = [
        ('总氢耗 (kg)', f'{rule_H2:.4f}', f'{dp_H2:.4f}', f'{impr_H2:.1f}%'),
        ('SOC 初值→终值', f'0.60→{rule_SOC_end:.3f}', f'0.60→{dp_SOC_end:.3f}', '—'),
        ('FC 平均效率', f'{rule_eff.mean():.1%}', f'{dp_eff.mean():.1%}', f'{(dp_eff.mean()-rule_eff.mean())*100:.1f}pp'),
        ('FC 最大功率 (kW)', f'{rule["P_fc_kW"].max():.1f}', f'{dp["P_fc_kW"].max():.1f}', '—'),
        ('总能量需求 (kWh)', f'{np.trapezoid(P_load, dx=DT)/3600:.2f}', '', ''),
    ]

    for name, r, d, im in rows:
        print(f'  {name:<25} {r:>12} {d:>12} {im:>10}')
    print('=' * 60)
    print()

def load_rule_results(cycle_name):
    """加载已有规则控制器结果"""
    csv_path = os.path.join(RESULTS_DIR, f'Day7_ems_sim_{cycle_name}.csv')
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        return {
            'time': df['time'].values,
            'SOC': df['SOC'].values,
            'P_fc_kW': df['P_fc_kW'].values,
            'P_bat_kW': df['P_bat_kW'].values,
            'm_H2_cumul_kg': np.cumsum(fc_hydrogen_flow(df['P_fc_kW'].values) * DT) / 1000,
        }
    return None

def main():
    parser = argparse.ArgumentParser(description='DP 动态规划 EMS 仿真')
    parser.add_argument('--cycle', choices=['wltc', 'nedc', 'cltc'], default='wltc', help='工况')
    parser.add_argument('--plot-only', action='store_true', help='只看已有结果')
    args = parser.parse_args()

    cycle = args.cycle

    print('=' * 55)
    print('  DP 动态规划 EMS 仿真')
    print(f'  工况: {cycle.upper()}')
    print('=' * 55)

    # 1. 加载工况
    t, v = load_drive_cycle(cycle)
    P_load = vehicle_power(v, DT)
    N = len(t)
    print(f'  功率需求范围: {P_load.min():.1f} ~ {P_load.max():.1f} kW')

    # 2. 后向 DP
    print(f'\n[1/4] 后向 DP (网格: SOC={N_SOC}, P_fc={N_PFC})...')
    J, pi = backward_dp(P_load)

    # 3. 前向 Rollout
    print(f'\n[2/4] 前向 Rollout...')
    dp = forward_rollout(P_load, pi)

    # 4. 规则控制器对比
    print(f'\n[3/4] 运行规则控制器...')
    rule = run_rule_controller(P_load)

    # 5. 指标打印
    print(f'\n[4/4] 对比结果:')
    print_metrics(rule, dp, P_load)

    # 6. 保存 DP 结果
    df_dp = pd.DataFrame({
        'time': dp['time'],
        'speed_kmh': v,
        'P_load_kW': P_load,
        'P_fc_kW': dp['P_fc_kW'],
        'P_bat_kW': dp['P_bat_kW'],
        'SOC': dp['SOC'],
        'm_H2_cumul_kg': dp['m_H2_cumul_kg'],
    })
    csv_path = os.path.join(RESULTS_DIR, f'dp_ems_{cycle}.csv')
    df_dp.to_csv(csv_path, index=False)
    print(f'[保存] {csv_path}')

    # 7. 对比图
    plot_comparison(t, v, P_load, rule, dp, cycle)

    print(f'\n[OK] DP 仿真完成！')
    print(f'   结果: results/dp_ems_{cycle}.csv')
    print(f'   图表: results/DP_vs_Rule_{cycle}.png')


if __name__ == '__main__':
    main()
