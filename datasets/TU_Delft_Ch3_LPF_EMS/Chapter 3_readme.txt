*** Lifetime design, operation, and cost analysis for the energy system of a retrofitted cargo vessel with fuel cells and batteries ***

Authors: Foivos Mylonopoulos, Sankarshan Durgaprasad, Andrea Coraddu, Henk Polinder
Maritime and Transport Technology, Faculty of Mechanical Engineering, 
Delft University of Technology
Corresponding author: Foivos Mylonopoulos

Contact Information: f.p.mylonopoulos@tudelft.nl

Delft University of Technology - Faculty of Mechanical Engineering
Mekelweg 2 (building 34)
2628 CD Delft
the Netherlands

*** Introduction ***
This dataset contains the results and inputs files collected as part of the Chapter 3 in the doctoral thesis of Mr. Foivos Mylonopoulos, Dipl.-Ing in Delft University of Technology, 2022-2026.
The present dataset is made public to act both as supplementary data for the publications of F. Mylonopoulos and to offer other researchers the ability to use this data in their own work.
This data is part of the SH2IPDRIVE project (Sustainable Hydrogen Integrated Propulsion Drives).
The project is funded by the Netherlands Enterprise Agency (RVO: Rijksdienst voor Ondernemend Nederland) under the grant number MOB21013.

*** Purpose of the dataset ***
This dataset was created to support the analysis of the design and lifetime cost implications of retrofitting a diesel-fuelled cargo ship to a hydrogen fuel cell-battery-electric configuration, as presented in Chapter 3 of the PhD dissertation. It provides data and scripts required to reproduce the energy management results, component degradation assessment, and lifetime cost comparisons between the diesel and hydrogen-based systems.


*** Description of the dataset ***
This dataset contains two ZIP archives. The first archive includes the MATLAB/Simulink models used in Chapter 3 to evaluate a low-pass filter energy management strategy (LPF EMS) for a fuel cell-battery-electric powertrain. The MATLAB script LPF_EMS.m prepares the input parameters that are used by the Simulink models (.slx). The Simulink simulations then run the EMS on the different vessel power-demand profiles and generate the power distribution results.  The 2nd archive contains the outputs and plotting material: Results_ch3.xlsx file summarizes the main results, and PLOTS.m reproduces the figures (of the published paper) using the accompanying Excel files. 



*** Dependencies *** 
MATLAB R2022b with Simulink for the models and simulations. 
Microsoft Excel for viewing .xlsx files


