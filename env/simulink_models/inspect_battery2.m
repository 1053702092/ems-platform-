% inspect_battery2.m — 深入查看 Battery 和 EMS 子系统
mdl = 'power_FCHPS_MEA2';
mdl_path = '资料/燃料电池-蓄电池-超级电容交直流微网能量管理策略Simulink模型/47901-main/燃料电池-混合储能微网EMS/power_FCHPS_MEA2.slx';
load_system(mdl_path);

fprintf('===== Battery 子系统内部 =====\n');
battery_blks = find_system([mdl '/Battery']);
fprintf('总子模块数: %d\n', length(battery_blks));
for i = 1:min(length(battery_blks), 30)
    fprintf('  %s\n', battery_blks{i});
end

fprintf('\n===== Energy Management System 子系统 =====\n');
ems_blks = find_system([mdl '/Energy Management System'], 'SearchDepth', 1);
fprintf('顶层模块:\n');
for i = 2:length(ems_blks)
    bt = get_param(ems_blks{i}, 'BlockType');
    fprintf('  [%s] %s\n', bt, get_param(ems_blks{i}, 'Name'));
end

% EMS 输入输出
ph = get_param([mdl '/Energy Management System'], 'PortHandles');
fprintf('\nEMS 输入端口: %d\n', length(ph.Inport));
fprintf('EMS 输出端口: %d\n', length(ph.Outport));

close_system(mdl, 0);

% 深入 Lead_Acid_Battery
fprintf('\n===== Lead_Acid_Battery 内部 =====\n');
load_system('Lead_Acid_Battery.slx');
all = find_system('Lead_Acid_Battery');
fprintf('总子模块数: %d\n', length(all));
for i = 1:length(all)
    fprintf('  %s\n', all{i});
end
close_system('Lead_Acid_Battery', 0);
