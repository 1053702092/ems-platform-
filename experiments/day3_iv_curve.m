% day3_iv_curve.m - 纯MATLAB计算PEM燃料电池I-V曲线
% 调用Cell_model.slx的物理参数，用公式计算
% 目的：打通 Python->MATLAB->CSV->画图 链路

res_dir = 'F:/CLAUDE/research/ems-platform/results';

% PEM燃料电池电压公式（简化学术模型）
% V = E_nernst - V_act - V_ohm - V_conc
% 其中：
%   E_nernst = 开路电压（能斯特方程）
%   V_act = 活化过电位（Butler-Volmer）
%   V_ohm = 欧姆过电位（i*R）
%   V_conc = 浓差过电位

% 参数（参考Cell_model.slx典型值）
T = 333;           % 温度 (K)
P_H2 = 2.3e5;      % 氢气分压 (Pa)
P_O2 = 0.21e5;     % 氧气分压 (Pa)
A = 100;           % 活化面积 (cm^2)
R_mem = 0.1;       % 膜电阻 (Ohm)
i_max = 1.5;       % 最大电流密度 (A/cm^2)

% 物理常数
F = 96485;         % 法拉第常数
R = 8.314;         % 气体常数
n = 2;             % 电子转移数

% 能斯特开路电压
E0 = 1.229 - 0.85e-3 * (T - 298.15) + 4.31e-5 * T * (log(P_H2/101325) + 0.5 * log(P_O2/101325));
fprintf('开路电压 E0 = %.4f V\n', E0);

% 扫描电流
currents = 0:2:100;  % 0A 到 100A (总电流，非电流密度)
voltages = zeros(size(currents));

fprintf('计算I-V曲线...\n');
for i = 1:length(currents)
    I = currents(i);
    i_density = I / A;  % A/cm^2

    % 活化过电位（简化的Tafel方程）
    if i_density > 1e-6
        V_act = (R * T) / (2 * 0.5 * F) * log(i_density / 1e-4);
    else
        V_act = 0;
    end

    % 欧姆过电位
    V_ohm = I * R_mem;

    % 浓差过电位
    if i_density < i_max * 0.99
        V_conc = -(R * T) / (2 * F) * log(1 - i_density / i_max);
    else
        V_conc = 0.5;  % 极限电流附近
    end

    % 总电压
    V = E0 - V_act - V_ohm - V_conc;
    voltages(i) = max(V, 0);
end

% 保存CSV
T = table(currents', voltages', 'VariableNames', {'Current_A', 'Voltage_V'});
csv_path = fullfile(res_dir, 'day3_cell_model_iv_curve.csv');
writetable(T, csv_path);
fprintf('\nI-V数据已保存: %s\n', csv_path);
fprintf('%d个数据点, 电流范围 0-%dA\n', length(currents), max(currents));

% 画图
figure('Position', [100 100 800 400]);
subplot(1,2,1);
plot(currents, voltages, 'b-o', 'LineWidth', 1.5, 'MarkerSize', 3);
xlabel('Current (A)'); ylabel('Voltage (V)');
title('PEMFC Polarization Curve'); grid on;

subplot(1,2,2);
power = currents .* voltages;
plot(currents, power, 'r-s', 'LineWidth', 1.5, 'MarkerSize', 3);
xlabel('Current (A)'); ylabel('Power (W)');
title('PEMFC Power Curve'); grid on;

saveas(gcf, fullfile(res_dir, 'day3_cell_model_iv_curve.png'));
fprintf('图已保存\n');

% 关键数据
[pmax, idx] = max(power);
fprintf('\n关键数据:\n');
fprintf('  开路电压: %.4f V\n', voltages(1));
fprintf('  最大功率: %.1f W (%.0fA时)\n', pmax, currents(idx));
% 找电压降到0.6V时的电流（用find跳过重复值）
idx_06 = find(voltages < 0.6, 1, 'first');
if ~isempty(idx_06)
    fprintf('  0.6V时电流: %.0f A\n', currents(idx_06));
else
    fprintf('  电压未降到0.6V以下\n');
end

fprintf('\nPython->MATLAB->CSV->画图 全链路测试完成!\n');
quit;
