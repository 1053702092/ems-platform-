# -*- coding: utf-8 -*-
import subprocess, time, os

proj_dir = 'F:/CLAUDE/research/ems-platform'

# Create MATLAB test script
with open(proj_dir + '/test_bridge.m', 'w') as f:
    f.write("cd '" + proj_dir.replace('\\', '/') + "';\n")
    f.write("x = linspace(0, 2*pi, 100);\n")
    f.write("y = sin(x);\n")
    f.write("T = table(x', y', 'VariableNames', {'x', 'y'});\n")
    f.write("writetable(T, 'test_output.csv');\n")
    f.write("fprintf('OK: %%d points computed\\n', length(x));\n")
    f.write("quit;\n")

# Call MATLAB
print('Starting MATLAB (first launch is slow)...')
t0 = time.time()

mfile = proj_dir.replace('\\', '/') + '/test_bridge.m'
proc = subprocess.Popen(
    ['F:/Matlab/bin/matlab.exe', '-batch', "run('" + mfile + "')"],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE
)

try:
    stdout, stderr = proc.communicate(timeout=120)
    out = stdout.decode('cp936', errors='replace')
    err = stderr.decode('cp936', errors='replace')

    t = time.time() - t0
    print(f'MATLAB completed in {t:.1f}s')

    # Show relevant output
    for line in out.split('\n'):
        if 'OK:' in line:
            print(' >', line.strip())

    # Check result
    csv_path = proj_dir + '/test_output.csv'
    if os.path.exists(csv_path):
        import pandas as pd
        df = pd.read_csv(csv_path)
        print(f'\nData loaded: {len(df)} rows, columns: {list(df.columns)}')
        print(f'x range: {df.x.min():.2f} to {df.x.max():.2f}')
        print(f'y range: {df.y.min():.2f} to {df.y.max():.2f}')
        print('\n=== MATLAB <=> Python bridge: WORKING! ===')
        print('Workflow: Python -> matlab -batch -> CSV -> pandas')
    else:
        print('ERROR: CSV not generated')
        if err.strip():
            print('MATLAB errors:', err[:500])

except subprocess.TimeoutExpired:
    proc.kill()
    print('ERROR: MATLAB timeout (120s)')
except Exception as e:
    print(f'ERROR: {e}')
