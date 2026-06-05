% cell_model_iv_sweep.m — Cell_model_v10_lit I-V 特性扫描
% 被 run_simulation.py 调用
% 输出: results/cell_model_iv_sweep.csv

mdl = 'Cell_model_v10_lit';

% 确保模型存在
if ~exist([mdl '.slx'], 'file')
    error('请先运行 setup_cell_model_logging 创建 %s.slx', mdl);
end

load_system([mdl '.slx']);

% 找到 Current Constant 模块
consts = find_system(mdl, 'SearchDepth', 1, 'BlockType', 'Constant');
cidx = find(cellfun(@(c) contains(lower(c), 'current'), get_param(consts, 'Name')));
if isempty(cidx)
    error('未找到 Current 模块');
end
currentBlk = consts{cidx(1)};

% I-V 扫描
fprintf('Cell_model_v10 I-V 扫描\n');
results = [];
I_values = 0:2:100;

for i = 1:length(I_values)
    I = I_values(i);
    set_param(currentBlk, 'Value', num2str(I));
    simOut = sim(mdl, 'StopTime', '5');
    try
        V = simOut.get('V_stack');
        V_final = V(end);
    catch
        V_final = 0;
    end
    results = [results; I, V_final];
    fprintf('  I=%3dA, V=%.6fV\n', I, V_final);
end

% 保存 CSV
csv_path = '../../results/cell_model_iv_sweep.csv';
csvwrite(csv_path, results);
fprintf('\n✅ 已保存: %s (%d 行)\n', csv_path, size(results, 1));

close_system(mdl, 1);
