classdef C_Module < handle

    properties(Abstract,Access = protected)
        bid
        vec_power
        vec_costs
        vec_marginal_costs
        memory
        clock
    end

    methods(Abstract)
        Param = get_param(obj)
        bid = get_bid(obj,price,delta_t)
        create_costs(obj)
        plot_costs(obj)
        run(obj,delta_t)
        memory = read_memory(obj)
        [marginal_costs, power] = get_marginal_costs(obj)
    end
end