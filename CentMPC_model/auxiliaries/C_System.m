classdef C_System < handle
    %C_SYSTEM Summary of this class goes here
    %   Detailed explanation goes here

    properties (Access = private)
        Manager
        Modules
        Load
        Time_Delta
        memory
        Est_Price
        clock
    end
    
    methods
        %% Constructor
        function obj = C_System(delta_t)
            obj.Manager=C_Manager();
            obj.Load=[];
            obj.Modules={};
            obj.Time_Delta=delta_t;
            obj.Est_Price=[];
            obj.memory=[];
            obj.clock=0;
        end

        %% System Building
        function add_load(obj)
            obj.Load=C_Load(obj.Time_Delta);
        end

        function plot_load(obj)
            obj.Load.plot_power();
        end
        
        function add_module(obj,module)
            obj.Modules(length(obj.Modules)+1)={module};
        end

        %% Simulation
        function bids = get_bids(obj,price)
            bids=zeros(1,length(obj.Modules));
            for i=1:length(bids)
                module=obj.Modules{i};
                bids(i)=module.get_bid(price,obj.Time_Delta);
            end
        end

        function run(obj)
            obj.clock=obj.clock+1;
            for i=1:length(obj.Modules)
                module=obj.Modules{i};
                module.run(obj.Time_Delta);
            end
            obj.Manager.run();
        end

        function memory = read_manager_memory(obj)
            memory = obj.Manager.read_memory();
        end

        function [it,price,convergence]=trade(obj,load)
            it=0;
            bids=[];
            [price,convergence]=obj.Manager.get_price(); %initial price
            while ~convergence && it<100
                bids=obj.get_bids(price);
                [price,convergence]=obj.Manager.get_price(load,bids,it);
                it=it+1;
            end
        end

        function simulate(obj)
            step=1;
            load=obj.Load.get_power(step);
            tic;
            while ~isempty(load)          
                [it,price,convergence]=obj.trade(load);
                obj.run();
                obj.memory.it(obj.clock)=it;
                obj.memory.price(obj.clock)=price;
                obj.memory.convergence(obj.clock)=convergence;
                step=step+1;
                load=obj.Load.get_power(step);
            end
            toc
        end

        %% Init
        function [soc, lambda]=compute_lambda(obj,soc_ref,soc_min,soc_max)
            c_min=Inf;
            c_max=0;
            for i=1:length(obj.Modules)
                module=obj.Modules{i};
                if isa(module,'C_ESS')
                    continue
                end
                [marginal_costs,power]=module.get_marginal_costs();
                c_min=min(c_min,min(marginal_costs));
                c_max=max(c_max,max(marginal_costs));
            end
            lambda_ref=(c_max+c_min)/2;
            A=[soc_min^3   soc_min^2 soc_min 1;...
               soc_max^3   soc_max^2 soc_max 1;...
               soc_ref^3   soc_ref^2 soc_ref 1;...
               3*soc_ref^2 2*soc_ref 1       0];
            v=[c_max;c_min;lambda_ref;0];
            x=A\v;
            soc=0:0.001:1;
            lambda = x(1)*soc.^3 + x(2)*soc.^2 + x(3)*soc + x(4);
        end

        function initialize_costs(obj)
            for i=1:length(obj.Modules)%find all non-ESS
                module=obj.Modules{i};
                if ~isa(module,'C_ESS')
                    module.create_costs();
                    module.build_optimizer();
                end
            end
            [soc, lambda]=obj.compute_lambda(0.5,0.2,0.8);
            for i=1:length(obj.Modules)%find all non-ESS
                module=obj.Modules{i};
                if isa(module,'C_ESS')
                    module.set_lambda(soc,lambda);
                    module.create_costs();
                    module.build_optimizer();
                end
            end
        end

        function memory = read_memory(obj)
            memory = obj.memory;
        end
        
        %% Plot Functions

        function plot_power(obj)
            figure
            [load_steps, load_power]=obj.Load.get_profile();
            plot(load_steps,load_power*1e-3)
            hold on
            for i=1:length(obj.Modules)
                module=obj.Modules{i};
                memory=module.read_memory();
                plot(load_steps,memory.power*1e-3)
            end
            xlabel('Time step')
            ylabel('Power [kW]')
            grid on
        end

        function plot_power_balance(obj)
            figure
            [load_steps, load_power]=obj.Load.get_profile();
            plot(load_steps,load_power*1e-3,'k')
            hold on
            FC_Power=zeros(1,length(load_steps));
            ESS_Power=zeros(1,length(load_steps));
            for i=1:length(obj.Modules)
                module=obj.Modules{i};
                memory=module.read_memory();
                if ~isa(module,'C_ESS')
                    FC_Power=FC_Power+memory.power;
                else
                    ESS_Power=ESS_Power+memory.power;
                end
            end
            plot(load_steps,FC_Power*1e-3,'b')
            plot(load_steps,ESS_Power*1e-3,'r')
            legend('Load','FC','ESS');
            xlabel('Time step')
            ylabel('Power [kW]')
            grid on
        end

        function plot_soc(obj)
            figure
            [load_steps, load_power]=obj.Load.get_profile();
            hold on
            for i=1:length(obj.Modules)
                module=obj.Modules{i};
                if ~isa(module,'C_ESS')
                    continue
                end
                memory=module.read_memory();
                plot([load_steps load_steps(end)+1],100*memory.soc)
            end
            xlabel('Time step')
            ylabel('SoC [%]')
            grid on
        end

        function plot_fuel_consumption(obj)
            figure
            [load_steps, load_power]=obj.Load.get_profile();
            hold on
            for i=1:length(obj.Modules)
                module=obj.Modules{i};
                if isa(module,'C_ESS')
                    continue
                end
                memory=module.read_memory();
                plot(load_steps,memory.h2_consumption)
            end
            xlabel('Time step')
            ylabel('H2 consumption [g]')
            grid on
        end

        function plot_fc_degradation(obj)
            figure
            [load_steps, load_power]=obj.Load.get_profile();
            hold on
            for i=1:length(obj.Modules)
                module=obj.Modules{i};
                if isa(module,'C_ESS')
                    continue
                end
                memory=module.read_memory();
                plot(load_steps,memory.vdeg_static*1e6)
            end
            xlabel('Time step')
            ylabel('FC voltage degradation [\muV]')
            grid on
        end
    end
end