function [pred_LUT,pred_LUT_time] = create_prediction_LUT(start_time,duration)
    manual_timeshift=25; %[s] shift time stamp of predictions; necessary due to mismatch between data and prediction timeseries (25s observed)
    filename =  "pred_lut_"+string(datetime(year(start_time),month(start_time),day(start_time),'Format','uuuu-MM-dd'))+".mat";
    load(filename)
    dataread.Seconds=seconds(dataread.Var1-start_time)-manual_timeshift;
    pred_LUT=dataread{find(dataread.Seconds==0):find(dataread.Seconds>duration,1),2:end-1}*10/1.35962*1e3;%all power values during missions time in W
    pred_LUT_time=dataread{find(dataread.Seconds==0):find(dataread.Seconds>duration,1),end};
end