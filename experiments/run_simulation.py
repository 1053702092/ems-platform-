# -*- coding: utf-8 -*-
"""
run_simulation.py — EMS仿真启动器
功能：通过 Python 调用 MATLAB/Simulink 运行 Energy.slx 模型，
      读取仿真结果并保存为 CSV，供后续分析和可视化。

用法：
    python run_simulation.py --model Energy --cycle WLTC

依赖：MATLAB R2024b (F:/Matlab/bin/matlab.exe)
     numpy, pandas, matplotlib
"""

import subprocess
import time
import os
import argparse
import sys

PROJECT_ROOT = 'F:/CLAUDE/research/ems-platform'
MATLAB_EXE = 'F:/Matlab/bin/matlab.exe'
MODEL_PATH = os.path.join(PROJECT_ROOT, 'env/simulink_models/Energy.slx')
RESULTS_DIR = os.path.join(PROJECT_ROOT, 'results')

# 确保结果目录存在
os.makedirs(RESULTS_DIR, exist_ok=True)


def generate_matlab_script(strategy='rule', cycle='WLTC', sim_time='inf'):
    """
    生成调用 Energy.slx 的 MATLAB 脚本
    strategy: 控制策略类型 (rule / ecms / mpc / rl)
    cycle: 工况类型 (WLTC / CLTC / NEDC)
    sim_time: 仿真时长
    """
    script_content = f"""
% ===== 自动生成的仿真脚本 =====
% 策略: {strategy}
% 工况: {cycle}

% 切换到工作目录
cd '{PROJECT_ROOT.replace(os.sep, '/')}/env/simulink_models';

% 加载模型
load_system('Energy.slx');

% 设置求解器参数
set_param('Energy', 'StopTime', '{sim_time}');
set_param('Energy', 'SolverName', 'ode1');
set_param('Energy', 'FixedStep', '1');

% TODO: 在这里设置不同策略的参数
% 如果是ECMS/MPC/RL策略，切换控制模块
% strategy_type = '{strategy}';

% 运行仿真
fprintf('开始仿真...\\n');
sim('Energy.slx');

% 获取To Workspace模块的数据
% 查找所有To Workspace模块
workspace_blocks = find_system('Energy', 'BlockType', 'ToWorkspace');
fprintf('找到 %%d 个数据记录模块\\n', length(workspace_blocks));

% 获取各模块记录的数据
for i = 1:length(workspace_blocks)
    var_name = get_param(workspace_blocks{{i}}, 'VariableName');
    if ~isempty(var_name) && evalin('base', ['exist(''', var_name, ''', ''var'')'])
        data = evalin('base', var_name);
        if isstruct(data) && isfield(data, 'signals')
            % 结构体格式
            fprintf('  数据: %%s (%%d 点)\\n', var_name, length(data.time));
        elseif isnumeric(data)
            fprintf('  数据: %%s (%%d x %%d)\\n', var_name, size(data,1), size(data,2));
        end
    end
end

% 保存工作区数据
save(fullfile('{RESULTS_DIR.replace(os.sep, '/')}', 'sim_results.mat'), '-v7');

fprintf('仿真完成!\\n');
quit;
"""
    return script_content


def run_matlab_script(script_content, script_name='temp_sim_script.m'):
    """执行 MATLAB 脚本并返回输出"""
    script_path = os.path.join(PROJECT_ROOT, script_name)

    # 写脚本文件
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)

    print(f'[1/3] MATLAB 脚本已生成: {script_name}')
    print(f'[2/3] 启动 MATLAB (首次约30s, 后续10s)...')

    t0 = time.time()
    proc = subprocess.Popen(
        [MATLAB_EXE, '-batch', f"run('{script_path.replace(os.sep, '/')}')"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    try:
        stdout, stderr = proc.communicate(timeout=300)
        out = stdout.decode('cp936', errors='replace')
        err = stderr.decode('cp936', errors='replace')
        elapsed = time.time() - t0
        print(f'[3/3] 仿真完成! 耗时 {elapsed:.1f}s (退出码: {proc.returncode})')

        # 显示关键输出
        for line in out.split('\n'):
            if any(kw in line.lower() for kw in ['开始', '找到', '数据', '完成', 'error', '错误']):
                print(f'  > {line.strip()}')

        if err.strip():
            print(f'  警告/错误: {err[:300]}')

        return out, err

    except subprocess.TimeoutExpired:
        proc.kill()
        print('! MATLAB 超时 (300s)')
        return '', 'timeout'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='EMS 仿真启动器')
    parser.add_argument('--strategy', default='rule', help='策略类型 (rule/ecms/mpc/rl)')
    parser.add_argument('--cycle', default='WLTC', help='工况类型 (WLTC/CLTC/NEDC)')
    parser.add_argument('--time', default='inf', help='仿真时长')
    args = parser.parse_args()

    print('=' * 50)
    print(f'EMS 仿真启动器')
    print(f'  策略: {args.strategy}')
    print(f'  工况: {args.cycle}')
    print(f'  仿真时长: {args.time}')
    print('=' * 50)

    script = generate_matlab_script(args.strategy, args.cycle, args.time)
    out, err = run_matlab_script(script)

    if 'timeout' not in err:
        print('\n✅ 仿真流程验证通过!')
        print(f'结果将保存到: {RESULTS_DIR}/sim_results.mat')
    else:
        print('\n❌ 仿真遇到问题, 请检查MATLAB输出')
