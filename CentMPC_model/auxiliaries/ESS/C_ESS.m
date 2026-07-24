%% Head
classdef C_ESS < C_Module
    properties (Access=private)
        ESS_Param
        lambda
        x_soc
        vec_soc
        vec_current
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
        function obj = C_ESS(soc_init,E,V)
            arguments
                %set default values for missing arguments
                soc_init=0.5;
                E=225e3;
                V=400;
            end
            obj.ESS_Param=create_ESS(E,V);
            obj.bid=0;
            obj.vec_power=[];
            obj.vec_costs=[];
            obj.vec_marginal_costs=[];
            obj.vec_current=linspace(-obj.ESS_Param.I_Max_Bat,obj.ESS_Param.I_Max_Bat,1000);
            obj.x_soc=soc_init;
            obj.memory=[];
            obj.memory.soc(1)=soc_init;
            obj.vec_soc=[];
            obj.lambda=[];
            obj.clock=0;
            obj.opti=[];
        end
%% Getter
        function Param = get_param(obj)
            Param = obj.ESS_Param;
        end

        function memory = read_memory(obj)
            memory = obj.memory;
        end

        function [marginal_costs, power] = get_marginal_costs(obj)
            marginal_costs=obj.vec_marginal_costs;
            power=obj.vec_power;
        end

%% Setter
        function set_lambda(obj,soc,lambda)
            obj.vec_soc=soc;
            obj.lambda=lambda;
        end

        function [soc,lambda] = get_lambda(obj)
            soc=obj.vec_soc;
            lambda=obj.lambda;
        end

        function create_costs(obj)
            OCV_idx=find(obj.x_soc<=obj.ESS_Param.SoC_vec,1);
            OCV=obj.ESS_Param.OCV_arr(OCV_idx);
            lambda_idx=find(obj.x_soc<=obj.vec_soc,1);
            obj.vec_power = obj.vec_current.*(OCV-obj.ESS_Param.R_Bat*obj.vec_current);
            obj.vec_costs = obj.vec_current*OCV*obj.lambda(lambda_idx);
            %TODO: add deg costs
            marginal_costs = (obj.vec_costs(2:end)-obj.vec_costs(1:end-1))./(obj.vec_power(2:end)-obj.vec_power(1:end-1));%[Euro/s]
            obj.vec_marginal_costs = [marginal_costs marginal_costs(end)];
        end

        function build_optimizer(obj)
            C_Bat=obj.ESS_Param.C_Bat;
            Ri=obj.ESS_Param.R_Bat;
            I_max=obj.ESS_Param.I_Max_Bat;
            SoC_min=0.2;
            SoC_max=0.8;

            res=inf;
            alpha=0.5;
            it=0;

            yalmip('clear')
            varx_soc = sdpvar(1,2);
            varu_I = sdpvar(1,1);
            var_price = sdpvar(1,1);
            var_lambda = sdpvar(1,1);
            var_OCV = sdpvar(1,1);
            var_time = sdpvar(1,1);
            objective = 0;
            constraints = [];

            objective = objective + (var_lambda - var_price)*var_OCV*varu_I + var_price*Ri*varu_I^2;%objective function
            constraints = [constraints, varx_soc(2)==varx_soc(1)-varu_I*var_time/(C_Bat*3600)];%state transition
            constraints = [constraints, varu_I<=I_max, varu_I>=(-I_max), varx_soc(2)<=SoC_max, varx_soc(2)>=SoC_min];%inequalities
            
            ops = sdpsettings('solver','quadprog');
            obj.opti = optimizer(constraints, objective, ops, [varx_soc(1),var_price,var_lambda,var_OCV,var_time], varu_I); %x(:,1) is the current measured state - acts as a input argument; u is the output argument
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
            OCV_idx=find(obj.x_soc<=obj.ESS_Param.SoC_vec,1);
            OCV=obj.ESS_Param.OCV_arr(OCV_idx);
            lambda_temp=interp1(obj.vec_soc,obj.lambda,obj.x_soc,"linear");

            I_opt=obj.opti([obj.x_soc,price,lambda_temp,OCV,delta_t]);
            obj.bid=max(obj.vec_power(1),min(obj.vec_power(end),I_opt*(OCV-obj.ESS_Param.R_Bat*I_opt)));
            bid=obj.bid;
        end

        function run(obj,delta_t)
            %update clock
            obj.clock=obj.clock+1;
            %store power and old state
            obj.memory.power(obj.clock)=obj.bid;%apply last bid
            obj.memory.soc(obj.clock+1)=obj.x_soc;
            %compute new state value(s)
            I_idx=find(obj.bid<=obj.vec_power,1);
            I_Bat=obj.vec_current(I_idx);
            obj.memory.current(obj.clock)=I_Bat;
            C_Bat=obj.ESS_Param.C_Bat;
            %I_Bat=OCV/(2*Ri)-sqrt(-P_bat/Ri+(OCV/(2*Ri))^2);
            obj.x_soc=obj.x_soc-I_Bat*delta_t/(3600*C_Bat);
            %update costs
            obj.create_costs();
            %reset
            obj.bid=0;
        end

%% Plots
        function plot_costs(obj)
            figure
            subplot(2,1,1)
            plot(obj.vec_power*1e-3,obj.vec_costs)
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