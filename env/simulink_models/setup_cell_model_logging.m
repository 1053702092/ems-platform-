% setup_cell_model_logging.m — 创建 Cell_model_v10_lit 加 To Workspace
src = 'Cell_model_v10';
dst = 'Cell_model_v10_lit';

if exist([dst '.slx'], 'file'), delete([dst '.slx']); end
if exist([dst '.slxc'], 'file'), delete([dst '.slxc']); end

load_system([src '.slx']);
save_system(src, dst);
close_system(src, 0);
load_system(dst);
fprintf('✅ 已创建 %s.slx\n', dst);

% 找 Current 模块
consts = find_system(dst, 'SearchDepth', 1, 'BlockType', 'Constant');
cidx = find(cellfun(@(c) contains(lower(c),'current'), get_param(consts,'Name')));
currentBlk = consts{cidx(1)};
fprintf('Current 模块: "%s"\n', strtrim(get_param(currentBlk, 'Name')));

% 查 Stack voltage 的输入
stk_ph = get_param([dst '/Stack voltage'], 'PortHandles');
stk_line = get_param(stk_ph.Inport, 'Line');
src_port_h = get_param(stk_line, 'SrcPortHandle');
src_block = get_param(src_port_h, 'Parent');

% 直接取源端口号 (numeric)
src_portnum = get_param(src_port_h, 'PortNumber');
fprintf('Stack voltage 来源: %s, 端口号=%d\n', src_block, src_portnum);

% 获取源位置
src_pos = get_param(src_port_h, 'Position');

% 添加 To Workspace 模块
tw_path = [dst '/V_stack'];
tw_pos = [src_pos(1)+50, src_pos(2)-40, src_pos(1)+150, src_pos(2)+40];
add_block('simulink/Sinks/To Workspace', tw_path, ...
    'Position', tw_pos, ...
    'VariableName', 'V_stack', ...
    'SaveFormat', 'Array', ...
    'SampleTime', '-1');

% 连线: 用 port handle 形式
add_line(dst, src_port_h, get_param(tw_path, 'PortHandles').Inport(1));
fprintf('连线成功: %s → V_stack\n', src_block);

% 保存
save_system(dst);
fprintf('✅ 已保存 %s.slx\n', dst);

% === 测试运行 ===
set_param(currentBlk, 'Value', '30');
fprintf('\n运行仿真 I=30A...\n');
simOut = sim(dst, 'StopTime', '10');

V = simOut.get('V_stack');
fprintf('V_stack: %.6f(%d点)\n', V(end), length(V));

% I-V 扫描
fprintf('\n======= I-V 曲线扫描 =======\n');
results = [];
I_values = 0:2:100;
for i = 1:length(I_values)
    I = I_values(i);
    set_param(currentBlk, 'Value', num2str(I));
    simOut = sim(dst, 'StopTime', '5');
    V = simOut.get('V_stack');
    results = [results; I, V(end)]; %#ok<AGROW>
    fprintf('  I=%3dA, V=%.6fV\n', I, V(end));
end

% 保存 CSV
csv_path = '../../results/cell_model_iv_sweep.csv';
csvwrite(csv_path, results);
fprintf('\n✅ I-V 数据已保存: %s (%d行)\n', csv_path, size(results,1));

close_system(dst, 1);
