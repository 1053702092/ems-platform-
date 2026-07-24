classdef C_Load < handle
    %C_LOAD Summary of this class goes here
    %   Detailed explanation goes here
    
    properties
        Steps
        Power
    end
    
    methods
        function obj = C_Load(delta_t)
            [obj.Steps,obj.Power]=create_load_profile(delta_t);
        end
       
        function [steps,power] = get_profile(obj)
            steps=obj.Steps;
            power=obj.Power;
        end

        function power = get_power(obj,step,horizon)
        arguments
            obj
            step
            horizon=0
        end
            if step > length(obj.Power)
                power = [];
            else
                power=zeros(1,horizon+1);
                for i=0:horizon
                    if step+i<=length(obj.Power)
                        power(i+1) = obj.Power(step+i);
                    else
                        power(i+1)=0;
                    end
                end
            end
        end

        function plot_power(obj)
            plot(obj.Steps,obj.Power*1e-3)
            xlabel('Time Step [-]')
            ylabel('Power [kW]')
            grid on
        end
    end
end

