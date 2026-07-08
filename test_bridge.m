cd 'F:/CLAUDE/research/ems-platform';
x = linspace(0, 2*pi, 100);
y = sin(x);
T = table(x', y', 'VariableNames', {'x', 'y'});
writetable(T, 'test_output.csv');
fprintf('OK: %%d points computed\n', length(x));
quit;
