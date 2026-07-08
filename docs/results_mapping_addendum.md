# results_mapping 补充（第7~8周新增）

> 原有映射表见 `docs/results_mapping.docx`
> 此处记录第7~8周新生成的文件

## Week 7 — MPC 原理与实现

| 结果文件 | 生成脚本 | 备注 |
|---------|---------|------|
| `results/mpc_ems_wltc_np50.csv` | `scripts/mpc_ems.py` | WLTC MPC 旧版时序数据 |
| `results/mpc_ems_nedc_np50.csv` | `scripts/mpc_ems.py` | NEDC MPC 旧版时序数据 |
| `results/mpc_ems_optimized_wltc_np50.csv` + summary | `scripts/mpc_ems_optimized.py` | WLTC MPC 优化版 |
| `results/mpc_ems_optimized_nedc_np50.csv` + summary | `scripts/mpc_ems_optimized.py` | NEDC MPC 优化版 |
| `results/MPC_np_sensitivity_wltc.csv` | `scripts/mpc_ems.py` | N_p 敏感性扫描（10→200） |
| `results/MPC_np_sensitivity_wltc.png` | `scripts/mpc_ems.py` | N_p 敏感性曲线图 |
| `results/FourWay_compare_optimized_wltc.png` | `scripts/mpc_ems_optimized.py` | WLTC 四方法对比图 |
| `results/FourWay_compare_optimized_nedc.png` | `scripts/mpc_ems_optimized.py` | NEDC 四方法对比图 |
| `docs/MPC_精细化原理解析.docx` | 手动编写 | MPC 完整推导（从 HJB 到 DP/ECMS/MPC 统一框架） |
| `docs/MPC_原理与实现_第7周学习笔记.docx` | 手动编写 | MPC 基础原理笔记 |
| `docs/MPC_第7周学习报告.docx` | 手动编写 | MPC 实验结果报告 |

### 🔑 Week 7 关键数据

| 项目 | 值 |
|------|-----|
| N_p 敏感性 | N_p=10→50 快速改善，N_p≥50 进入饱和区 |
| MPC 旧版 WLTC | H2_raw=0.2011 kg, SOC_end=0.55（电池透支） |
| MPC 优化版 WLTC | H2_raw=0.2432 kg, SOC_end=0.576, H2_eq=0.2976 kg |
| MPC 优化版 NEDC | H2_raw=0.0812 kg, SOC_end=0.574, H2_eq=0.1403 kg |

## Week 8 — 四方法大对比报告 + MPC+EKF（2026-07-01）

_以下内容由 `scripts/gen_week8_report.py` 汇总生成_

| 结果文件 | 生成脚本 | 生成函数/方法 | 关键行号 | 备注 |
|---------|---------|-------------|---------|------|
| `FourWay_compare_optimized_cltc.png` | `scripts/mpc_ems_optimized.py` | `plot_four_way()` | ~L425 | CLTC 优化版四方法对比图 |
| `mpc_ems_optimized_cltc_np50.csv` | `scripts/mpc_ems_optimized.py` | `mpc_sim()` / `main()` | ~L689 | CLTC MPC 优化版时序数据 |
| `mpc_ems_optimized_cltc_np50_summary.csv` | `scripts/mpc_ems_optimized.py` | `main()` | ~L702 | CLTC summary（H2_raw / SOC_end / H2_eq） |
| `week8_fourway_metrics_complete.csv` | `scripts/gen_week8_report.py` | `load_results()` | ~L33 | WLTC+NEDC+CLTC 三工况12组统一指标 |
| `docs/Week8_四方法大对比报告.docx` | `scripts/gen_week8_report.py` | `generate_report()` | ~L220 | 完整对比报告（1.1MB, 含三工况对比图） |

## 新增脚本

| 脚本 | 说明 |
|------|------|
| `scripts/gen_week8_report.py` | Week 8 四方法大对比报告生成器 |
