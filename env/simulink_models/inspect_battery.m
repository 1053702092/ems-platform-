% inspect_battery.m — 查看参考模型 Battery 子系统和 Lead_Acid_Battery
mdl = 'power_FCHPS_MEA2';
mdl_path = '资料/燃料电池-蓄电池-超级电容交直流微网能量管理策略Simulink模型/47901-main/燃料电池-混合储能微网EMS/power_FCHPS_MEA2.slx';

load_system(mdl_path);
fprintf('===== Battery 子系统 =====\n');
blks = find_system([mdl '/Battery'], 'SearchDepth', 1);
for i = 2:length(blks)
    bt = get_param(blks{i}, 'BlockType');
    fprintf('  [%s] %s\n', bt, get_param(blks{i}, 'Name'));
end

% 看 Battery 的输入输出
ph = get_param([mdl '/Battery'], 'PortHandles');
if isfield(ph, 'Inport')
    fprintf('\n输入端口: %d个\n', length(ph.Inport));
end
if isfield(ph, 'Outport')
    fprintf('输出端口: %d个\n', length(ph.Outport));
end

% 内部 To Workspace
tw = find_system([mdl '/Battery'], 'BlockType', 'ToWorkspace');
fprintf('\nBattery 内 To Workspace:\n');
for i = 1:length(tw)
    fprintf('  %s -> var: %s\n', tw{i}, get_param(tw{i}, 'VariableName'));
end

close_system(mdl, 0);

% 看 Lead_Acid_Battery.slx
fprintf('\n===== Lead_Acid_Battery (已分析的) =====\n');
load_system('Lead_Acid_Battery.slx');
blks2 = find_system('Lead_Acid_Battery', 'SearchDepth', 1);
fprintf('顶层模块 (%d个):\n', length(blks2)-1);
for i = 2:length(blks2)
    bt = get_param(blks2{i}, 'BlockType');
    fprintf('  [%s] %s\n', bt, get_param(blks2{i}, 'Name'));
end
close_system('Lead_Acid_Battery', 0);
