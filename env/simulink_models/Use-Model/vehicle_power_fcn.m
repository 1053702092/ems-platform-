function P_load = vehicle_power_fcn(v_kmh, a_ms2)
% vehicle_power_fcn — 车速+加速度 → 负载功率 [kW]
% 基于纵向动力学：P = (F_roll + F_aero + F_inertia) * v / eta
%
% 输入:
%   v_kmh — 车速 [km/h]        (标量)
%   a_ms2 — 加速度 [m/s^2]     (标量, Simulink 中由 Derivative 模块提供)
% 输出:
%   P_load — 驱动轮功率需求 [kW] (正=驱动, 负=制动, 怠速=0)
%
% 用法:
%   P_load = vehicle_power_fcn(50, 0.5)   → 50 km/h, 加速0.5m/s²
%   P_load = vehicle_power_fcn(v, a)      → 数组运算

% ========== 整车参数 (典型中型轿车) ==========
m   = 1500;      % 整车质量 [kg]
g   = 9.81;      % 重力加速度
f_r = 0.015;     % 滚动阻力系数
rho = 1.225;     % 空气密度 [kg/m^3]
Cd  = 0.32;      % 风阻系数
A   = 2.2;       % 迎风面积 [m^2]
eta = 0.90;      % 传动效率

% ========== 动力学计算 ==========
v_ms = v_kmh / 3.6;                     % km/h → m/s

F_rr    = m * g * f_r;                  % 滚动阻力 (与速度无关)
F_aero  = 0.5 * rho * Cd * A * v_ms^2;  % 空气阻力 (与 v² 成正比)
F_grade = 0;                            % 坡度阻力 (假设平路)
F_inertia = m * a_ms2;                  % 惯性力 F = ma

% 总牵引力 → 功率
P_wheel = (F_rr + F_aero + F_grade + F_inertia) .* v_ms;

% 传动效率 & W → kW
P_load = P_wheel / eta / 1000;

% 停车时输出0 (蠕行功率不计)
P_load(v_kmh < 0.5) = 0;

end
