%% run_ems_matlab.m — 在 MATLAB 中运行 EMS_hybrid_v1 仿真并保存结果
% 用法: 在命令行执行:  run_ems_matlab
%       或: matlab -batch "cd('F:/CLAUDE/research/ems-platform/env/simulink_models/Use-Model'); run_ems_matlab"

PROJECT_ROOT = 'F:/CLAUDE/research/ems-platform';
MODEL_DIR = fullfile(PROJECT_ROOT, 'env/simulink_models/Use-Model');
RESULTS_DIR = fullfile(PROJECT_ROOT, 'results');

cd(MODEL_DIR);

fprintf('===== EMS 仿真收尾验证 =====\n');

%% 1. 加载模型
fprintf('[1/5] 加载模型...\n');
if ~exist('EMS_hybrid_v1', 'file')
    error('EMS_hybrid_v1.slx 不存在，请先运行 build_ems_model');
end
load_system('EMS_hybrid_v1');

%% 2. 加载 WLTC 数据到工作区
fprintf('[2/5] 加载 WLTC 数据...\n');
wltc_csv = fullfile(RESULTS_DIR, 'wltc_cycle.csv');
if ~exist(wltc_csv, 'file')
    error('WLTC 数据不存在: %s', wltc_csv);
end
data = csvread(wltc_csv, 1, 0);
sim_wltc = [data(:,1), data(:,2)];
assignin('base', 'sim_wltc', sim_wltc);
fprintf('  WLTC 数据: %d 点, %.0f s\n', length(data), data(end,1));

%% 3. 运行仿真
fprintf('[3/5] 运行仿真 (1800s)...\n');
tic;
simOut = sim('EMS_hybrid_v1');
t_elapsed = toc;
fprintf('  仿真完成: %.1f s (实时 %.1f%%)', t_elapsed, 1800/t_elapsed*100);

%% 4. 保存结果为 CSV
fprintf('[4/5] 保存结果...\n');
t_out = simOut.tout;
% 获取 To Workspace 变量
try
    P_fc = simOut.get('sim_P_fc');
catch
    P_fc = evalin('base', 'sim_P_fc');
end
try
    SOC = simOut.get('sim_SOC');
catch
    SOC = evalin('base', 'sim_SOC');
end
try
    P_load = simOut.get('sim_P_load');
catch
    P_load = evalin('base', 'sim_P_load');
end
try
    V_fc = simOut.get('sim_V_fc');
catch
    V_fc = evalin('base', 'sim_V_fc');
end
try
    V_bat = simOut.get('sim_V_bat');
catch
    V_bat = evalin('base', 'sim_V_bat');
end
try
    I_bat = simOut.get('sim_I_bat');
catch
    I_bat = evalin('base', 'sim_I_bat');
end
try
    status = simOut.get('sim_status');
catch
    status = evalin('base', 'sim_status');
end

% 保证长度一致
min_len = min([length(P_fc), length(SOC), length(P_load), ...
               length(V_fc), length(V_bat), length(I_bat), length(status)]);
T = table((0:min_len-1)', P_load(1:min_len), P_fc(1:min_len), ...
    SOC(1:min_len), V_bat(1:min_len), I_bat(1:min_len), status(1:min_len), ...
    'VariableNames', {'time', 'P_load_kW', 'P_fc_kW', 'SOC', 'V_bat', 'I_bat', 'mode'});
csv_path = fullfile(RESULTS_DIR, 'ems_sim_matlab_wltc.csv');
writetable(T, csv_path);
fprintf('  ✓ 已保存: %s (%d 行)\n', csv_path, min_len);

%% 5. 输出统计
fprintf('[5/5] 结果统计:\n');
fprintf('  ─────────────────────────────\n');
fprintf('  总能量需求:     %.2f kWh\n', trapz(T.P_load_kW) / 3600);
fprintf('  FC 提供能量:    %.2f kWh\n', trapz(T.P_fc_kW) / 3600);
fprintf('  初始 SOC → 终值: %.2f → %.2f\n', T.SOC(1), T.SOC(end));
fprintf('  FC 最大功率:    %.2f kW\n', max(T.P_fc_kW));
fprintf('  电池最大放电:   %.2f kW\n', max(T.P_load_kW - T.P_fc_kW));
fprintf('  ─────────────────────────────\n');
fprintf('[✓] EMS 仿真收尾验证完成!\n');

end
