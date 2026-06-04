% inspect_ref_ems.m — 查看参考 EMS 模型的结构
mdl = 'power_FCHPS_MEA2';
mdl_path = '资料/燃料电池-蓄电池-超级电容交直流微网能量管理策略Simulink模型/47901-main/燃料电池-混合储能微网EMS/power_FCHPS_MEA2.slx';

if ~exist(mdl_path, 'file')
    error('模型不存在: %s', mdl_path);
end

load_system(mdl_path);
fprintf('===== %s =====\n', mdl);
fprintf('描述: %s\n', get_param(mdl, 'Description'));
fprintf('求解器: %s\n', get_param(mdl, 'SolverName'));
fprintf('StopTime: %s\n', get_param(mdl, 'StopTime'));

% 顶层模块
blks = find_system(mdl, 'SearchDepth', 1);
fprintf('\n顶层模块 (%d个):\n', length(blks)-1);
for i = 2:length(blks)
    bt = get_param(blks{i}, 'BlockType');
    fprintf('  [%s] %s\n', bt, get_param(blks{i}, 'Name'));
end

% To Workspace
tw = find_system(mdl, 'BlockType', 'ToWorkspace');
fprintf('\nTo Workspace (%d个):\n', length(tw));
for i = 1:length(tw)
    fprintf('  %s → var: %s\n', tw{i}, get_param(tw{i}, 'VariableName'));
end

% Scope
sc = find_system(mdl, 'BlockType', 'Scope');
fprintf('\nScope (%d个)\n', length(sc));

close_system(mdl, 0);
