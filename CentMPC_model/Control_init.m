close all; clear;
%% Builds Paths
addpath(genpath('components')); %add component library
addpath(genpath('init'));
addpath(genpath('models'));
addpath(genpath('functions'));
addpath(genpath('auxiliaries'));
addpath(genpath('components'));

%% Initialize Power System
SoH_FC=1.0;
power_system_init;

%% Coordinated Control Settings
Sim_Mode=2; %0:single; 1:full batch; 2:test cycle
Control_Strategy = 2;%0:Filter-based; 1:ECMS; 2:MPC
Prediction_Mode = 1;%0:Constant, 1:Perfect, 2:Data-driven

SoC_ref_default=0.5;
SoC_max=0.8;
SoC_min=0.2;
switch Control_Strategy 
    case 0 %Filter-based
        tau_fd=60;
        alpha_soc=1;
        kp_soc=1*FC_A_Param.P_max;
        N_pred=0;%required for bus signal dimensions
    case 1 %ECMS
        global ecms_optimizer
        Ts_ecms=5;%[s]
        ecms_optimizer = build_ecms_optimizer(Ts_ecms,FC_A_Param,Bat_A_Param,[SoC_ref_default,SoC_min,SoC_max]);
        N_pred=0;%required for bus signal dimensions
    case 2 %MPC
        global mpc_optimizer
        Ts_mpc=30;%[s]
        N_pred=40;%[-]
        mpc_optimizer = build_mpc_optimizer(Ts_mpc,N_pred,FC_A_Param,Bat_A_Param,[SoC_ref_default,SoC_min,SoC_max]);
    otherwise
        display("Invalid Control Strategy")
        return
end

%% Define Bus Datatypes
Com_Init;

%% Simulation settings
t_sim = 1; % [s]
load_filter = false;
tau_load_filter = 1e-3;
P_load_grad_lim = 1e9; %[W/s]

%% Run Simulation
missions=167;%Original Data: 167 mission profiles (not in archive due to confidentiality)

switch Sim_Mode
    case 0
        mission_nr=floor(missions*rand())+1;
        load(['mission_',num2str(mission_nr),'.mat'])%ADD MISSION DATA TO RUN SIMULATION!!!
        load_profile.time = mission.Seconds;
        load_profile.power = 1e3*mission.PowerkW;

        t_stop = max(load_profile.time); % [s] Data is defined in min, so factor 60 is used
        time_vec=load_profile.time;
        power_vec=load_profile.power;
        load_profile_size=size(time_vec);

        if Control_Strategy==2 && Prediction_Mode==2
            [pred_LUT,pred_LUT_time]=create_prediction_LUT(mission.Datetime(1),t_stop);
            if isempty(pred_LUT)
                error(['Invalid Prediction LUT for Mission ',num2str(mission_nr)])
            end
        end

        tic;
        out = sim('Control_Model.slx');
        simulation_time=toc
        plot_results;
        compute_kpi;
    case 1
        for i_mis=1:missions
            mission_nr=i_mis;
            load(['mission_',num2str(mission_nr),'.mat'])
            load_profile.time = mission.Seconds;
            load_profile.power = 1e3*mission.PowerkW;

            t_stop = max(load_profile.time); % [s] Data is defined in min, so factor 60 is used
            time_vec=load_profile.time;
            power_vec=load_profile.power;
            load_profile_size=size(time_vec);

            if Control_Strategy==2 && Prediction_Mode==2
                [pred_LUT,pred_LUT_time]=create_prediction_LUT(mission.Datetime(1),t_stop);
                if isempty(pred_LUT)
                    display(['Invalid Prediction LUT for Mission ',num2str(mission_nr)])
                    kpi.m_h2=[];
                    kpi_vec(i_mis)=kpi;
                    continue
                end
            end

            tic;
            i_mis
            out = sim('Control_Model.slx');
            simulation_time=toc
            compute_kpi;
            kpi_vec(i_mis)=kpi;
        end
    case 2
        %define square pulse
        P_low=1300e3;%[W]
        P_high=3800e3;%[W]
        pulse_start=60*60;%[s]
        pulse_end=pulse_start+60*10;%[s]
        t_stop=pulse_end+60*60;%[s]

        load_profile.time=0:5:t_stop;
        load_profile.power=P_low*(load_profile.time<pulse_start | load_profile.time>pulse_end) + P_high*(load_profile.time>=pulse_start & load_profile.time<=pulse_end);
        time_vec=load_profile.time;
        power_vec=load_profile.power;
        load_profile_size=size(time_vec);

        tic;
        out = sim('Control_Model.slx');
        simulation_time=toc
        plot_results;
        compute_kpi;     
    otherwise
        display("Invalid Sim Mode")
        return
    end