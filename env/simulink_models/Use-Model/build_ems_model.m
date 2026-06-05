 %% build_ems_model.m — 搭建燃料电池混合动力 EMS 顶层 Simulink 模型
% 整合: Fuel Cell + Battery + Load + Rule-based EMS Controller
%
% 架构:
%   WLTC Drive Cycle → Vehicle Power Demand → EMS Controller
%                                               ├→ FC System (Cell_model_v10)
%                                               └→ Battery (R-int model)
%   → Power Bus → Data Logging
%
% 用法:
%   build_ems_model              % 创建并打开模型
%   build_ems_model('open')      % 只打开已存在的模型
%   build_ems_model('rebuild')   % 删除重建

function build_ems_model(action)
if nargin < 1, action = 'build'; end

mdl = 'EMS_hybrid_v1';
SCRIPT_DIR = fileparts(mfilename('fullpath'));          % 脚本所在目录: .../d/
MODEL_DIR = fileparts(SCRIPT_DIR);                      % 上级: .../simulink_models/
PROJECT_ROOT = fileparts(fileparts(MODEL_DIR));         % 项目根目录: .../ems-platform/

switch action
    case 'open'
        slx_path = fullfile(SCRIPT_DIR, [mdl '.slx']);
        if exist(slx_path, 'file')
            load_system(slx_path);
            open_system(mdl);
        else
            error('模型 %s 不存在，先运行 build_ems_model', slx_path);
        end
        return;
    case 'rebuild'
        slx_path = fullfile(SCRIPT_DIR, [mdl '.slx']);
        if exist(slx_path, 'file')
            close_system(mdl, 0);
            delete(slx_path);
        end
    case 'build'
        slx_path = fullfile(SCRIPT_DIR, [mdl '.slx']);
        if exist(slx_path, 'file')
            fprintf('[✓] 模型 %s 已存在\n', mdl);
            load_system(mdl);
            open_system(mdl);
            return;
        end
    otherwise
        error('未知操作: %s', action);
end

fprintf('===== 构建 %s =====\n', mdl);

%% 0. 清理之前的残存模型
close_system(mdl, 0);

%% 1. 创建新模型
new_system(mdl);
open_system(mdl);

% 求解器设置
set_param(mdl, 'Solver',          'ode45');
set_param(mdl, 'StopTime',        '1800');     % WLTC=1800s
set_param(mdl, 'MaxStep',         '0.1');
set_param(mdl, 'AbsTol',          '1e-4');
set_param(mdl, 'RelTol',          '1e-3');

%% 2. 添加 WLTC 工况数据源
% Simulink From Workspace 需要 [t, v] 格式的时间序列
add_block('simulink/Sources/From Workspace', [mdl '/WLTC Data']);
set_param([mdl '/WLTC Data'], ...
    'VariableName', 'sim_wltc', ...
    'SampleTime', '0.1', ...
    'Interpolate', 'on');
% 位置 [x, y, w, h]
set_param([mdl '/WLTC Data'], 'Position', [50, 100, 150, 130]);

%% 3. 车辆动力学 — 车速+加速度 → 功率
add_block('simulink/User-Defined Functions/MATLAB Function', ...
    [mdl '/Vehicle Power']);
set_param([mdl '/Vehicle Power'], 'Position', [250, 80, 380, 170]);
veh_code = fileread(fullfile(SCRIPT_DIR, 'vehicle_power_fcn.m'));
set_matlab_func_code([mdl '/Vehicle Power'], veh_code);
% 注意: MATLAB Function 自动从函数签名推导端口 调用'vehicle_power_fcn.m'
% function P_load = vehicle_power_fcn(v_kmh, a_ms2)
% 所以有 2个输入 (v_kmh, a_ms2), 1个输出 (P_load)

%% 4. EMS 控制器
add_block('simulink/User-Defined Functions/MATLAB Function', ...
    [mdl '/EMS Controller']);
set_param([mdl '/EMS Controller'], 'Position', [480, 100, 630, 200]);
ems_code = fileread(fullfile(SCRIPT_DIR, 'ems_controller_fcn.m'));
set_matlab_func_code([mdl '/EMS Controller'], ems_code);

%% 5. 燃料电池系统
add_block('simulink/Ports & Subsystems/Subsystem', [mdl '/FC System']);
set_param([mdl '/FC System'], 'Position', [730, 50, 900, 200]);
build_fc_subsystem([mdl '/FC System'], SCRIPT_DIR);

%% 6. 蓄电池系统
add_block('simulink/User-Defined Functions/MATLAB Function', ...
    [mdl '/Battery']);
set_param([mdl '/Battery'], 'Position', [730, 260, 900, 380]);
bat_code = fileread(fullfile(SCRIPT_DIR, 'battery_simple_fcn.m'));
set_matlab_func_code([mdl '/Battery'], bat_code);

%% 7. 数据记录 (To Workspace)
% FC 输出: 电压和实际功率分别记录
add_block('simulink/Sinks/To Workspace', [mdl '/log_V_fc']);
set_param([mdl '/log_V_fc'], 'VariableName', 'sim_V_fc', ...
    'SaveFormat', 'Array');

add_block('simulink/Sinks/To Workspace', [mdl '/log_P_fc']);
set_param([mdl '/log_P_fc'], 'VariableName', 'sim_P_fc', ...
    'SaveFormat', 'Array', 'MaxDataPoints', 'inf');

% 电池输出
add_block('simulink/Sinks/To Workspace', [mdl '/log_SOC']);
set_param([mdl '/log_SOC'], 'VariableName', 'sim_SOC', ...
    'SaveFormat', 'Array');

add_block('simulink/Sinks/To Workspace', [mdl '/log_P_load']);
set_param([mdl '/log_P_load'], 'VariableName', 'sim_P_load', ...
    'SaveFormat', 'Array');

add_block('simulink/Sinks/To Workspace', [mdl '/log_V_bat']);
set_param([mdl '/log_V_bat'], 'VariableName', 'sim_V_bat', ...
    'SaveFormat', 'Array');

add_block('simulink/Sinks/To Workspace', [mdl '/log_I_bat']);
set_param([mdl '/log_I_bat'], 'VariableName', 'sim_I_bat', ...
    'SaveFormat', 'Array', 'Position', [960, 335, 1060, 360]);

add_block('simulink/Sinks/To Workspace', [mdl '/log_status']);
set_param([mdl '/log_status'], 'VariableName', 'sim_status', ...
    'SaveFormat', 'Array', 'Position', [960, 380, 1060, 405]);

%% 8. 信号路由
% From Workspace 输出已经是单列速度信号 (1st列=时间用于插值, 输出只有数据列)
% 加速度: Derivative 模块 (dv/dt)
add_block('simulink/Continuous/Derivative', [mdl '/Acceleration']);
set_param([mdl '/Acceleration'], 'Position', [170, 145, 200, 175]);

%% 9. 连线
% WLTC Data (速度) → Vehicle Power/1 (v_kmh)
add_line(mdl, 'WLTC Data/1', 'Vehicle Power/1');
% WLTC Data (速度) → Acceleration → Vehicle Power/2 (a_ms2)
add_line(mdl, 'WLTC Data/1', 'Acceleration/1');
add_line(mdl, 'Acceleration/1', 'Vehicle Power/2');

% Vehicle Power → EMS Controller
add_line(mdl, 'Vehicle Power/1', 'EMS Controller/1');

% 初始SOC用 Constant 0.6 作为输入 (Battery 反馈之后再加)
add_block('simulink/Sources/Constant', [mdl '/SOC_init']);
set_param([mdl '/SOC_init'], 'Value', '0.6');
set_param([mdl '/SOC_init'], 'Position', [400, 230, 450, 255]);
add_line(mdl, 'SOC_init/1', 'EMS Controller/2');

% EMS Controller → FC System
add_line(mdl, 'EMS Controller/1', 'FC System/1');

% EMS Controller → Battery/1 (P_bat_ref)
add_line(mdl, 'EMS Controller/2', 'Battery/1');
% SOC 反馈: Battery/1 (SOC) → Memory → Battery/2 (SOC_init)
% Memory 块延迟一步, 打破代数环
add_block('simulink/Discrete/Memory', [mdl '/SOC_feedback']);
set_param([mdl '/SOC_feedback'], 'InitialCondition', '0.6');
set_param([mdl '/SOC_feedback'], 'Position', [800, 330, 830, 350]);
add_line(mdl, 'Battery/1', 'SOC_feedback/1');
add_line(mdl, 'SOC_feedback/1', 'Battery/2');
% dt → Battery/3 (固定步长 0.1s 用于 Ah 积分)
add_block('simulink/Sources/Constant', [mdl '/dt']);
set_param([mdl '/dt'], 'Value', '0.1');
set_param([mdl '/dt'], 'Position', [680, 300, 720, 320]);
add_line(mdl, 'dt/1', 'Battery/3');

% FC System → 日志 (V_fc, P_fc_actual 分开记录)
add_line(mdl, 'FC System/1', 'log_V_fc/1');
add_line(mdl, 'FC System/2', 'log_P_fc/1');

% Battery → SOC日志
add_line(mdl, 'Battery/1', 'log_SOC/1');
add_line(mdl, 'Battery/2', 'log_V_bat/1');

% EMS status (模式) → 日志
add_line(mdl, 'EMS Controller/3', 'log_status/1');

% Battery I_bat → 日志
add_line(mdl, 'Battery/3', 'log_I_bat/1');

% Vehicle Power → 日志
add_line(mdl, 'Vehicle Power/1', 'log_P_load/1');

%% 10. 生成WLTC数据 (如果不存在)
wltc_csv = fullfile(PROJECT_ROOT, 'results/wltc_cycle.csv');
if exist(wltc_csv, 'file')
    assign_wltc_data(mdl, wltc_csv);
end

%% 12. 自动整理布局和接线
fprintf('[整理] 自动排列模块位置...\n');
try
    Simulink.BlockDiagram.arrangeSystem(mdl);
catch
    fprintf('  (arrangeSystem 不可用, 跳过)\n');
end

fprintf('[整理] 优化信号线走线...\n');
try
    lines = find_system(mdl, 'FindAll', 'on', 'Type', 'line');
    for i = 1:length(lines)
        try
            Simulink.BlockDiagram.routeLine(lines(i));
        catch
        end
    end
catch
end

save_system(mdl, fullfile(SCRIPT_DIR, [mdl '.slx']));
fprintf('[✓] %s 构建完成!\n', mdl);
end

%% ========== 子函数: 构建 FC 子系统 ==========
function build_fc_subsystem(fc_path, script_dir)
% FC System 内部: I-V 查表 (MATLAB Function) + DC/DC 效率
if nargin < 2, script_dir = fileparts(fileparts(mfilename('fullpath'))); end

% 删除 SubSystem 默认自带的 In1 和 Out1 (否则端口号会偏移)
delete_block([fc_path '/In1']);
delete_block([fc_path '/Out1']);

% 输入
add_block('simulink/Sources/In1', [fc_path '/P_fc_ref']);
set_param([fc_path '/P_fc_ref'], 'Position', [30, 60, 50, 80]);

% 输出电压
add_block('simulink/Sinks/Out1', [fc_path '/V_fc']);
set_param([fc_path '/V_fc'], 'Position', [350, 30, 370, 50]);

% 输出功率
add_block('simulink/Sinks/Out1', [fc_path '/P_fc_actual']);
set_param([fc_path '/P_fc_actual'], 'Position', [350, 80, 370, 100]);

% I-V 查表 (MATLAB Function 使用 interp1, 比 Lookup Table 块更稳定) 之前的IV查表函数导入
add_block('simulink/User-Defined Functions/MATLAB Function', ...
    [fc_path '/I_to_V']);
set_param([fc_path '/I_to_V'], 'Position', [200, 55, 260, 95]);
iv_code = fileread(fullfile(script_dir, 'fc_iv_lookup_fcn.m'));
set_matlab_func_code([fc_path '/I_to_V'], iv_code);

% 计算: I_fc = P_fc_ref / V_fc_prev (带限制)
add_block('simulink/Math Operations/Divide', [fc_path '/Div']);
set_param([fc_path '/Div'], 'Position', [120, 55, 150, 85]);

% 饱和限幅 (0-300A)
add_block('simulink/Discontinuities/Saturation', [fc_path '/Sat']);
set_param([fc_path '/Sat'], ...
    'UpperLimit', '300', 'LowerLimit', '0');
set_param([fc_path '/Sat'], 'Position', [160, 58, 190, 82]);

% DC/DC 效率
add_block('simulink/Math Operations/Gain', [fc_path '/Efficiency']);
set_param([fc_path '/Efficiency'], 'Gain', '0.95');
set_param([fc_path '/Efficiency'], 'Position', [280, 70, 310, 90]);

% 实际功率 = V * I * eta
add_block('simulink/Math Operations/Product', [fc_path '/Product']);
set_param([fc_path '/Product'], 'Position', [310, 55, 330, 95]);

% Unit Delay 打破代数环
add_block('simulink/Discrete/Unit Delay', [fc_path '/V_feedback']);
set_param([fc_path '/V_feedback'], ...
    'SampleTime', '0.1', ...
    'InitialCondition', '350');
set_param([fc_path '/V_feedback'], 'Position', [250, 120, 270, 140]);

% 连线
add_line(fc_path, 'P_fc_ref/1', 'Div/1');
add_line(fc_path, 'V_feedback/1', 'Div/2');
add_line(fc_path, 'Div/1', 'Sat/1');
add_line(fc_path, 'Sat/1', 'I_to_V/1');
add_line(fc_path, 'I_to_V/1', 'V_feedback/1');
add_line(fc_path, 'I_to_V/1', 'Product/1');
add_line(fc_path, 'Sat/1', 'Product/2');
add_line(fc_path, 'Product/1', 'Efficiency/1');
add_line(fc_path, 'Efficiency/1', 'P_fc_actual/1');
add_line(fc_path, 'I_to_V/1', 'V_fc/1');
end

%% ========== 子函数: 生成 WLTC 时间序列数据 ==========
function assign_wltc_data(mdl, wltc_csv)
% 从 CSV 读取 WLTC 数据并赋值到 MATLAB 工作区
% Simulink From Workspace 需要 [t, u] 格式
data = csvread(wltc_csv, 1, 0);  % 跳过 header
t = data(:, 1);
v = data(:, 2);
sim_wltc = [t, v];
assignin('base', 'sim_wltc', sim_wltc);
fprintf('[✓] WLTC 数据已加载: %d 点, %.1f s\n', length(t), t(end));
end

%% ========== 辅助函数: 设置 MATLAB Function 块的代码 ==========
function set_matlab_func_code(block_path, code_str)
% set_matlab_func_code — 安全设置 MATLAB Function 块代码
% 优先使用官方 API，失败回退到 set_param
try
    Simulink.MATLABFunctionBlock.setMATLABFunctionCode(block_path, code_str);
catch
    try
        set_param(block_path, 'Script', code_str);
    catch
        % 最后手段: 通过 Stateflow API 设置
        drawnow;
        chart = sfroot().find('-isa', 'Stateflow.EMChart', 'Path', block_path);
        if ~isempty(chart)
            chart.Script = code_str;
        else
            error('无法设置 MATLAB Function 块代码: %s', block_path);
        end
    end
end
end
