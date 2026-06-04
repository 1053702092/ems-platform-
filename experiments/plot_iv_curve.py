# -*- coding: utf-8 -*-
"""
plot_iv_curve.py — 读取 Cell_model_v10 的 I-V 扫描结果并画图
用法: python experiments/plot_iv_curve.py
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

results_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'results')
csv_path = os.path.join(results_dir, 'cell_model_iv_sweep.csv')

df = pd.read_csv(csv_path, header=None, names=['Current_A', 'Voltage_V'])
print(f'已读取 {len(df)} 个数据点')
print(f'电流范围: {df.Current_A.min():.0f} - {df.Current_A.max():.0f} A')
print(f'电压范围: {df.Voltage_V.min():.4f} - {df.Voltage_V.max():.4f} V')

# 计算功率
df['Power_kW'] = df.Current_A * df.Voltage_V / 1000
max_power_idx = df.Power_kW.idxmax()

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# I-V 曲线
ax1.plot(df.Current_A, df.Voltage_V, 'b-o', linewidth=1.5, markersize=3)
ax1.set_xlabel('Current (A)')
ax1.set_ylabel('Stack Voltage (V)')
ax1.set_title(r'PEMFC Polarization Curve (Cell_model_v10)')
ax1.grid(True, alpha=0.3)
ax1.axvline(x=df.Current_A[max_power_idx], color='r', linestyle='--', alpha=0.5,
            label=f'Max Power @ {df.Current_A[max_power_idx]:.0f}A')

# 功率曲线
ax2.plot(df.Current_A, df.Power_kW, 'r-s', linewidth=1.5, markersize=3)
ax2.set_xlabel('Current (A)')
ax2.set_ylabel('Power (kW)')
ax2.set_title('PEMFC Power Curve')
ax2.grid(True, alpha=0.3)
ax2.axvline(x=df.Current_A[max_power_idx], color='r', linestyle='--', alpha=0.5)
ax2.axhline(y=df.Power_kW[max_power_idx], color='g', linestyle=':', alpha=0.5)
ax2.annotate(f'Max: {df.Power_kW[max_power_idx]:.1f} kW\n@ {df.Current_A[max_power_idx]:.0f}A',
             xy=(df.Current_A[max_power_idx], df.Power_kW[max_power_idx]),
             xytext=(df.Current_A[max_power_idx]+15, df.Power_kW[max_power_idx]-10),
             arrowprops=dict(arrowstyle='->', color='green'), fontsize=10)

plt.tight_layout()
png_path = os.path.join(results_dir, 'cell_model_iv_curve.png')
plt.savefig(png_path, dpi=150)
print(f'图已保存: {png_path}')

# 输出关键指标
print(f'\n===== 关键指标 =====')
print(f'开路电压: {df.Voltage_V.iloc[0]:.2f} V')
print(f'最大功率: {df.Power_kW.max():.1f} kW (在 {df.Current_A[df.Power_kW.idxmax()]:.0f}A)')
print(f'额定功率 (100A): {df.Power_kW.iloc[-1]:.1f} kW')
print(f'电压降: {df.Voltage_V.iloc[0] - df.Voltage_V.iloc[-1]:.1f} V (0→100A)')
