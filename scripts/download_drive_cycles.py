# -*- coding: utf-8 -*-
"""
download_drive_cycles.py — 标准工况数据生成

从下载的 Excel 源文件读取 WLTC/CLTC/NEDC 工况数据，
输出标准 CSV 供 EMS 仿真使用。

用法：
    python scripts/download_drive_cycles.py             # 全部生成
    python scripts/download_drive_cycles.py --wltc       # 只生成 WLTC
    python scripts/download_drive_cycles.py --plot-only  # 只看已有的图
"""

import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt

# 下载目录 — 你放工况 Excel 的地方
DOWNLOAD_DIR = r'F:\BaiduNetdiskDownload\汽车行驶工况数据'
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PROJECT_ROOT, 'results')


def read_from_excel(filename):
    """从下载的 Excel 文件读取工况数据"""
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    if not os.path.exists(filepath):
        print(f'[跳过] 未找到文件: {filepath}')
        return None
    df = pd.read_excel(filepath)
    # 取第二列（速度），转为列表
    speed = df.iloc[:, 1].values.tolist()
    print(f'[读取] {filepath} → {len(speed)} 个数据点')
    return speed


def save_to_csv(speeds, filename, cycle_name='WLTC'):
    """将速度序列保存为 CSV"""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    filepath = os.path.join(RESULTS_DIR, filename)

    df = pd.DataFrame({
        'time': range(len(speeds)),
        'speed_kmh': speeds
    })
    df.to_csv(filepath, index=False)
    print(f'[保存] {filepath} ({len(speeds)} 行)')
    return filepath


def plot_cycle(csv_path, title='Drive Cycle'):
    """画出工况速度曲线"""
    df = pd.read_csv(csv_path)
    t = df['time']
    v = df['speed_kmh']

    plt.figure(figsize=(14, 4))
    plt.plot(t, v, 'b-', linewidth=1)
    plt.axhline(y=0, color='gray', linewidth=0.5)
    plt.xlabel('Time (s)')
    plt.ylabel('Speed (km/h)')
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    png_path = csv_path.replace('.csv', '.png')
    plt.savefig(png_path, dpi=150)
    print(f'[图] {png_path}')
    plt.close()

    # 输出关键指标
    print(f'  最高速度: {v.max():.1f} km/h')
    print(f'  平均速度: {v.mean():.1f} km/h')
    print(f'  总时长: {len(t)} s ({len(t)//60} min {len(t)%60} s)')
    print(f'  怠速占比: {(v == 0).mean() * 100:.1f}%')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='工况数据生成')
    parser.add_argument('--wltc', action='store_true', help='只生成 WLTC')
    parser.add_argument('--plot-only', action='store_true', help='只看图')
    args = parser.parse_args()

    cycles = {
        'WLTC': ('WLTC工况.xlsx', 'wltc_cycle.csv'),
        'CLTC': ('CLTC工况.xlsx', 'cltc_cycle.csv') if os.path.exists(
            os.path.join(DOWNLOAD_DIR, 'CLTC工况.xlsx')) else None,
        'NEDC': ('NEDC工况.xlsx', 'nedc_cycle.csv'),
    }

    if args.plot_only:
        for name, files in cycles.items():
            if files:
                csv = os.path.join(RESULTS_DIR, files[1])
                if os.path.exists(csv):
                    plot_cycle(csv, f'{name} Drive Cycle')
        exit(0)

    # 过滤只生成指定的
    if args.wltc:
        cycles = {k: v for k, v in cycles.items() if k == 'WLTC'}

    for name, files in cycles.items():
        if files is None:
            continue
        excel_name, csv_name = files
        speeds = read_from_excel(excel_name)
        if speeds is None:
            continue
        csv_path = save_to_csv(speeds, csv_name, name)
        plot_cycle(csv_path, f'{name} Drive Cycle')

    print('\n完成！生成的文件在 results/ 目录下')
