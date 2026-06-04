# EMS-PLAN 进度跟踪

> 更新日期：2026-06-04
> 当前阶段：第1个月 第1周（100% ✅）
> 最后会话：Day6 — Cell_model_v10 I-V 扫描仿真跑通
> 
> 备注：2026年秋招（8-10月）期间边学边投，不赶进度，先投再看。

---

## 当前状态

- [x] **第1个月：工程底座 + DP入门**
  - [x] 第1周：Python/Git/环境复盘
    - [x] Day1-3: Python数据处理+Git (已完成)
    - [x] Day4-5: Simulink复盘+接口 (已完成)
    - [x] ✅ VS Code 1.122.1 已安装
    - [x] ✅ MATLAB-Python桥接已测试通过
    - [x] ✅ Energy.slx 模型已分析 → 改用 Cell_model_v10_lit
    - [x] ✅ GitHub 仓库已推送
    - [x] ✅ 双设备同步配置完成 (sync_memory.py + STATUS.md)
    - [x] ✅ .slx 已从 Git 移除
    - [x] ✅ Day6: run_simulation.py 跑通 Cell_model_v10 I-V 扫描
    - [x] ✅ Python→MATLAB→Simulink→CSV→画图 全链路闭环
  - [ ] 第2周：Simulink环境标准化
  - [ ] 第3周：Rule-based + DP手写
  - [ ] 第4周：DP深度分析
- [ ] **第2个月：传统EMS策略深度实现**
  - [ ] 第5-6周：ECMS
  - [ ] 第7-8周：MPC + 四方法对比
- [ ] **第3个月：强化学习**
  - [ ] 第9-12周：DQN/PPO/SAC
- [ ] **第4个月：RL调优 + RAG**
  - [ ] 第13-16周
- [ ] **第5个月：工程化**
  - [ ] 第17-20周
- [ ] **第6个月：求职**
  - [ ] 第21-24周

---

## 待办 (第2周)

- [ ] 下载标准工况数据（WLTC/CLTC/NEDC）
- [ ] 搭建顶层 EMS 系统模型（Fuel Cell + Battery + Load）
- [ ] 写 Rule-based EMS 控制器
- [ ] 跑通 WLTC 工况下的完整 EMS 仿真

## Day6 成果

- `experiments/run_simulation.py` — 总入口脚本（python run_simulation.py）
- `env/simulink_models/Cell_model_v10_lit.slx` — 带 To Workspace 的拷贝
- `env/simulink_models/cell_model_iv_sweep.m` — I-V 扫描脚本
- `results/cell_model_iv_sweep.csv` — 扫描数据（51点）
- `results/cell_model_iv_curve.png` — I-V + 功率曲线图

### 关键指标

| 参数 | 值 |
|------|-----|
| 开路电压 | 387.99 V (~400 cells) |
| 最大功率 | 30.1 kW @ 100A |
| 电压降 (0→100A) | 86.9 V |

> ⚠️ 注意：I-V 曲线在 0-20A 区间有非单调行为，可能是模型热动态未稳定。后续需延长仿真时间或检查模型参数。

## 文件索引

### Day1 — Python数据处理
| 文件 | 说明 |
|------|------|
| `experiments/day1_pandas_intro.py` | pandas + matplotlib 入门练习 |
| `results/day1_wltc_sample.csv` | 生成的 WLTC 模拟数据 |
| `results/day1_wltc_sample_plot.png` | 工况曲线图 |
| `results/day1_wltc_dual_axis.png` | 车速+功率双y轴图 |

### Day2 — Git工作流 + 文档
| 文件 | 说明 |
|------|------|
| `docs/Day2学习总结.docx` | 学习笔记 |

### Day3 — Python-MATLAB接口
| 文件 | 说明 |
|------|------|
| `experiments/day3_call_matlab.py` | Python 调 MATLAB 总入口 |
| `experiments/day3_iv_curve.m` | I-V 曲线 MATLAB 计算脚本 |
| `results/day3_cell_model_iv_curve.csv` | I-V 数据 |
| `results/day3_cell_model_iv_curve.png` | I-V 曲线图 (MATLAB 出图) |
| `results/day3_cell_model_iv_curve_py.png` | I-V 曲线图 (Python 出图) |

### Day6 — 完整仿真链路打通
| 文件 | 说明 | 阅读顺序 |
|------|------|----------|
| `experiments/run_simulation.py` | 总入口脚本 (`python run_simulation.py`) | ① |
| `env/simulink_models/cell_model_iv_sweep.m` | I-V 扫描 MATLAB 脚本 | ② |
| `env/simulink_models/setup_cell_model_logging.m` | 创建 Cell_model_v10_lit（加 To Workspace） | ③ |
| `env/simulink_models/Cell_model_v10_lit.slx` | 带数据记录的模型副本 | — |
| `env/simulink_models/Cell_model_v10.slx` | 原始模型（供对比） | — |
| `experiments/plot_iv_curve.py` | 可视化脚本 | ④ |
| `results/cell_model_iv_sweep.csv` | I-V 扫描数据（51点） | — |
| `results/cell_model_iv_curve.png` | I-V + 功率曲线图 | — |

## 环境

- MATLAB R2024b + Simulink ✅ (F:\Matlab)
- Python 3.13.13 ✅
- VS Code 1.122.1 ✅ (F:\vscode)
- GitHub: https://github.com/1053702092/ems-platform-
