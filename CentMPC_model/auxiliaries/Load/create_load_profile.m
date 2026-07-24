function [Steps,Power]=create_load_profile(delta_t)
    %% Load Power Profile
    % data_read=h5read('Ankie_20230404_200ms.h5','/data/table'); %short maneuvering
    % load_profile.time = data_read.Time_s(5*45000:5*53000)-data_read.Time_s(5*45000);
    % load_profile.power = data_read.Power_Prop_W(5*45000:5*53000)+data_read.Power_Shaft_Gen_W(5*45000:5*53000)+data_read.Power_Aux_gen_W(5*45000:5*53000);
    % data_read=h5read('Ankie_20230402_200ms.h5','/data/table'); %variable operation
    % load_profile.time = data_read.Time_s(5*20000:5*65000)-data_read.Time_s(5*20000);
    % load_profile.power = data_read.Power_Prop_W(5*20000:5*65000)+data_read.Power_Shaft_Gen_W(5*20000:5*65000)+data_read.Power_Aux_gen_W(5*20000:5*65000);
    
    data_read_A=h5read('Ankie_20230411_200ms.h5','/data/table'); %variable operation short part A
    data_read_B=h5read('Ankie_20230412_200ms.h5','/data/table'); %variable operation short part B
    load_profile.time_A = data_read_A.Time_s(5*65000:end)-data_read_A.Time_s(5*65000);
    load_profile.power_A = data_read_A.Power_Prop_W(5*65000:end)+data_read_A.Power_Shaft_Gen_W(5*65000:end)+data_read_A.Power_Aux_gen_W(5*65000:end);
    load_profile.time_B = data_read_B.Time_s(2:5*5000)+load_profile.time_A(end);
    load_profile.power_B = data_read_B.Power_Prop_W(2:5*5000)+data_read_B.Power_Shaft_Gen_W(2:5*5000)+data_read_B.Power_Aux_gen_W(2:5*5000);
    load_profile.time=[load_profile.time_A;load_profile.time_B];
    load_profile.power=[load_profile.power_A;load_profile.power_B];
    
    %% Sectionalize Power Profile
    no_intervals=floor(load_profile.time(end)/delta_t);
    interval_elems=floor(length(load_profile.time)/no_intervals);
    Steps=1:no_intervals;
    Power=zeros(1,no_intervals);
    for k=1:(no_intervals)
        Power(k)=mean(load_profile.power(((interval_elems*k-(interval_elems-1):k*interval_elems))));  
    end
end