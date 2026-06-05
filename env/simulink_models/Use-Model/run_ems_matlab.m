%% run_ems_matlab.m — 运行 EMS_hybrid_v1 仿真并保存结果

PROJECT_ROOT = 'F:/CLAUDE/research/ems-platform';
RESULTS_DIR = fullfile(PROJECT_ROOT, 'results');
cd(fullfile(PROJECT_ROOT, 'env/simulink_models/Use-Model'));

fprintf('===== EMS 仿真收尾验证 =====\n');

%% 1. 准备
fprintf('[1/4] 准备...\n');
load_system('EMS_hybrid_v1');
data = csvread(fullfile(RESULTS_DIR, 'wltc_cycle.csv'), 1, 0);
assignin('base', 'sim_wltc', [data(:,1), data(:,2)]);

%% 2. 仿真
fprintf('[2/4] 仿真 (1800s)...\n');
tic;
simOut = sim('EMS_hybrid_v1', 'StopTime', '1800');
fprintf('  仿真: %.1f s\n', toc);

%% 3. 读结果
fprintf('[3/4] 保存...\n');
% 读取 To Workspace 数据
P_load  = get_sim_var(simOut, 'sim_P_load');
P_fc    = get_sim_var(simOut, 'sim_P_fc');
SOC     = get_sim_var(simOut, 'sim_SOC');
V_bat   = get_sim_var(simOut, 'sim_V_bat');
V_fc    = get_sim_var(simOut, 'sim_V_fc');
I_bat   = get_sim_var(simOut, 'sim_I_bat');
status  = get_sim_var(simOut, 'sim_status');

% debug: 检查前几个值
fprintf('  P_load[1:5] = [%.2f %.2f %.2f %.2f %.2f]\n', P_load(1:5));
fprintf('  P_fc[1:5]   = [%.2f %.2f %.2f %.2f %.2f]\n', P_fc(1:5));
fprintf('  V_fc[1:5]   = [%.2f %.2f %.2f %.2f %.2f]\n', V_fc(1:5));
fprintf('  SOC[1:5]    = [%.4f %.4f %.4f %.4f %.4f]\n', SOC(1:5));
fprintf('  V_bat[1:5]  = [%.2f %.2f %.2f %.2f %.2f]\n', V_bat(1:5));

min_len = min([length(P_load) length(P_fc) length(SOC)]);
% 使用 tout 时间向量 (变步长求解器)
try t_vec = simOut.tout; catch, t_vec = linspace(0, 1800, min_len)'; end
t_vec = t_vec(1:min_len);

T = table(t_vec, P_load(1:min_len), P_fc(1:min_len), ...
    SOC(1:min_len), V_bat(1:min_len), ...
    'VariableNames', {'time','P_load_kW','P_fc_kW','SOC','V_bat'});

csv_path = fullfile(RESULTS_DIR, 'Day7_ems_sim_matlab_wltc.csv');
writetable(T, csv_path);
fprintf('  -> %s (%d 行)\n', csv_path, min_len);

%% 4. 统计
fprintf('[4/4] 结果:\n');
fprintf('  ─────────────────────────────\n');
fprintf('  总能量:     %.2f kWh\n', trapz(T.time, T.P_load_kW)/3600);
fprintf('  FC能量:     %.2f kWh\n', trapz(T.time, T.P_fc_kW)/3600);
fprintf('  SOC:        %.2f -> %.2f\n', T.SOC(1), T.SOC(end));
fprintf('  FC最大功率:  %.1f kW\n', max(P_fc));
fprintf('  ─────────────────────────────\n');
fprintf('[✓] 第2周收尾完成! 下一步: 第3周 DP\n');

%% 辅助函数
function v = get_sim_var(simOut, name)
    val = simOut.get(name);
    if isa(val, 'timeseries')
        v = val.Data;
    elseif isstruct(val) && isfield(val, 'signals')
        v = val.signals.values;
    else
        v = val;
    end
    v = double(v(:));  % 确保双精度列向量
end
