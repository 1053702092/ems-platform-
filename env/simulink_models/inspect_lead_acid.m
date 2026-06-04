% inspect_lead_acid.m — 看 Lead_Acid_Battery 内部接线
mdl = 'Lead_Acid_Battery';
load_system([mdl '.slx']);

fprintf('===== 顶层模块详细 =====\n');
blks = find_system(mdl, 'SearchDepth', 1);
for i = 2:length(blks)
    bt = get_param(blks{i}, 'BlockType');
    name = get_param(blks{i}, 'Name');
    if strcmp(bt, 'Constant')
        val = get_param(blks{i}, 'Value');
        fprintf('  [Constant] %s = %s\n', strtrim(name), strtrim(val));
    elseif strcmp(bt, 'Gain')
        val = get_param(blks{i}, 'Gain');
        fprintf('  [Gain] %s = %s\n', strtrim(name), strtrim(val));
    elseif strcmp(bt, 'Sum')
        fprintf('  [Sum] %s\n', strtrim(name));
    elseif strcmp(bt, 'Display')
        fprintf('  [Display] %s\n', strtrim(name));
    elseif strcmp(bt, 'Saturate')
        ul = get_param(blks{i}, 'UpperLimit');
        ll = get_param(blks{i}, 'LowerLimit');
        fprintf('  [Saturate] %s [%s, %s]\n', strtrim(name), strtrim(ul), strtrim(ll));
    elseif strcmp(bt, 'Integrator')
        ic = get_param(blks{i}, 'InitialCondition');
        fprintf('  [Integrator] %s IC=%s\n', strtrim(name), strtrim(ic));
    elseif strcmp(bt, 'Product')
        fprintf('  [Product] %s\n', strtrim(name));
    else
        fprintf('  [%s] %s\n', bt, strtrim(name));
    end
end

% 看两个子系统的内部
for sub = {'Battery_Resistance', 'Eu_Caculation'}
    s = sub{1};
    fprintf('\n===== %s 内部 =====\n', s);
    try
        blks2 = find_system([mdl '/' s], 'SearchDepth', 1);
        for j = 2:length(blks2)
            bt2 = get_param(blks2{j}, 'BlockType');
            name2 = get_param(blks2{j}, 'Name');
            if strcmp(bt2, 'Constant')
                fprintf('  [%s] %s = %s\n', bt2, strtrim(name2), strtrim(get_param(blks2{j}, 'Value')));
            else
                fprintf('  [%s] %s\n', bt2, strtrim(name2));
            end
        end
    catch e
        fprintf('  无法打开: %s\n', e.message);
    end
end

close_system(mdl, 0);
