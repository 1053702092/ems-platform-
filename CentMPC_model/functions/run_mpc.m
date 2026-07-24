function dPdt_opt = run_mpc(P_load_pred,P_act,SoC)
    global mpc_optimizer
    dPdt_vec=mpc_optimizer([P_act,SoC,P_load_pred]);
    if ~isnan(dPdt_vec(1))
        dPdt_opt=dPdt_vec(1);
    else
        dPdt_opt=0;
    end
end