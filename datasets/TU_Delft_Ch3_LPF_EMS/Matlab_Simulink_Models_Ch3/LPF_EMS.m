
 clc, clear, close all
% -----------FUEL CELL
% Voltage and current values

V_0 = 750; %open circuit voltage (V) ----these v0 and v1 may need to be fixed.
v_1 = 730; %Voltage (V) at 1 Ampere
V_nom = 635; %RatedVoltage (V)
I_nom = 188.97; %Rated Current (A)
V_end = 520; %End voltage (V)
I_end = 288.46; %End current (A)

%FC efficinecy and number of cells
FCeff = 54.5; %nominal stack efficiency unit in %
Ncell = 2*96485*V_nom/(241.8e3*FCeff*0.01); %number of cells in each stack
Ncell  = round(Ncell);

Tnom = 60; %Nominal operating temperature in Celsius
H2_utiliz = 98.19; %unit in %
O2_utiliz = 49.32; %unit in %


%air flow rate calculation
R = 8.3145; %J/molK Gas constant
F = 96485; %A s/mol Faraday constant 
z = 2; %number of moving electrons
Vfuel_max = 464.5; %Maximum fuel flow rate (lpm)
Vfuel_min = 0; 
Vair_max = 1.1e4; %Maximum air flow rate (lpm)
Pfuel_nom = 5; %nominal supply fuel pressure (bar)
Pair_nom = 1; %nominal supply air pressure (bar) 

Vair_nom = (60000*R*(Tnom+273.15)*Ncell*I_nom)/(2*z*F*Pair_nom*100000*0.5*0.21); %Nominal air flow rate (lpm)

%hydrogen, oxygen water compositions %
H_2_comp = 99.95; %unit is %
O_2_comp = 21; %unit is %
H20_comp = 1; %unit is %


Nfc = 9; %number of fuel cell stacks



% ------BATTERY

Vbatt_nom = 800; %nominal battery Voltage (V) 
Nbatt  = 2;  %number of battery packs
Ebatt = 200*1000/Nbatt; %Energy of one battery in wh
Qbatt_rated = Ebatt/Vbatt_nom; %battery rated capacity in Ah
Initial_SoC = 50; %Initial battery SoC
ResponseBatt = 1; %response time in seconds

Crate = 1; % 3 for LTO, 1 for LFP



%-------FC CONVERTER 

%BoostConverter FC

Vout = 1000; %Voltage output from the converter (V) = dc bus voltage
Vinmax = 750; %upper limit (V) in the operating voltage range (output voltage from fc)
Kind = 0.3; %inductor ripple current relative to maximum output current
Fsw = 5000; %switching frequency of converter in Hz
PFC_rated = 150e3; %rated power of FC stack (W)
Vinmin = 520; %minimum input voltage to the converter (V)
Ioutmax = PFC_rated/Vinmin; %Maximoum output current from converter (A)
Vripple = 0.01*Vout; %desired voltage ripple for a well-designed converter = 1%


eta_conv = 0.97; %converter efficiency
Dboost = 1 - ((Vinmin*eta_conv)/Vout); %Duty cycle for boost mode
Cboost = (Ioutmax*Dboost)/(Fsw*Vripple); %Minimum capacitance in boost mode (F)

%MEXRI EDO CHECKED.


Dbuck = Vout*eta_conv/Vinmax; %Duty cycle for buck mode

Lboostfc = (V_nom*(Vout-V_nom))/(0.3*Ioutmax*Vout^2*V_nom^(-1)*Fsw);
Lboostfc = Lboostfc*10*10;
Cboostfc = Cboost;

Lbuck = (Vinmax*(Vout-Vinmax))/(Kind*Fsw*Vout*Ioutmax); %Minimum inductance value in Henry (H) in buck mode
Cbuck = (Kind*Ioutmax)/(8*Fsw*Vripple); %minimum capacitance (F) for converter



%BATT CONVERTER (bidirectional converter)

%Select the minimum inductance from both buck and boost modes - 
% for buck already have above

%boost mode minimum inductance

Lboostbatt = (Vinmin^2 * (Vout - Vinmin))/(Fsw*Kind*Ioutmax*Vout^2); %Minimum inductance H for boost mode


Lbatt = min(Lbuck,Lboostbatt);
Lbatt = Lbatt*100;


%Battery converter inductance value

%now select the minimum capacitance from both buck and boost modes
%for buck already have done




Cbatt = min(Cboost,Cbuck); %Battery converter capacitance value


%DC BUS

Cbus = Cbuck*Nfc + Cbatt*Nbatt;
Cbus = Cbus*100;

% test for a large Cbus
%Cbus = Cbus*1000;
 
%DC bus capacitance (F) 
DCbusV = 1000; %(V)




%gains for fuel cells and batteries

gfc = 1/Nfc; 
gbat = 1/Nbatt;



%kp and ki for controllers - from fomrulae calculations

%DC bus voltage PI controller
TC = 0.01; %time constant
KpDC = Cbus/TC; 
KiDC = (0.25*KpDC^2)/(4*Cbus); 



%Battery SoC contrller


Pmaxbatt = Ebatt*Crate; %maximum battery power in Watt for 1 battery
DSoCbatt = 40; %(difference between max and ref SoC) = 50% for LTO (100-50) but 40% foR LFP(90-50);
Ibatmax = Pmaxbatt/DCbusV; %maximum battery current in Ampere
KpSoC = Ibatmax*Nbatt/DSoCbatt;


%FC converter contrller
TC_FC = 0.003;
KpFC = Lboostfc/TC_FC/DCbusV;
KiFC = KpFC^2/(4*Lboostfc);


%Batter converter controller 
TC_Batt = 0.003;
KpBatt = Lbatt/TC_Batt/DCbusV; 
KiBatt = KpBatt^2/(4*Lbatt); 


%fuel cell current limits
Ifc_max = 288; %max fuel cell current for 1 stack at 100% rated load
%Ifc_min = 19.5; %min fuel cell current for 1 stack at 10% rated load
Ifc_min = 0; %min fuel cell current for 1 stack at 0% rated load



%Time constant in the Low Pass Filter
T0 = 600; % it has to be comparative to the measurements of power profile




% fuel consumption ---TO be estimated based on FC = k1 * Pfc^2 + k2 Pfc +
% k3 after we get the results from the simout blocks.

% t = 108600; %simulation time in seconds
% FC = mean(simout)*t*Nfc;   %not sure if this is the correct way to take
% teh average.




%%
fs = 18;
set(0, 'defaultAxesTickLabelInterpreter', 'latex')
set(0, 'defaultTextInterpreter', 'latex')
set(0, 'defaultLegendInterpreter', 'latex')
set(0, 'defaultAxesFontSize', fs)
set(0, 'defaultTextFontSize', fs)
set(0, 'defaultLegendFontSize',fs)


% figure('position',[50,50,1000,600]), hold on, grid on, box on
% plot(simout,'-r','linewidth',2,'Displayname','Efficiency'); 
% plot(simout1, '-g','linewidth',2,'Displayname','FC Power');
% xlabel('FC Power [kW]','Interpreter','latex',FontSize=fs); 
% ylabel('Efficiency','Interpreter','latex',FontSize=fs); 
% legend show
% name1 = 'Results_power.png';
% print(sprintf('%s',name1),'-dpng','-r0');

% figure('position',[50,50,1000,600]), hold on, grid on, box on
% plot(simout3,'-b','linewidth',2,'Displayname','Power Profile'); 
% plot(simout1,'-r','linewidth',2,'Displayname','Fuel cell Power'); 
% plot(simout2, '-g','linewidth',2,'Displayname','Battery Power');
% xlabel('Time [seconds]','Interpreter','latex',FontSize=fs); 
% ylabel('Power(kW)','Interpreter','latex',FontSize=fs); 
% legend show
% name1 = 'Results_power.png';
% print(sprintf('%s',name1),'-dpng','-r0');

% 
% figure('position',[50,50,1000,600]), hold on, grid on, box on
% plot(simout3,'-b','linewidth',2)  
% xlabel('Time [seconds]','Interpreter','latex',FontSize=fs); 
% ylabel('Battery SoC (%)','Interpreter','latex',FontSize=fs); 
% name2 = 'Battery_SoC.png';
% print(sprintf('%s',name2),'-dpng','-r0');
% 
% 
% figure('position',[50,50,1000,600]), hold on, grid on, box on
% plot(simout4,'-b','linewidth',2)  
% xlabel('Time [seconds]','Interpreter','latex',FontSize=fs); 
% ylabel('Bus Voltage (V)','Interpreter','latex',FontSize=fs); 
% name3 = 'DCbusVoltage.png';
% print(sprintf('%s',name3),'-dpng','-r0');


