#!/usr/bin/env python3
"""
run_multicycle.py — 多工况 ECMS 验证 + DP 反推标定
NEDC / CLTC / WLTC 三工况对比
"""
import os, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PROJECT_ROOT, 'results')
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, 'scripts')
sys.path.insert(0, SCRIPTS_DIR)

from day9_ecms_ems import (
    ecms_sim, ecms_adaptive, scan_s_factor, find_best_s,
    fc_efficiency, vehicle_power, load_drive_cycle,
    plot_ecms_comparison, print_metrics,
    S_FACTOR_DEFAULT, SOC_REF,
)
from day8_dp_ems import (
    DT, run_rule_controller, load_rule_results,
)
from day9_ecms_ems import load_dp_results

def run_single_cycle(cycle_name, ecms_s=None, s0=None, Kp=3.0):
    """跑单个工况的 ECMS + A-ECMS + DP + Rule"""
    print(f'\n{"#"*60}')
    print(f'  {cycle_name.upper()} 工况')
    print(f'{"#"*60}')

    t, v = load_drive_cycle(cycle_name)
    P_load = vehicle_power(v, DT)

    # 加载 Rule 和 DP
    rule = load_rule_results(cycle_name) or run_rule_controller(P_load)
    dp = load_dp_results(cycle_name)

    if ecms_s is None:
        df_scan = scan_s_factor(P_load, cycle_name)
        best_s = find_best_s(df_scan)['s_factor']
    else:
        best_s = ecms_s

    ecms = ecms_sim(P_load, s_factor=best_s)
    aecms = ecms_adaptive(P_load, s_0=(s0 or best_s), Kp=Kp)

    print_metrics(rule, dp, ecms, aecms)
    plot_ecms_comparison(t, v, P_load, rule, dp, ecms, aecms, cycle_name, best_s)

    # 保存 CSV
    for label, res in [('ecms', ecms), ('aecms', aecms)]:
        df = pd.DataFrame({
            'time': np.arange(len(t)),
            'speed_kmh': v,
            'P_load_kW': P_load,
            'P_fc_kW': res['P_fc_kW'],
            'P_bat_kW': res['P_bat_kW'],
            'SOC': res['SOC'],
            'm_H2_cumul_kg': res['m_H2_cumul_kg'],
        })
        csv_path = os.path.join(RESULTS_DIR, f'{label}_ems_{cycle_name}.csv')
        df.to_csv(csv_path, index=False)
        print(f'[保存] {csv_path}')

    return rule, dp, ecms, aecms, best_s

def create_summary_table(results):
    """生成三工况汇总表"""
    rows = []
    for cycle, data in results.items():
        rule, dp, ecms, aecms, best_s = data
        row = {
            'Cycle': cycle.upper(),
            'Best_s': f'{best_s:.0f}',
            'DP_H2_kg': dp['m_H2_cumul_kg'][-1],
            'DP_SOC_end': dp['SOC'][-1],
            'ECMS_H2_kg': ecms['m_H2_cumul_kg'][-1],
            'ECMS_SOC_end': ecms['SOC'][-1],
            'AECMS_H2_kg': aecms['m_H2_cumul_kg'][-1],
            'AECMS_SOC_end': aecms['SOC'][-1],
            'Rule_H2_kg': rule['m_H2_cumul_kg'][-1] if rule else None,
        }
        # ECMS vs DP: H2 差距
        h2_dp = row['DP_H2_kg']
        row['ECMS_H2_delta'] = f'{(row["ECMS_H2_kg"] - h2_dp)/h2_dp*100:+.1f}%'
        row['AECMS_H2_delta'] = f'{(row["AECMS_H2_kg"] - h2_dp)/h2_dp*100:+.1f}%'
        rows.append(row)

    df = pd.DataFrame(rows)
    print(f'\n{"="*80}')
    print(f'  三工况汇总对比')
    print(f'{"="*80}')
    print(df.to_string(index=False))
    print(f'{"="*80}')

    csv_path = os.path.join(RESULTS_DIR, 'ecms_multicycle_summary.csv')
    df.to_csv(csv_path, index=False)
    print(f'\n[保存] {csv_path}')

def main():
    cycles = ['wltc', 'nedc', 'cltc']
    results = {}

    # s0 基准用前期扫描找到的 DP 匹配值
    ECMS_S_FIXED = {'wltc': 130, 'nedc': 130, 'cltc': 130}
    AECMS_S0 = 130
    AECMS_KP = 3.0

    for cycle in cycles:
        results[cycle] = run_single_cycle(
            cycle,
            ecms_s=ECMS_S_FIXED.get(cycle),
            s0=AECMS_S0, Kp=AECMS_KP,
        )

    create_summary_table(results)

if __name__ == '__main__':
    main()
