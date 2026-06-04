# -*- coding: utf-8 -*-
"""
run_simulation.py — EMS 仿真启动器 (v2.0)
功能：通过 Python 调用 MATLAB/Simulink 运行燃料电池模型，
      完成 I-V 特性扫描，保存结果并可视化。

用法：
    python run_simulation.py                         # 运行完整 I-V 扫描
    python run_simulation.py --sweep-only            # 只跑扫描
    python run_simulation.py --plot-only             # 只画图

依赖：
    MATLAB R2024b (F:/Matlab/bin/matlab.exe)
    numpy, pandas, matplotlib
"""

import subprocess
import time
import os
import sys
import argparse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATLAB_EXE = 'F:/Matlab/bin/matlab.exe'
RESULTS_DIR = os.path.join(PROJECT_ROOT, 'results')

os.makedirs(RESULTS_DIR, exist_ok=True)


def run_iv_sweep():
    """调用 MATLAB 执行 I-V 扫描"""
    matlab_script = os.path.join(PROJECT_ROOT, 'env', 'simulink_models',
                                  'cell_model_iv_sweep.m')
    print('=' * 50)
    print('EMS 仿真器 — Cell_model_v10 I-V 扫描')
    print('=' * 50)

    # 先确保 Cell_model_v10_lit 存在
    if not os.path.exists(os.path.join(PROJECT_ROOT, 'env', 'simulink_models',
                                        'Cell_model_v10_lit.slx')):
        print('[1/3] 创建 Cell_model_v10_lit (带数据记录)...')
        proc = subprocess.Popen(
            [MATLAB_EXE, '-batch',
             "cd('" + PROJECT_ROOT.replace(os.sep, '/')
             + "/env/simulink_models'); setup_cell_model_logging"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        proc.communicate(timeout=120)
        print('  模型创建完成')
    else:
        print('[1/3] Cell_model_v10_lit 已存在')

    print('[2/3] 执行 I-V 扫描...')
    proc = subprocess.Popen(
        [MATLAB_EXE, '-batch',
         "cd('" + PROJECT_ROOT.replace(os.sep, '/')
         + "/env/simulink_models'); cell_model_iv_sweep"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        stdout, stderr = proc.communicate(timeout=180)
        out = stdout.decode('cp936', errors='replace')
        for line in out.split('\n'):
            if any(kw in line for kw in ['I=', 'V=', '完成', '已保存', 'Error']):
                print(f'  {line.strip()}')
        print('[3/3] I-V 扫描完成')
    except subprocess.TimeoutExpired:
        proc.kill()
        print('! MATLAB 超时')
        return False

    return True


def plot_results():
    """画 I-V 曲线"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import plot_iv_curve


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='EMS 仿真启动器 v2.0')
    parser.add_argument('--sweep-only', action='store_true', help='只跑 I-V 扫描')
    parser.add_argument('--plot-only', action='store_true', help='只画图')
    args = parser.parse_args()

    if args.plot_only:
        plot_results()
        sys.exit(0)

    if args.sweep_only or run_iv_sweep():
        plot_results()

    print('\n✅ Day6 任务完成！')
    print(f'   CSV: {RESULTS_DIR}/cell_model_iv_sweep.csv')
    print(f'   图:  {RESULTS_DIR}/cell_model_iv_curve.png')
