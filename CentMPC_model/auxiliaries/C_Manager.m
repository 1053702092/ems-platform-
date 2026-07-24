classdef C_Manager < handle
    
    properties (Access = private)
        price
        converged
        settings
        memory
        clock
        bid_mem
        price_mem
        grad_est
    end

    methods
        function obj = C_Manager()
            obj.price = 1e-7; %initial price/hard-coded to lamda of ESS
            obj.converged = false;
            obj.settings=[];
            obj.memory=[];
            obj.bid_mem=[];
            obj.price_mem=[];
            obj.grad_est=[];
            obj.clock=0;
        end

        function run(obj)
            obj.clock=obj.clock+1;
            obj.memory.price(obj.clock)=obj.price;
            obj.converged=false;
        end

        function memory = read_memory(obj)
            memory = obj.memory;
        end

        function [price,converged] = get_price(obj,load,bids,it)
            arguments
                obj
                load = []
                bids = []
                it = []
            end
            if isempty(bids)
                price=obj.price;
                converged=obj.converged;
                return
            end
            if ~isempty(obj.price_mem)&&~isempty(obj.bid_mem)
                if sum(bids)-obj.bid_mem == 0
                    obj.grad_est=[];
                else
                    obj.grad_est=max(1e-15,min((obj.price-obj.price_mem)/(sum(bids)-obj.bid_mem),1e-9));
                end
            end
            obj.price_mem=obj.price;
            mismatch=load-sum(bids);

            step_size=(5./(it+5));
            conv_limit=1e3+it/100*9e3;
            if abs(mismatch) < conv_limit
                obj.converged=true;
            elseif isempty(obj.grad_est)
                obj.price=obj.price*(1+0.0003*mismatch/100e3); %hard-coded value
                obj.converged=false;
            else
                obj.price=max(0,obj.price+step_size*obj.grad_est*mismatch);
            end
            price=obj.price;
            obj.bid_mem=sum(bids);
            converged=obj.converged;
        end

    end
end

