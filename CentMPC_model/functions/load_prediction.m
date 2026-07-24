function P_load_pred = load_prediction(P_load_act,t_act,Ts_mpc,N_pred,time_vec,power_vec)
    P_load_pred=zeros(1,N_pred+1);
    for idx_start=1:length(time_vec) %for-loop as alternative to find() to avoid variable size signal
        if(time_vec(idx_start)>=t_act)
            break
        end
    end
    for k=1:N_pred+1
        for idx_end=idx_start:length(time_vec) %for-loop as alternative to find() to avoid variable size signal
            if(time_vec(idx_end)>=t_act+k*Ts_mpc)
                break
            end
        end
        P_load_pred(k)=mean(power_vec(idx_start:idx_end));
        idx_start=idx_end;
    end
end