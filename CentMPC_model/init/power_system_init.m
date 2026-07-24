%% Open Component Models
% DC Link
V_DC_ref = 1000; % [V]

Pload_max = 3800e3;
p_eol=0.9;
p_rat=0.8;
Pstep=50e3;
P_FC_BOL=Pstep*ceil(Pload_max/Pstep/p_eol);

P_thresh=p_eol*p_rat*P_FC_BOL;
E_thresh=750e3;
DoD=0.6;
Estep=50e3;
E_bat_BOL=Estep*ceil(E_thresh/Estep/DoD);


%Fuel Cell
Njoya2009_PEMFC_BOP_Init;
FC_A_Obj  = C_FC(P_FC_BOL,800,0,SoH_FC);
FC_A_Param = FC_A_Obj.get_param();

%Batteries
Simscape_Battery_Init;
E_target=E_bat_BOL;%[Wh] target energy for one battery system
V_target=400;%[V] target voltage for one battery system
SoC_Bat_A_Init=0.5;
Bat_A_Obj = C_ESS(SoC_Bat_A_Init,E_target,V_target);
Bat_A_Param = Bat_A_Obj.get_param();