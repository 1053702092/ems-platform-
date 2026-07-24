%% Owner
% Implemented from source material by Timon Kopka 23/10
% Default values taken from simulink model (derived from paper)
% Parameter-Sets


%% Sources
% Tremblay et al. 2007: A Generic Battery Model for the Dynamic Simulation
% of Hybrid Electric Vehicles (Battery Model)
% Omar et al. 2014: Lithium iron phosphate based battery — Assessment of
% the aging parameters and development of cycle life model (Aging)

%% Output Bus
bus_elems(1)=Simulink.BusElement;
bus_elems(1).Name='V_Bat'; %Stack output voltage [V]
bus_elems(1).DataType='double';
bus_elems(2)=Simulink.BusElement;
bus_elems(2).Name='I_Bat'; %Stack output current [V]
bus_elems(2).DataType='double';
bus_elems(3)=Simulink.BusElement;
bus_elems(3).Name='SoC'; %State-of-charge [-]
bus_elems(3).DataType='double';
bus_elems(4)=Simulink.BusElement;
bus_elems(4).Name='C_max'; %Maximum capacity [Ah]
bus_elems(4).DataType='double';
bus_elems(5)=Simulink.BusElement;
bus_elems(5).Name='Age'; %Age in equivalent full cycles [-]
bus_elems(5).DataType='double';
bus_elems(6)=Simulink.BusElement;
bus_elems(6).Name='SoH'; %State of Health[-]
bus_elems(6).DataType='double';
bus_elems(7)=Simulink.BusElement;
bus_elems(7).Name='Ri_nom'; %Nominal internal resistance[-]
bus_elems(7).DataType='double';
Bus_Bat=Simulink.Bus;
Bus_Bat.Elements=bus_elems;
clear bus_elems