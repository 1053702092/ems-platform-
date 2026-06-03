% run_first_sim.m
% 第1次完整仿真：加载Energy.slx模型，跑仿真，导出结果
% 被Python调用：matlab -batch run('...run_first_sim.m')

project_dir = 'F:/CLAUDE/research/ems-platform';
model_dir = fullfile(project_dir, 'env/simulink_models');
results_dir = fullfile(project_dir, 'results');

% 切换到模型目录
cd(model_dir);

% 加载工作区数据（模型需要这些变量）
if exist('matlab.mat', 'file')
    load('matlab.mat');
    fprintf('工作区数据已加载\n');
end

% 加载模型
load_system('Energy.slx');
fprintf('模型已加载: Energy.slx\n');

% 查看模型中的ToWorkspace模块
ws_blocks = find_system('Energy', 'BlockType', 'ToWorkspace');
fprintf('找到 %d 个ToWorkspace模块\n', length(ws_blocks));
for i = 1:length(ws_blocks)
    var_name = get_param(ws_blocks{i}, 'VariableName');
    fprintf('  [%d] %s -> 变量: %s\n', i, ws_blocks{i}, var_name);
end

% 查看Scope模块
scopes = find_system('Energy', 'BlockType', 'Scope');
fprintf('找到 %d 个Scope模块\n', length(scopes));

% 跑仿真
fprintf('\n开始仿真...\n');
tic;
sim('Energy.slx');
elapsed = toc;
fprintf('仿真完成! 耗时 %.2f秒\n', elapsed);

% 检查有哪些变量被写入了工作区
vars = who;
fprintf('\n工作区变量 (%d个):\n', length(vars));
for i = 1:length(vars)
    v = vars{i};
    if evalin('base', ['isa(', v, ', ''struct'') || isnumeric(', v, ')'])
        s = evalin('base', ['size(', v, ')']);
        fprintf('  %s (%dx%d)\n', v, s(1), s(2));
    end
end

% 保存关键数据到CSV用于Python读取
% （先做一次空跑看看哪些变量生成，再决定导出什么）
save(fullfile(results_dir, 'sim_first_run.mat'));

fprintf('\n结果已保存到: %s\n', fullfile(results_dir, 'sim_first_run.mat'));
fprintf('首次仿真完成!\n');
quit;
