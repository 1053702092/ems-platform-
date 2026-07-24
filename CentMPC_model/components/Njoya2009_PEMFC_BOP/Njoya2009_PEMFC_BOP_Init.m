% Implemented by Timon Kopka based on literature reference 05-2023

% FUEL CELL STACK
% Model Source: Njoya et al. 2009 - A generic fuel cell model for the simulation of fuel cell vehicles
% Calculation H2 consumption + efficiency - PEM Fuel Cells: Theory and Practice Chapter 3

% INTERNAL CURRENTS
% Modeled as percentage of maximum current based on data from Mao et al.
% 2017 - Investigation of polymer electrolyte membrane fuel cell internal behaviour during long term operation and its use in prognostics

% AIR COMPRESSION
% based on datasheet values; adiabatic compression + constant compressor
% efficiency

% H2 RECIRCULATION
% based on datasheet values; adiabatic compression + constant compressor
% efficiency

% COOLING PUMP
% based on datasheet values; required flow power P=Vdot*delta_p(assuming no compression); Volume flow based on max temperature drop and values for cooling liquid; constant pump
% efficiency

%% Notes
% Simplified model. Not taking into account BOP, concentration losses, etc.
% Simplified BOP components. Only air+H2 compression and cooling pump.

%% Define Output Bus
bus_elems(1)=Simulink.BusElement;
bus_elems(1).Name='V_FC'; %Stack output voltage [V]
bus_elems(1).DataType='double';
bus_elems(2)=Simulink.BusElement;
bus_elems(2).Name='eta_stack'; %Stack efficiency [-]
bus_elems(2).DataType='double';
bus_elems(3)=Simulink.BusElement;
bus_elems(3).Name='eta_system'; %System efficiency [-]
bus_elems(3).DataType='double';
bus_elems(4)=Simulink.BusElement;
bus_elems(4).Name='dmdt_H2'; %Hydrogen flow [kg/s]
bus_elems(4).DataType='double';
bus_elems(5)=Simulink.BusElement;
bus_elems(5).Name='dVdt_air'; %Air flow [m^3/s]
bus_elems(5).DataType='double';
bus_elems(6)=Simulink.BusElement;
bus_elems(6).Name='P_BOP'; %Total BOP power [W]
bus_elems(6).DataType='double';
bus_elems(7)=Simulink.BusElement;
bus_elems(7).Name='P_air'; %Power for air compression [W]
bus_elems(7).DataType='double';
bus_elems(8)=Simulink.BusElement;
bus_elems(8).Name='P_H2'; %Power for H2 recirculation [W]
bus_elems(8).DataType='double';
bus_elems(9)=Simulink.BusElement;
bus_elems(9).Name='P_cool'; %Power for cooling pump [W]
bus_elems(9).DataType='double';
bus_elems(10)=Simulink.BusElement;
bus_elems(10).Name='dV_stat'; %Static degradation [V/cell]
bus_elems(10).DataType='double';
bus_elems(11)=Simulink.BusElement;
bus_elems(11).Name='dV_dyn'; %Dynamic degradation [V/cell]
bus_elems(11).DataType='double';
Bus_PEMFC=Simulink.Bus;
Bus_PEMFC.Elements=bus_elems;
clear bus_elems

%% Constants
PEMFC_Param.F               = 96485;                % Faraday constant [C/mol]
PEMFC_Param.R               = 8.3145;               % Gas constant [J/mol K]
PEMFC_Param.k               = 1.38e-23;             % Boltzmann constant [J/K]
PEMFC_Param.h               = 6.626e-34;            % Planck constant [J/K]
PEMFC_Param.delH_H2O_l      = 285.84e3;             % Enthalpy of H20 formation [J/mol]
PEMFC_Param.z               = 2;                    % Number of moving electrons per H2 molecule [-]
PEMFC_Param.delta_H         = 241.83e3;             % Hydrogen's lower heating value [J/mol]
PEMFC_Param.M_H2            = 2;                    % Molar mass of H2 [g/mol]
PEMFC_Param.M_O2            = 32;                   % Molar mass of O2 [g/mol]
PEMFC_Param.gamma_air       = 1.40;                 % Adiabatic constant of air, dry, 20C [J/(molK)] (wikipedia)
PEMFC_Param.gamma_h2        = 1.41;                 % Adiabatic constant of air, dry, 20C [J/(molK)] (wikipedia)
PEMFC_Param.rho_o2          = 1.43;                 % Density of O2 at STP [kg/m^3]
PEMFC_Param.rho_h2          = 0.090;                % Density of H2 at STP [kg/m^3]
PEMFC_Param.p_atm           = 101325;               % Standard atmospheric pressure [Pa]

%% Dataset Nedstack PS6
% Data for Nedstack PS6 taken from example in source

%Datasheet/test values
PEMFC_Nedstack_PS6_Param.E_oc = 65; %[V] Open Circuit Voltage (voltage at 0A)
PEMFC_Nedstack_PS6_Param.V_1 = 63; %[V] Voltage at 1A
PEMFC_Nedstack_PS6_Param.I_nom = 133.3; %[A] Nominal current
PEMFC_Nedstack_PS6_Param.V_nom = 45; %[V] Nominal voltage
PEMFC_Nedstack_PS6_Param.I_max = 225; %[A] Max current
PEMFC_Nedstack_PS6_Param.V_min = 37; %[V] Min voltage
PEMFC_Nedstack_PS6_Param.eta_nom = 55; %[%] Nominal efficiency
PEMFC_Nedstack_PS6_Param.N_series = 65; %[-] Number of cells in series
PEMFC_Nedstack_PS6_Param.T_nom = 65; %[degC] Nominal operating Temperature
PEMFC_Nedstack_PS6_Param.V_air_nom = 297; %[l/min] Nominal air flow rate
PEMFC_Nedstack_PS6_Param.x_nom = 0.999; %[%] Nominal percentage of hydrogen in fuel
PEMFC_Nedstack_PS6_Param.y_nom = 0.21; %[%] Nominal percentage of oxygen in oxidant
PEMFC_Nedstack_PS6_Param.w_nom = 1; %[%] Nominal percentage of water vapor in oxidant
PEMFC_Nedstack_PS6_Param.p_h2_nom = 1.25; %[atm] Nominal supply pressure fuel
PEMFC_Nedstack_PS6_Param.p_o2_nom = 1.2; %[atm] Nominal supply pressure oxidant (from NS 13XXL)
PEMFC_Nedstack_PS6_Param.p_h2_bp = 1.1; %[atm] Backpressure anode(fuel) (from NS 13XXL)
PEMFC_Nedstack_PS6_Param.T_d = 1; %[s] Response time (assumed)
PEMFC_Nedstack_PS6_Param.U_f_O2 = 1/2.0; %[%] Utilization rate of oxigen (from NS 13XXL)
PEMFC_Nedstack_PS6_Param.U_f_H2 = 1/1.25; %[%] Utilization rate of oxigen (from NS 13XXL)
PEMFC_Nedstack_PS6_Param.V_u = 0.02*PEMFC_Nedstack_PS6_Param.V_nom; %[V] Voltage undershoot (estimated)
PEMFC_Nedstack_PS6_Param.I_n = 0.007; %[-] Internal current density relative to maximum current density (estimated from Mao et al. 2017)
PEMFC_Nedstack_PS6_Param.delta_T_cool = 5; %[K]
PEMFC_Nedstack_PS6_Param.delta_p_cool = 25000; %[Pa]
PEMFC_Nedstack_PS6_Param.cp_cool = 4186; %[J/(kg*K)] (demi-water at 60C)
PEMFC_Nedstack_PS6_Param.rho_cool = 983.13; %[kg/m^3] (demi-water at 60C)
PEMFC_Nedstack_PS6_Param.eta_h2_comp  = 0.7; %Efficiency of H2 compressor (estimated)
PEMFC_Nedstack_PS6_Param.eta_air_comp = 0.7; %Efficiency of air compressor (estimated)
PEMFC_Nedstack_PS6_Param.eta_cool_pump= 0.7; %Efficiency of cooling pump (guessed)

%Model parameter approximation
PEMFC_Nedstack_PS6_Param.NA=((PEMFC_Nedstack_PS6_Param.V_1-PEMFC_Nedstack_PS6_Param.V_nom)*(PEMFC_Nedstack_PS6_Param.I_max-1)...
                                -(PEMFC_Nedstack_PS6_Param.V_1-PEMFC_Nedstack_PS6_Param.V_min)*(PEMFC_Nedstack_PS6_Param.I_nom-1))...
                                /(log(PEMFC_Nedstack_PS6_Param.I_nom)*(PEMFC_Nedstack_PS6_Param.I_max-1)...
                                -log(PEMFC_Nedstack_PS6_Param.I_max)*(PEMFC_Nedstack_PS6_Param.I_nom-1));
PEMFC_Nedstack_PS6_Param.R_ohm=(PEMFC_Nedstack_PS6_Param.V_1-PEMFC_Nedstack_PS6_Param.V_nom...
                                -PEMFC_Nedstack_PS6_Param.NA*log(PEMFC_Nedstack_PS6_Param.I_nom))...
                                /(PEMFC_Nedstack_PS6_Param.I_nom-1);
PEMFC_Nedstack_PS6_Param.i_0=exp((PEMFC_Nedstack_PS6_Param.V_1-PEMFC_Nedstack_PS6_Param.E_oc+PEMFC_Nedstack_PS6_Param.R_ohm)...
                                /PEMFC_Nedstack_PS6_Param.NA);
% PEMFC_Nedstack_PS6_Param.alpha=PEMFC_Nedstack_PS6_Param.N_series*PEMFC_Param.R*PEMFC_Nedstack_PS6_Param.T_nom...
%                                 /(PEMFC_Param.z*PEMFC_Param.F*PEMFC_Nedstack_PS6_Param.NA);
% PEMFC_Nedstack_PS6_Param.delta_G=
% PEMFC_Nedstack_PS6_Param.K_c=
% PEMFC_Nedstack_PS6_Param.K=

%% Dataset 250kW Nedstack
%Data based on scaling of PS6 module (x8 in series, x5 in parallel)

%Datasheet/test values
PEMFC_Nedstack_250kW_Param.E_oc = 65*8; %[V] Open Circuit Voltage (voltage at 0A)
PEMFC_Nedstack_250kW_Param.V_1 = 63*8; %[V] Voltage at 1A
PEMFC_Nedstack_250kW_Param.I_nom = 133.3*5; %[A] Nominal current
PEMFC_Nedstack_250kW_Param.V_nom = 45*8; %[V] Nominal voltage
PEMFC_Nedstack_250kW_Param.I_max = 225*5; %[A] Max current
PEMFC_Nedstack_250kW_Param.V_min = 37*8; %[V] Min voltage
PEMFC_Nedstack_250kW_Param.eta_nom = 55; %[%] Nominal efficiency
PEMFC_Nedstack_250kW_Param.N_series = 65*8; %[-] Number of cells in series
PEMFC_Nedstack_250kW_Param.T_nom = 65; %[degC] Nominal operating Temperature
PEMFC_Nedstack_250kW_Param.V_air_nom = 297*8*5; %[l/min] Nominal air flow rate
PEMFC_Nedstack_250kW_Param.x_nom = 0.999; %[%] Nominal percentage of hydrogen in fuel
PEMFC_Nedstack_250kW_Param.y_nom = 0.21; %[%] Nominal percentage of oxygen in oxidant
PEMFC_Nedstack_250kW_Param.w_nom = 1; %[%] Nominal percentage of water vapor in oxidant
PEMFC_Nedstack_250kW_Param.p_h2_nom = 1.25; %[atm] Nominal supply pressure fuel
PEMFC_Nedstack_250kW_Param.p_o2_nom = 1.2; %[atm] Nominal supply pressure oxidant (from NS 13XXL)
PEMFC_Nedstack_250kW_Param.p_h2_bp = 1.1; %[atm] Backpressure anode(fuel) (from NS 13XXL)
PEMFC_Nedstack_250kW_Param.T_d = 1; %[s] Response time (assumed)
PEMFC_Nedstack_250kW_Param.U_f_O2 = 1/2.0; %[%] Utilization rate of oxigen (from NS 13XXL)
PEMFC_Nedstack_250kW_Param.U_f_H2 = 1/1.25; %[%] Utilization rate of oxigen (from NS 13XXL)
PEMFC_Nedstack_250kW_Param.V_u = 0.02*PEMFC_Nedstack_250kW_Param.V_nom; %[V] Voltage undershoot (estimated)
PEMFC_Nedstack_250kW_Param.I_n = 0.007; %[-] Internal current density relative to maximum current density (estimated from Mao et al. 2017)
PEMFC_Nedstack_250kW_Param.delta_T_cool = 5; %[K]
PEMFC_Nedstack_250kW_Param.delta_p_cool = 25000; %[Pa]
PEMFC_Nedstack_250kW_Param.cp_cool = 4186; %[J/(kg*K)] (demi-water at 60C)
PEMFC_Nedstack_250kW_Param.rho_cool = 983.13; %[kg/m^3] (demi-water at 60C)
PEMFC_Nedstack_250kW_Param.eta_h2_comp  = 0.7; %Efficiency of H2 compressor (estimated)
PEMFC_Nedstack_250kW_Param.eta_air_comp = 0.7; %Efficiency of air compressor (estimated)
PEMFC_Nedstack_250kW_Param.eta_cool_pump= 0.7; %Efficiency of cooling pump (guessed)

%Model parameter approximation
PEMFC_Nedstack_250kW_Param.NA=((PEMFC_Nedstack_250kW_Param.V_1-PEMFC_Nedstack_250kW_Param.V_nom)*(PEMFC_Nedstack_250kW_Param.I_max-1)...
                                -(PEMFC_Nedstack_250kW_Param.V_1-PEMFC_Nedstack_250kW_Param.V_min)*(PEMFC_Nedstack_250kW_Param.I_nom-1))...
                                /(log(PEMFC_Nedstack_250kW_Param.I_nom)*(PEMFC_Nedstack_250kW_Param.I_max-1)...
                                -log(PEMFC_Nedstack_250kW_Param.I_max)*(PEMFC_Nedstack_250kW_Param.I_nom-1));
PEMFC_Nedstack_250kW_Param.R_ohm=(PEMFC_Nedstack_250kW_Param.V_1-PEMFC_Nedstack_250kW_Param.V_nom...
                                -PEMFC_Nedstack_250kW_Param.NA*log(PEMFC_Nedstack_250kW_Param.I_nom))...
                                /(PEMFC_Nedstack_250kW_Param.I_nom-1);
PEMFC_Nedstack_250kW_Param.i_0=exp((PEMFC_Nedstack_250kW_Param.V_1-PEMFC_Nedstack_250kW_Param.E_oc+PEMFC_Nedstack_250kW_Param.R_ohm)...
                                /PEMFC_Nedstack_250kW_Param.NA);

%% Dataset MT FCPP 100 from Nedstack
%Data based on scaling of PS6 module (x8 in series, x5 in parallel)

%Datasheet/test values
MTFCPP100_FC_Param.E_oc = 94*6; %[V] Open Circuit Voltage (voltage at 0A)
MTFCPP100_FC_Param.V_1 = 93.1*6; %[V] Voltage at 1A
MTFCPP100_FC_Param.I_nom = 120*2; %[A] Nominal current
MTFCPP100_FC_Param.V_nom = 69*6; %[V] Nominal voltage
MTFCPP100_FC_Param.I_max = 230*2; %[A] Max current
MTFCPP100_FC_Param.V_min = 59*6; %[V] Min voltage
MTFCPP100_FC_Param.eta_nom = 56; %[%] Nominal efficiency
MTFCPP100_FC_Param.N_series = 96*6; %[-] Number of cells in series
MTFCPP100_FC_Param.T_nom = 65; %[degC] Nominal operating Temperature
MTFCPP100_FC_Param.V_air_nom = 732*6*2; %[l/min] Nominal air flow rate
MTFCPP100_FC_Param.x_nom = 0.999; %[-] Nominal content of hydrogen in fuel
MTFCPP100_FC_Param.y_nom = 0.21; %[-] Nominal content of oxygen in oxidant
MTFCPP100_FC_Param.w_nom = 0.01; %[-] Nominal content of water vapor in oxidant
MTFCPP100_FC_Param.p_h2_nom = 1.25; %[atm] Nominal supply pressure fuel
MTFCPP100_FC_Param.p_o2_nom = 1.2; %[atm] Nominal supply pressure oxidant (from NS 13XXL)
MTFCPP100_FC_Param.p_h2_bp = 1.1; %[atm] Backpressure anode(fuel) (from NS 13XXL)
MTFCPP100_FC_Param.T_d = 10; %[s] Response time (assumed)
MTFCPP100_FC_Param.U_f_O2 = 1/2.0; %[%] Utilization rate of oxigen (from NS 13XXL)
MTFCPP100_FC_Param.U_f_H2 = 1/1.25; %[%] Utilization rate of oxigen (from NS 13XXL)
MTFCPP100_FC_Param.V_u = 0.02*MTFCPP100_FC_Param.V_nom; %[V] Voltage undershoot (estimated)
MTFCPP100_FC_Param.I_n = 0.007; %[-] Internal current density relative to maximum current density (estimated from Mao et al. 2017)
MTFCPP100_FC_Param.delta_T_cool = 5; %[K]
MTFCPP100_FC_Param.delta_p_cool = 25000; %[Pa]
MTFCPP100_FC_Param.cp_cool = 4186; %[J/(kg*K)] (demi-water at 60C)
MTFCPP100_FC_Param.rho_cool = 983.13; %[kg/m^3] (demi-water at 60C)
MTFCPP100_FC_Param.eta_h2_comp  = 0.7; %Efficiency of H2 compressor (estimated)
MTFCPP100_FC_Param.eta_air_comp = 0.7; %Efficiency of air compressor (estimated)
MTFCPP100_FC_Param.eta_cool_pump= 0.7; %Efficiency of cooling pump (guessed)

%Model parameter approximation
MTFCPP100_FC_Param.NA=((MTFCPP100_FC_Param.V_1-MTFCPP100_FC_Param.V_nom)*(MTFCPP100_FC_Param.I_max-1)...
                                -(MTFCPP100_FC_Param.V_1-MTFCPP100_FC_Param.V_min)*(MTFCPP100_FC_Param.I_nom-1))...
                                /(log(MTFCPP100_FC_Param.I_nom)*(MTFCPP100_FC_Param.I_max-1)...
                                -log(MTFCPP100_FC_Param.I_max)*(MTFCPP100_FC_Param.I_nom-1));
MTFCPP100_FC_Param.R_ohm=(MTFCPP100_FC_Param.V_1-MTFCPP100_FC_Param.V_nom...
                                -MTFCPP100_FC_Param.NA*log(MTFCPP100_FC_Param.I_nom))...
                                /(MTFCPP100_FC_Param.I_nom-1);
MTFCPP100_FC_Param.i_0=exp((MTFCPP100_FC_Param.V_1-MTFCPP100_FC_Param.E_oc+MTFCPP100_FC_Param.R_ohm)...
                                /MTFCPP100_FC_Param.NA);

