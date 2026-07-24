%% Test MATLAB-Python bridge
x = linspace(0, 2*pi, 100);
y = sin(x);
save(test_output.mat, x, y);
fprintf(Test complete: sin(x) computed with %d points
, length(x));
quit;
