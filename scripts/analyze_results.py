# -*- coding: utf-8 -*-
"""Analyze DP vs Rule-based results"""
import numpy as np
import pandas as pd

bp = np.array([0, 2, 5, 8, 10, 15, 20, 25, 30])
eta = np.array([0, 0.28, 0.40, 0.48, 0.50, 0.55, 0.53, 0.48, 0.40])
LHV_H2 = 120e6
DT = 1.0

def fc_hydrogen_flow(P_fc):
    eta_interp = np.interp(P_fc, bp, eta)
    with np.errstate(divide='ignore', invalid='ignore'):
        mdot = P_fc * 1000 / (eta_interp * LHV_H2) * 1000
    mdot[~np.isfinite(mdot)] = 0
    mdot[P_fc == 0] = 0
    return mdot

# ===== WLTC =====
dw = pd.read_csv('results/dp_ems_wltc.csv')
rw = pd.read_csv('results/Day7_ems_sim_wltc.csv')
rw_mdot = fc_hydrogen_flow(rw['P_fc_kW'].values)
rw_h2 = rw_mdot.sum() / 1000
dp_h2_w = dw['m_H2_cumul_kg'].iloc[-1]

print('=' * 55)
print('  EMS 成果评估: DP vs Rule-Based (WLTC)')
print('=' * 55)
print(f'  {"指标":<25} {"规则":>10} {"DP":>10} {"改善":>10}')
print('-' * 55)
print(f'  {"总氢耗 (kg)":<25} {rw_h2:>10.4f} {dp_h2_w:>10.4f} {(rw_h2-dp_h2_w)/rw_h2*100:>9.1f}%')
print(f'  {"SOC 初→终":<25} {f"0.60→{rw['SOC'].iloc[-1]:.3f}":>10} {f"0.60→{dw['SOC'].iloc[-1]:.3f}":>10} {"—":>10}')

rule_eff = np.interp(rw['P_fc_kW'].values, bp, eta)
dp_eff = np.interp(dw['P_fc_kW'].values, bp, eta)
print(f'  {"FC平均效率":<25} {rule_eff.mean():>10.2%} {dp_eff.mean():>10.2%} {dp_eff.mean()-rule_eff.mean():>+9.1%}')
print(f'  {"FC高效(>45%)占比":<25} {(rule_eff>0.45).mean():>10.1%} {(dp_eff>0.45).mean():>10.1%} {(dp_eff>0.45).mean()-(rule_eff>0.45).mean():>+9.1%}')
print(f'  {"FC>50% 占比":<25} {(rule_eff>0.50).mean():>10.1%} {(dp_eff>0.50).mean():>10.1%} {(dp_eff>0.50).mean()-(rule_eff>0.50).mean():>+9.1%}')
print(f'  {"FC平均功率 (kW)":<25} {rw['P_fc_kW'].mean():>10.2f} {dw['P_fc_kW'].mean():>10.2f}')
print(f'  {"能量需求 (kWh)":<25} {np.trapezoid(dw['P_load_kW'].values, dx=DT)/3600:>10.2f}', end='')
print(f'  {"(1800s WLTC)":>12}')
print('-' * 55)
print()

# ===== DP 工作点分析 =====
print('=== DP 最优策略分析 ===')
print(f'FC 功率范围: {dw["P_fc_kW"].min():.1f} ~ {dw["P_fc_kW"].max():.1f} kW')
non_zero = dw[dw['P_fc_kW'] > 0]
print(f'FC 开机时功率范围: {non_zero["P_fc_kW"].min():.2f} ~ {non_zero["P_fc_kW"].max():.1f} kW')
print(f'FC 开机占比: {len(non_zero)/len(dw):.1%}')
print(f'电池辅助占比(P_bat>0放电): {(dw["P_bat_kW"]>1).mean():.1%}')
print(f'电池充电占比(P_bat<-1充电): {(dw["P_bat_kW"]<-1).mean():.1%}')
print(f'FC=0占比: {(dw["P_fc_kW"]==0).mean():.1%}')
print()

# 按负载分段的 FC 功率分析
print('=== 负载分段 FC 功率策略 ===')
for lo, hi in [(0,2),(2,5),(5,10),(10,15),(15,25),(25,50)]:
    mask = (dw['P_load_kW'] >= lo) & (dw['P_load_kW'] < hi)
    if mask.sum() > 0:
        pfc_mean = dw.loc[mask, 'P_fc_kW'].mean()
        soc_mean = dw.loc[mask, 'SOC'].mean()
        print(f'  负载 {lo:3d}-{hi:3d} kW ({mask.sum():4d} 点): FC={pfc_mean:.2f} kW, SOC={soc_mean:.3f}')

# ===== NEDC =====
print()
print('=== NEDC DP 结果 ===')
dn = pd.read_csv('results/dp_ems_nedc.csv')
print(f'DP总氢耗: {dn["m_H2_cumul_kg"].iloc[-1]:.4f} kg')
print(f'DP SOC: 0.60 -> {dn["SOC"].iloc[-1]:.3f}')
print(f'能量需求: {np.trapezoid(dn["P_load_kW"].values, dx=DT)/3600:.2f} kWh ({len(dn)}s NEDC)')
ndp_eff = np.interp(dn['P_fc_kW'].values, bp, eta)
print(f'DP FC平均效率: {ndp_eff.mean():.2%}')
print(f'DP FC>50%占比: {(ndp_eff>0.50).mean():.1%}')

# 文献参考值
print()
print('=== 文献参考对比 ===')
print('文献报道 DP vs Rule-based 改善率一般在 10-25% 范围')
print('WLTC: 19.2% — 处于文献报告的合理区间上沿')
print('理由: 规则控制器设计偏保守（SOC维持优先），DP通过')
print('      全局最优分配找到了更优的FC/Battery能量分配。')
print()
print('需要改进的地方:')
print('1. SOC 终端 0.574 与参考值 0.6 有微小偏差 → 可调 β 或增加终端约束')
print('2. 部分区间FC功率0 → 频繁启停对FC寿命不利（需加启停惩罚）')
print('3. 目前只做了 WLTC/NEDC，缺少 CLTC 工况对比')
