function [P_fc_ref, P_bat_ref, status] = ems_controller_fcn(P_load, SOC)
% ems_controller_fcn — 规则基能量管理控制器
% 输入:
%   P_load — 功率需求 [kW] (正=驱动)
%   SOC    — 电池荷电状态 [0-1]
% 输出:
%   P_fc_ref  — 燃料电池功率参考 [kW]
%   P_bat_ref — 电池功率参考 [kW] (正=放电, 负=充电)
%   status    — 当前模式 (1=FC-only, 2=hybrid, 3=charging, 4=idle)

% ========== 燃料电池参数 ==========
P_fc_min = 3;      % 最低功率 [kW] (低于此效率差)
P_fc_max = 25;     % 额定最大功率 [kW]
P_fc_max_peak = 30;% 峰值功率 [kW] (短时)

% ========== 电池SOC限制 ==========
SOC_min = 0.30;     % 最低SOC
SOC_low = 0.40;     % 偏低SOC (进入充电维持)
SOC_high = 0.80;    % 偏高SOC (允许深度放电)
SOC_max = 0.90;     % 最高SOC

% ========== 默认输出 ==========
P_fc_ref = 0;
P_bat_ref = 0;
status = 4;  % idle

% ========== 情形0: 停车/制动 ==========
if P_load < 1.0
    % 停车或极低负载
    if SOC < SOC_max
        % 可以怠速充电
        P_fc_ref = P_fc_min;
        P_bat_ref = P_load - P_fc_min;  % 负=充电， 以最小功率开着实现充电
        status = 3;
    else
        P_fc_ref = 0;
        P_bat_ref = 0;
        status = 4;
    end
    return;
end

% ========== 情形1: SOC 过低 — 充电维持模式 ==========
if SOC < SOC_low
    % 强制FC输出, 同时满足负载和充电需求
    P_fc_ref = min(P_load + (SOC_target(SOC) * 5), P_fc_max);
    P_fc_ref = max(P_fc_ref, P_fc_min);
    P_bat_ref = P_load - P_fc_ref;  % 如果FC>负载, 则充电
    status = 3;
    return;
end

% ========== 情形2: SOC 过高 — 尽量用电池 ==========
if SOC > SOC_high
    % 电池优先, FC仅补充不足
    P_fc_ref = max(P_load - 10, P_fc_min);
    P_fc_ref = min(P_fc_ref, P_fc_max);
    P_bat_ref = P_load - P_fc_ref;  % 正=放电
    status = 2;
    return;
end

% ========== 情形3: 正常SOC — 跟随模式 ==========
if P_load <= P_fc_min
    % 负载低于FC最低效率点: FC保持最低, 余电充电池
    P_fc_ref = P_fc_min;
    P_bat_ref = P_load - P_fc_min;
    status = 3;  % 充电
elseif P_load <= P_fc_max
    % 负载在FC高效区: FC跟随负载, 电池不参与
    P_fc_ref = P_load;
    P_bat_ref = 0;
    status = 1;  % FC-only
else
    % 负载超过FC上限: FC最大, 电池补充
    P_fc_ref = P_fc_max;
    P_bat_ref = P_load - P_fc_max;
    status = 2;  % 混合
end

end

% ========== 辅助函数 ==========
function factor = SOC_target(SOC)
    % SOC 越低, 充电系数越大
    if SOC < 0.2
        factor = 1.0;
    elseif SOC < 0.3
        factor = 0.7;
    elseif SOC < 0.4
        factor = 0.4;
    else
        factor = 0.2;
    end
end
