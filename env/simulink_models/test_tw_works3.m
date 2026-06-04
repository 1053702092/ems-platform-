% test_tw_works3.m — 确认 simOut.get 能取到 To Workspace 数据
mdl = 'test_tw3';
if exist([mdl '.slx'], 'file'), delete([mdl '.slx']); end
if exist([mdl '.slxc'], 'file'), delete([mdl '.slxc']); end

new_system(mdl);
load_system(mdl);
add_block('simulink/Sources/Constant', [mdl '/Input'], ...
    'Position', [100,100,150,140], 'Value', '42');
add_block('simulink/Sinks/To Workspace', [mdl '/Sink'], ...
    'Position', [250,100,350,140], ...
    'VariableName', 'test_data', ...
    'SaveFormat', 'Array', ...
    'SampleTime', '-1');
add_line(mdl, 'Input/1', 'Sink/1');
save_system(mdl);

simOut = sim(mdl, 'StopTime', '5');

% 取数据
data = simOut.get('test_data');
fprintf('test_data class: %s\n', class(data));
fprintf('test_data size: %s\n', mat2str(size(data)));
fprintf('test_data value: %.2f (first)\n', data(1));
fprintf('test_data length: %d点\n', length(data));

% 确认可以写到 CSV
csvwrite('../../results/test_tw_output.csv', data);
fprintf('✅ CSV 写入成功: results/test_tw_output.csv\n');

close_system(mdl, 1);
delete([mdl '.slx']);
