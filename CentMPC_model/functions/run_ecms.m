function dPdt_opt = run_ecms(P_load,P_FC_act,SoC)
    global ecms_optimizer
    dPdt=ecms_optimizer([P_FC_act,SoC,P_load]);
    if ~isnan(dPdt)
        dPdt_opt=dPdt;
    else
        dPdt_opt=0;
    end
end