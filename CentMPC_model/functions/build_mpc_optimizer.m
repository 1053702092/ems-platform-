function mpc_optimizer = build_mpc_optimizer(delta_t,N,FC_Param,Bat_Param,SoC_lim)
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
    dyn_cost = FC_Param.Cost_Param.c_FC_deg*FC_Param.dV_dP;%[C/((W/s)^2*s)]

    %Bat Constraint Parameters
    SoC_ref=SoC_lim(1);
    SoC_Min=SoC_lim(2);
    SoC_Max=SoC_lim(3);
    OCV_idx=find(SoC_ref<=Bat_Param.SoC_vec,1);
    OCV=Bat_Param.OCV_arr(OCV_idx);
    C_Bat=Bat_Param.C_Bat;
    Ri=Bat_Param.R_Bat;

    %Bat Cost Parameters
    p_eq=0.4;
    lambda_0=2*static_cost_fit(1)*p_eq*P_FC_Max+static_cost_fit(2);%marginal cost
    lambda_lo=static_cost_fit(2);%marginal cost at minimal power
    lambda_hi=2*static_cost_fit(1)*P_FC_Max+static_cost_fit(2);%marginal cost at reference power
    dlambda_dsoc=0.05*(lambda_lo-lambda_hi)/(SoC_Max-SoC_Min);%ensure monotonous decrease

    %Build Lambda(SoC) Cubic
    A=[SoC_Min^3   SoC_Min^2 SoC_Min 1;...
       SoC_Max^3   SoC_Max^2 SoC_Max 1;...
       SoC_ref^3   SoC_ref^2 SoC_ref 1;...
       3*SoC_ref^2 2*SoC_ref 1       0];
    v=[lambda_hi;lambda_lo;lambda_0;dlambda_dsoc];
    k_SoC=A\v;

    %Optimization Variables
    varu_dPfc=sdpvar(1,N+1);
    varx_Pfc=sdpvar(1,N+2);
    varx_SoC=sdpvar(1,N+2);
    varp_Pl=sdpvar(1,N+1);

    %Equivalent Battery Costs
    lambda=(k_SoC(1)*varx_SoC(1)^3+k_SoC(2)*varx_SoC(1)^2+k_SoC(3)*varx_SoC(1)+k_SoC(4));%SoC dependant Cubic
%     lambda=lambda_0;%SoC independant

    %Optimization
    cost_factor=1e9;
    objective = 0;
    constraints = [];
    for i=1:N+1
        objective = objective + cost_factor*delta_t*(static_cost_fit(1)*varx_Pfc(i)^2 + static_cost_fit(2)*varx_Pfc(i));%static FC cost
        objective = objective + cost_factor*delta_t*dyn_cost*varu_dPfc(i)^2;%dynamic FC cost
        objective = objective + cost_factor*delta_t*lambda*Ri*((varp_Pl(i)-varx_Pfc(i)-varu_dPfc(i)*delta_t/2)/OCV)^2;%battery losses
        constraints = [constraints, varx_Pfc(i+1)==varx_Pfc(i)+varu_dPfc(i)*delta_t];%FC dynamics
        constraints = [constraints, varx_SoC(i+1)==varx_SoC(i)-(varp_Pl(i)-varx_Pfc(i)-varu_dPfc(i)*delta_t/2)/(OCV)*delta_t/(C_Bat*3600)];%Bat dynamics
        constraints = [constraints, varu_dPfc(i)<=dPdt_max, varu_dPfc(i)>=dPdt_min];%input constraints
        constraints = [constraints, varx_Pfc(i)<=P_FC_Max, varx_Pfc(i)>=P_FC_Min];%FC state constraints
        constraints = [constraints, varx_SoC(i)<=SoC_Max, varx_SoC(i)>=SoC_Min];%Bat state constraints
    end
    objective = objective - cost_factor*lambda*varx_SoC(N+2)*OCV*(C_Bat*3600);%Terminal Bat cost
%     objective = objective + cost_factor*((varx_SoC(N+2)-SoC_ref)/(SoC_Max-SoC_ref))^2*lambda_hi*(SoC_Max-SoC_ref)*OCV*C_Bat*3600;
    constraints = [constraints, varx_Pfc(N+2)<=P_FC_Max, varx_Pfc(N+2)>=P_FC_Min];%Terminal FC constraint
    constraints = [constraints, varx_SoC(N+2)<=SoC_Max, varx_SoC(N+2)>=SoC_Min];%Terminal Bat constraint

    ops = sdpsettings('solver','quadprog');
    mpc_optimizer = optimizer(constraints, objective, ops, [varx_Pfc(1),varx_SoC(1),varp_Pl], varu_dPfc);
end