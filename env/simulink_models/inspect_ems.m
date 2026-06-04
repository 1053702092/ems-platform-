% inspect_ems.m — 查看 EMS 控制逻辑和 Load Profile
mdl = 'power_FCHPS_MEA2';
mdl_path = '资料/燃料电池-蓄电池-超级电容交直流微网能量管理策略Simulink模型/47901-main/燃料电池-混合储能微网EMS/power_FCHPS_MEA2.slx';
load_system(mdl_path);

% EMS 子系统内部
fprintf('===== EMS 子系统顶层模块 =====\n');
ems_blks = find_system([mdl '/Energy Management System'], 'SearchDepth', 1);
for i = 2:length(ems_blks)
    bt = get_param(ems_blks{i}, 'BlockType');
    name = get_param(ems_blks{i}, 'Name');
    fprintf('  [%s] %s\n', bt, name);
end

% Load Profile 模块
fprintf('\n===== Load Profile =====\n');
lp = [mdl '/Load Profile'];
fprintf('类型: %s\n', get_param(lp, 'BlockType'));
fprintf('参数:\n');
params = get_param(lp, 'DialogParameters');
if isstruct(params)
    pn = fieldnames(params);
    for i = 1:length(pn)
        fprintf('  %s\n', pn{i});
    end
end

% FC Power Module
fprintf('\n===== FC Power Module 顶层 =====\n');
fc = find_system([mdl '/Fuel Cell Power Module (FCPM)'], 'SearchDepth', 1);
for i = 2:length(fc)
    bt = get_param(fc{i}, 'BlockType');
    name = get_param(fc{i}, 'Name');
    fprintf('  [%s] %s\n', bt, name);
end

% 连接关系：FC DCDC 到 EMS
fprintf('\n===== 关键连接 =====\n');
% 查 EMS 输入输出名
for p = 1:6
    try
        lh = get_param([mdl '/Energy Management System'], 'LineHandles');
        src = get_param(lh.Inport(p), 'SrcPortHandle');
        src_block = get_param(src, 'Parent');
        fprintf('EMS 输入%s <- %s\n', num2str(p), src_block);
    catch
    end
end

close_system(mdl, 0);
