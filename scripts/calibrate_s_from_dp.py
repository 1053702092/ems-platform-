#!/usr/bin/env python3
"""
calibrate_s_from_dp.py — DP 反推标定等效因子 s₀

原理：
  PMP Hamiltonian: H = m_dot_H2 + λ * SOC_dot
  ECMS:          H_eq = m_dot_H2 + s * |P_bat| / 3600

  从 DP 代价矩阵 J 计算 costate λ_k = ∂J_k/∂SOC (沿最优轨迹)
  再近似换算为最优等效因子 s₀

用法：
  python scripts/calibrate_s_from_dp.py --cycle wltc
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

from day8_dp_ems import (
    backward_dp, forward_rollout, vehicle_power, load_drive_cycle,
    state_transition, fc_hydrogen_flow,
    SOC_REF, SOC_MIN, SOC_MAX, N_SOC, N_PFC, PFC_MIN, PFC_MAX,
    ALPHA, BETA, DT, Q_BAT, V_NOM,
)
from day9_ecms_ems import load_dp_results

def compute_costate(J, SOC_GRID, opt_soc_traj):
    """
    沿 DP 最优 SOC 轨迹计算 costate λ_k

    λ_k = (J[k, i+1] - J[k, i-1]) / (SOC_grid[i+1] - SOC_grid[i-1])

    Parameters
    ----------
    J : (N+1, N_SOC) — 后向 DP 代价矩阵
    SOC_GRID : (N_SOC,) — SOC 网格
    opt_soc_traj : (N+1,) — DP 最优 SOC 轨迹

    Returns
    -------
    lambdas : (N,) — 每个时间步的 costate
    """
    N = opt_soc_traj.shape[0] - 1
    dSOC = SOC_GRID[1] - SOC_GRID[0]  # 网格间距
    lambdas = np.zeros(N)

    for k in range(N):
        # 找 SOC 轨迹对应的网格索引
        i = np.argmin(np.abs(SOC_GRID - opt_soc_traj[k]))
        # 有限差分
        i_l = max(0, i - 1)
        i_r = min(N_SOC - 1, i + 1)
        if i_l == i_r:
            lambdas[k] = 0
        else:
            lambdas[k] = (J[k, i_r] - J[k, i_l]) / (SOC_GRID[i_r] - SOC_GRID[i_l])

    return lambdas

def costate_to_s(lambda_k):
    """
    将 costate λ 转换为 ECMS 等效因子 s

    理论关系（近似）:
    s ≈ -λ * 1000 / (V_oc * Q_bat)

    其中 V_oc ≈ 352V (SOC=0.6 开路电压), Q_bat = 50 Ah
    """
    V_oc_approx = 352.0  # 典型开路电压 @ SOC=0.6
    s_k = -lambda_k * 1000 / (V_oc_approx * Q_BAT)
    return s_k

def main():
    parser = argparse.ArgumentParser(description='DP 反推标定等效因子')
    parser.add_argument('--cycle', choices=['wltc', 'nedc', 'cltc'], default='wltc')
    args = parser.parse_args()

    cycle = args.cycle
    print(f'{"="*60}')
    print(f'  DP 反推标定 ECMS 等效因子 — {cycle.upper()}')
    print(f'{"="*60}')

    # 1. 加载工况
    t, v = load_drive_cycle(cycle)
    P_load = vehicle_power(v, DT)
    N = len(t)

    SOC_GRID = np.linspace(SOC_MIN, SOC_MAX, N_SOC)

    # 2. 运行后向 DP（获取代价矩阵 J）
    print('\n[1/4] 运行后向 DP...')
    J, pi = backward_dp(P_load)

    # 3. 前向 Rollout（获取最优 SOC 轨迹）
    print('\n[2/4] 前向 Rollout...')
    dp = forward_rollout(P_load, pi)
    opt_soc = dp['SOC']  # (N+1,)

    # 4. 沿轨迹计算 costate λ
    print('\n[3/4] 计算 costate λ...')
    lambdas = compute_costate(J, SOC_GRID, opt_soc)

    # 5. 转换为等效因子 s
    print('\n[4/4] 转换为等效因子...')
    s_k = costate_to_s(lambdas)

    # 统计
    s_valid = s_k[np.isfinite(s_k)]

    print(f'\n{"="*60}')
    print(f'  DP 反推标定结果 — {cycle.upper()}')
    print(f'{"="*60}')
    print(f'  Costate λ:')
    print(f'    均值: {np.mean(lambdas):.4f}')
    print(f'    标准差: {np.std(lambdas):.4f}')
    print(f'    范围: [{np.min(lambdas):.4f}, {np.max(lambdas):.4f}]')
    print(f'  ECMS 等效因子 s [g/kWh]:')
    print(f'    均值: {np.mean(s_valid):.1f}')
    print(f'    中位数: {np.median(s_valid):.1f}')
    print(f'    标准差: {np.std(s_valid):.1f}')
    print(f'    范围: [{np.min(s_valid):.1f}, {np.max(s_valid):.1f}]')
    print(f'    推荐 s0: {np.median(s_valid):.0f} g/kWh')
    print(f'    经验校准 s0（abs公式）: 130 g/kWh')
    print(f'  DP 最优 SOC 轨迹:')
    print(f'    SOC_0={opt_soc[0]:.3f} → SOC_end={opt_soc[-1]:.3f}')
    print(f'  DP 总氢耗: {dp["m_H2_cumul_kg"][-1]:.4f} kg')
    print(f'{"="*60}')

    # 绘图
    fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True)
    t_min = t / 60

    # 第一行：SOC 轨迹
    ax = axes[0]
    ax.plot(t_min, opt_soc[:N], 'b-', lw=1.2, label='DP Optimal SOC')
    ax.axhline(y=SOC_REF, color='gray', ls=':', alpha=0.7, label=f'SOC_ref={SOC_REF}')
    ax.set_ylabel('SOC')
    ax.set_ylim(0.2, 0.9)
    ax.legend(loc='upper right', fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_title(f'DP Optimal SOC Trajectory — {cycle.upper()}')

    # 第二行：Costate λ
    ax = axes[1]
    ax.plot(t_min, lambdas, 'r-', lw=0.8)
    ax.axhline(y=0, color='gray', ls='--', alpha=0.3)
    ax.set_ylabel('Costate λ')
    ax.grid(True, alpha=0.3)
    ax.set_title('Costate λ (sensitivity of cost-to-go w.r.t. SOC)')

    # 第三行：等效因子 s
    ax = axes[2]
    ax.plot(t_min, s_k, 'g-', lw=0.8, label='s(t) from DP')
    ax.axhline(y=np.median(s_valid), color='orange', ls='--', lw=1.5,
               label=f'median s₀={np.median(s_valid):.0f}')
    ax.fill_between(t_min, np.percentile(s_valid, 25), np.percentile(s_valid, 75),
                    alpha=0.15, color='green', label='25-75 percentile')
    ax.set_ylabel('Equiv. Factor s [g/kWh]')
    ax.legend(loc='upper right', fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_title('ECMS Equivalence Factor from DP')

    # 第四行：s 直方图
    ax = axes[3]
    ax.hist(s_valid, bins=50, color='green', alpha=0.6, edgecolor='none')
    ax.axvline(x=np.median(s_valid), color='orange', ls='--', lw=1.5,
               label=f'median={np.median(s_valid):.0f}')
    ax.axvline(x=np.mean(s_valid), color='red', ls=':', lw=1.5,
               label=f'mean={np.mean(s_valid):.0f}')
    ax.set_xlabel('Equivalence Factor s [g/kWh]')
    ax.set_ylabel('Count')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_title('Distribution of Equivalence Factor')

    plt.tight_layout()
    png_path = os.path.join(RESULTS_DIR, f'dp_calibrate_s_{cycle}.png')
    plt.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f'\n[图] {png_path}')
    plt.close()

    # 保存数据
    df = pd.DataFrame({
        'time': t,
        'speed_kmh': v,
        'P_load_kW': P_load,
        'SOC_opt': opt_soc[:N],
        'lambda': lambdas,
        's_factor': s_k,
    })
    csv_path = os.path.join(RESULTS_DIR, f'dp_calibrate_s_{cycle}.csv')
    df.to_csv(csv_path, index=False)
    print(f'[数据] {csv_path}')

    return np.median(s_valid)

if __name__ == '__main__':
    main()
