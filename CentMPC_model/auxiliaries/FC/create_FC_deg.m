function vec_FC_deg_volt = create_FC_deg(dV_low,dV_mid,dV_high,thresh_low,thresh_high,vec_FC_deg_power,mode)
%modes:step,logistic,linear,linear_fade,quad_superpos
vec_FC_deg_volt=zeros(1,length(vec_FC_deg_power));
switch mode
    case 'step'
        for i=1:length(vec_FC_deg_power)
            if vec_FC_deg_power(i)<=thresh_low
                vec_FC_deg_volt(i)=dV_low;
            elseif vec_FC_deg_power(i)>=thresh_high
                vec_FC_deg_volt(i)=dV_high;
            else
                vec_FC_deg_volt(i)=dV_mid;
            end
        end
    case 'logistic'
        vec_FC_deg_volt=dV_mid... %base degradation
            +(dV_high-dV_mid)*1./(1+exp(5/(1-thresh_high)*(thresh_high-vec_FC_deg_power)))... %fade in high band deg
            +(dV_low-dV_mid)*1./(1+exp(5/thresh_low*(vec_FC_deg_power-thresh_low))); %fade out low band deg
    case 'linear'
        vec_FC_deg_volt=max(dV_mid,max(dV_low+(dV_mid-dV_low)/thresh_low*vec_FC_deg_power,dV_mid+(vec_FC_deg_power-thresh_high)*(dV_high-dV_mid)/(1-thresh_high)));
    case 'linear_fade'
        fade_width=0.05;
        for i=1:length(vec_FC_deg_power)
            if vec_FC_deg_power(i)<=thresh_low-fade_width
                vec_FC_deg_volt(i)=dV_low;
            elseif vec_FC_deg_power(i)<=thresh_low+fade_width
                vec_FC_deg_volt(i)=dV_low+(vec_FC_deg_power(i)-thresh_low+fade_width)/(2*fade_width)*(dV_mid-dV_low);
            elseif vec_FC_deg_power(i)>=thresh_high+fade_width
                vec_FC_deg_volt(i)=dV_high;
            elseif vec_FC_deg_power(i)>=thresh_high-fade_width
                vec_FC_deg_volt(i)=dV_mid+(vec_FC_deg_power(i)-thresh_high+fade_width)/(2*fade_width)*(dV_high-dV_mid);
            else
                vec_FC_deg_volt(i)=dV_mid;
            end
        end
    case 'quad_superpos'
        vec_FC_deg_volt=dV_mid+(dV_high-dV_mid)*vec_FC_deg_power.^4+(dV_low-dV_mid)*(1-vec_FC_deg_power).^4;
    case 'square_superpos'
        vec_FC_deg_volt=dV_mid+(dV_high-dV_mid)*vec_FC_deg_power.^2+(dV_low-dV_mid)*(1-vec_FC_deg_power).^2;
    otherwise
        disp('Invalid Mode')
        vec_FC_deg_volt=inf;
end

