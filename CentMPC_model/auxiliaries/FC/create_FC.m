function FC_Param = create_FC(P_target,V_target,SoH)
arguments
    %set default values for missing arguments
    P_target=325e3;%maximum power[W]
    V_target=400;%OCV[V]
    SoH=1.0;%Factor for cell voltage
end

FC_Param.delta_P_max=0.05*P_target;%[W/s]
FC_Param.delta_P=1e-4*P_target;%[W]

%% Load Data from Model Library
%Fuel Cell
Njoya2009_PEMFC_BOP_Init;
Nedstack_13XXL_OCV=94;%[V]
Nedstack_13XXL_Imax=230;%[A]
Nedstack_13XXL_Vmin=59;%[V]
%Nedstack 13XXL (13.6kWe) x 24 -> 325kW (4 series, 6 parallel)
%Here: Allow different amount FCs to match voltage and power rating
modules_series=round(V_target/Nedstack_13XXL_OCV);
modules_parallel=round(P_target/(modules_series*Nedstack_13XXL_Imax*Nedstack_13XXL_Vmin));

%Datasheet/test values
PEMFC_Param.E_oc = Nedstack_13XXL_OCV*modules_series; %[V] Open Circuit Voltage (voltage at 0A)
PEMFC_Param.V_1 = 93.1*modules_series; %[V] Voltage at 1A
PEMFC_Param.I_max = Nedstack_13XXL_Imax*modules_parallel; %[A] Max current
PEMFC_Param.V_min = Nedstack_13XXL_Vmin*modules_series*SoH; %[V] Min voltage
PEMFC_Param.I_nom = 120*modules_parallel; %[A] Nominal current
PEMFC_Param.V_nom = 69*modules_series*(1-(1-SoH)*PEMFC_Param.I_nom/PEMFC_Param.I_max); %[V] Nominal voltage
PEMFC_Param.eta_nom = 56; %[%] Nominal efficiency
PEMFC_Param.N_series = 96*modules_series; %[-] Number of cells in series
PEMFC_Param.T_nom = 65; %[degC] Nominal operating Temperature
PEMFC_Param.V_air_nom = 732*modules_series*modules_parallel; %[l/min] Nominal air flow rate
PEMFC_Param.x_nom = 0.999; %[-] Nominal content of hydrogen in fuel
PEMFC_Param.y_nom = 0.21; %[-] Nominal content of oxygen in oxidant
PEMFC_Param.w_nom = 0.01; %[-] Nominal content of water vapor in oxidant
PEMFC_Param.p_h2_nom = 1.25; %[atm] Nominal supply pressure fuel
PEMFC_Param.p_o2_nom = 1.2; %[atm] Nominal supply pressure oxidant (from NS 13XXL)
PEMFC_Param.p_h2_bp = 1.1; %[atm] Backpressure anode(fuel) (from NS 13XXL)
PEMFC_Param.T_d = 10; %[s] Response time (assumed)
PEMFC_Param.U_f_O2 = 1/2.0; %[%] Utilization rate of oxigen (from NS 13XXL)
PEMFC_Param.U_f_H2 = 1/1.25; %[%] Utilization rate of oxigen (from NS 13XXL)
PEMFC_Param.V_u = 0.02*PEMFC_Param.V_nom; %[V] Voltage undershoot (estimated)
PEMFC_Param.I_n = 0.007; %[-] Internal current density relative to maximum current density (estimated from Mao et al. 2017)
PEMFC_Param.delta_T_cool = 5; %[K]
PEMFC_Param.delta_p_cool = 25000; %[Pa]
PEMFC_Param.cp_cool = 4186; %[J/(kg*K)] (demi-water at 60C)
PEMFC_Param.rho_cool = 983.13; %[kg/m^3] (demi-water at 60C)
PEMFC_Param.eta_h2_comp  = 0.7; %Efficiency of H2 compressor (estimated)
PEMFC_Param.eta_air_comp = 0.7; %Efficiency of air compressor (estimated)
PEMFC_Param.eta_cool_pump= 0.7; %Efficiency of cooling pump (guessed)
%Model parameter approximation
PEMFC_Param.NA=((PEMFC_Param.V_1-PEMFC_Param.V_nom)*(PEMFC_Param.I_max-1)...
                                -(PEMFC_Param.V_1-PEMFC_Param.V_min)*(PEMFC_Param.I_nom-1))...
                                /(log(PEMFC_Param.I_nom)*(PEMFC_Param.I_max-1)...
                                -log(PEMFC_Param.I_max)*(PEMFC_Param.I_nom-1));
PEMFC_Param.R_ohm=(PEMFC_Param.V_1-PEMFC_Param.V_nom...
                                -PEMFC_Param.NA*log(PEMFC_Param.I_nom))...
                                /(PEMFC_Param.I_nom-1);
PEMFC_Param.i_0=exp((PEMFC_Param.V_1-PEMFC_Param.E_oc+PEMFC_Param.R_ohm)...
                                /PEMFC_Param.NA);

%% Generate Degradation Curve
FC_Param.threshold_lo=0.1; %[%] treshold between low and base power operation
FC_Param.threshold_hi=0.8; %[%] treshold between base and high power operation
FC_Param.dV_dt_base=2e-6; %[V/h] hourly degradation in base power region
FC_Param.dV_dt_lo=8.6e-6; %[V/h] hourly degradation in low power region
FC_Param.dV_dt_hi=10e-6; %[V/h] hourly degradation in high power region
% FC_Param.dV_dyn=0.5*0.0441e-6*4.8; %[V/-] voltage loss from dynamic loading 0-100%; from Fletcher 
% FC_Param.dV_dyn=0.5*5.93e-7*PEMFC_Param.E_oc/PEMFC_Param.N_series; %[V/-] voltage loss from dynamic loading 0-100%; from Pei
FC_Param.dV_dyn=0.5*1.9e-5; %[V/-] voltage loss from dynamic loading 0-100%; from Meng
FC_Param.dV_tref=10; %[s] reference cycling time for dynamic degradation
FC_Param.dV_dP=FC_Param.dV_dyn*FC_Param.dV_tref/(PEMFC_Param.I_max*PEMFC_Param.V_min)^2;%[V/s/(W/s)^2]
FC_Param.dV_on=13.79e-6; %[V] degradation due to on-switching (off-sw. assumed 0V)

PEMFC_Param.dV_loading_arr=0:0.001:1;
PEMFC_Param.dV_dI=FC_Param.dV_dyn*FC_Param.dV_tref/(PEMFC_Param.I_max)^2;%[V/s/(W/s)^2]
PEMFC_Param.dV_static_arr=1/3600*create_FC_deg(FC_Param.dV_dt_lo,FC_Param.dV_dt_base,FC_Param.dV_dt_hi,FC_Param.threshold_lo,FC_Param.threshold_hi,PEMFC_Param.dV_loading_arr,'logistic');

%% Simulate Polarization Curve
simulink_dIdt_rate=10;%[A/s]
simulink_ramp_start_time=10;%[s]
simulink_I_end=PEMFC_Param.I_max;
simulink_time_step=0.1;%[s]
simulink_stop_time=simulink_ramp_start_time + simulink_I_end/simulink_dIdt_rate + 10;%[s]

FCSimOut=sim('FCSim','SrcWorkspace', 'current');
temp_idx=find(FCSimOut.I_FC==0.0);
FCSimOut.arraystart=temp_idx(end);
temp_idx=find(FCSimOut.I_FC<=simulink_I_end);
FCSimOut.arrayend=temp_idx(end);
temp_I_FC=FCSimOut.I_FC(FCSimOut.arraystart:FCSimOut.arrayend);
temp_V_FC=FCSimOut.V_FC(FCSimOut.arraystart:FCSimOut.arrayend);
temp_Qh2=FCSimOut.Q_h2(FCSimOut.arraystart:FCSimOut.arrayend);
temp_eta_stack=FCSimOut.eta_stack(FCSimOut.arraystart:FCSimOut.arrayend);
temp_eta_sys=FCSimOut.eta_system(FCSimOut.arraystart:FCSimOut.arrayend);
temp_P_BOP=FCSimOut.P_BOP(FCSimOut.arraystart:FCSimOut.arrayend);
temp_P_FC=temp_I_FC.*temp_V_FC-temp_P_BOP;

FC_Param.N_series=PEMFC_Param.N_series;
FC_Param.P_min=0;%[W]
FC_Param.P_max=temp_P_FC(end);
% %Reduce Array Size
FC_Param.P_arr=0:FC_Param.delta_P:FC_Param.P_max;
FC_Param.P_max=FC_Param.P_arr(end);
for temp_idx=1:length(FC_Param.P_arr)
    FC_Param.I_arr(temp_idx)=interp1(temp_P_FC,temp_I_FC,FC_Param.P_arr(temp_idx),'linear');
    FC_Param.V_arr(temp_idx)=interp1(temp_P_FC,temp_V_FC,FC_Param.P_arr(temp_idx),'linear');
    FC_Param.Qh2_arr(temp_idx)=interp1(temp_P_FC,temp_Qh2,FC_Param.P_arr(temp_idx),'linear');
    FC_Param.eta_stack_arr(temp_idx)=interp1(temp_P_FC,temp_eta_stack,FC_Param.P_arr(temp_idx),'linear');
    FC_Param.eta_sys_arr(temp_idx)=interp1(temp_P_FC,temp_eta_sys,FC_Param.P_arr(temp_idx),'linear');
end
%Overwrite static deg array with new breakpoints from simulation
FC_Param.dV_static_arr=1/3600*create_FC_deg(FC_Param.dV_dt_lo,FC_Param.dV_dt_base,FC_Param.dV_dt_hi,FC_Param.threshold_lo,FC_Param.threshold_hi,FC_Param.P_arr/FC_Param.P_arr(end),'logistic');

%% Set Cost Params
%Hydrogen Costs
Cost_Param.c_h2=8;%[Euro/kg]
%FC Degrad.tion Costs
Cost_Param.c_FC_stack=1.5; %[Euro/W]
Cost_Param.stack_ratio=0.5; %Stack Replacement Costs/Capex
% Cost_Param.dV_EOL=0.075;%[V] voltage loss at EOL
Cost_Param.dV_EOL=0.1*PEMFC_Param.V_min/PEMFC_Param.N_series/SoH;%[V] voltage loss at EOL (referred to BOL system)
Cost_Param.C_stack_replace=Cost_Param.stack_ratio*Cost_Param.c_FC_stack*FC_Param.P_max/SoH;
Cost_Param.c_FC_deg=Cost_Param.C_stack_replace/Cost_Param.dV_EOL; %[Euro/V]
FC_Param.Cost_Param = Cost_Param;
FC_Param.Sim_Param = PEMFC_Param;
