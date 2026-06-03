# -*- coding: utf-8 -*-
"""
第1周 Day1：Python数据处理入门
练习目标：用pandas读取工况数据，matplotlib画图
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# ===== 1. 生成WLTC工况数据（练手用） =====
print('生成WLTC工况数据...')

# WLTC是国际标准工况，包含低速、中速、高速、超高速四个阶段
# 这里先生成模拟数据
np.random.seed(42)
t = np.arange(0, 1800, 1)  # 1800秒 = 30分钟

# 模拟车速曲线（简化版WLTC）
v = np.zeros_like(t)
# 低速段 (0-600s)
v[0:200] = np.sin(np.linspace(0, np.pi, 200)) * 15  # 0-15 km/h
v[200:400] = 15 + np.sin(np.linspace(0, np.pi*2, 200)) * 5
v[400:600] = np.linspace(15, 0, 200)
# 中速段 (600-1200s)
v[600:800] = np.sin(np.linspace(0, np.pi, 200)) * 25 + 25  # 25-50 km/h
v[800:1000] = 50 + np.sin(np.linspace(0, np.pi, 200)) * 5
v[1000:1200] = np.linspace(50, 0, 200)
# 高速段 (1200-1800s)
v[1200:1400] = np.sin(np.linspace(0, np.pi, 200)) * 35 + 35  # 35-70 km/h
v[1400:1600] = 70 + np.sin(np.linspace(0, np.pi, 200)) * 10
v[1600:1800] = np.linspace(70, 0, 200)
v = np.clip(v, 0, None)

# 计算功率需求（简化模型：P = a*v^2 + b*v + c）
P_demand = 0.005 * v**2 + 0.1 * v + 2 + np.random.normal(0, 0.5, len(v))
P_demand = np.clip(P_demand, 0, None)

# 保存到CSV
df_cycle = pd.DataFrame({
    'time': t,
    'speed': v,
    'power_demand': P_demand
})
df_cycle.to_csv('results/wltc_sample.csv', index=False)
print(f'  -> 已保存: results/wltc_sample.csv ({len(df_cycle)}行)')

# ===== 2. pandas基础操作 =====
print('\n===== pandas基础操作 =====')

# 读取CSV
df = pd.read_csv('results/wltc_sample.csv')
print(f'\n数据集概况:')
print(f'  行数: {len(df)}')
print(f'  列名: {list(df.columns)}')
print(f'\n前5行:')
print(df.head())
print(f'\n数据统计:')
print(df.describe())

# 数据筛选
print(f'\n高速段 (speed > 50 km/h): {len(df[df["speed"] > 50])} 个数据点')
print(f'平均功率需求: {df["power_demand"].mean():.2f} kW')
print(f'最大功率需求: {df["power_demand"].max():.2f} kW')

# ===== 3. matplotlib画图 =====
print('\n===== 画图 =====')

fig, axes = plt.subplots(2, 1, figsize=(12, 6))

# 子图1：车速
axes[0].plot(df['time'], df['speed'], 'b-', linewidth=1)
axes[0].set_ylabel('Speed (km/h)')
axes[0].set_title('WLTC Driving Cycle (Sample)')
axes[0].grid(True, alpha=0.3)

# 子图2：功率需求
axes[1].plot(df['time'], df['power_demand'], 'r-', linewidth=1)
axes[1].set_xlabel('Time (s)')
axes[1].set_ylabel('Power Demand (kW)')
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('results/wltc_sample_plot.png', dpi=150)
print('  -> 已保存: results/wltc_sample_plot.png')

# 双y轴图（一个图里看车速+功率）
fig2, ax1 = plt.subplots(figsize=(12, 4))
ax1.plot(df['time'], df['speed'], 'b-', label='Speed', linewidth=1)
ax1.set_ylabel('Speed (km/h)', color='b')
ax1.tick_params(axis='y', labelcolor='b')

ax2 = ax1.twinx()
ax2.plot(df['time'], df['power_demand'], 'r-', label='Power', linewidth=1, alpha=0.7)
ax2.set_ylabel('Power (kW)', color='r')
ax2.tick_params(axis='y', labelcolor='r')

ax1.set_xlabel('Time (s)')
ax1.set_title('Speed & Power Demand (Dual Y-Axis)')
ax1.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('results/wltc_dual_axis.png', dpi=150)
print('  -> 已保存: results/wltc_dual_axis.png')

print('\n✅ Day1 练习完成!')
print('  - pandas: 读取CSV, 查看统计, 筛选数据')
print('  - matplotlib: 双y轴图, 多子图')
