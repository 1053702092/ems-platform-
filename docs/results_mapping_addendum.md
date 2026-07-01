# results_mapping 补充（第8周新增）

> 原有映射表见 `docs/results_mapping.docx`
> 此处记录第8周新生成的文件

## Week 8 — 四方法大对比报告（2026-07-01）

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
