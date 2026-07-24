init_environment;

%% Settings
delta_t=15;

%% System Definition
FC_A  = C_FC(325e3,400);
FC_B  = C_FC(300e3,400);
FC_C  = C_FC(175e3,400);
FC_D  = C_FC(200e3,400);
Bat_A = C_ESS(0.7,200e3,350);
Bat_B = C_ESS(0.4,250e3,400);

Sys = C_System(delta_t);

Sys.add_module(FC_A);
Sys.add_module(FC_B);
Sys.add_module(FC_C);
Sys.add_module(FC_D);
Sys.add_module(Bat_A);
Sys.add_module(Bat_B);
Sys.add_load(); %time steps hard-coded
Sys.initialize_costs();
%
% price=0:1e-9:2e-7;
% for i=1:length(price)
%     bid_fc_a(i)=FC_A.get_bid(price(i),delta_t);
%     bid_fc_b(i)=FC_B.get_bid(price(i),delta_t);
%     bid_fc_c(i)=FC_C.get_bid(price(i),delta_t);
%     bid_fc_d(i)=FC_D.get_bid(price(i),delta_t);
%     bid_bat_a(i)=Bat_A.get_bid(price(i),delta_t);
%     bid_bat_b(i)=Bat_B.get_bid(price(i),delta_t);
% end

%% Simulation
Sys.simulate();

%% Data Processing
Sys.plot_power();
Sys.plot_soc();
Sys.plot_fuel_consumption();
Sys.plot_fc_degradation();