close all;

%% Power Balance
figure
plot(out.time/3600,(out.I_out_FC_A_act.*out.V_DC_act-out.P_BOP_FC_A_act)/1e3,'Color','#228B22') %Forest Green
hold on
plot(out.time/3600,out.I_out_Bat_A_act.*out.V_DC_act/1e3,'Color','#FF5733') %Fancy Red
plot(out.time/3600,out.P_prop_act/1e3,'Color','#4169E1') %Royal Blue
grid minor
xlabel('Time [h]')
ylabel('Power [kW]')
% legend('Fuel Cells',...
%     'Batteries',...
%     'Load')

%% Battery SoC
figure
ax1=subplot(2,1,1);
plot(out.time,out.I_out_Bat_A_act,'Color','#FF5733') %Fancy Red
title('Battery Charge')
ylabel('Current [A]')
grid minor
ax2=subplot(2,1,2);
plot(out.time,out.SoC_Bat_A_act*100,'Color','#FF5733') %Fancy Red
ylabel('SoC [%]')
xlabel('Time [s]')
grid minor
linkaxes([ax1 ax2],'x')

%% Fuel Cell
figure
ax1=subplot(4,1,1);
plot(out.time,out.I_out_FC_A_act.*out.V_DC_act,'Color','#4169E1') %Royal Blue
title('Hydrogen Consumption')
ylabel('Power [W]')
grid minor
ax2=subplot(4,1,2);
plot(out.time,(out.eta_FC_A_act)*100,'Color','#4169E1') %Royal Blue
ylabel('Efficiency [%]')
grid minor
ax3=subplot(4,1,3);
plot(out.time,out.m_H2_FC_A_act,'Color','#4169E1') %Royal Blue
ylabel('Consumed Hydrogen [kg]')
xlabel('Time [s]')
grid minor
ax4=subplot(4,1,4);
plot(out.time,out.dV_stat_FC_A_act,out.time,out.dV_dyn_FC_A_act,'Color','#4169E1') %Royal Blue
ylabel('Fuel Cell Degradation [V]')
xlabel('Time [s]')
grid minor
linkaxes([ax1 ax2 ax3 ax4],'x')
