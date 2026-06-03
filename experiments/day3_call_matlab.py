# -*- coding: utf-8 -*-
"""
Day3: Python调用MATLAB计算PEM燃料电池I-V曲线
链路：Python -> MATLAB -> CSV -> pandas -> matplotlib
"""
import subprocess, time, os
import pandas as pd
import matplotlib.pyplot as plt

MATLAB = 'F:/Matlab/bin/matlab.exe'
SCRIPT = 'F:/CLAUDE/research/ems-platform/experiments/day3_iv_curve.m'
CSV = 'F:/CLAUDE/research/ems-platform/results/day3_cell_model_iv_curve.csv'
PNG = 'F:/CLAUDE/research/ems-platform/results/day3_cell_model_iv_curve.png'

# 1. 调用MATLAB
print('[1/3] 调用MATLAB计算I-V曲线...')
t0 = time.time()
proc = subprocess.Popen([MATLAB, '-batch', f"run('{SCRIPT}')"],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
out, _ = proc.communicate(timeout=60)
print(f'  MATLAB完成 ({time.time()-t0:.1f}s)')

# 2. 读取CSV
print('[2/3] 读取结果...')
df = pd.read_csv(CSV)
print(f'  {len(df)}个数据点')

# 3. 画图
print('[3/3] 画图...')
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

axes[0].plot(df['Current_A'], df['Voltage_V'], 'b-o', linewidth=1.5, markersize=3)
axes[0].set_xlabel('Current (A)'); axes[0].set_ylabel('Voltage (V)')
axes[0].set_title('PEMFC Polarization Curve'); axes[0].grid(True, alpha=0.3)

power = df['Current_A'] * df['Voltage_V']
axes[1].plot(df['Current_A'], power, 'r-s', linewidth=1.5, markersize=3)
axes[1].set_xlabel('Current (A)'); axes[1].set_ylabel('Power (W)')
axes[1].set_title('PEMFC Power Curve'); axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(PNG, dpi=150)
print(f'  图已保存: {PNG}')
print(f'\n开路电压: {df.iloc[0]["Voltage_V"]:.4f} V')
print(f'最大功率: {power.max():.1f} W')
print('\nDay3完成! Python->MATLAB->CSV->画图 全链路打通')
