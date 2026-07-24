figure(1)
yyaxis left
plot(out.I_FC.data,out.V_FC.data)
grid minor
xlabel('Current [A]')
ylabel('Voltage [V]')
yyaxis right
plot(out.I_FC.data,out.eta_FC.data*100,...
    out.I_FC.data,out.eta_sys_FC.data*100)
ylabel('Efficiency [%]')

figure(2)
ax1=subplot(4,1,1);
plot(out.I_FC);
grid minor
ylabel('Current [A]')

ax2=subplot(4,1,2);
plot(out.P_FC);
hold on
plot(out.P_BOP);
grid minor
ylabel('Power [W]')

ax3=subplot(4,1,3);
plot(out.eta_FC*100);
grid minor
ylabel('Efficiency [%]')

ax4=subplot(4,1,4);
plot(out.H2_cons);
grid minor
ylabel('H2 consumption [g/s]')

linkaxes([ax1 ax2 ax3 ax4],'x')