# -*- coding: utf-8 -*-
"""
┌─────────────────────────────────────────────────────────────┐
│  🏋️  DP 动态规划 — 练习文件                               │
│                                                             │
│  说明：以下 5 个函数的关键部分被挖空，由你来填。             │
│  填完后运行 `python scripts/exercise_day8_dp_ems.py`       │
│  如果结果和 day8_dp_ems.py 一致，就说明你写对了。           │
│                                                             │
│  难度：★★☆☆☆  (1)  fc_hydrogen_flow     ★★☆☆☆          │
│         ★★★☆☆  (2)  state_transition      ★★★☆☆          │
│         ★★★★☆  (3)  backward_dp           ★★★★☆          │
│         ★★★☆☆  (4)  forward_rollout       ★★★☆☆          │
│         ★★☆☆☆  (5)  run_rule_controller   ★★☆☆☆          │
└─────────────────────────────────────────────────────────────┘
"""

import os, sys, argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PROJECT_ROOT, 'results')
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts'))

# ═══════════════════════════════════════════════════════════════
# 0. 参数（已填好，不需要改）
# ═══════════════════════════════════════════════════════════════
MASS = 1500
G = 9.81
F_R = 0.015
RHO = 1.225
CD = 0.32
AREA = 2.2
ETA_DRIVE = 0.90

Q_BAT = 50
V_NOM = 350
R_INT = 0.05
SOC_MIN, SOC_MAX = 0.2, 0.9
SOC_BP = np.array([0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9, 1.0])
OCV_LU = np.array([320, 330, 338, 345, 352, 358, 362, 368, 380])

PFC_MIN, PFC_MAX = 0, 30
LHV_H2 = 120e6
PFC_EFF_BP = np.array([0, 2, 5, 8, 10, 15, 20, 25, 30])
ETA_FC     = np.array([0, 0.28, 0.40, 0.48, 0.50, 0.55, 0.53, 0.48, 0.40])

N_SOC = 150
N_PFC = 60
SOC_REF = 0.6
ALPHA = 100.0
BETA = 10000.0
DT = 1.0


# ═══════════════════════════════════════════════════════════════
# 1. FC 氢耗模型
# ═══════════════════════════════════════════════════════════════

def fc_efficiency(P_fc):
    """FC 效率曲线查表（已填好）"""
    return np.interp(P_fc, PFC_EFF_BP, ETA_FC)


def fc_hydrogen_flow(P_fc):
    """
    ★ 练习 1：FC 功率 → 氢耗 (g/s)

    公式：mdot = P_fc(W) / (效率 × LHV_H2(J/kg)) × 1000(kg→g)

    提示：
      - P_fc 可能是标量（如 3.5）也可能是数组（如 shape(60,)）
      - 先用 np.atleast_1d(np.asarray(P_fc, dtype=float)) 统一转数组
      - 效率查 fc_efficiency()
      - P_fc=0 时效率=0，直接计算会除零 → 结果先设为0
      - 用 np.errstate(divide='ignore', invalid='ignore') 避免警告
      - mdot 中的 nan/inf 值要置为 0
      - 如果输入是标量，返回 float；如果是数组，返回数组

    参考答案：10 行左右
    """
    # ─── 你的代码 ─────────────────────────────────
    is_scalar = np.isscalar(P_fc)
    P_fc = np.atleast_1d(np.asarray(P_fc, dtype=float))
    eta = fc_efficiency(P_fc)
    with np.errstate(divide='ignore', invalid='ignore'):
        mdot = P_fc * 1000 / (eta * LHV_H2) * 1000
    mdot[~np.isfinite(mdot)] = 0
    mdot[P_fc == 0] = 0
    return float(mdot[0]) if is_scalar else mdot
    # ──────────────────────────────────────────────


# ═══════════════════════════════════════════════════════════════
# 2. 车辆动力学 & 电池模型
# ═══════════════════════════════════════════════════════════════

def vehicle_power(v_kmh, dt=1.0):
    """车速→功率需求（已填好，不需要改）"""
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
    ★ 练习 2：电池 SOC 状态转移

    输入：
      SOC_k   : 当前 SOC (float)
      P_fc    : FC 输出功率 (标量或数组)
      P_load_k: 负载需求功率 (float)
      dt      : 时间步长 (s)

    返回：
      SOC_{k+1}，与 P_fc 同形状

    原理：
      P_bat = P_load_k - P_fc           # 电池需求功率（正=放电，负=充电）
      V_oc = f(SOC) 查表
      求解 I:  R_int × I² - V_oc × I + P_bat = 0
        → Delta = V_oc² - 4 × R_int × P_bat
        → I = (V_oc - sqrt(Delta)) / (2 × R_int)   (Delta >= 0 时)
      SOC_next = SOC_k - I / (Q_BAT × 3600) × dt

    提示：
      - 先统一转数组（同练习1的写法）
      - P_bat 很小（绝对值 < 0.01）时可以不处理，SOC 基本不变
      - Delta < 0 时该控制不可行，保持原 SOC
      - 最终 clip 到 [SOC_MIN, SOC_MAX]

    参考答案：15-20 行
    """
    # ─── 你的代码 ─────────────────────────────────
    is_scalar = np.isscalar(P_fc)
    P_fc = np.atleast_1d(np.asarray(P_fc, dtype=float))

    P_bat = P_load_k - P_fc
    V_oc = np.interp(SOC_k, SOC_BP, OCV_LU)

    SOC_next = np.full_like(P_fc, SOC_k)

    mask_large = np.abs(P_bat) >= 0.01
    if mask_large.any():
        P_w = P_bat[mask_large] * 1000  # kW → W
        Delta = V_oc**2 - 4 * R_INT * P_w
        valid = Delta >= 0
        valid_indices = np.where(mask_large)[0][valid]
        if len(valid_indices) > 0:
            I = (V_oc - np.sqrt(Delta[valid])) / (2 * R_INT)
            I = np.clip(I, -300, 300)
            SOC_next[valid_indices] = SOC_k - I / (Q_BAT * 3600) * dt

    SOC_next = np.clip(SOC_next, SOC_MIN, SOC_MAX)
    return float(SOC_next[0]) if is_scalar else SOC_next
    # ──────────────────────────────────────────────



# ═══════════════════════════════════════════════════════════════
# 3. 工况加载
# ═══════════════════════════════════════════════════════════════

def load_drive_cycle(name='wltc'):
    """加载工况数据（已填好，不需要改）"""
    csv_map = {'wltc': 'wltc_cycle.csv', 'nedc': 'nedc_cycle.csv', 'cltc': 'cltc_cycle.csv'}
    csv_path = os.path.join(RESULTS_DIR, csv_map.get(name, 'wltc_cycle.csv'))
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f'工况数据未找到: {csv_path}\n请先运行: python scripts/download_drive_cycles.py')
    df = pd.read_csv(csv_path)
    t = df['time'].values
    v = df['speed_kmh'].values
    print(f'[载入] {name.upper()} 工况: {len(t)} 点, {t[-1]:.0f}s')
    return t, v


# ═══════════════════════════════════════════════════════════════
# 4. ★ 后向 DP（最难的一个）
# ═══════════════════════════════════════════════════════════════

def backward_dp(P_load, SOC_0=0.6):
    """
    ★ 练习 3：后向 DP 主算法

    输入：
      P_load: 功率需求序列，shape (N,)
      SOC_0 : 初始 SOC 参考值

    返回：
      J : 代价表，shape (N+1, N_SOC)
      pi: 策略表，shape (N, N_SOC)

    你要实现的核心逻辑（面试白板版）：
      J[k][i] = min_{p_fc} [ g(p_fc) + α×(SOC_next-SOC_ref)² + J[k+1][lookup(SOC_next)] ]

    提示：
      - SOC_GRID = np.linspace(SOC_MIN, SOC_MAX, N_SOC)
      - PFC_GRID = np.linspace(PFC_MIN, PFC_MAX, N_PFC)
      - 先初始化 J 和 pi 为 0
      - 终端惩罚：J[N, :] = BETA × (SOC_GRID - SOC_0)²
      - 预计算 H2_flow_grid = fc_hydrogen_flow(PFC_GRID)
      - 主循环从 N-1 到 0：
        - 对每个 SOC 状态 i：
          - 用 state_transition 一次算所有 PFC_GRID 的 SOC_next
          - 筛选 feasibility (SOC_MIN <= SOC_next <= SOC_MAX)
          - 对未来代价插值 np.interp(SOC_next[feasible], SOC_GRID, J[k+1])
          - 总代价 = g + SOC惩罚 + 未来代价
          - 取最小，存 J[k,i] 和 pi[k,i]

    参考答案：40-50 行
    """
    # ─── 你的代码 ─────────────────────────────────
    # N = len(P_load)
    # SOC_GRID = np.linspace(SOC_MIN, SOC_MAX, N_SOC)
    # PFC_GRID = np.linspace(PFC_MIN, PFC_MAX, N_PFC)

    # J = np.zeros((N + 1, N_SOC))
    # pi = np.zeros((N, N_SOC))

    # 预计算氢耗
    # H2_flow_grid = ???

    # 终端惩罚
    # J[N, :] = ???

    # 后向遍历
    # for k in range(N-1, -1, -1):
    #     P_load_k = P_load[k]
    #     J_next_k = J[k+1, :]

    #     for i in range(N_SOC):
    #         soc = SOC_GRID[i]
    #         1) 算所有PFC_GRID的SOC_next
    #         2) 找可行控制
    #         3) 未来代价插值 + SOC惩罚
    #         4) 总代价取最小

    # return J, pi
    # ──────────────────────────────────────────────
    pass  # 删掉这行


# ═══════════════════════════════════════════════════════════════
# 5. 前向 Rollout
# ═══════════════════════════════════════════════════════════════

def forward_rollout(P_load, pi, SOC_0=0.6):
    """
    ★ 练习 4：前向 Rollout — 查策略表仿真

    输入：
      P_load: 功率需求，shape (N,)
      pi    : 策略表，shape (N, N_SOC)
      SOC_0 : 初始 SOC

    返回：dict，包含
      time, SOC, P_fc_kW, P_bat_kW, m_H2_g, m_H2_cumul_kg

    提示：
      SOC_GRID = np.linspace(SOC_MIN, SOC_MAX, N_SOC)
      对每个时刻 k：
        pfc = np.interp(SOC[k], SOC_GRID, pi[k, :])   # 查表
        pfc = np.clip(pfc, PFC_MIN, PFC_MAX)
        SOC[k+1] = state_transition(SOC[k], pfc, P_load[k])
        M_H2[k] = fc_hydrogen_flow(pfc) * DT

    参考答案：25-30 行
    """
    # ─── 你的代码 ─────────────────────────────────
    N = len(P_load)
    SOC_GRID = np.linspace(SOC_MIN, SOC_MAX, N_SOC)

    SOC = np.zeros(N + 1)
    P_FC = np.zeros(N)
    P_BAT = np.zeros(N)
    M_H2 = np.zeros(N)

    SOC[0] = SOC_0

    for k in range(N):
      pfc = float (np.interp(SOC[k], SOC_GRID, pi[k, :]))
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

  

# ═══════════════════════════════════════════════════════════════
# 6. ★ 规则控制器
# ═══════════════════════════════════════════════════════════════

def run_rule_controller(P_load, SOC_0=0.6):
    """
    ★ 练习 5：规则控制器

    输入：P_load（功率需求），SOC_0（初始 SOC）
    返回：同 forward_rollout 的 dict 格式

    规则逻辑：
      如果 P_load < 1kW：
        如果 SOC < 0.9:  FC = 3kW（最小功率充电）
        否则:            FC = 0（SOC满了，关FC）
      否则如果 SOC < 0.4（过低）：
        额外充电功率 = (1 - SOC/0.4) × 10
        FC = min(max(P_load + 充电功率, 3), 25)
      否则如果 SOC > 0.8（过高）：
        FC = max(P_load - 10, 3)，限制 ≤ 25
      否则（正常范围）：
        FC = clip(P_load, 3, 25)  # 跟随负载

    提示：和 forward_rollout 结构类似，但 pfc 由规则决定而非查表

    参考答案：30-40 行
    """
    # ─── 你的代码 ─────────────────────────────────
    # params = {'P_fc_min': 3, 'P_fc_max': 25, ...}
    # N = len(P_load)
    # P_fc = np.zeros(N)
    # soc = SOC_0
    # SOC = np.zeros(N)
    # M_H2 = np.zeros(N)

    # for k in range(N):
    #     pl = P_load[k]
    #     if pl < 1.0: ...
    #     elif soc < 0.4: ...
    #     elif soc > 0.8: ...
    #     else: ...
    #     SOC[k] = soc（更新后的值）
    #     M_H2[k] = fc_hydrogen_flow(P_fc[k]) * DT

    # return {...}
    # ──────────────────────────────────────────────
    pass  # 删掉这行


# ═══════════════════════════════════════════════════════════════
# 以下代码已填好，不需要改 — 用来验证你的答案
# ═══════════════════════════════════════════════════════════════

def print_metrics(rule, dp, P_load):
    print('\n' + '='*60)
    print(f'  {"指标":<25} {"规则控制器":>12} {"DP":>12} {"改善":>10}')
    print('='*60)
    rule_H2 = rule['m_H2_cumul_kg'][-1]
    dp_H2 = dp['m_H2_cumul_kg'][-1]
    impr_H2 = (rule_H2 - dp_H2) / rule_H2 * 100
    rule_eff = fc_efficiency(rule['P_fc_kW'])
    dp_eff = fc_efficiency(dp['P_fc_kW'])
    rows = [
        ('总氢耗 (kg)', f'{rule_H2:.4f}', f'{dp_H2:.4f}', f'{impr_H2:.1f}%'),
        ('SOC 初值→终值', f'0.60→{rule["SOC"][-1]:.3f}', f'0.60→{dp["SOC"][-1]:.3f}', '—'),
        ('FC 平均效率', f'{rule_eff.mean():.1%}', f'{dp_eff.mean():.1%}', f'{(dp_eff.mean()-rule_eff.mean())*100:.1f}pp'),
        ('FC >50% 占比', f'{(rule_eff>0.50).mean():.1%}', f'{(dp_eff>0.50).mean():.1%}', f'+{((dp_eff>0.50).mean()-(rule_eff>0.50).mean())*100:.1f}pp'),
        ('FC 最大功率 (kW)', f'{rule["P_fc_kW"].max():.1f}', f'{dp["P_fc_kW"].max():.1f}', '—'),
    ]
    for name, r, d, im in rows:
        print(f'  {name:<25} {r:>12} {d:>12} {im:>10}')
    print('='*60 + '\n')

def plot_comparison(t, v, P_load, rule, dp, cycle_name='wltc'):
    t_min = t / 60
    fig, axes = plt.subplots(5, 1, figsize=(14, 12), sharex=True)
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
    ax = axes[1]
    ax.fill_between(t_min, 0, P_load, alpha=0.15, color='gray', label='Load')
    ax.plot(t_min, rule['P_fc_kW'], 'orange', linewidth=0.8, linestyle='--', label='Rule FC')
    ax.plot(t_min, dp['P_fc_kW'], 'r-', linewidth=1.0, label='DP FC')
    ax.fill_between(t_min, 0, dp['P_bat_kW'], where=dp['P_bat_kW'] > 0, alpha=0.3, color='green', label='DP Bat Discharge')
    ax.fill_between(t_min, 0, dp['P_bat_kW'], where=dp['P_bat_kW'] < 0, alpha=0.3, color='orange', label='DP Bat Charge')
    ax.set_ylabel('Power (kW)')
    ax.legend(loc='upper right', fontsize=7, ncol=4)
    ax.grid(True, alpha=0.3)
    ax = axes[2]
    ax.plot(t_min, rule['SOC'], 'orange', linewidth=1.0, linestyle='--', label='Rule')
    ax.plot(t_min, dp['SOC'], 'g-', linewidth=1.2, label='DP')
    ax.axhline(y=SOC_REF, color='gray', linestyle=':', alpha=0.5, label=f'SOC_ref={SOC_REF}')
    ax.set_ylabel('SOC')
    ax.set_ylim(0.2, 0.9)
    ax.legend(loc='lower right', fontsize=8)
    ax.grid(True, alpha=0.3)
    ax = axes[3]
    ax.plot(t_min, rule['m_H2_cumul_kg'], 'orange', linewidth=1.0, linestyle='--', label=f'Rule ({rule["m_H2_cumul_kg"][-1]:.3f} kg)')
    ax.plot(t_min, dp['m_H2_cumul_kg'], 'g-', linewidth=1.2, label=f'DP ({dp["m_H2_cumul_kg"][-1]:.3f} kg)')
    ax.set_ylabel('Cumul. H₂ (kg)')
    ax.legend(loc='upper left', fontsize=8)
    ax.grid(True, alpha=0.3)
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

def save_results(dp, v, P_load, cycle):
    df_dp = pd.DataFrame({
        'time': dp['time'], 'speed_kmh': v, 'P_load_kW': P_load,
        'P_fc_kW': dp['P_fc_kW'], 'P_bat_kW': dp['P_bat_kW'],
        'SOC': dp['SOC'], 'm_H2_cumul_kg': dp['m_H2_cumul_kg'],
    })
    csv_path = os.path.join(RESULTS_DIR, f'dp_ems_{cycle}.csv')
    df_dp.to_csv(csv_path, index=False)
    print(f'[保存] {csv_path}')

def main():
    parser = argparse.ArgumentParser(description='DP 动态规划 EMS — 练习版')
    parser.add_argument('--cycle', choices=['wltc', 'nedc'], default='wltc', help='工况')
    parser.add_argument('--check', action='store_true', help='和参考答案对比')
    args = parser.parse_args()
    cycle = args.cycle

    print('=' * 55)
    print('  🏋️  DP 动态规划 — 练习版')
    print(f'  工况: {cycle.upper()}')
    print('=' * 55)

    # 1. 加载工况
    t, v = load_drive_cycle(cycle)
    P_load = vehicle_power(v, DT)

    # 2. 后向 DP
    print(f'\n[1/4] 后向 DP...')
    J, pi = backward_dp(P_load)

    # 3. 前向 Rollout
    print(f'\n[2/4] 前向 Rollout...')
    dp = forward_rollout(P_load, pi)

    # 4. 规则控制器
    print(f'\n[3/4] 规则控制器...')
    rule = run_rule_controller(P_load)

    # 5. 结果
    print(f'\n[4/4] 对比结果:')
    print_metrics(rule, dp, P_load)

    save_results(dp, v, P_load, cycle)
    plot_comparison(t, v, P_load, rule, dp, cycle)

    if args.check:
        # 加载参考答案的结果进行对比
        ref_csv = os.path.join(RESULTS_DIR, f'dp_ems_{cycle}.csv')
        if os.path.exists(ref_csv):
            ref = pd.read_csv(ref_csv)
            max_soc_diff = np.max(np.abs(dp['SOC'] - ref['SOC'].values))
            max_pfc_diff = np.max(np.abs(dp['P_fc_kW'] - ref['P_fc_kW'].values))
            print(f'\n[验证] 与参考答案对比:')
            print(f'  SOC 最大偏差: {max_soc_diff:.4f}  {"✅" if max_soc_diff < 0.01 else "❌"}')
            print(f'  FC功率最大偏差: {max_pfc_diff:.4f}  {"✅" if max_pfc_diff < 0.5 else "❌"}')
            if max_soc_diff < 0.01 and max_pfc_diff < 0.5:
                print('  🎉 全部通过！你写对了！')
            else:
                print('  ⚠️  有偏差，检查一下代码逻辑')
        else:
            print(f'\n[跳过] 未找到参考答案，先跑一次 day8_dp_ems.py 生成')

    print(f'\n[OK] 完成！')


if __name__ == '__main__':
    main()
