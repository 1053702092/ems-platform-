# -*- coding: utf-8 -*-
"""
第4周：DP 参数敏感性分析
遍历 Alpha/Beta/网格密度，观察对氢耗和 SOC 的影响
"""
import sys, os, time
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PROJECT_ROOT, 'results')
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, 'scripts')
sys.path.insert(0, SCRIPTS_DIR)

# 先导入原模块
import day8_dp_ems
from day8_dp_ems import (
    load_drive_cycle, vehicle_power, fc_hydrogen_flow, fc_efficiency,
    run_rule_controller
)
import importlib

DT = 1.0

def run_dp(P_load, N_SOC=150, N_PFC=60, ALPHA=100.0, BETA=10000.0):
    """修改 day8_dp_ems 的全局参数后跑 DP"""
    day8_dp_ems.N_SOC = N_SOC
    day8_dp_ems.N_PFC = N_PFC
    day8_dp_ems.ALPHA = ALPHA
    day8_dp_ems.BETA = BETA
    # 通过模块对象调用，函数会读取更新后的全局参数
    t0 = time.time()
    J, pi = day8_dp_ems.backward_dp(P_load)
    dp = day8_dp_ems.forward_rollout(P_load, pi)
    t_cost = time.time() - t0
    return {
        'H2_kg': dp['m_H2_cumul_kg'][-1],
        'SOC_end': dp['SOC'][-1],
        'time_s': t_cost,
        'improve_pct': 0,
    }


def main():
    # ─── 加载工况 ───
    cycles = {}
    for name in ['wltc', 'nedc', 'cltc']:
        try:
            t, v = load_drive_cycle(name)
            P_load = vehicle_power(v, DT)
            cycles[name] = {'t': t, 'v': v, 'P_load': P_load}
        except FileNotFoundError as e:
            print(f'[跳过] {name}')

    if not cycles:
        print('没有可用的工况数据')
        return

    # 预计算规则控制器的结果（作为对比基线）
    rule_results = {}
    for name, data in cycles.items():
        rule = run_rule_controller(data['P_load'])
        rule_results[name] = rule['m_H2_cumul_kg'][-1]

    # ======================================================
    # 1. Alpha (SOC维持惩罚) 敏感性
    # ======================================================
    print('='*60)
    print('1. Alpha (SOC维持惩罚) 敏感性')
    print('='*60)
    alpha_vals = [10, 50, 100, 200, 500]
    alpha_data = []

    for name, data in cycles.items():
        for a in alpha_vals:
            r = run_dp(data['P_load'], ALPHA=a)
            r['param'] = a
            r['cycle'] = name
            r['rule_H2'] = rule_results[name]
            r['improve_pct'] = (rule_results[name] - r['H2_kg']) / rule_results[name] * 100
            alpha_data.append(r)
            print(f'  {name:5s}  Alpha={a:4d}  H2={r["H2_kg"]:.4f}  SOC={r["SOC_end"]:.3f}  '
                  f'{r["improve_pct"]:.1f}%')

    # ======================================================
    # 2. Beta (终端惩罚) 敏感性
    # ======================================================
    print('\n' + '='*60)
    print('2. Beta (终端惩罚) 敏感性')
    print('='*60)
    beta_vals = [1000, 5000, 10000, 50000, 100000]
    beta_data = []

    for name, data in cycles.items():
        for b in beta_vals:
            r = run_dp(data['P_load'], BETA=b)
            r['param'] = b
            r['cycle'] = name
            r['rule_H2'] = rule_results[name]
            r['improve_pct'] = (rule_results[name] - r['H2_kg']) / rule_results[name] * 100
            beta_data.append(r)
            print(f'  {name:5s}  Beta={b:6d}  H2={r["H2_kg"]:.4f}  SOC={r["SOC_end"]:.3f}  '
                  f'{r["improve_pct"]:.1f}%')

    # ======================================================
    # 3. 网格密度 敏感性
    # ======================================================
    print('\n' + '='*60)
    print('3. 网格密度（N_SOC x N_PFC）敏感性')
    print('='*60)
    grid_configs = [
        (50, 20, '50x20'),
        (100, 40, '100x40'),
        (150, 60, '150x60'),
        (200, 80, '200x80'),
    ]
    grid_data = []

    for name, data in cycles.items():
        for ns, npfc, label in grid_configs:
            r = run_dp(data['P_load'], N_SOC=ns, N_PFC=npfc)
            r['param'] = label
            r['cycle'] = name
            r['rule_H2'] = rule_results[name]
            r['improve_pct'] = (rule_results[name] - r['H2_kg']) / rule_results[name] * 100
            grid_data.append(r)
            print(f'  {name:5s}  {label:8s}  H2={r["H2_kg"]:.4f}  SOC={r["SOC_end"]:.3f}  '
                  f'{r["time_s"]:.1f}s  {r["improve_pct"]:.1f}%')

    # ======================================================
    # 4. 画图
    # ======================================================
    print('\n[画图]...')
    fig, axes = plt.subplots(3, 3, figsize=(15, 12))
    colors = {'wltc': '#2196F3', 'nedc': '#FF9800', 'cltc': '#4CAF50'}
    markers = {'wltc': 'o', 'nedc': 's', 'cltc': '^'}

    def plot_data(ax, x_vals_groups, y_vals_groups, xlabel, ylabel):
        for name in cycles:
            ax.plot(x_vals_groups[name], y_vals_groups[name],
                   color=colors[name], marker=markers[name],
                   label=name.upper(), linewidth=1.8, markersize=8)
        ax.set_xlabel(xlabel, fontsize=11)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=9)

    # --- Alpha ---
    ax = axes[0,0]
    groups = {n: [d['H2_kg'] for d in alpha_data if d['cycle']==n] for n in cycles}
    xg = {n: [d['param'] for d in alpha_data if d['cycle']==n] for n in cycles}
    plot_data(ax, xg, groups, 'Alpha', 'H2 (kg)')

    ax = axes[0,1]
    groups = {n: [d['SOC_end'] for d in alpha_data if d['cycle']==n] for n in cycles}
    plot_data(ax, xg, groups, 'Alpha', 'SOC End')

    ax = axes[0,2]
    groups = {n: [d['improve_pct'] for d in alpha_data if d['cycle']==n] for n in cycles}
    plot_data(ax, xg, groups, 'Alpha', 'Improvement (%)')
    axes[0,0].set_title('Alpha Sensitivity - H2', fontsize=11, fontweight='bold')
    axes[0,1].set_title('Alpha Sensitivity - SOC End', fontsize=11, fontweight='bold')
    axes[0,2].set_title('Alpha Sensitivity - Improvement', fontsize=11, fontweight='bold')

    # --- Beta ---
    ax = axes[1,0]
    groups = {n: [d['H2_kg'] for d in beta_data if d['cycle']==n] for n in cycles}
    xg = {n: [d['param'] for d in beta_data if d['cycle']==n] for n in cycles}
    plot_data(ax, xg, groups, 'Beta', 'H2 (kg)')

    ax = axes[1,1]
    groups = {n: [d['SOC_end'] for d in beta_data if d['cycle']==n] for n in cycles}
    plot_data(ax, xg, groups, 'Beta', 'SOC End')

    ax = axes[1,2]
    groups = {n: [d['improve_pct'] for d in beta_data if d['cycle']==n] for n in cycles}
    plot_data(ax, xg, groups, 'Beta', 'Improvement (%)')
    axes[1,0].set_title('Beta Sensitivity - H2', fontsize=11, fontweight='bold')
    axes[1,1].set_title('Beta Sensitivity - SOC End', fontsize=11, fontweight='bold')
    axes[1,2].set_title('Beta Sensitivity - Improvement', fontsize=11, fontweight='bold')

    # --- Grid ---
    ax = axes[2,0]
    for name in cycles:
        dlist = [d for d in grid_data if d['cycle']==name]
        labels = [d['param'] for d in dlist]
        vals = [d['H2_kg'] for d in dlist]
        ax.plot(labels, vals, color=colors[name], marker=markers[name],
               label=name.upper(), linewidth=1.8, markersize=8)
    ax.set_xlabel('Grid', fontsize=11); ax.set_ylabel('H2 (kg)', fontsize=11)
    ax.legend(fontsize=10); ax.grid(True, alpha=0.3)

    ax = axes[2,1]
    for name in cycles:
        dlist = [d for d in grid_data if d['cycle']==name]
        labels = [d['param'] for d in dlist]
        vals = [d['SOC_end'] for d in dlist]
        ax.plot(labels, vals, color=colors[name], marker=markers[name],
               label=name.upper(), linewidth=1.8, markersize=8)
    ax.set_xlabel('Grid', fontsize=11); ax.set_ylabel('SOC End', fontsize=11)
    ax.legend(fontsize=10); ax.grid(True, alpha=0.3)

    ax = axes[2,2]
    for name in cycles:
        dlist = [d for d in grid_data if d['cycle']==name]
        labels = [d['param'] for d in dlist]
        vals = [d['time_s'] for d in dlist]
        ax.plot(labels, vals, color=colors[name], marker=markers[name],
               label=name.upper(), linewidth=1.8, markersize=8)
    ax.set_xlabel('Grid', fontsize=11); ax.set_ylabel('Time (s)', fontsize=11)
    ax.legend(fontsize=10); ax.grid(True, alpha=0.3)
    axes[2,0].set_title('Grid Sensitivity - H2', fontsize=11, fontweight='bold')
    axes[2,1].set_title('Grid Sensitivity - SOC End', fontsize=11, fontweight='bold')
    axes[2,2].set_title('Grid Sensitivity - Compute Time', fontsize=11, fontweight='bold')

    plt.suptitle('DP Parameter Sensitivity Analysis', fontsize=14, fontweight='bold')
    plt.tight_layout()
    png_path = os.path.join(RESULTS_DIR, 'DP_sensitivity_analysis.png')
    plt.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f'[Saved] {png_path}')
    plt.close()

    # ======================================================
    # 5. 输出 CSV 数据
    # ======================================================
    for name, dlist, fname in [
        ('Alpha', alpha_data, 'sensitivity_alpha.csv'),
        ('Beta', beta_data, 'sensitivity_beta.csv'),
        ('Grid', grid_data, 'sensitivity_grid.csv'),
    ]:
        df = pd.DataFrame(dlist)
        csv_path = os.path.join(RESULTS_DIR, fname)
        df.to_csv(csv_path, index=False)
        print(f'[Saved] {csv_path}')

    # ======================================================
    # 6. 总结
    # ======================================================
    print('\n' + '='*60)
    print('SUMMARY')
    print('='*60)
    for name in cycles:
        print(f'\n--- {name.upper()} ---')
        base = [d for d in alpha_data if d['cycle']==name and d['param']==100][0]
        print(f'Default (Alpha=100, Beta=10000, 150x60):')
        print(f'  H2 = {base["H2_kg"]:.4f} kg, SOC_end = {base["SOC_end"]:.3f}, '
              f'Improvement = {base["improve_pct"]:.1f}%')

        dlist = [d for d in alpha_data if d['cycle']==name]
        h2_range = max(d['H2_kg'] for d in dlist) - min(d['H2_kg'] for d in dlist)
        print(f'  Alpha sensitivity: H2 range = {h2_range:.4f} kg')

        dlist = [d for d in beta_data if d['cycle']==name]
        h2_range = max(d['H2_kg'] for d in dlist) - min(d['H2_kg'] for d in dlist)
        print(f'  Beta sensitivity: H2 range = {h2_range:.4f} kg')

    print('\n[Done] Sensitivity analysis complete')

if __name__ == '__main__':
    main()
