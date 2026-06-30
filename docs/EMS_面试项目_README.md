# 燃料电池混合动力系统 EMS 能量管理策略对比与优化平台

## 项目定位

本项目面向 EMS/BMS 算法岗、新能源汽车能量管理岗、燃料电池系统仿真岗和新能源央企技术岗面试展示。

一句话介绍：

> 搭建燃料电池-电池混合动力系统 EMS 仿真平台，统一比较规则控制、DP、ECMS、MPC 和优化版 MPC，并针对 MPC 原始氢耗虚低问题，引入 SOC 公平修正和工程约束。

## 项目亮点

1. 不是只跑单一算法，而是建立了 Rule、DP、ECMS、MPC 的统一对比框架。
2. 不是只看原始氢耗，而是同时分析 `H2_raw`、`SOC_end`、`H2_eq`、燃料电池效率和功率峰值。
3. 发现旧版 MPC 原始氢耗低于 DP 的异常现象，并从终端 SOC 透支角度解释，而不是直接宣称 MPC 优于 DP。
4. 新建 `scripts/mpc_ems_optimized.py`，加入 SOC 软下限、真实终点 SOC 欠差惩罚和 FC 功率变化惩罚。
5. 保留旧版 `scripts/mpc_ems.py`，优化版单独输出 `results/mpc_ems_optimized_*`，便于对比复盘。

## 技术栈

- Python、NumPy、Pandas、Matplotlib
- 动态规划 DP
- 等效消耗最小化策略 ECMS
- 模型预测控制 MPC
- 燃料电池效率曲线插值
- 电池 SOC 状态转移模型
- WLTC / NEDC 工况仿真

## 核心文件

| 文件 | 作用 |
|---|---|
| `scripts/day8_dp_ems.py` | DP 基准、车辆功率模型、电池 SOC 状态转移、规则控制器 |
| `scripts/day9_ecms_ems.py` | ECMS / A-ECMS 策略 |
| `scripts/mpc_ems.py` | 旧版 MPC，保留用于对照 |
| `scripts/mpc_ems_optimized.py` | 优化版 MPC，加入 SOC 与 FC 工程约束 |
| `results/FourWay_compare_optimized_metrics.csv` | 四方法结果汇总 |
| `results/FourWay_compare_optimized_wltc.png` | WLTC 四方法对比图 |
| `results/FourWay_compare_optimized_nedc.png` | NEDC 四方法对比图 |

## 优化版 MPC 设计

旧版 MPC 的问题：

- 只看原始氢耗时，MPC 会倾向于多用电池、少用燃料电池。
- WLTC 旧版 MPC 原始氢耗低于 DP，但终端 SOC 更低，说明部分收益来自电池能量透支。
- 这个结果不能直接解释为“MPC 优于 DP”。

优化版处理：

- 加入 `SOC_SOFT_MIN = 0.57`，低 SOC 区域快速加罚。
- 加入真实工况终点 SOC 欠差惩罚，避免终点透支。
- 加入 `W_PFC_SLEW`，抑制燃料电池功率跳变。
- 输出 `H2_raw`、`SOC_end`、`H2_eq` 三类指标。

## 当前结果

| 工况 | 方法 | H2_raw (kg) | SOC_end | H2_eq (kg) | 相对 DP 原始氢耗 | 相对 DP SOC修正氢耗 |
|---|---|---:|---:|---:|---:|---:|
| WLTC | Rule | 0.2873 | 0.611 | 0.2618 | +20.3% | -13.7% |
| WLTC | DP | 0.2388 | 0.572 | 0.3035 | 0.0% | 0.0% |
| WLTC | ECMS | 0.2616 | 0.594 | 0.2745 | +9.5% | -9.6% |
| WLTC | MPC_optimized | 0.2432 | 0.576 | 0.2976 | +1.8% | -1.9% |
| NEDC | Rule | 0.1447 | 0.613 | 0.1142 | +53.2% | -31.4% |
| NEDC | DP | 0.0944 | 0.568 | 0.1664 | 0.0% | 0.0% |
| NEDC | ECMS | 0.0984 | 0.585 | 0.1334 | +4.2% | -19.8% |
| NEDC | MPC_optimized | 0.0812 | 0.574 | 0.1403 | -14.0% | -15.7% |

注意：`H2_eq` 是当前项目定义的 SOC 修正评价指标，用于避免“用电池能量换低氢耗”的误判。面试表达中不直接说 MPC 超过 DP，而应说“在当前修正口径下接近 DP，需要进一步统一终端 SOC 约束复核”。

## 运行方式

```bash
python scripts/mpc_ems_optimized.py --cycle wltc --np 50 --compare
python scripts/mpc_ems_optimized.py --cycle nedc --np 50 --compare
```

## 面试表达

30 秒版本：

> 我做了一个燃料电池混合动力系统 EMS 能量管理项目，搭建了规则控制、DP、ECMS、MPC 的统一仿真平台。项目里我不只比较原始氢耗，还加入终端 SOC 和 SOC 修正氢耗，发现旧版 MPC 看似低于 DP 是因为透支了电池能量，因此进一步设计了优化版 MPC，加入 SOC 软约束和燃料电池功率变化惩罚。

2 分钟版本：

> 这个项目的目标是做燃料电池-电池混合动力系统的能量管理。输入是 WLTC/NEDC 工况，根据车辆动力学计算功率需求，再由控制策略决定燃料电池功率和电池功率分配。我实现了规则控制作为 baseline，用 DP 做离线最优基准，用 ECMS 做实时策略，再实现 MPC 做滚动优化。项目中一个关键发现是，旧版 MPC 原始氢耗低于 DP，但终端 SOC 明显更低，这说明它并不是真的更优，而是多消耗了电池能量。为了解决这个问题，我引入了 SOC 修正氢耗 `H2_eq`，并新建优化版 MPC，加入 SOC 软下限、终点 SOC 欠差惩罚和燃料电池功率变化惩罚。最终项目形成了算法实现、异常分析、工程修正和可视化报告的完整闭环。

## 后续优化

1. 增加 CLTC 工况统一对比。
2. 对 `SOC_SOFT_MIN`、`BETA_TERM`、`W_PFC_SLEW` 做参数敏感性扫描。
3. 增加预测误差场景，验证 MPC 鲁棒性。
4. 将核心控制器迁移到 C++ 或 Simulink，强化工程化表达。
5. 接入 PPO 强化学习，形成 DP / ECMS / MPC / RL 全景对比。
