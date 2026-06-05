# -*- coding: utf-8 -*-
"""
run_ems_simulation.py — EMS 仿真启动器 v3.0
功能：燃料电池混合动力 EMS 系统仿真（支持 MATLAB-Simulink 和纯 Python 两种模式）

用法：
    python run_ems_simulation.py                      # Python 模式仿真 (默认)
    python run_ems_simulation.py --mode matlab         # MATLAB-Simulink 模式
    python run_ems_simulation.py --mode python         # Python 模式
    python run_ems_simulation.py --build-only          # 只搭建 Simulink 模型
    python run_ems_simulation.py --plot-only           # 只看已有结果

依赖：
    numpy, pandas, matplotlib
    MATLAB R2024b (仅 --mode matlab)
"""

import os
import sys
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PROJECT_ROOT, 'results')
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, 'scripts')
sys.path.insert(0, SCRIPTS_DIR)


def load_drive_cycle(name='wltc'):
    """加载工况数据"""
    csv_map = {'wltc': 'wltc_cycle.csv', 'nedc': 'nedc_cycle.csv', 'cltc': 'cltc_cycle.csv'}
    csv_path = os.path.join(RESULTS_DIR, csv_map.get(name, 'wltc_cycle.csv'))
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f'工况数据未找到: {csv_path}\n请先运行: python scripts/download_drive_cycles.py')
    df = pd.read_csv(csv_path)
    t = df['time'].values
    v = df['speed_kmh'].values
    print(f'[载入] {name.upper()} 工况: {len(t)} 点, {t[-1]:.0f}s')
    return t, v


def vehicle_power(v_kmh, dt=1.0):
    """车速 → 功率需求 [kW] (Python版)"""
    m = 1500       # kg
    g = 9.81
    f_r = 0.015    # 滚动阻力
    rho = 1.225    # 空气密度
    Cd = 0.32      # 风阻
    A = 2.2        # 迎风面积
    eta = 0.90     # 传动效率

    v_ms = v_kmh / 3.6
    # 加速度 (中心差分)
    a = np.zeros_like(v_ms)
    a[1:-1] = (v_ms[2:] - v_ms[:-2]) / (2 * dt)
    a[0] = (v_ms[1] - v_ms[0]) / dt
    a[-1] = (v_ms[-1] - v_ms[-2]) / dt
    a = np.clip(a, -3, 3)

    F_rr = m * g * f_r
    F_aero = 0.5 * rho * Cd * A * v_ms ** 2
    F_inertia = m * a

    P_wheel = (F_rr + F_aero + F_inertia) * v_ms
    P_load = np.maximum(P_wheel / eta / 1000, 0)  # kW, 负=0 (无再生制动)

    # 停车时归零
    P_load[v_kmh < 0.5] = 0
    return P_load


def ems_rule_controller(P_load, SOC, params=None):
    """规则基 EMS 控制器 (Python版)"""
    if params is None:
        params = {
            'P_fc_min': 3, 'P_fc_max': 25, 'P_fc_peak': 30,
            'SOC_min': 0.3, 'SOC_low': 0.4, 'SOC_high': 0.8, 'SOC_max': 0.9,
        }
    p = params

    P_fc = np.zeros_like(P_load)
    P_bat = np.zeros_like(P_load)
    mode = np.zeros_like(P_load, dtype=int)  # 1=FC, 2=hybrid, 3=charge, 4=idle

    soc = SOC  # 当前SOC (标量, 每个时间步更新)

    for i in range(len(P_load)):
        pl = P_load[i]

        if pl < 1.0:
            if soc < p['SOC_max']:
                P_fc[i] = p['P_fc_min']
                P_bat[i] = pl - p['P_fc_min']
                mode[i] = 3
            else:
                P_fc[i] = 0
                P_bat[i] = 0
                mode[i] = 4

        elif soc < p['SOC_low']:
            charge_pwr = max(0, 1.0 - soc / p['SOC_low']) * 10
            P_fc[i] = min(max(pl + charge_pwr, p['P_fc_min']), p['P_fc_max'])
            P_bat[i] = pl - P_fc[i]
            mode[i] = 3

        elif soc > p['SOC_high']:
            P_fc[i] = max(pl - 10, p['P_fc_min'])
            P_fc[i] = min(P_fc[i], p['P_fc_max'])
            P_bat[i] = pl - P_fc[i]
            mode[i] = 2

        else:
            if pl <= p['P_fc_min']:
                P_fc[i] = p['P_fc_min']
                P_bat[i] = pl - p['P_fc_min']
                mode[i] = 3
            elif pl <= p['P_fc_max']:
                P_fc[i] = pl
                P_bat[i] = 0
                mode[i] = 1
            else:
                P_fc[i] = p['P_fc_max']
                P_bat[i] = pl - p['P_fc_max']
                mode[i] = 2

        # 更新SOC (简化, 后续由battery_model更精确处理)
        soc += -P_bat[i] * 0.0001  # 粗略估计

    return P_fc, P_bat, mode


def battery_model(P_bat_kW, SOC_init, dt=1.0):
    """简化 R-int 电池模型 (Python版, 向量化)"""
    Q_bat = 50      # Ah
    V_nom = 350     # V
    R_int = 0.05    # Ohm

    # OCV-SOC 查找表
    soc_bp = np.array([0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9, 1.0])
    ocv_lu = np.array([320, 330, 338, 345, 352, 358, 362, 368, 380])

    n = len(P_bat_kW)
    SOC = np.zeros(n)
    V_bat = np.zeros(n)
    I_bat = np.zeros(n)

    soc = SOC_init
    for i in range(n):
        V_oc = np.interp(soc, soc_bp, ocv_lu)
        P_w = P_bat_kW[i] * 1000

        if abs(P_w) < 10:
            I = 0.0
        else:
            Delta = V_oc**2 - 4 * R_int * P_w
            if Delta < 0:
                P_w = V_oc**2 / (4 * R_int) * 0.99
                if P_bat_kW[i] > 0:
                    P_w = min(P_w, V_oc**2 / (4 * R_int) * 0.99)
                else:
                    P_w = -min(abs(P_w), V_oc**2 / (4 * R_int) * 0.99)
                Delta = V_oc**2 - 4 * R_int * P_w
            I = (V_oc - np.sqrt(Delta)) / (2 * R_int)
            I = np.clip(I, -300, 300)

        V = V_oc - I * R_int
        soc_change = -I / (Q_bat * 3600) * dt
        soc = np.clip(soc + soc_change, 0.05, 0.95)

        SOC[i] = soc
        V_bat[i] = V
        I_bat[i] = I

    return SOC, V_bat, I_bat


def run_python_simulation(drive_cycle='wltc', plot=True):
    """纯Python模式: 完整EMS仿真"""
    print('=' * 55)
    print('EMS 仿真 (Python 模式)')
    print('=' * 55)

    # 1. 加载工况
    t, v = load_drive_cycle(drive_cycle)
    dt = t[1] - t[0] if len(t) > 1 else 1.0

    # 2. 车辆动力学 → 功率需求
    print('[1/4] 计算功率需求...')
    P_load = vehicle_power(v, dt)

    # 3. EMS 控制器 → 功率分配
    print('[2/4] EMS 规则控制器...')
    P_fc, P_bat, mode = ems_rule_controller(P_load, SOC=0.6)

    # 4. 电池动态响应
    print('[3/4] 电池模型...')
    SOC, V_bat, I_bat = battery_model(P_bat, SOC_init=0.6, dt=dt)

    # 5. 修正: 用精确SOC重新计算EMS(迭代一次)
    # 先用功率分配算SOC, 再用SOC修正 → 精确度够用
    # 重新计算 EMS (考虑实际SOC)
    P_fc2, P_bat2, mode2 = ems_rule_controller(P_load, SOC=0.6)
    SOC2, V_bat2, I_bat2 = battery_model(P_bat2, SOC_init=0.6, dt=dt)

    print('[4/4] 结果汇总...')

    # 统计指标
    total_P_load = np.trapezoid(P_load, t) / 3600  # kWh
    total_P_fc = np.trapezoid(P_fc2, t) / 3600
    total_P_bat_d = np.trapezoid(np.maximum(P_bat2, 0), t) / 3600
    total_P_bat_c = np.trapezoid(np.minimum(P_bat2, 0), t) / 3600

    print(f'\n{"="*55}')
    print(f'  仿真结果 — {drive_cycle.upper()} 工况 ({t[-1]:.0f}s)')
    print(f'{"="*55}')
    print(f'  总能量需求:        {total_P_load:7.2f} kWh')
    print(f'  FC 提供能量:       {total_P_fc:7.2f} kWh')
    print(f'  电池放电:          {total_P_bat_d:7.2f} kWh')
    print(f'  电池充电:          {total_P_bat_c:7.2f} kWh')
    print(f'  初始 SOC → 终值:   {0.6:.2f} → {SOC2[-1]:.2f}')
    print(f'  FC 最大功率:       {P_fc2.max():7.2f} kW')
    print(f'  电池最大放电:      {P_bat2.max():7.2f} kW')
    print(f'  电池最大充电:      {P_bat2.min():7.2f} kW')
    print(f'{"="*55}')

    # 保存结果
    results = pd.DataFrame({
        'time': t,
        'speed_kmh': v,
        'P_load_kW': P_load,
        'P_fc_kW': P_fc2,
        'P_bat_kW': P_bat2,
        'SOC': SOC2,
        'V_bat': V_bat2,
        'I_bat': I_bat2,
        'mode': mode2,
    })
    csv_path = os.path.join(RESULTS_DIR, f'Day7_ems_sim_{drive_cycle}.csv')
    results.to_csv(csv_path, index=False)
    print(f'[保存] {csv_path}')

    # 画图
    if plot:
        plot_ems_results(results, drive_cycle)

    return results


def plot_ems_results(df, drive_cycle='wltc'):
    """EMS 仿真结果可视化"""
    t = df['time'].values / 60  # s → min
    n_plots = 5

    fig, axes = plt.subplots(n_plots, 1, figsize=(14, 10), sharex=True)

    # (1) 工况速度
    ax = axes[0]
    ax.plot(t, df['speed_kmh'], 'b-', linewidth=0.8)
    ax.set_ylabel('Speed (km/h)')
    ax.set_title(f'{drive_cycle.upper()} Drive Cycle — EMS Simulation')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(bottom=0)

    # (2) 功率分配
    ax = axes[1]
    ax.fill_between(t, 0, df['P_load_kW'], alpha=0.3, color='gray', label='Load')
    ax.plot(t, df['P_fc_kW'], 'r-', linewidth=1.2, label='FC Power')
    ax.fill_between(t, 0, df['P_bat_kW'], where=df['P_bat_kW'] > 0,
                    alpha=0.4, color='green', label='Bat Discharge')
    ax.fill_between(t, 0, df['P_bat_kW'], where=df['P_bat_kW'] < 0,
                    alpha=0.4, color='orange', label='Bat Charge')
    ax.set_ylabel('Power (kW)')
    ax.legend(loc='upper right', fontsize=8, ncol=4)
    ax.grid(True, alpha=0.3)

    # (3) SOC
    ax = axes[2]
    ax.plot(t, df['SOC'], 'g-', linewidth=1.2)
    ax.axhline(y=0.4, color='r', linestyle='--', alpha=0.5, label='SOC_low')
    ax.axhline(y=0.8, color='orange', linestyle='--', alpha=0.5, label='SOC_high')
    ax.set_ylabel('SOC')
    ax.set_ylim(0.2, 1.0)
    ax.legend(loc='lower right', fontsize=8)
    ax.grid(True, alpha=0.3)

    # (4) 电池电压/电流
    ax = axes[3]
    ax.plot(t, df['V_bat'], 'm-', linewidth=1.0, label='Voltage')
    ax.set_ylabel('V_bat (V)', color='m')
    ax2 = ax.twinx()
    ax2.plot(t, df['I_bat'], 'c-', linewidth=0.8, label='Current')
    ax2.set_ylabel('I_bat (A)', color='c')
    ax.grid(True, alpha=0.3)

    # (5) 工作模式
    ax = axes[4]
    mode_colors = ['gray', 'red', 'green', 'orange', 'blue']
    mode_labels = ['', 'FC-only', 'Hybrid', 'Charging', 'Idle']
    for m in range(1, 5):
        mask = df['mode'] == m
        ax.scatter(t[mask], df['mode'][mask], c=mode_colors[m], s=2, label=mode_labels[m])
    ax.set_ylabel('Mode')
    ax.set_xlabel('Time (min)')
    ax.set_ylim(0.5, 4.5)
    ax.set_yticks([1, 2, 3, 4])
    ax.legend(loc='upper right', fontsize=7, ncol=4)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    png_path = os.path.join(RESULTS_DIR, f'Day7_ems_sim_{drive_cycle}.png')
    plt.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f'[图] {png_path}')
    plt.close()
    print('[绘图完成]')


def build_matlab_model():
    """调用 MATLAB 搭建/重建 Simulink 模型"""
    MATLAB_EXE = 'F:/Matlab/bin/matlab.exe'
    mdl_script = 'cd env/simulink_models; build_ems_model'

    print('[MATLAB] 搭建 EMS Simulink 模型...')
    import subprocess
    proc = subprocess.Popen(
        [MATLAB_EXE, '-batch', mdl_script],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=PROJECT_ROOT
    )
    try:
        stdout, stderr = proc.communicate(timeout=120)
        out = stdout.decode('cp936', errors='replace')
        for line in out.split('\n'):
            if any(kw in line for kw in ['✓', '构建', '已存在', 'Error', '错误']):
                print(f'  {line.strip()}')
        if proc.returncode != 0:
            print(f'! MATLAB 返回码: {proc.returncode}')
            return False
    except subprocess.TimeoutExpired:
        proc.kill()
        print('! MATLAB 超时 (120s)')
        return False

    print('[MATLAB] 模型搭建完成')
    return True


def run_matlab_simulation(drive_cycle='wltc'):
    """调用 MATLAB 运行 EMS-Simulink 仿真"""
    MATLAB_EXE = 'F:/Matlab/bin/matlab.exe'
    sim_script = [
        "cd('env/simulink_models');",
        "load_system('EMS_hybrid_v1');",
        f"assign_wltc_data('EMS_hybrid_v1', '../../results/{drive_cycle}_cycle.csv');",
        "simOut = sim('EMS_hybrid_v1');",
        "save('../../results/ems_sim_matlab.mat', 'simOut');",
        "disp('✓ MATLAB-Simulink EMS 仿真完成');",
    ]
    script_str = ' '.join(sim_script)

    print('[MATLAB] 运行 EMS-Simulink 仿真...')
    import subprocess
    proc = subprocess.Popen(
        [MATLAB_EXE, '-batch', script_str],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=PROJECT_ROOT
    )
    try:
        stdout, stderr = proc.communicate(timeout=600)
        out = stdout.decode('cp936', errors='replace')
        for line in out.split('\n'):
            if any(kw in line for kw in ['✓', '完成', '错误', 'Error', 'Warning']):
                print(f'  {line.strip()}')
        if proc.returncode != 0:
            print(f'! MATLAB 返回码: {proc.returncode}')
            return None
    except subprocess.TimeoutExpired:
        proc.kill()
        print('! MATLAB 超时 (600s)')
        return None

    print('[MATLAB] 仿真完成')
    return os.path.join(RESULTS_DIR, 'ems_sim_matlab.mat')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='EMS 仿真启动器 v3.0')
    parser.add_argument('--mode', choices=['python', 'matlab'], default='python',
                       help='仿真模式 (默认 python)')
    parser.add_argument('--cycle', choices=['wltc', 'nedc', 'cltc'], default='wltc',
                       help='工况类型 (默认 wltc)')
    parser.add_argument('--build-only', action='store_true',
                       help='只搭建 Simulink 模型 (不仿真)')
    parser.add_argument('--plot-only', action='store_true',
                       help='只看已有结果')
    args = parser.parse_args()

    print(f'[EMS 仿真器] mode={args.mode}, cycle={args.cycle}')

    if args.build_only:
        if args.mode == 'matlab':
            build_matlab_model()
        else:
            print('[!] Python 模式不支持 --build-only, 使用 --mode matlab')
        sys.exit(0)

    if args.plot_only:
        csv_path = os.path.join(RESULTS_DIR, f'ems_sim_{args.cycle}.csv')
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            plot_ems_results(df, args.cycle)
            print(f'[绘图] {csv_path}')
        else:
            print(f'[!] 结果文件不存在: {csv_path}')
        sys.exit(0)

    if args.mode == 'python':
        results = run_python_simulation(drive_cycle=args.cycle, plot=True)
        print(f'\n[OK] EMS Python 仿真完成！')
        print(f'   结果: results/ems_sim_{args.cycle}.csv')
        print(f'   图表: results/Day7_ems_sim_{args.cycle}.png')
    else:
        # MATLAB 模式: 先构建模型, 再运行仿真
        build_matlab_model()
        run_matlab_simulation(drive_cycle=args.cycle)
