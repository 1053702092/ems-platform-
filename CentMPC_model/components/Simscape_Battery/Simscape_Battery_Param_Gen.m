%% Generate Parameter Set for Simscape Battery
clear all;close;

% Parameters
Simscape_Battery_Param.V_nom = 7.2; %[V] Nominal voltage
Simscape_Battery_Param.C_rat = 5.4; %[Ah] Rated capacity
Simscape_Battery_Param.tau_bat = 30; %[s] Battery response time

%Discharge
Simscape_Battery_Param.C_max = Simscape_Battery_Param.C_rat; %[Ah] Maximum capacity
Simscape_Battery_Param.V_cutoff = 0.75*Simscape_Battery_Param.V_nom; %[V] Cutoff voltage
Simscape_Battery_Param.V_full = 1.164*Simscape_Battery_Param.V_nom; %[V] Fully charged voltage
Simscape_Battery_Param.I_cnom = 0.4348*Simscape_Battery_Param.C_rat; %[A] Nominal charge current
Simscape_Battery_Param.I_dnom = 0.4348*Simscape_Battery_Param.C_rat; %[A] Nominal discharge current
Simscape_Battery_Param.R_i = 0.013333*Simscape_Battery_Param.V_nom/7.2*5.4/Simscape_Battery_Param.C_rat; %[Ohm] Internal resistance
Simscape_Battery_Param.C_nom = 0.9044*Simscape_Battery_Param.C_rat; %[Ah] Capacity at nominal voltage
Simscape_Battery_Param.V_exp = 1.0804*Simscape_Battery_Param.V_nom; %[V] Voltage, Exponential zone
Simscape_Battery_Param.I_exp = 0.0491*Simscape_Battery_Param.C_rat; %[Ah] Capacity, Exponential zone
Simscape_Battery_Param.I_disp = [0.5 1 2.5]*Simscape_Battery_Param.C_rat ; %[A] Current vector for display

% Aging
Simscape_Battery_Param.t_age_sample = 10; % [s] Aging model smaple time
Simscape_Battery_Param.Ta1 = 25; % [degC] Ambient temperature Ta1
Simscape_Battery_Param.Ta2 = 45; % [degC] Ambient temperature Ta2
Simscape_Battery_Param.C_eol = 0.9*Simscape_Battery_Param.C_nom; % [Ah] Capacity at EOL
Simscape_Battery_Param.R_eol = 1.2*Simscape_Battery_Param.R_i; % [Ohm] Internal resistance at EOL
Simscape_Battery_Param.I_cmax = 0.5556*Simscape_Battery_Param.C_nom; %[A] Maximum charge current
Simscape_Battery_Param.I_dmax = 1.8519*Simscape_Battery_Param.C_nom; %[A] Maximum discharge current
Simscape_Battery_Param.CL_100_nom = 1500; %[-] Cycle life at 100 % DOD, Ic and Id (Cycles)
Simscape_Battery_Param.CL_25_nom = 10500; %[-] Cycle life at 25 % DOD, Ic and Id (Cycles)
Simscape_Battery_Param.CL_100_Idmax = 1000; %[-] Cycle life at 100 % DOD, Ic and Idmax (Cycles)
Simscape_Battery_Param.CL_100_Icmax = 1400; %[-] Cycle life at 100 % DOD, Icmax and Id (Cycles)
Simscape_Battery_Param.CL_100_Ta2 = 950; %[-] Cycle life at 100 % DOD, Ic and Id (Cycles) at Ta2

% Initial Values

Simscape_Battery_Param.soc_init = 0.5; % [-] Initial state-of-charge
Simscape_Battery_Param.age_init = 0; % [-] Intial battery age (Eq. full cycles)

% Store Parameter Set
save Simscape_Battery_LFP_RSPro_NCF_18650-1500mAh-3.2V Simscape_Battery_Param