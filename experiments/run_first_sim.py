# -*- coding: utf-8 -*-
"""首次完整仿真：Python -> MATLAB -> Simulink -> 读结果"""
import subprocess, time, os, sys

PROJECT = 'F:/CLAUDE/research/ems-platform'
RESULTS = os.path.join(PROJECT, 'results')
os.makedirs(RESULTS, exist_ok=True)

print('=' * 50)
print('第1次完整仿真')
print(f'模型: Energy.slx')
print(f'MATLAB: F:/Matlab/bin/matlab.exe')
print('=' * 50)

t0 = time.time()
proc = subprocess.Popen(
    ['F:/Matlab/bin/matlab.exe', '-batch',
     "run('F:/CLAUDE/research/ems-platform/experiments/run_first_sim.m')"],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE
)

try:
    stdout, stderr = proc.communicate(timeout=300)
    out = stdout.decode('cp936', errors='replace')
    err = stderr.decode('cp936', errors='replace')

    print(f'\n⏱ 总耗时: {time.time()-t0:.1f}s (退出码: {proc.returncode})')
    print('-' * 50)

    # 显示关键输出
    for line in out.split('\n'):
        line_s = line.strip()
        if line_s and ('工作区' in line_s or '找到' in line_s or '开始' in line_s
                       or '完成' in line_s or '结果' in line_s or '耗时' in line_s
                       or '变量' in line_s or '模型' in line_s):
            print(f'  {line_s}')

    if err.strip():
        print(f'\nMATLAB 错误输出: {err[:500]}')

    # 检查结果文件
    mat_file = os.path.join(RESULTS, 'sim_first_run.mat')
    if os.path.exists(mat_file):
        size = os.path.getsize(mat_file)
        print(f'\n✅ 仿真结果已保存: {mat_file} ({size/1024:.1f}KB)')
    else:
        print('\n⚠️  未生成结果文件（首次空跑正常）')

except subprocess.TimeoutExpired:
    proc.kill()
    print('❌ MATLAB 超时（300s）')
except Exception as e:
    print(f'❌ 错误: {e}')
