function [SOC, V_bat, I_bat] = battery_simple_fcn(P_bat_kW, SOC_init, dt)
% battery_simple_fcn — 简化电池模型 (R-int 模型)
% 输入:
%   P_bat_kW — 电池功率 [kW] (正=放电, 负=充电)
%   SOC_init — 当前SOC [0-1]
%   dt       — 时间步长 [s]
% 输出:
%   SOC   — 更新后的SOC
%   V_bat — 端电压 [V]
%   I_bat — 电流 [A]
%
% 使用内阻模型: V_t = V_oc - I * R_int
% SOC 通过 Ah 积分更新

% ========== 电池参数 (参考: 50Ah 锂离子) ==========
Q_bat = 50;         % 容量 [Ah]
V_nom = 350;        % 额定电压 [V]
R_int = 0.05;       % 内阻 [Ohm]
SOC_0 = SOC_init;   % 初始SOC

% ========== SOC → 开路电压 (简化的OCV曲线) ==========
% 典型 LFP/三元 的 OCV-SOC 关系  查表得到
SOC_breakpoints = [0,    0.1,  0.2,  0.3,  0.5,  0.7,  0.8,  0.9,  1.0];
V_ocv_lookup    = [320,  330,  338,  345,  352,  358,  362,  368,  380];

% 插值求当前 OCV
V_oc = interp1(SOC_breakpoints, V_ocv_lookup, SOC_init, 'linear', 'extrap');

% ========== 电流计算 (由功率和OCV迭代) ==========
% P = V * I = (V_oc - I*R) * I = V_oc*I - I^2*R
% → I^2*R - V_oc*I + P = 0
% 判別式: Δ = V_oc^2 - 4*R*P

if abs(P_bat_kW) < 0.01
    I_bat = 0;  % 接近0
else
    P_w = P_bat_kW * 1000;  % kW → W
    Delta = V_oc^2 - 4 * R_int * P_w;

    if Delta < 0
        % 功率超过电池能力, 限幅
        P_w = V_oc^2 / (4 * R_int);  % 最大功率 充电放电都有个限幅
        if P_bat_kW > 0
            P_w = min(P_w, 0.99 * V_oc^2 / (4 * R_int));
        else
            P_w = -min(-P_w, 0.99 * V_oc^2 / (4 * R_int));
        end
        Delta = V_oc^2 - 4 * R_int * P_w;
    end

    I_bat = (V_oc - sqrt(Delta)) / (2 * R_int);
    % 限流 ±300A
    if P_bat_kW > 0
        I_bat = min(I_bat,  300);   % 放电: 电流不超过 +300A
    else
        I_bat = max(I_bat, -300);   % 充电: 电流不低于 -300A
    end
end

% ========== 端电压 ==========
V_bat = V_oc - I_bat * R_int;

% ========== SOC 更新 (Ah积分) ==========
% d(SOC)/dt = -I / (Q * 3600)
SOC_change = -I_bat / (Q_bat * 3600) * dt;
SOC = SOC_init + SOC_change;

% SOC 限幅 [0.05, 0.95]
SOC = min(max(SOC, 0.05), 0.95);

end
