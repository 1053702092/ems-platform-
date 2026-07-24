clear; close all;
%% Font settings
font_selection='Times New Roman';
set(0, 'defaultTextFontName', font_selection);
set(0, 'DefaultAxesFontName', font_selection);
set(0, 'defaultUicontrolFontName', font_selection);
set(0, 'defaultUitableFontName', font_selection);
set(0, 'defaultUipanelFontName', font_selection);
%% Builds Paths
DATA_PATH='C:\Users\tkopka\OneDriveTUDelft\Delft\Research\Data'; %define path to data storage location
REPO_PATH='C:\Repos'; %path to repositories
addpath(genpath(pwd))
addpath(genpath([DATA_PATH '\02-Processed_Data']));
addpath(genpath([REPO_PATH '\components-library'])); %add component library and all subfolders