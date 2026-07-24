classdef C_FC < C_Module
    %C_FC Summary of this class goes here
    %   Detailed explanation goes here
    properties (Access=private)
        FC_Param
        x_power
        curve_fit
        opti
    end
    properties (Access = protected)     
        bid
        vec_power
        vec_costs
        vec_marginal_costs
        memory
        clock
    end
%% Constructor
    methods
        function obj = C_FC(P,V,P_init,SoH)
            arguments
                %set default values for missing arguments
                P=325e3;
                V=400;
                P_init=0;%initial power
                SoH=1.0;%state-of-health
            end 
            obj.FC_Param=create_FC(P,V,SoH);
            obj.bid=0;
            obj.vec_power=[];
            obj.vec_costs=[];
            obj.vec_marginal_costs=[];
            obj.curve_fit=[];
            obj.memory=[];
            obj.clock=0;
            obj.opti=[];

            obj.x_power=P_init;
            obj.memory.power(1)=P_init;
            obj.memory.h2_consumption(1)=0;%not accurate/ improvement required?
            obj.memory.vdeg_static(1)=0;%not accurate/ improvement required?
        end
%% Getter
        function Param = get_param(obj)
            Param = obj.FC_Param;
        end

        function memory = read_memory(obj)
            memory = obj.memory;
        end

        function [marginal_costs, power] = get_marginal_costs(obj)
            marginal_costs=obj.vec_marginal_costs;
            power=obj.vec_power;
        end
%% Setter
        function create_costs(obj)
            if isempty(obj.vec_costs)
                fuel_costs = obj.FC_Param.Cost_Param.c_h2*obj.FC_Param.Qh2_arr;
                deg_static_costs = 0;%obj.FC_Param.Cost_Param.c_FC_deg*obj.FC_Param.dV_static_arr/3600;
                obj.vec_costs = fuel_costs + deg_static_costs;
            end
            if isempty(obj.vec_power)
                obj.vec_power = obj.FC_Param.P_arr;
            end
            obj.curve_fit = polyfit(obj.vec_power,obj.vec_costs,2);

            marginal_costs = (obj.vec_costs(2:end)-obj.vec_costs(1:end-1))./(obj.vec_power(2:end)-obj.vec_power(1:end-1));%[Euro/s]
            obj.vec_marginal_costs = [marginal_costs marginal_costs(end)];
        end

        function build_optimizer(obj)
            yalmip('clear')
            P_max = obj.vec_power(end);
            dP_max = obj.FC_Param.delta_P_max;

            varx_P = sdpvar(1,2); %[W]
            varu_dP = sdpvar(1,1); %[W/s]
            var_price = sdpvar(1,1); %[Eur/kW]
            var_time = sdpvar(1,1); %[s]
            constraints = [];

            objective = 1e12* (obj.curve_fit(1)*varx_P(2)^2 + (obj.curve_fit(2)-var_price)*varx_P(2) + 0*(varu_P^2));%objective function/ multiplied by 1e3 so that solution converges (numerical issue, objective function too small?)
            constraints = [constraints, varx_P(2)==varx_P(1)+varu_dP*var_time];%state transition
            constraints = [constraints, varu_dP<=dP_max, varu_dP>=(-dP_max), varx_P(2)<=P_max, varx_P(2)>=0];%inequalities
             
            ops = sdpsettings('solver','quadprog');
            obj.opti = optimizer(constraints, objective, ops, [varx_P(1),var_price,var_time], varu_dP); %x(:,1) is the current measured state - acts as a input argument; u is the output argument
        end
%% Simulation
        function bid = get_bid(obj,price,delta_t)
            arguments
                obj
                price=[]
                delta_t=0
            end
            if isempty(price)
                bid=obj.bid;
                return
            end
            dP_opt=obj.opti([obj.x_power,price,delta_t]);
            obj.bid=min(obj.vec_power(end),obj.x_power+dP_opt*delta_t);
            bid=obj.bid;
        end

        function run(obj,delta_t)
            obj.clock=obj.clock+1;
            obj.memory.power(obj.clock)=obj.bid;%apply last bid
            obj.x_power=obj.bid;
            p_idx=find(obj.bid<=obj.vec_power,1);
            obj.memory.h2_consumption(obj.clock)=obj.FC_Param.Qh2_arr(p_idx)*delta_t;
            obj.memory.vdeg_static(obj.clock)=obj.FC_Param.dV_static_arr(p_idx)*delta_t/3600;
            obj.bid=0;
        end
%% Plots
        function plot_costs(obj)
            cost_est = obj.curve_fit(1)*obj.vec_power.^2 + obj.curve_fit(2)*obj.vec_power + obj.curve_fit(3);
            figure
            subplot(2,1,1)
            plot(obj.vec_power*1e-3,obj.vec_costs,'b-')
            hold on
            plot(obj.vec_power*1e-3,cost_est,'b--')
            ylabel('E/s')
            grid on
            subplot(2,1,2)
            plot(obj.vec_power*1e-3,obj.vec_marginal_costs)
            ylabel('Costs [dE/Ws]')
            xlabel('Power [kW]')
            grid on
        end
    end
end

