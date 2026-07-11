# 多堆燃料电池船舶动力系统 + 深度学习：研究方案

> 日期：2026-07-11
> 路线：LLM-as-Student — DRL 教师 → LLM 学生知识蒸馏
> 目标期刊：eTransportation / Energy Conversion and Management
> 时间线：3 个月

---

## 一、研究背景

### 1.1 船舶燃料电池的独特需求

与传统车载燃料电池不同，船舶燃料电池系统具有以下关键特征：

| 维度 | 车载 | 船舶 |
|------|------|------|
| 工况特征 | 剧烈波动、不可预测 | 固定航线、规律性航段（靠港/离港/巡航/机动） |
| 运行时长 | 数小时/天 | 数千小时连续运行 |
| 功率等级 | 50-200 kW | MW 级 |
| 安全冗余 | 有限 | 极高（海上救援困难） |
| 法规 | 无特定 | DNV / Lloyd's / CCS 船检规范 |

这些特征使得船舶场景对 **可解释性、退化感知、多时间尺度协调** 有更高要求。

### 1.2 多堆燃料电池系统

多堆（Multi-Stack）配置是船舶 MW 级功率需求的自然选择，优势包括：
- **模块化扩展**：通过增减堆数量适配不同船型
- **冗余容错**：单堆故障不影响全局
- **效率优化**：根据负载动态调整工作堆数量，使每个堆在高效区运行
- **退化管理**：差异化调度延长系统寿命

### 1.3 当前技术前沿

**2025-2026 年关键进展：**

- **AgentEMS** (Wang et al., *eTransportation*, 2026)：首次将 DRL + LLM 结合用于多堆 FC 能量管理，LLM 从 DP 轨迹提炼可解释规则，降退化 45%
- **健康感知 TD3** (Zhu et al., *JMSE*, 2026)：基于各堆实时 SOH 进行差异化功率分配
- **CNN-BiLSTM-Attention + VDP** (Feng et al., *Energy*, 2026)：多时间尺度协调的深度学习预测 + 优化
- **DRL 船舶 EMS** (Wu et al., *IJHE*, 2025)：TD3 用于多簇 FC 沿海渡轮

### 1.4 核心问题

**AgentEMS 的局限：** LLM 只作为离线规则提炼器，规则生成后固定不变。船舶航行中 FC 持续老化，静态规则无法适应系统时变特性。

**本文提出的解决方案：** 将 LLM 从"规则提炼器"升级为"控制策略直接执行者"，通过 DRL → LLM 知识蒸馏，实现 **可解释、自适应、轻量化** 的船舶多堆 FC 能量管理。

---

## 二、技术方案：LLM-as-Student 知识蒸馏框架

### 2.1 总体架构

```
┌──────────────────────────────────────────────────────────────┐
│                    LLM-as-Student 框架                        │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  阶段一：DRL 教师训练                                          │
│  ┌────────────────────────────────────────────────┐          │
│  │ 教师：PPO/TD3 在多堆船舶系统上训练到收敛          │          │
│  │ 状态空间：[负载, SOC, 各堆SOH/温度/电压/电流]    │          │
│  │ 动作空间：各堆功率分配比例（连续）                 │          │
│  │ 奖励函数：J = m_H2 + λ_degrade·D + λ_soc·ΔSOC  │          │
│  │ 记录：状态-动作对 + Q 值 + 轨迹频率               │          │
│  └──────────────────┬─────────────────────────────┘          │
│                     ↓                                        │
│  阶段二：经验数据生成与结构化                                  │
│  ┌────────────────────────────────────────────────┐          │
│  │ Rollout → 10万+ 状态-动作对                      │          │
│  │ Q 值筛选（只保留高质量决策）                      │          │
│  │ 结构化翻译为自然语言格式：                         │          │
│  │   "Vessel in cruising, load=340kW, SOC=62%,    │          │
│  │    Stack1[SOH=0.95,T=65°C],                    │          │
│  │    Stack2[SOH=0.82,T=68°C]                     │          │
│  │    → Allocate: Stack1=120kW, Stack2=80kW,      │          │
│  │      Stack3=140kW. Reason: Stack2 age-limited"  │          │
│  └──────────────────┬─────────────────────────────┘          │
│                     ↓                                        │
│  阶段三：LLM 学生微调                                         │
│  ┌────────────────────────────────────────────────┐          │
│  │ 模型：Qwen2.5-7B-Instruct / DeepSeek-Coder     │          │
│  │ 方法：LoRA（~12GB VRAM 可训）                   │          │
│  │ 损失：ℒ = α·ℒ_action(MSE) + β·ℒ_explain(CE)   │          │
│  │ 训练后：给定状态 → 生成控制动作 + 自然语言解释     │          │
│  └──────────────────┬─────────────────────────────┘          │
│                     ↓                                        │
│  阶段四：部署与推理                                           │
│  ┌────────────────────────────────────────────────┐          │
│  │ 轻量 LLM 推理（无需 RL 策略网络）               │          │
│  │ 输入：实时传感器状态 → 输出：功率分配 + 原因     │          │
│  │ 可在线更新：新数据增量 LoRA                     │          │
│  └────────────────────────────────────────────────┘          │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 与现有方法的区别

| 维度 | AgentEMS | 本文 (LLM-as-Student) |
|------|---------|----------------------|
| 知识来源 | DP 最优轨迹 | DRL 训练后的策略网络 |
| LLM 角色 | 规则提炼器（需人工设计 Prompt） | 控制策略的直接执行者 |
| 可解释性 | 规则是副产品 | 每个动作自带自然语言解释 |
| 泛化能力 | 限于 DP 可见工况 | DRL 探索过的状态空间更广 |
| 部署方式 | DRL 选模式 + 规则执行 | 纯 LLM 推理，无 DRL 组件 |
| 在线适应 | 规则固定不变 | 可增量微调 |

### 2.3 创新点

1. **方法论创新**：首次将 LLM 作为控制策略的直接载体，而非规则提炼工具
2. **范式创新**：DRL → LLM 知识蒸馏新范式，可推广到任意 RL 控制问题
3. **可解释控制**：每个决策附带自然语言推理过程，满足船检法规需求
4. **轻量部署**：蒸馏后的小 LLM 只需前向传播，算力要求低于 DRL 推理

---

## 三、开源数据方案（零采集成本）

### 3.1 船舶负载数据

| 来源 | 内容 | 用途 |
|------|------|------|
| **TU Delft SH2IPDRIVE**（2026） | 天气修正功率曲线 + DP 优化代码 | 主力仿真输入 + DP 基准 |
| **NAUTILUS Zenodo**（2025） | 62.6 MWh SOFC+电池实测，邮轮负载剖面 | 交叉验证 |
| **ShipNetSim**（2025） | 开源船舶仿真器，支持混合推进 | 辅助验证 |
| **AIS marinecadastre.gov** | 免费 AIS 数据→功率曲线生成 | 泛化性证明 |

### 3.2 燃料电池退化数据

| 来源 | 内容 |
|------|------|
| **NBSDC 中国数据集**（5.6GB） | 107 个文件，堆级温度/电压/电流 vs 时间 |
| **NREL / DOE / JRC**（整理自 2026 RSER 综述） | 公开 PEFMC 耐久性数据集 |
| **4TU Delft 海洋污染数据** | NaCl/HCl 对 PEMFC 的退化影响 |

### 3.3 仿真环境

基于用户现有的 **Day6/7 MATLAB 模型** 改造为船舶多堆版本，复用已有的：
- 燃料电池电化学模型
- 锂电池模型
- DP、ECMS、MPC 算法实现（Day4-8 成果）

---

## 四、论文结构计划

| 章节 | 内容 | 页数 |
|------|------|------|
| **1. Introduction** | 船舶多堆 FC 背景 + DRL 可解释性痛点 + 本文贡献 | 1.5 |
| **2. Related Work** | AgentEMS、健康感知 EMS、LLM for control、知识蒸馏 | 1.5 |
| **3. Problem Formulation** | 船舶多堆系统模型 + 多目标优化问题 | 1.5 |
| **4. Methodology** | 四阶段框架（教师→数据→学生→部署） | 3.0 |
| **5. Experiments** | 5 组实验 + 消融 + 泛化 + 实时性 | 2.5 |
| **6. Conclusion** | 结论 + 局限 + 未来方向 | 0.5 |

---

## 五、开源资源链接汇总

| 资源 | 链接 |
|------|------|
| TU Delft SH2IPDRIVE Chapter 5 | https://research.tudelft.nl/en/datasets/data-accompanying-chapter-5-of-the-phd-dissertation-energy-system/ |
| TU Delft DP-EMS | https://research.tudelft.nl/en/datasets/matlabsimulink-simulation-model-accompanying-publication-optimal-/ |
| TU Delft 层级控制 | https://research.tudelft.nl/en/datasets/matlabsimulink-model-supporting-the-publication-hierarchical-cont/ |
| NAUTILUS 实测数据 | https://zenodo.org/records/14643552 |
| ShipNetSim | https://www.mdpi.com/2077-1312/13/3/518 |
| NBSDC FC 退化数据 | https://nbsdc.cn/general/dataDetail?id=6406d42687c4320b879918f2 |
| DTU dEMS | https://orbit.dtu.dk/en/datasets/dems-degradation-aware-energy-management-system/ |
| FC 退化综述（数据目录） | https://www.sciencedirect.com/science/article/abs/pii/S1364032125012717 |
| GitHub 油耗建模 | https://github.com/yuquandu/Data-driven-Ship-Fuel-Efficiency-Modeling |
| AgentEMS 原文 | https://www.sciencedirect.com/science/article/abs/pii/S2590116826000676 |
