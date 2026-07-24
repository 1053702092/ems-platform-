function ecms_optimizer = build_ecms_optimizer(delta_t,FC_Param,Bat_Param,SoC_lim)
%% Combined
    yalmip('clear')
    
    %FC Constraint Parameters
    P_FC_Max=FC_Param.P_max;
    P_FC_Min=0;
    dPdt_max = FC_Param.delta_P_max;
    dPdt_min = -dPdt_max;

    %FC Cost Parameters
    fuel_costs = FC_Param.Cost_Param.c_h2*FC_Param.Qh2_arr;
    deg_static_costs = FC_Param.Cost_Param.c_FC_deg*FC_Param.dV_static_arr;
    static_cost_fit = polyfit(FC_Param.P_arr,fuel_costs+deg_static_costs,2);
%     dyn_cost = FC_Param.Cost_Param.c_FC_deg*FC_Param.dV_dP;%[C/((W/s)^2*s)]
    dyn_cost = 1e-12;%[C/((W/s)^2*s)]

    %Bat Constraint Parameters
    SoC_ref=SoC_lim(1);
    SoC_Min=SoC_lim(2);
    SoC_Max=SoC_lim(3);
    OCV_idx=find(SoC_ref<=Bat_Param.SoC_vec,1);
    OCV=Bat_Param.OCV_arr(OCV_idx);
    %C_Bat=Bat_Param.C_Bat;
    Ri=Bat_Param.R_Bat;

    %Bat Cost Parameters
    p_eq=0.4;
    lambda_0=2*static_cost_fit(1)*p_eq*P_FC_Max+static_cost_fit(2);%marginal cost
    lambda_lo=static_cost_fit(2);%marginal cost at minimal power
    lambda_hi=2*static_cost_fit(1)*P_FC_Max+static_cost_fit(2);%marginal cost at reference power
    dlambda_dsoc=0.05*(lambda_lo-lambda_hi)/(SoC_Max-SoC_Min);%ensure monotonous decrease

    %Build Lambda(SoC)
    A=[SoC_Min^3   SoC_Min^2 SoC_Min 1;...
       SoC_Max^3   SoC_Max^2 SoC_Max 1;...
       SoC_ref^3   SoC_ref^2 SoC_ref 1;...
       3*SoC_ref^2 2*SoC_ref 1       0];
    v=[lambda_hi;lambda_lo;lambda_0;dlambda_dsoc];
    k_SoC=A\v;

    %Optimization Variables
    varu_dPfc=sdpvar(1,1);
    varx_Pfc=sdpvar(1,1);
    varx_SoC=sdpvar(1,1);
    varp_Pl=sdpvar(1,1);

    %Optimization - Minimize Marginal Costs (benefits of shifting dPfc)
    cost_factor=1e10;
    objective = 0;
    constraints = [];
    lambda=k_SoC(1)*varx_SoC^3+k_SoC(2)*varx_SoC^2+k_SoC(3)*varx_SoC+k_SoC(4);
%     lambda=lambda_0;
    objective = objective + cost_factor*0.5*delta_t^2*(2*static_cost_fit(1)*varx_Pfc+static_cost_fit(2)-lambda)*varu_dPfc;%marginal FC+Bat costs
    objective = objective + cost_factor*0.5*delta_t^2*lambda*Ri*2*(varp_Pl-varx_Pfc)/OCV*(-1/OCV)*varu_dPfc;%Battery losses
    objective = objective + cost_factor*delta_t*dyn_cost*varu_dPfc^2;%FC dynamic cost

    constraints = [constraints, varu_dPfc<=dPdt_max, varu_dPfc>=dPdt_min];

    ops = sdpsettings('solver','quadprog');
    ecms_optimizer = optimizer(constraints, objective, ops, [varx_Pfc,varx_SoC,varp_Pl], varu_dPfc);
end