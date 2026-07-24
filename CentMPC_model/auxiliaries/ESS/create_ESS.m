function ESS_Param=create_ESS(E_target,V_target,SoC_vec)
    arguments
        %set default values for missing arguments
        E_target=225e3;%[Wh]
        V_target=400;%[V]
        SoC_vec=0.01:0.001:1;
    end
    %Use Simscape Battery Model
    Simscape_Battery_Init;
    Struct_Bat_Cell=load('Simscape_Battery_LFP_RSPro_NCF_18650-1500mAh-3.2V.mat');%load single cell data
    
    ESS_Param.SoC_vec=SoC_vec;
    ESS_Param.V_target=V_target; %target voltage for battery system
    ESS_Param.E_target=E_target; %target energy for battery system
    
    ESS_Param.N_Series=round(ESS_Param.V_target/Struct_Bat_Cell.Simscape_Battery_Param.V_nom);
    ESS_Param.N_Parallel=round(ESS_Param.E_target/(Struct_Bat_Cell.Simscape_Battery_Param.V_nom*Struct_Bat_Cell.Simscape_Battery_Param.C_nom*ESS_Param.N_Series));
    ESS_Param.I_Max_Bat=ESS_Param.N_Parallel*Struct_Bat_Cell.Simscape_Battery_Param.I_dmax;
    ESS_Param.R_Bat=Struct_Bat_Cell.Simscape_Battery_Param.R_i*ESS_Param.N_Series/ESS_Param.N_Parallel;
    ESS_Param.C_Bat=Struct_Bat_Cell.Simscape_Battery_Param.C_nom*ESS_Param.N_Parallel;
    ESS_Param.Cr_max=ESS_Param.I_Max_Bat/ESS_Param.C_Bat;
    
    Struct_Bat_Cell.Simscape_Battery_Param.tau_bat=1000;
    
    %Simulate Polarization Curve
    simulink_C_rate=0.1;
    simulink_SoC_start=max(ESS_Param.SoC_vec);
    simulink_SoC_end=min(ESS_Param.SoC_vec);
    simulink_time_step=0.1;%[s]
    simulink_stop_time=3600/simulink_C_rate*1.1;%[s]
    simulink_I_discharge=ESS_Param.C_Bat*simulink_C_rate;
    
    BatSimOut=sim('BatSim','SrcWorkspace', 'current');
    temp_idx=find(BatSimOut.SoC_Bat<simulink_SoC_start);
    BatSimOut.arraystart=temp_idx(1);
    temp_idx=find(BatSimOut.SoC_Bat>simulink_SoC_end);
    BatSimOut.arrayend=temp_idx(end);
    temp_SoC=BatSimOut.SoC_Bat(BatSimOut.arraystart:BatSimOut.arrayend);
    temp_V=BatSimOut.V_Bat(BatSimOut.arraystart:BatSimOut.arrayend);
    %save ESS/BatSimData.mat temp_V temp_SoC
    
    %Reduce Array Size
    for temp_idx=1:length(ESS_Param.SoC_vec)
        ESS_Param.OCV_arr(temp_idx)=interp1(temp_SoC,temp_V,ESS_Param.SoC_vec(temp_idx),'linear','extrap');
    end
    ESS_Param.Sim_Param=Struct_Bat_Cell.Simscape_Battery_Param;
end
%plot(SoC_vec,ESS_Param.OCV_arr)
%hold on
%plot(temp_SoC,temp_V)