function [bid_M, bid_p] = get_ICE_bid(p_eq,ICE_param)
    P_rel=-ICE_param.l/(2*ICE_param.q)+real(sqrt((p_eq-ICE_param.c)/ICE_param.q+((ICE_param.l/(2*ICE_param.q))^2)));
    bid_M=ICE_param.P_max*P_rel;
    bid_p=ICE_param.q*P_rel^2+ICE_param.l*P_rel+ICE_param.c;
end