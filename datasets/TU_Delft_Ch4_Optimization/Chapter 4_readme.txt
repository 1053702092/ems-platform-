*** A holistic framework for optimal ship energy system design, including operational requirements, lifetime cost, and vessel stability ***

Authors: Foivos Mylonopoulos, Andrea Coraddu, Henk Polinder
Maritime and Transport Technology, Faculty of Mechanical Engineering, 
Delft University of Technology
Corresponding author: Foivos Mylonopoulos

Contact Information: f.p.mylonopoulos@tudelft.nl

Delft University of Technology - Faculty of Mechanical Engineering
Mekelweg 2 (building 34)
2628 CD Delft
the Netherlands

*** Introduction ***
This dataset contains the results and inputs files collected as part of the Chapter 4 in the doctoral thesis of Mr. Foivos Mylonopoulos, Dipl.-Ing in Delft University of Technology, 2022-2026.
The present dataset is made public to act both as supplementary data for the publications of F. Mylonopoulos and to offer other researchers the ability to use this data in their own work.
This data is part of the SH2IPDRIVE project (Sustainable Hydrogen Integrated Propulsion Drives).
The project is funded by the Netherlands Enterprise Agency (RVO: Rijksdienst voor Ondernemend Nederland) under the grant number MOB21013.

*** Purpose of the dataset ***
This dataset was created to support the development and evaluation of representative operating profile synthesis methods and the combined design-operation optimization framework presented in Chapter 4 of the PhD dissertation. It enables reproduction of power profile reduction techniques, system sizing and operation optimization, and lifetime cost minimization results, including the effects of ship stability and component placements constraints on the optimal hydrogen-based system design.  



*** Description of the dataset ***
This dataset contains two ZIP archives. The first one, includes MATLAB scripts implementing the algorithmic (RDP-based) and probability-based downsampling approaches for representative operating profile synthesis, together with the associated Excel inputs files. The second archive contains the lifetime cost and stability optimization code (Cost_Stability_Code.py) which uses as input the representative power profile (Power_Profile.xlsx) and the available engine-room component placement positions (positions.xlsx). 




*** Dependencies *** 
MATLAB was used to run the representative operating profile synthesis scripts. Python was used to run the optimization code, which uses the SCIP solver via PySCIPOpt.

Microsoft Excel was used to view and edit the .xlsx input files.

