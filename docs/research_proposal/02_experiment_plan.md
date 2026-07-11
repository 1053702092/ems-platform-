# 实验方案设计：LLM-as-Student 知识蒸馏框架

> 船舶多堆燃料电池动力系统 × 深度学习
> 周期：12 周（2026-07-11 → 2026-10-03）
> 目标期刊：eTransportation / Energy Conversion and Management

---

## 一、实验总路线图

```
第1个月（Week 1-4）  第2个月（Week 5-8）    第3个月（Week 9-12）
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ 仿真环境搭建   │    │ DRL 教师训练  │    │ 实验验证      │
│ DP 基线       │ →  │ 数据管道      │ →  │ 论文写作      │
│ 工况分析      │    │ LLM 学生微调  │    │ 投稿          │
└──────────────┘    └──────────────┘    └──────────────┘
```

---

## 二、Week 1-2：仿真环境搭建

### 2.1 船舶多堆 FC 混合动力模型

**目标**：建立一个可模拟多堆 PEMFC + 锂电池船舶动力系统的仿真环境。

**系统架构：**

```
                        ┌─────────────┐
  航段负载曲线 ─────────→│             │
                        │   EMS 控制器 │
  FC 各堆 SOH ─────────→│  (待验证算法) │
                        │             │
  SOC / 电池状态 ──────→│             │
                        └──────┬──────┘
                               │ 功率分配指令
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
   │ FC Stack #1  │    │ FC Stack #2  │    │ FC Stack #3  │
   │ SOH=0.95     │    │ SOH=0.82     │    │ SOH=0.88     │
   │ 100kW max    │    │ 100kW max    │    │ 100kW max    │
   └──────┬───────┘    └──────┬───────┘    └──────┬───────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              ▼
                       ┌──────────────┐
                       │   DC 总线     │
                       └──────┬───────┘
                              │
                       ┌──────▼───────┐
                       │  LiB Battery │
                       │  50 kWh      │
                       └──────────────┘
```

**具体实现：**

| 模块 | 实现方式 | 基础来源 |
|------|---------|---------|
| PEMFC 电化学模型 | 极化曲线 + 效率 map | Day6 MATLAB 代码 |
| FC 退化模型 | SOH 线性衰减 + 负载依赖加速因子 | NBSDC 数据集拟合 |
| 锂电池模型 | Rint / RC 等效电路 | Day7 电池模型 |
| 船舶负载 | TU Delft 功率曲线 + 航段分割 | SH2IPDRIVE 数据 |
| 仿真调度器 | Python, 0.1s 步长, 航次循环 | 新写 |

### 2.2 航段工况定义

基于 TU Delft 数据和典型船舶运行模式，定义 4 种航段：

| 航段 | 时长 | 功率特征 | 负载范围 |
|------|------|---------|---------|
| 靠港 (Idle) | 1-4h | 低功率稳定 | 10-50 kW |
| 离港/机动 (Maneuver) | 10-30min | 高功率突增 | 200-350 kW peak |
| 巡航 (Cruising) | 4-20h | 中等功率稳定 | 150-250 kW |
| 恶劣海况 (Storm) | 1-3h | 波动剧烈 | 100-300 kW 波动 |

每个航次由多个航段按随机顺序组成，模拟完整航行。

**实现任务清单：**

- [ ] 将 Day6 MATLAB PEMFC 模型移植为 Python
- [ ] 扩展为多堆（3-6 堆）配置
- [ ] 实现退化模型（从 NBSDC 数据拟合参数）
- [ ] 实现 TU Delft 风格船舶负载生成器
- [ ] 实现航段分割器（基于规则或聚类）
- [ ] 验证仿真环境：DP 结果应与 TU Delft 开源结果一致

---

## 三、Week 3-4：DP 基线 + 基准策略

### 3.1 DP 离线最优（复用 Day8 经验）

对每个航段类型分别跑 DP：

```
输入：航段负载曲线 + 各堆初始 SOH + 电池 SOC₀
输出：各堆功率分配时间序列 + 总氢耗 + 退化量
约束：SOC 范围 [0.3, 0.9], 各堆功率范围 [P_min, P_max]
优化：min J = Σ (m_H2(t) + λ·D_degrade(t)) · Δt
```

DP 结果将作为：
1. **理论上界**（Performance Upper Bound）
2. **AgentEMS 规则的知识来源**（复现基线用）
3. **奖励塑形参考**（DRL 教师训练用）

### 3.2 对比基线实现

| 基线策略 | 说明 | 实现来源 |
|---------|------|---------|
| 规则式（均匀分配） | 功率按各堆额定容量比例分配 | 简单 |
| 规则式（SOH 优先级） | SOH 高的堆承担更多负载 | 新写 |
| ECMS | 等效消耗最小化策略 | Week5 代码改造 |
| AgentEMS (复现) | DRL 选模式 + LLM 规则 | 从论文描述重实现 |
| DRL 端到端 (PPO/TD3) | 直接输出功率分配 | 你的 RL 实现 |

### 3.3 评价指标体系

| 指标 | 公式 | 说明 |
|------|------|------|
| 等效氢耗 | m_H2_eq = m_H2 + λ·ΔSOC | 考虑电池能量变化 |
| 退化成本 | C_degrade = Σ(ΔSOH_i) × C_stack | 堆寿命折损成本 |
| 总运营成本 | J_total = C_H2 + C_degrade | 综合指标 |
| 效率保持率 | η_avg = 平均效率 / 最优效率 | 堆是否在高效区 |
| SOC 维持 | SOC_end - SOC_ref | 终端 SOC 偏差 |
| 可解释性评分 | XAI_score | LLM 输出质量（人工+自动） |

---

## 四、Week 5-6：DRL 教师训练

### 4.1 算法选择

**首选：PPO（你正在学的）**

理由：
- 你的第 11 周计划就是 PPO
- PPO 的 clipped surrogate objective 训练稳定
- 适合连续动作空间（功率分配比例）

**备选：TD3**

理由：
- 船舶 EMS 文献中 TD3 使用最广（Wu 2025, Zhu 2026）
- 处理连续动作的 sample efficiency 更高
- 如果 PPO 收敛慢，切换到 TD3

### 4.2 MDP 定义

| 元素 | 定义 |
|------|------|
| **状态** | [P_load, SOC, T_stack_1..N, SOH_1..N, V_stack_1..N, 航段类型] |
| **动作** | [α_1, α_2, ..., α_N] 各堆功率占比，∑α_i = 1 |
| **奖励** | r = -(m_H2 + w1·D_degrade + w2·|SOC - SOC_ref| + w3·η_penalty) |

### 4.3 训练配置

| 参数 | 值 |
|------|-----|
| Episode 长度 | 1 航次（8-24h 仿真） |
| 隐层大小 | [256, 256] |
| 学习率 | 3e-4 |
| 折扣因子 γ | 0.99 |
| GAE λ | 0.95 |
| PPO clip ε | 0.2 |
| 总训练步数 | 2e6 |
| Evaluation 间隔 | 每 10000 步 |

### 4.4 奖励塑形策略

奖励函数设计是成功关键：

```
r = -[ w_H2 · m_H2 / m_H2_max                          ← 氢耗
     + w_degrade · Σ ΔSOH_i / N                        ← 退化
     + w_soc · |SOC - SOC_ref|                         ← SOC 维持
     + w_eff · max(0, η_target - η_avg)                ← 效率惩罚
     + w_balance · std(α_i · P_load / P_i_max)         ← 堆间均衡
     ]
```

权重调整策略：
1. 先用 w_H2=1.0，其他为 0 训练，观察氢耗最优行为
2. 逐步加入 w_degrade、w_soc
3. 最终在验证集上网格搜索最优权重组合

### 4.5 多航段训练策略

由于船舶具有规律性航段，使用 **课程学习 (Curriculum Learning)**：

```
Phase 1: 只在巡航段训练（最简单，功率稳定）
Phase 2: 引入巡航+靠港
Phase 3: 全航段混合
Phase 4: 随机航段序列 + 不同 SOH 初始值
```

### 4.6 关键产出

- [ ] PPO/TD3 策略收敛曲线
- [ ] 与 DP 最优的差距量化（Gap ≤ 5% 为成功）
- [ ] 10万+ 状态-动作对（用于 LLM 训练）
- [ ] 策略可视化（t-SNE 降维策略分布）

---

## 五、Week 7：经验数据生成与结构化

### 5.1 数据生成

使用训练好的教师策略在所有航段类型上 Rollout：

| 数据源 | 数量 | 覆盖条件 |
|--------|------|---------|
| 巡航（不同负载） | 30,000 | 3 种载重 × 5 种 SOH 组合 × 2000 步 |
| 离港/机动 | 20,000 | 2 种机动强度 × 5 种 SOH 组合 |
| 靠港 | 15,000 | 2 种靠港模式 × 5 种 SOH |
| 恶劣海况 | 15,000 | 3 种海况等级 |
| 混合航段序列 | 20,000 | 随机序列 + 随机初始 SOH |
| **总计** | **100,000** | 覆盖 95% 以上运行场景 |

### 5.2 Q 值筛选

只保留 Q 值在 top-50% 的决策对，确保：

```
高质量决策条件：
  ① Q_value ≥ median(Q_all)    ← 教师认为好的决策
  ② 动作不违反安全约束         ← 功率限制 / 爬坡率
  ③ 状态分布覆盖均匀           ← 避免样本偏差
```

### 5.3 结构化翻译模板

每个训练样本格式：

```
【输入 - 系统状态】
{
  "voyage_segment": "cruising",
  "sea_condition": "calm",
  "load_kW": 340.0,
  "battery_SOC": 0.62,
  "stacks": [
    {"id": 1, "SOH": 0.95, "temp_C": 65.0, "voltage_V": 48.2, "current_A": 120},
    {"id": 2, "SOH": 0.82, "temp_C": 68.0, "voltage_V": 47.5, "current_A": 95},
    {"id": 3, "SOH": 0.88, "temp_C": 63.0, "voltage_V": 48.0, "current_A": 110}
  ]
}

【输出 - 控制决策与解释】
{
  "action": {
    "stack_power_kW": [120.0, 80.0, 140.0],
    "battery_power_kW": 0.0
  },
  "reasoning": "Allocating higher power to Stack1 and Stack3 \
    based on their better SOH ratings. Stack2, with SOH=0.82, \
    is limited to 80kW to extend its remaining lifetime. \
    All stacks operate within their peak efficiency range \
    (45-65% rated power). Battery is neither charging nor \
    discharging as current load can be met by stacks alone."
}
```

### 5.4 数据增强

对数据进行轻微扰动（添加 ±5% 噪声）以增强 LLM 的泛化性。

---

## 六、Week 8：LLM 学生微调

### 6.1 模型选择

| 模型 | 参数量 | 显存需求 (LoRA) | 推荐度 |
|------|--------|----------------|--------|
| Qwen2.5-7B-Instruct | 7B | ~14GB | ⭐⭐⭐⭐⭐ 首选 |
| DeepSeek-Coder-V2-Lite | 16B | ~24GB | ⭐⭐⭐ 更强但需更大显存 |
| Qwen2.5-1.5B-Instruct | 1.5B | ~6GB | ⭐⭐ 轻量但容量可能不够 |
| Llama-3.1-8B-Instruct | 8B | ~16GB | ⭐⭐⭐ 备选 |

**首选推荐：Qwen2.5-7B-Instruct**
- 中英文能力均衡
- 指令跟随能力强
- 12GB 显存可 LoRA 微调

### 6.2 微调方法：LoRA

```
LoRA 配置：
  r = 16        (低秩矩阵秩)
  α = 32        (缩放参数)
  dropout = 0.1
  目标模块: q_proj, v_proj (注意力层)
  优化器: AdamW, lr=2e-4
  批大小: 16 (gradient accumulation)
  训练轮数: 3 epochs
  学习率调度: cosine with warmup
```

### 6.3 损失函数

联合损失函数设计：

```
ℒ = α · ℒ_action + β · ℒ_explain

其中：
  ℒ_action = MSE(α_pred, α_true)          ← 动作准确率
  ℒ_explain = CrossEntropy(exp_pred, exp_true)  ← 解释质量

  初期 α=1.0, β=0.5
  后期 α=0.8, β=1.0（逐步放大解释权重）
```

### 6.4 训练/验证集划分

| 数据集 | 比例 | 数量 |
|--------|------|------|
| 训练集 | 80% | 80,000 |
| 验证集 | 10% | 10,000 |
| 测试集 | 10% | 10,000 |

测试集严格按 **未见过 SOH 组合 + 未见过航段序列** 划分，验证泛化性。

### 6.5 可行性检查清单

- [x] 你已有 PyTorch 基础（Week 9 完成）
- [ ] 安装 Qwen2.5 推理依赖（transformers + vLLM 或 llama.cpp）
- [ ] 确认 GPU 显存 ≥ 12GB（否则用 Qwen2.5-1.5B 或租用 GPU）
- [ ] 准备微调脚本（基于 unsloth 或 LLaMA-Factory）
- [ ] 验证单条样本的前向推理正确性

---

## 七、Week 9-10：实验验证

### 7.1 实验 1：主对比实验

**目的**：与所有基线比较，验证 LLM-Student 的有效性。

| 方法 | 氢耗 (kg) | 退化成本 ($) | 总成本 ($) | SOC 偏差 |
|:----:|:---------:|:-----------:|:---------:|:--------:|
| DP (理论最优) | — | — | — | — |
| 规则均匀 | — | — | — | — |
| 规则 SOH 优先 | — | — | — | — |
| ECMS | — | — | — | — |
| AgentEMS (复现) | — | — | — | — |
| DRL 端到端 (PPO) | — | — | — | — |
| **LLM-Student (本文)** | — | — | — | — |

**假设**：LLM-Student 接近 DRL 教师性能（Gap ≤ 5%），且优于所有基线。

### 7.2 实验 2：泛化性测试

| 测试场景 | 训练集包含？ | 预期效果 |
|---------|:----------:|---------|
| 未见过的 SOH 组合（如 SOH=[0.70, 0.75, 0.80]） | ❌ | 良好泛化 |
| 不同船舶参数（200kW→400kW总功率） | ❌ | 需验证 |
| 极端天气负载 | ❌ | 退化但不应崩溃 |
| 多航次连续运行（50 航次） | ❌ | 退化累积效果 |

### 7.3 实验 3：消融实验

| 变体 | 说明 | 目的 |
|------|------|------|
| 无 Q 值筛选 | 使用全部数据训练 | 验证 Q 值筛选必要性 |
| 无解释损失 | α=1.0, β=0.0 | 验证解释损失对动作的影响 |
| 更小模型 | Qwen2.5-1.5B | 探索模型大小与性能关系 |
| 不同蒸馏方法 | Behavior Cloning（直接监督学习） | 验证蒸馏框架优于 BC |

### 7.4 实验 4：实时性与部署验证

| 指标 | 要求 | LLM-Student | DRL Teacher |
|:----:|:----:|:-----------:|:----------:|
| 单步推理时间 | <100ms | — | — |
| 显存占用 | <4GB | — | — |
| 模型大小 | <500MB (4bit) | — | — |

**实验方法**：在 CPU 和 GPU 上分别测试推理延迟，与 DRL 策略网络对比。

### 7.5 实验 5：可解释性评估

**量化评估：**
- **Action Accuracy**：LLM 输出动作与教师动作的归一化误差
- **Reasoning Relevance**：利用 LLM-as-Judge（GPT-4）评估解释与动作的匹配度
- **Human Rating**：邀请 3 位领域研究者对 50 个随机样本进行 1-5 分打分

---

## 八、Week 11：论文写作

### 8.1 论文大纲（详细）

```
Title: "LLM-as-Student: Distilling Interpretable Control Policies 
       from Deep Reinforcement Learning for Multi-Stack Fuel Cell 
       Marine Power Systems"

Abstract (~200 words):
  [背景] 船舶多堆FC系统需要可解释、自适应的能量管理。
  [问题] DRL策略是黑箱，现有LLM方法（如AgentEMS）只做离线规则提炼。
  [方法] 提出LLM-as-Student框架：DRL教师 → 知识蒸馏 → LLM学生。
  [结果] 在XX个航次仿真中，LLM学生控制精度达到DRL教师的XX%。
  [贡献] 1)新范式 2)可解释× 3)轻量级。

1. Introduction (~500 words)
   1.1 船舶FC背景与多堆必要性
   1.2 DRL在EMS中的成功与局限
   1.3 AgentEMS与LLM+控制的最新进展
   1.4 本文贡献（三点）

2. Related Work (~400 words)
   2.1 船舶多堆FC能量管理
   2.2 DRL在EMS中的应用
   2.3 LLM for Control / 知识蒸馏

3. Problem Formulation (~400 words)
   3.1 船舶多堆FC混合动力系统模型
   3.2 优化目标函数
   3.3 约束条件

4. Methodology (~800 words)
   4.1 总体框架
   4.2 Phase I: DRL Teacher Training
      - MDP设计
      - 课程学习策略
   4.3 Phase II: Experience Structuring
      - 数据生成与Q值筛选
      - 结构化翻译模板
   4.4 Phase III: LLM Student Finetuning
      - 模型选择与LoRA配置
      - 联合损失函数
   4.5 Phase IV: Deployment

5. Experiments (~800 words)
   5.1 实验设置（仿真环境、参数、基线）
   5.2 主对比实验（表2）
   5.3 泛化性实验
   5.4 消融实验
   5.5 实时性分析
   5.6 可解释性评估

6. Discussion (~300 words)
   6.1 发现总结
   6.2 局限性
   6.3 未来方向

7. Conclusion (~200 words)

Figures:
  Fig 1: 总体框架图（四阶段流程图）
  Fig 2: 船舶航段负载曲线
  Fig 3: 训练收敛曲线
  Fig 4: 主对比结果柱状图
  Fig 5: 泛化性热力图
  Fig 6: 可解释性样本展示

Tables:
  Table 1: 仿真参数
  Table 2: 主对比结果
  Table 3: 消融实验
  Table 4: 实时性对比
```

### 8.2 图件制作计划

| 图号 | 内容 | 工具 | 优先级 |
|:----:|------|:----:|:-----:|
| Fig 1 | 框架架构图 | draw.io / Matplotlib | P0 |
| Fig 2 | 航段负载曲线 | Matplotlib | P0 |
| Fig 3 | 训练收敛曲线 | TensorBoard + Matplotlib | P0 |
| Fig 4 | 对比柱状图 | Matplotlib | P0 |
| Fig 5 | 泛化性热力图 | Seaborn | P1 |
| Fig 6 | LLM 输出样本截图 | 截图 | P1 |

---

## 九、Week 12：修改与投稿

### 9.1 投稿前检查清单

- [ ] 所有实验可复现（提供代码+随机种子）
- [ ] 数值结果统计显著性（多次运行取 mean±std）
- [ ] 图件分辨率 ≥ 300dpi
- [ ] 参考文献 40-60 篇，覆盖 2025-2026 最新
- [ ] 所有缩写首次出现有定义
- [ ] 与 AgentEMS 的对比有公平的算力/数据条件
- [ ] 附录提供 LLM 输出的完整样本

### 9.2 目标期刊投稿策略

| 优先级 | 期刊 | IF | 审稿周期 | 匹配度 |
|:-----:|:----:|:--:|:-------:|:-----:|
| 首选 | **eTransportation** | ~15 | 2-3月 | ⭐⭐⭐⭐⭐ |
| 备选 | **Energy Conversion and Management** | ~10 | 2-4月 | ⭐⭐⭐⭐ |
| 备选 | **Applied Energy** | ~11 | 2-3月 | ⭐⭐⭐⭐ |

### 9.3 时间分配

```
Week 9:   实验 1-2（主对比 + 泛化性）
          开始写 Introduction + Related Work

Week 10:  实验 3-5（消融 + 实时性 + 可解释性）
          完成 Methods + Experiments 草稿

Week 11:  图件制作 + 全文润色 + 参考文献
          内部审读 + 修改

Week 12:  最终校对 + 格式调整 + 投稿
          准备 Supplementary Materials
```

---

## 十、风险评估与应对

| 风险 | 概率 | 影响 | 应对方案 |
|:----:|:----:|:----:|---------|
| LLM 动作精度不够 | 中 | 高 | 增大解释损失权重→牺牲解释保动作；或用 Ensemble |
| 仿真环境调试超时 | 高 | 中 | Week1-2 集中攻坚，Day6/7 代码复用 |
| GPU 显存不足 | 中 | 中 | Qwen2.5-1.5B 或 租用 AutoDL/趋动云 |
| PPO 不收敛 | 低 | 中 | 换成 TD3，你的 Reward Shaping 要调 |
| 审稿人质疑 LLM必要性 | 中 | 低 | 强调船检法规的可解释性刚需 + 轻量部署优势 |
| 与 AgentEMS 太相似 | 低 | 高 | LLM-as-Student 是本质不同的范式，对比 section 要突出差异 |
| 时间不够 | 中 | 高 | 第 10 周末必须定稿，删非核心实验 |
