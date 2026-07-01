# results/ 文件映射表

> 每次在 `scripts/` 或 `experiments/` 中生成新的 `*.png` / `*.csv` 文件时，
> 必须在此文件中新增一行记录，写明 **文件名 → 生成脚本 → 生成函数/行号**。
> 这样回溯结果时可以直接定位代码。

---

## 格式说明

```
| 结果文件 | 生成脚本 | 生成函数/方法 | 关键行号 | 备注 |
```

---

## DP 动态规划

| 结果文件 | 生成脚本 | 生成函数/方法 | 关键行号 | 备注 |
|---------|---------|-------------|---------|------|
| `DP_vs_Rule_{wltc,nedc,cltc}.png` | `scripts/day8_dp_ems.py` | `print_dp_vs_rule_comparison()` | ~L407 | Rule/DP 五合一对比图 |
| `dp_ems_{wltc,nedc,cltc}.csv` | `scripts/day8_dp_ems.py` | `dp_ems_main()` | ~L504 | DP 时序数据 |
| `dp_ems_{wltc,nedc,cltc}.csv` | `scripts/day9_ecms_ems.py` | `load_dp_results()` | ~L292 | DP 结果加载（复写） |
| `DP_sensitivity_analysis.png` | `experiments/week4_sensitivity_analysis.py` | `main()` | ~L222 | Alpha/Beta/网格密度敏感性全景图 |
| `sensitivity_alpha.csv` | `experiments/week4_sensitivity_analysis.py` | `main()` | ~L231 | Alpha 敏感性原始数据 |
| `sensitivity_beta.csv` | `experiments/week4_sensitivity_analysis.py` | `main()` | ~L232 | Beta 敏感性原始数据 |
| `sensitivity_grid.csv` | `experiments/week4_sensitivity_analysis.py` | `main()` | ~L233 | 网格密度敏感性原始数据 |

## ECMS 标准 + 自适应

| 结果文件 | 生成脚本 | 生成函数/方法 | 关键行号 | 备注 |
|---------|---------|-------------|---------|------|
| `ECMS_compare_{wltc,nedc,cltc}.png` | `scripts/day9_ecms_ems.py` | `plot_ecms_comparison()` | ~L434 | Rule/DP/ECMS/A-ECMS 四方法对比 |
| `ecms_s_scan_{wltc}.png` | `scripts/day9_ecms_ems.py` | `plot_s_scan()` | ~L476 | 等效因子 s 扫描结果 |
| `ecms_scan_{cycle}.csv` | `scripts/day9_ecms_ems.py` | `scan_s_factor()` | ~L251 | s 扫描原始数据 |
| `ecms_ems_{wltc,nedc,cltc}.csv` | `scripts/run_multicycle.py` | `run_single_cycle()` | ~L65 | ECMS 时序数据 |
| `aecms_ems_{wltc,nedc,cltc}.csv` | `scripts/run_multicycle.py` | `run_single_cycle()` | ~L65 | A-ECMS 时序数据 |
| `ecms_multicycle_summary.csv` | `scripts/run_multicycle.py` | `create_summary_table()` | ~L100 | 三工况汇总对比表 |
| `aecms_tune_wltc.csv` | `scripts/tune_aecms.py` | `main()` | ~L53 | A-ECMS 参数调优 104 组合结果 |

## MPC 网格搜索

| 结果文件 | 生成脚本 | 生成函数/方法 | 关键行号 | 备注 |
|---------|---------|-------------|---------|------|
| `FourWay_compare_{wltc,nedc}.png` | `scripts/mpc_ems.py` | `plot_four_way_compare()` | ~L325 | 旧版四方法对比 |
| `MPC_np_sensitivity_{wltc}.png` | `scripts/mpc_ems.py` | `run_np_sensitivity()` | ~L409 | N_p 敏感性曲线 |
| `MPC_vs_DP_Rule_{wltc,nedc}_np{n_p}.png` | `scripts/mpc_ems.py` | `run_mpc_with_np()` | ~L539 | 单 N_p 对比图 |
| `mpc_ems_{wltc,nedc}_np{n_p}.csv` | `scripts/mpc_ems.py` | `run_mpc_with_np()` | ~L554 | MPC 时序数据 |
| `MPC_np_sensitivity_{wltc}.csv` | `scripts/mpc_ems.py` | `run_np_sensitivity()` | ~L562 | N_p 敏感性原始数据 |

## MPC 优化版

| 结果文件 | 生成脚本 | 生成函数/方法 | 关键行号 | 备注 |
|---------|---------|-------------|---------|------|
| `FourWay_compare_optimized_{wltc,nedc}.png` | `scripts/mpc_ems_optimized.py` | `plot_four_way_compare()` | ~L425 | 优化版四方法对比图 |
| `FourWay_compare_optimized_metrics.csv` | `scripts/mpc_ems_optimized.py` | `main()` | — | 统一指标对比表 |
| `mpc_ems_optimized_{wltc,nedc}_np50.csv` | `scripts/mpc_ems_optimized.py` | `run_mpc_with_np()` | ~L689 | 优化版时序数据 |
| `mpc_ems_optimized_{wltc,nedc}_np50_summary.csv` | `scripts/mpc_ems_optimized.py` | `run_mpc_with_np()` | ~L702 | 优化版 summary（H2_raw / SOC_end / H2_eq） |

## DP 反推标定

| 结果文件 | 生成脚本 | 生成函数/方法 | 关键行号 | 备注 |
|---------|---------|-------------|---------|------|
| `dp_calibrate_s_{wltc,nedc,cltc}.png` | `scripts/calibrate_s_from_dp.py` | `main()` | ~L185 | costate → s 换算 4 子图 |
| `dp_calibrate_s_{wltc,nedc,cltc}.csv` | `scripts/calibrate_s_from_dp.py` | `main()` | ~L199 | 含 speed / P_load / SOC / lambda / s_factor |

## 早期实验文件

| 结果文件 | 生成脚本 | 生成函数/方法 | 关键行号 | 备注 |
|---------|---------|-------------|---------|------|
| `Day6_cell_model_iv_curve.png` | ~~`experiments/day3_call_matlab.py`~~ | — | ~L13 | I-V 曲线（脚本已修改，文件名后续可能变动） |
| `day3_cell_model_iv_curve.png` | `experiments/day3_call_matlab.py` | `main()` | ~L42 | MATLAB 版 I-V 曲线 |
| `day3_cell_model_iv_curve_py.png` | `experiments/plot_iv_curve.py` | `main()` | ~L49 | Python 版 I-V 曲线 |
| `Day7_ems_sim_wltc.png/.csv` | `experiments/run_ems_simulation.py` | `run_ems_simulation()` | ~L318 / ~L242 | EMS 仿真结果（Day7 版） |
| `Day7_ems_sim_wltc.png/.csv` | `scripts/day8_dp_ems.py` | — | ~L447 | 也被此脚本生成（路径复用） |
| `Day7_ems_sim_wltc.png/.csv` | `scripts/day9_ecms_ems.py` | — | ~L307 | 也被此脚本生成（路径复用） |
| `day1_wltc_sample_plot.png` | `experiments/day1_pandas_intro.py` | `main()` | ~L66 | WLTC 采样图 |
| `day1_wltc_dual_axis.png` | `experiments/day1_pandas_intro.py` | `main()` | ~L84 | WLTC 双轴图 |
| `wltc_sample_plot.png` | `experiments/day1_pandas_intro.py` | `main()` | ~L66 | 无 Day1 前缀版本 |
| `wltc_dual_axis.png` | `experiments/day1_pandas_intro.py` | `main()` | ~L84 | 无 Day1 前缀版本 |
| `wltc_sample.csv` | `experiments/day1_pandas_intro.py` | `main()` | ~L42 | WLTC 采样数据 |

## 工况数据

| 结果文件 | 生成脚本 | 生成函数/方法 | 关键行号 | 备注 |
|---------|---------|-------------|---------|------|
| `wltc_cycle.csv` | `scripts/download_drive_cycles.py` | — | — | WLTC 工况数据（CSV 格式） |
| `nedc_cycle.csv` | `scripts/download_drive_cycles.py` | — | — | NEDC 工况数据 |
| `cltc_cycle.csv` | `scripts/download_drive_cycles.py` | — | — | CLTC 工况数据 |
| `wltc_cycle.png` | ~~早期脚本~~ | — | — | ~~已移除~~，现在用 `data/cycles/WLTC.csv` 原始数据 |
| `nedc_cycle.png` | ~~早期脚本~~ | — | — | ~~已移除~~，现在用 `data/cycles/NEDC.csv` 原始数据 |

## 已移除/重命名脚本产生的文件

| 结果文件 | 原始生成脚本 | 现用等价文件 | 备注 |
|---------|------------|------------|------|
| `Day9_ECMS_compare_wltc.png` | ~~Week 5 早期脚本~~ | `ECMS_compare_wltc.png` | `day9_ecms_ems.py` 重构后命名改变 |
| `Day9_ecms_scan_wltc.png` | ~~Week 5 早期脚本~~ | `ecms_s_scan_wltc.png` | `day9_ecms_ems.py` 重构后命名改变 |

---

## 新增记录模板

```markdown
| {新文件名} | {生成脚本} | {生成函数} | ~L{行号} | {备注说明} |
```

**示例：**
```markdown
| `week8_fourway_report_wltc.png` | `scripts/gen_week8_report.py` | `generate_report()` | ~L150 | Week 8 四方法最终报告图 |
| `week8_metrics_summary.csv` | `scripts/gen_week8_report.py` | `compute_metrics()` | ~L80 | 统一指标汇总表 |
```
