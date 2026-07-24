

% PLOTS FOR THE PAPER 

% Plots specifications
fs = 24;
set(0, 'defaultAxesTickLabelInterpreter', 'latex')
set(0, 'defaultTextInterpreter', 'latex')
set(0, 'defaultLegendInterpreter', 'latex')
set(0, 'defaultAxesFontSize', fs)
set(0, 'defaultTextFontSize', fs)
set(0, 'defaultLegendFontSize',fs)


profile_data = xlsread("Round_trip.xlsx");
time = profile_data(:,3); % Time data in days
demand = profile_data(:,4); % Power data in kW
% 
% 
% Power Profile Plot
figure('position',[50,50,1000,600]), hold on, grid on, box on
plot(time,demand,'-b','linewidth',2,'Displayname','Power Profile'); 
xlabel('Time [Days]','Interpreter','latex',FontSize=fs); 
ylabel('Propulsive Power Demand[kW]','Interpreter','latex',FontSize=fs); 
legend off
name = 'Results_powerprofile.png';
print(sprintf('%s',name),'-dpng','-r0');




% %PROFILES AFTER THE SIMULATIONS IN LOW PASS FILTER CONTROLLER
% 
% filename = 'Results_ch3.xlsx';
% 
% 
% sheet = 11; %we can change the sheet number from here in excel (sheet no.)
% 
% profile_data = xlsread(filename,sheet);
% time = profile_data(1:278,1)/3600; % Time data in hours
% demand = profile_data(1:278,2); % Power data in kW
% 
% Pfc_total = profile_data(1:278,7); % FCtotal power in kW
% Pbat_total = profile_data(1:278,4); % total battery power kW
%  SoC = profile_data (1:278,8); % batt SoC
% 
% 
% 
% % Maneuvering profile (Belgium-Dordrecht) Plot
% figure('position',[50,50,1000,600]), hold on, grid on, box on
% plot(time,demand,'-b','linewidth',2,'Displayname','Power Profile'); 
% plot(time,Pfc_total,'-g','linewidth',2,'Displayname','Total FC power'); 
% plot(time,Pbat_total,'-r','linewidth',2,'Displayname','Total BAT power'); 
% xlabel('Time [hours]','Interpreter','latex',FontSize=fs); 
% ylabel('Power[kW]','Interpreter','latex',FontSize=fs); 
% legend show
% name2 = 'Maneuvering_powerprofile.png';
% print(sprintf('%s',name2),'-dpng','-r0');
% 
% 
% %BATTERY SoC _ maneuvering power profile (Belgium-dordrecht)
% figure('position',[50,50,1000,600]), hold on, grid on, box on
% plot(time,SoC,'-b','linewidth',2,'Displayname','SoC'); 
% xlabel('Time [hours]','Interpreter','latex',FontSize=fs); 
% ylabel('SoC[%]','Interpreter','latex',FontSize=fs); 
% legend off
% name4 = 'SoC_Maneuv_powerprofile.png';
% print(sprintf('%s',name4),'-dpng','-r0');

% 
% 
% 
% filename = 'Results_ch3.xlsx';
% 
% 
% sheet = 9; %we can change the sheet number from here in excel (sheet no.)
% 
% profile_data = xlsread(filename,sheet);
% time = profile_data(1:278,1)/3600; % Time data in hours
% demand = profile_data(1:278,2); % Power data in kW
% 
% Pfc_total = profile_data(1:278,7); % FCtotal power in kW
% Pbat_total = profile_data(1:278,4); % total battery power kW
% SoC = profile_data (1:278,8); % batt SoC
% 
% 
% % Constant power profile (Sweden_ports) Plot
% figure('position',[50,50,1000,600]), hold on, grid on, box on
% plot(time,demand,'-b','linewidth',2,'Displayname','Power Profile'); 
% plot(time,Pfc_total,'-g','linewidth',2,'Displayname','Total FC power'); 
% plot(time,Pbat_total,'-r','linewidth',2,'Displayname','Total BAT power'); 
% xlabel('Time [hours]','Interpreter','latex',FontSize=fs); 
% ylabel('Power[kW]','Interpreter','latex',FontSize=fs); 
% legend show
% name1 = 'Constant_powerprofile.png';
% print(sprintf('%s',name1),'-dpng','-r0');
% 
% 
% 
% %BATTERY SoC _ constant power profile (Sweden)
% figure('position',[50,50,1000,600]), hold on, grid on, box on
% plot(time,SoC,'-b','linewidth',2,'Displayname','SoC'); 
% xlabel('Time [hours]','Interpreter','latex',FontSize=fs); 
% ylabel('SoC[%]','Interpreter','latex',FontSize=fs); 
% legend off
% nameSoCc = 'SoC_const_powerprofile.png';
% print(sprintf('%s',nameSoCc),'-dpng','-r0');


% 
% 
% 
% 
%  %DEGRADATION - SoH plots of FC and BAT
% 
% profile_data = xlsread("SoH_data.xlsx");
% round_trips = profile_data(:,1); % Number of round trips
% FC_SoH = profile_data(:,2); % FC SOH as percentage
% 
% 
% Bat_years = profile_data(:,3); % Battery years until replacement
% BAT_SoH = profile_data(:,4); % Battery SoH as %
% 
% 
% 
% 
% % FC AND BAT SOH Plot
% figure('position',[50,50,1000,600]), hold on, grid on, box on
% plot(round_trips,FC_SoH,'-b','linewidth',2,'Displayname','FC SoH'); 
% plot(Bat_years,BAT_SoH,'-g','linewidth',2,'Displayname','BAT SoH'); 
% xlabel('Time [years]','Interpreter','latex',FontSize=fs); 
% ylabel('SoH [%]','Interpreter','latex',FontSize=fs); 
% legend show
% nameSOH = 'SoH.png';
% print(sprintf('%s',nameSOH),'-dpng','-r0');
% 
% 
% 
% %FUEL CONSUMPTION PLOTS
% 
% profile_data = xlsread("FuelConsumption.xlsx");
% 
% % HYDROGEN
% HydrogenYears = profile_data(:,1); % until replacement in 4.9 years
% HydrogenCons = profile_data(:,2); % hydrogen consumption increase until 4.9 years 
% 
% figure('position',[50,50,1000,600]), hold on, grid on, box on
% plot(HydrogenYears,HydrogenCons,'-b','linewidth',2,'Displayname','Hydrogen consumption increase'); 
% xlabel('Time [years]','Interpreter','latex',FontSize=fs); 
% ylabel('Round trip consumption [tons]','Interpreter','latex',FontSize=fs); 
% legend off
% nameH2cons = 'HydrogenConsumption.png';
% print(sprintf('%s',nameH2cons),'-dpng','-r0');
% 
% 
% %DIESEL
% 
% DieselYears = [1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20]; % until the end of life of the vessel
% DieselCons=[0 0.5	1	1.5	2	0.8	1.4	2	2.6	1.2	1.9	2.6	3.3	1.9	2.5	3.1	3.7	2.5	3.2	3.9]; % progressive percentage increase of diesel consumption in 20 years
% 
% figure('position',[50,50,1000,600]), hold on, grid on, box on
% plot(DieselYears,DieselCons,'-b','linewidth',2,'Displayname','Diesel consumption increase'); 
% xlabel('Time [years]','Interpreter','latex',FontSize=fs); 
% ylabel('Diesel consumption increase [%]','Interpreter','latex',FontSize=fs); 
% legend off
% nameMGOcons = 'MGOConsumption.png';
% print(sprintf('%s',nameMGOcons),'-dpng','-r0');
% 
% 
% 
% 
% % variable CAPEX OF FC and BATT
% FC_YEARS = [2025, 2026, 2027, 2028, 2029];
% FC_CAPEX = [1000 900 800 700 600];
% 
% BAT_YEARS = [2025 2026 2027 2028 2029];
% BAT_CAPEX = [500 430 360 290 224];
% 
% figure('position',[50,50,1000,600]), hold on, grid on, box on
% plot(FC_YEARS,FC_CAPEX,'-b','linewidth',2,'Displayname','FC CAPEX'); 
% plot(BAT_YEARS,BAT_CAPEX,'-g','linewidth',2,'Displayname','BAT CAPEX'); 
% xlabel('Time [years]','Interpreter','latex',FontSize=fs); 
% ylabel('CAPEX [$/kW]','Interpreter','latex',FontSize=fs); 
% legend show
% namecapex = 'VariableCAPEX.png';
% print(sprintf('%s',namecapex),'-dpng','-r0');
% 
% 
% 
% % variable H2 and MGO prices
% FuelYears = [2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035, 2036, 2037, 2038, 2039, 2040, 2041, 2042, 2043, 2044];
% H2price = [4.2
% 4.05
% 3.92
% 3.72
% 3.52
% 3.42
% 3.32
% 3.22
% 3.17
% 3.02
% 2.92
% 2.87
% 2.77
% 2.67
% 2.62
% 2.47
% 2.47
% 2.47
% 2.47
% 2.47
% ];
% 
% H2price = H2price'; % $/kg of green hydrogen pwc
% 
% MGOprice =  [0.82 
%  0.86 
%  0.90 
%  0.94 
%  0.99 
%  1.03 
%  1.07 
%  1.12 
%  1.16 
%  1.21 
%  1.25 
%  1.30 
%  1.34 
%  1.38 
%  1.42 
%  1.47 
%  1.51 
%  1.56 
%  1.62 
%  1.66 
% ];
% 
% MGOprice = MGOprice'; % MGO price in $/kg DNV
% 
% figure('position',[50,50,1000,600]), hold on, grid on, box on
% plot(FuelYears,H2price,'-b','linewidth',2,'Displayname','H2 price'); 
% plot(FuelYears,MGOprice,'-g','linewidth',2,'Displayname','MGO price'); 
% xlabel('Time [years]','Interpreter','latex',FontSize=fs); 
% ylabel('Fuel price [$/kg]','Interpreter','latex',FontSize=fs); 
% legend show
% nameFUEL = 'VariableFUELprices.png';
% print(sprintf('%s',nameFUEL),'-dpng','-r0');