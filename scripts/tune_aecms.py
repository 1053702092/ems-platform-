#!/usr/bin/env python3
"""
tune_aecms.py — A-ECMS 参数扫描调优
扫描 Kp 和 s0 的组合，找最优 SOC 维持 + 最低氢耗
"""
import os, sys, itertools
import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts'))

from day9_ecms_ems import ecms_adaptive, ecms_sim, vehicle_power, load_drive_cycle
from day9_ecms_ems import fc_efficiency, SOC_REF, S_ADAPTIVE_MIN, S_ADAPTIVE_MAX
from day8_dp_ems import DT

def main():
    # 加载 WLTC
    t, v = load_drive_cycle('wltc')
    P_load = vehicle_power(v, DT)

    # 参数网格
    s0_grid = np.arange(80, 201, 10)   # 80~200, 步长 10
    Kp_grid = np.arange(1.0, 8.1, 1.0) # 1~8, 步长 1

    results = []
    total = len(s0_grid) * len(Kp_grid)
    idx = 0

    for s0, Kp in itertools.product(s0_grid, Kp_grid):
        idx += 1
        if idx % 10 == 0:
            print(f'[{idx}/{total}] s0={s0:.0f}, Kp={Kp:.1f}...')

        res = ecms_adaptive(P_load, s_0=s0, Kp=Kp)
        eff = fc_efficiency(res['P_fc_kW'])
        soc_dev = abs(res['SOC'][-1] - SOC_REF)

        results.append({
            's0': s0,
            'Kp': Kp,
            'H2_kg': res['m_H2_cumul_kg'][-1],
            'SOC_end': res['SOC'][-1],
            'SOC_dev': soc_dev,
            'FC_eff_mean': eff.mean(),
            'FC_eff_gt50': (eff > 0.50).mean(),
        })

    df = pd.DataFrame(results)

    # 保存
    csv_path = os.path.join(PROJECT_ROOT, 'results', 'aecms_tune_wltc.csv')
    df.to_csv(csv_path, index=False)

    # 找 Pareto 最优：SOC 接近目标 + 氢耗低
    print(f'\n{"="*70}')
    print(f'  A-ECMS 参数调优结果 — WLTC')
    print(f'{"="*70}')
    print(f'  {"s0":>5}  {"Kp":>5}  {"H2(kg)":>8}  {"SOC_end":>8}  {"|SOC-0.6|":>10}  {"FC_eff":>7}  {"FC>50%":>7}')
    print(f'  {"-"*62}')
    for _, r in df.sort_values('SOC_dev').head(20).iterrows():
        print(f'  {r["s0"]:>5.0f}  {r["Kp"]:>5.1f}  {r["H2_kg"]:>8.4f}  {r["SOC_end"]:>8.4f}  {r["SOC_dev"]:>10.4f}  {r["FC_eff_mean"]:>6.1%}  {r["FC_eff_gt50"]:>6.1%}')

    # 找 SOC_dev < 0.05 中 H2 最低的
    good = df[df['SOC_dev'] < 0.05]
    if len(good) > 0:
        best = good.loc[good['H2_kg'].idxmin()]
        print(f'\n★ 最优 (SOC偏差<0.05最低氢耗): s0={best["s0"]:.0f}, Kp={best["Kp"]:.1f}')
        print(f'  H2={best["H2_kg"]:.4f} kg, SOC_end={best["SOC_end"]:.3f}')
    else:
        # 放宽条件
        best = df.loc[df['SOC_dev'].idxmin()]
        print(f'\n★ 最接近目标: s0={best["s0"]:.0f}, Kp={best["Kp"]:.1f}')
        print(f'  SOC_dev={best["SOC_dev"]:.4f}, H2={best["H2_kg"]:.4f} kg')

    print(f'\n[保存] {csv_path}')

if __name__ == '__main__':
    main()
