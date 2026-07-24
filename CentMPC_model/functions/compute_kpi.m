%% Compute Performance Criteria (KPI)
lhv_h2=33.3;%kWh/kg

kpi.m_h2 = out.m_H2_FC_A_act(end);% [kg]
kpi.m_h2_dt = kpi.m_h2/out.time(end);% [kg/s]
kpi.eta_avg = 100*mean(out.Bus_Plant_FC_A.eta_act.Data); % [%]
kpi.delta_soc = 100*(out.Bus_Plant_Bat_A.SoC_act.Data(1)-out.Bus_Plant_Bat_A.SoC_act.Data(end));
kpi.m_h2_eq = kpi.m_h2+Bat_A_Param.E_target*1e-3*kpi.delta_soc/100/(lhv_h2*kpi.eta_avg/100);
kpi.m_h2_eq_dt = kpi.m_h2_eq/out.time(end);
kpi.dV_stat=out.dV_stat_FC_A_act(end);
kpi.dV_stat_dt=kpi.dV_stat/out.time(end);
kpi.dV_dyn=out.dV_dyn_FC_A_act(end);
kpi.dV_dyn_dt=kpi.dV_dyn/out.time(end);
kpi.dV=kpi.dV_stat+kpi.dV_dyn;
kpi.dV_dt=kpi.dV_stat_dt+kpi.dV_dyn_dt;
kpi.P_FC_avg=mean(out.I_out_FC_A_act)*V_DC_ref;