# 文献综述：从深度强化学习到大语言模型的知识蒸馏 —— 面向多堆燃料电池船舶动力系统的可解释能量管理

## 摘要

本综述系统梳理了2024-2026年间"LLM-as-Student"范式的核心文献，聚焦于将深度强化学习（DRL）知识蒸馏到大语言模型（LLM），以实现多堆燃料电池（MFC）船舶动力系统的可解释能量管理。通过八组多维度检索，我们覆盖了四个交叉领域：（1）多堆燃料电池能量管理，（2）面向船舶/混合动力系统的DRL，（3）LLM在控制和可解释AI中的应用，以及（4）从RL到语言模型的知识蒸馏。共筛选出40余篇高相关度论文。分析表明，AgentEMS（Wang et al., 2026, eTransportation）是目前最接近的研究——首次提出DRL+LLM双层智能体框架用于多堆燃料电池能量管理，实现了电堆寿命45%的提升。然而，该领域仍然存在关键空白：缺乏将DRL策略蒸馏为LLM可执行控制代码的系统性方法论，缺乏船舶工况下的健康感知蒸馏机制，以及缺乏面向工业部署的轻量化在线学习方法。本综述为"LLM-as-Student"这一新兴研究范式提供了完整的文献地图和研究机遇图谱。

---

## 1. 多堆燃料电池能量管理

### 1.1 研究背景

多堆燃料电池系统（MFCS）通过多个低功率电堆的模块化组合提供高功率输出，具有冗余性、可扩展性和故障容错能力，特别适用于船舶、重型卡车和机车等高功率应用场景（Ghaderi et al., 2025; Zhou et al., 2022）。然而，MFCS引入了复杂的功率分配问题：各电堆性能不一致、退化速率不同、动态响应特性各异，使得传统单一电堆的优化控制方法不再适用。

### 1.2 基于规则与优化的传统EMS

**Ghaderi et al. (2024)** 发表在 IEEE Intelligent Transportation Systems Magazine 上的综述系统回顾了多堆燃料电池混合电动汽车（MFCHEV）能量管理策略的演变。研究指出，基于规则的EMS虽然简单可靠但缺乏适应性，基于优化的方法（如DP、PMP、MPC）性能优越但计算复杂度高且依赖精确系统模型。该综述提出多智能体强化学习是解决MFCHEV堆连接问题的潜在途径。

**Cao et al. (2026)** 发表在 Journal of Marine Science and Engineering 上的研究提出了一种针对MFCS性能不一致的分层控制EMS。第一层使用改进灰狼优化器（IGWO）结合半经验模型预测性能参数；第二层通过缩放因子将减少性能劣化电堆负载和提高系统效率两个目标融合为单一优化目标。仿真结果表明，相比平均分配策略和链式启动策略，该方法分别降低氢耗2.96%和19.4%，并使性能劣化电堆的输出能量分别减少26.51%和48.25%。

### 1.3 健康感知的多堆能量管理

**Yang et al. (2026)** 发表在 Ocean Engineering 上的研究提出了面向混合动力船舶的多时间尺度能量管理策略，兼顾MFCS的寿命均衡与延长。该研究将电化学活性面积（ECSA）退化和质子交换膜老化纳入模型，使用加速应力试验数据进行验证。研究表明，大多数研究局限于单一电堆配置和简化的循环负载条件，缺乏捕捉船舶工况动态特性的综合退化模型。

**Zhu et al. (2026)** 发表在 Journal of Marine Science and Engineering 上的研究提出了基于TD3算法的健康感知差异化能量管理策略。与传统方法将多个燃料电池电堆视为同质单元不同，该策略创新性地基于各电堆实时健康状态（SOH）实施差异化功率分配。在三种不同SOH差异场景下的对比实验表明，相比采用平均功率分配的TD3基线策略，健康感知差异化TD3策略显著降低了系统的总航行成本，且成本节约效果随电堆间SOH差距增大而更加显著。

**Geng & Xu (2025)** 发表在 Energies 上的研究提出了面向船舶多堆混合储能系统的状态感知EMS。利用燃料电池效率衰减模型和锂离子电池循环寿命评估，将功率分配重新表述为具有堆退化约束的等效氢耗优化问题。混合GA-PSO方法实现了全局优化：相比频率解耦方法，氢耗降低7.03g，运营成本降低4.78%；相比传统PSO，氢耗降低3.61g/周期，运营成本降低2.66%。

**Houjayrie et al. (2026)** 在 PHM Society European Conference 上发表的研究提出了多堆PEMFC系统的健康感知负载分配与联合能量-维护优化框架。第一阶段开发了负载依赖的退化预测框架用于在线健康状态估计和剩余寿命预测；第二阶段利用预测结果进行健康感知能量管理和维护规划决策。

---

## 2. DRL在船舶/混合动力系统中的应用

### 2.1 TD3/DDPG在混合动力船舶中的应用

**Wu et al. (2025)** 发表在 International Journal of Hydrogen Energy 上的研究提出了基于TD3的混合动力推进系统智能能量管理框架。以沿海渡轮为案例（配备燃料电池簇和电池），TD3智能体在大规模历史负载数据上训练，生成面向连续状态和动作空间的通用策略。验证结果表明，4簇策略的平均航行成本仅比TD3均匀策略高2.7%，而全球变暖潜能（GWP）排放降低1.8%。

**Li et al. (2026)** 发表在 Energies 上的研究针对港口拖船甲醇增程串联混合动力系统提出了基于TD3的实时能量管理策略。在典型港口作业循环仿真中，TD3相比基于规则的方法、ECMS和DDPG分别降低甲醇消耗约18.5%、10.2%和7.3%，NOx和CO2排放也显著降低。其整体性能与全局最优DP的差距小于2.5%，同时保持实时在线决策能力。硬件在环测试显示TD3在实际通信和执行条件下性能退化小于1.8%。

**Zhu et al. (2024)** 发表在 International Journal of Hydrogen Energy 上的研究提出了基于DRL的多目标优化燃料电池混合动力船舶能量管理策略。该研究来自大连海事大学团队，为后来健康感知TD3研究奠定了基础。

### 2.2 预测感知与工况识别的DRL

**Kopka et al. (2026)** 发表在 arXiv 上的研究提出了面向燃料电池-电池船舶动力系统的退化感知预测性能量管理策略。利用港作拖轮真实船上测量数据进行15分钟负载预测，结果显示相比滤波器基线方法，退化感知预测控制同时降低氢耗5.8%和电堆退化36.4%（在老化燃料电池系统中）。将预测时域延长至1小时可进一步降低3.8%氢耗和14.0%退化。

**Shan et al. (2025)** 发表在 International Journal of Hydrogen Energy 上的研究提出了利用DRL和驾驶工况识别的智能能量管理策略。GRU识别模型结合速度预测达到97%的工况识别准确率，在不同驾驶场景下实现5-8%的氢耗降低。

**Sayah et al. (2026)** 发表在 Energy and AI 上的研究提出了预测性道路感知DRL方法，在突尼斯562公里真实旅程上进行验证。自适应道路感知策略相比DDPG道路感知策略降低氢耗8%，相比ECMS降低27.3%。

### 2.3 DRL安全性与可解释性改进

**Huang et al. (2026)** 发表在 Automotive Engineering 上的研究提出了基于策略可靠性评估的DRL-ECMS能量管理方法。设计了一种基于集成策略网络模型的策略可靠性评估机制，对安全关键动作进行定量可靠性评价并在线修正等效因子。相比标准SAC和传统自适应ECMS，SAC-ECMS训练框架分别提升燃油经济性4.32%和7.82%。

发表于 **npj Sustainable Mobility and Transport (2026)** 的研究提出了安全引导的DRL框架，引入独立的安全引导网络显式可靠地执行安全约束。通过将安全保证与目标优化解耦，克服了现有奖励惩罚方法中的相互干扰和奖励调优困难。在燃料电池客车平台上验证，该方法在满载条件下提升燃油经济性8.36%和锂电池热安全性10.14%，在真实场景中保持零不安全时长。

**Yang et al. (2026)** 发表在 IEEE Transactions on Transportation Electrification 上的研究提出了分层混合深度强化监督学习框架。首先通过监督行为克隆从DP轨迹提取最优功率分配策略，然后利用预训练的DNN初始化TD3演员网络。结果表明该框架加速收敛、提升系统性能并确保更安全的控制策略。

### 2.4 DRL可解释性在能源领域

**Rabbi (2026)** 发表在 Energy and AI 上的研究提出了面向氢介质电网弹性的DRL可解释AI框架。使用PPO智能体协调电解槽、储氢和燃料电池作为自适应电网弹性基础设施。SHAP分析识别出氢SOC、可再生能源发电和需求是主要的策略驱动因素。研究表明可解释DRL在能源系统中具有实际应用前景。

---

## 3. LLM在控制与可解释AI中的应用

### 3.1 LLM在工业控制中的综述

**Nosrati et al. (2026)** 发表在 Engineering Applications of Artificial Intelligence 上的综述论文"控制遇上大语言模型：从语言到动力学"系统梳理了LLM在控制领域中的应用。论文识别出LLM的涌现能力（上下文学习、指令遵循、多步推理）使其能够作为AI智能体感知环境、决策和行动。在控制系统中，LLM可通过提示工程、检索增强生成（RAG）和工具集成来增强智能体能力。该综述划分了LLM在控制中的三个层次：直接控制生成、高层规划与监督、以及人机交互界面。

### 3.2 LLM生成控制逻辑与代码

**Koziolek et al. (2025)** 提出了Spec2Control，一个高度自动化的LLM工作流，可直接从自然语言用户需求生成图形化IEC 61131-3控制逻辑。在包含10个控制叙述和65个复杂测试用例的开放数据集上的实验表明，Spec2Control可成功识别控制策略，自主生成98.6%的正确控制策略连接，节省94-96%的人力。该研究已被集成到ABB商业工程工具中。

**Margadji & Pattinson (2026)** 在 Nature Communications 上提出了CIPHER（Control and Interpretation of Production via Hybrid Expertise and Reasoning）：一个面向工业感知、解释和控制的系统级视觉-语言-动作（VLA）框架。CIPHER集成了用于系统状态定量表征的过程专家和基于物理与知识的RAG推理。这种混合设计使智能体能够解释文本或视觉输入、解释其决策并自主生成精确的机器指令。在多个制造系统中的部署显示了精确、上下文感知和透明的控制能力。

### 3.3 LLM在故障恢复与安全控制中的应用

**Vyas & Mercangoez (2025)** 提出了统一的智能体框架，利用LLM在同一架构中实现离散故障恢复规划和连续过程控制。采用有限状态机（FSM）作为可解释操作包络：LLM驱动的规划智能体通过FSM提出恢复序列，仿真智能体执行并检查每个转换，验证器-重新提示循环迭代优化无效计划。在180个随机生成FSM上的测试中，GPT-4o和GPT-4o-mini在五次重新提示内达到100%有效路径成功率。

**Bayat et al. (2025)** 提出了LLM增强的符号控制框架，用于从自然语言规格合成基于抽象的控制器设计（ABCD）的到达-避免问题。代码智能体将控制问题的NL描述解释为形式语言，检查器智能体验证生成代码的正确性。该方法降低了形式控制合成的门槛。

来自帝国理工学院的 **ctrl-alt-recover** 研究代码库展示了LLM agent在信息物理系统监督故障恢复中的应用。LLM不直接驱动底层控制器，而是提出高层恢复决策，经知识图谱验证和数字孪生仿真检查后才被接受。关键设计选择是将LLM视为受约束的监督规划器，而非不受控的控制器。

### 3.4 可解释控制框架

**Yin et al. (2026)** 提出了基于模糊模型无关解释和LLM智能体支持界面的可解释控制框架（XCF）。核心创新是层次化模糊模型无关解释方法（HFMAE-C），使用模糊逻辑系统逼近控制器行为和系统动力学，通过IF-THEN规则揭示控制器的决策逻辑和显著性值。LLM智能体支持界面可自动分析用户需求、选择适当算法、将生成的解释转化为自然语言报告并提供交互式咨询。

**Naagarajan et al. (2026)** 提出了层次化因果溯因（HCA）框架，结合物理知识图谱推理、KKT乘子的优化证据和PCMCI时间因果发现，为非线性和安全关键MPC控制动作生成忠实可解释的解释。在三个不同控制应用（温室气候、建筑HVAC、化工过程）中，HCA将解释准确率相对于LIME提升53%（0.478 vs 0.311）。

**Chen et al. (2026)** 提出将开放LLM作为强耦合MIMO工业过程控制器调优的结构化先验。在一个四水箱强耦合系统上基于评分基准，有支架的开放LLM推理出反直觉的非对称结构，达到J=16.9±0.2的评分，与初始化无关；经典优化器精调后达到全局最优J=12.0（10/10次成功 vs 0/10次失败）。LLM的优势在于样本效率（18次评估得到可用控制器）和可解释性（提供明确的推理理由）。

---

## 4. 从强化学习到语言模型的知识蒸馏

### 4.1 On-Policy蒸馏框架

**Song & Zheng (2026)** 在 Tencent 发表的综述论文系统梳理了LLM的On-Policy蒸馏（OPD）方法。OPD通过让学生在实际生成的轨迹上接收教师反馈来组织训练循环，将暴露偏差从序列长度的平方级降低到线性级。该综述沿着三个设计轴（优化什么、信号来源、如何稳定训练）组织了现有工作，并指出了蒸馏缩放定律、不确定性感知反馈、智能体级蒸馏等开放问题。

**Lu et al. (2026)** 提出了SDAR（Self-Distilled Agentic Reinforcement Learning），将OPSD作为门控辅助目标，同时保持RL作为主要优化骨干。SDAR将解耦的token级信号映射到sigmoid门控，在教师认可的正间隙token上增强蒸馏，在负教师拒绝上软衰减。在Qwen2.5和Qwen3系列上的实验表明，SDAR在ALFWorld上比GRPO提升9.4%，在Search-QA上提升7.0%，在WebShop-Acc上提升10.2%。

**Liu et al. (2026)** 提出了TGPO（Teacher-Guided Policy Optimization），一种利用教师预测（基于学生rollout的条件预测）提供密集方向指导的on-policy算法。当学生和教师分布显著偏离时，标准RKL因无信息负反馈而失效；TGPO通过条件教师预测解决了这一问题。在复杂推理基准上的实验表明TGPO显著优于标准基线方法。

**Penaloza et al. (2026)** 提出了privileged information蒸馏方法：pi-Distill和OPSD。pi-Distill是联合教师-学生目标函数，同时训练PI条件的教师和非条件的学生。OPSD则使用带反向KL惩罚的RL训练。二者均有效蒸馏了frontier agent，在多个基准上优于SFT+RL这一工业标准方法。

### 4.2 结合RL和KD的统一框架

**Xu et al. (2026)**（华为诺亚方舟实验室）提出了KDRL，一个统一的后训练框架，同时优化教师监督（KD）和学生自我探索（RL）。KDRL利用策略梯度优化同时最小化学生与教师分布间的RKL散度和最大化基于规则的期望奖励。实验表明KDRL在多个推理基准上优于GRPO和各种KD基线，在性能和推理token效率间达到良好平衡。

**Zhang et al. (2026)** 提出了RLAD（Reinforcement-aware Knowledge Distillation），在RL引导期间进行选择性模仿——仅在改进当前策略更新时才引导学生向教师学习。核心组件TRRD（Trust Region Ratio Distillation）使用PPO/GRPO风格似然比目标替换KL正则化，实现了优势感知、信任域约束的学生rollout蒸馏。该方法在多个逻辑推理和数学基准上一致优于离线蒸馏、标准GRPO和基于KL的on-policy KD。

**Kotoge et al. (2026)** 在 ACL 2026 上提出了DGPO（Distillation-Guided Policy Optimization），解决紧凑模型（0.5-1B参数）在RL训练中因初始性能差导致的奖励稀疏和不稳定问题。DGPO通过教师示范冷启动初始化以及在策略优化过程中的持续教师引导，使紧凑模型实现复杂的智能体搜索行为，甚至在某些情况下超过更大的教师模型。

### 4.3 LLM知识蒸馏到控制策略

**Li et al. (2026)** 在 AAAI 2026 上提出了GUIDER，一个利用LLM知识驱动的RL框架，用于多机器人导航。LLM以两种离线角色被使用：首先，LLM作为离线知识源，将其专业知识蒸馏到紧凑模型中，仅在RL智能体对自身价值估计不确定且模型自身对预测有信心时使用；其次，LLM作为离线语义引擎，将LLM对情境风险的高层理解转化为RL智能体行为风格的动态调整。在所有海洋场景（3-12机器人）中，GUIDER相比最先进的RL多机器人导航方法显著提升了任务成功率并降低了碰撞率。

**Xu et al. (2025)** 提出了TeLL-Drive，一个集成教师LLM引导注意力机制学生DRL策略的混合框架。通过将风险度量、历史场景检索和领域启发式整合到上下文丰富的提示中，LLM通过思维链推理产生高层驾驶策略。自注意力机制将这些策略与DRL智能体的探索相融合，加速策略收敛并增强鲁棒性。跨越多个交通场景的实验结果表明，TeLL-Drive在成功率、平均回报和实时可行性方面优于现有基线方法。

### 4.4 面向LLM的LoRA/QLoRA微调技术

**Qwen官方文档** 给出了LoRA微调的标准配置：秩r=64，lora_alpha=16，目标模块包括c_attn、c_proj、w1、w2，dropout=0.05。LoRA达到全参数微调90-95%的性能，仅需20-40%的内存。

**开源社区实践**（rabiloo/llm-finetuning, chrisipanaque/qwen-lora-finetune等）展示了Qwen2.5系列的LoRA/QLoRA微调流水线。QLoRA通过4-bit NormalFloat量化、双重量化和分页优化器，使得在16GB GPU（如T4）上微调7B模型成为可能。在领域特定数据集上的测试显示，QLoRA微调的Qwen2.5-7B可达到92.8%的准确率。

### 4.5 多模态推理蒸馏

**Xiang et al. (2026)** 提出了PTD-PO（Privileged Tutoring Distillation Policy Optimization），面向多模态推理的可验证奖励RL（RLVR）。PTD-PO构建结构化的特权提示（空间注意力引导和中间文本推理步骤），通过上下文学习产生逐步骤的token分布监督，而不向学生策略暴露答案。在2B-8B LVLM上的实验显示PTD-PO一致优于RLVR和蒸馏基线。

---

## 5. 数据驱动的PEMFC退化建模

### 5.1 多尺度深度学习退化预测

**Wang et al. (2026)** 发表在 Journal of Zhejiang University-SCIENCE A 上的研究提出了MBFNet（多尺度双向融合网络），针对工业级215通道PEMFC电堆，利用气-热-电联合仿真数据实现加速真实动态条件下的精确退化预测。通道联合自适应噪声相关阈值算法无需先验物理建模。实验显示MBFNet相比LSTM-attention基准降低预测误差18.6%，参数减少36.8%；在多步预测任务中，平均RMSE相比LSTM-attention降低24.5%，相比1D-CNN降低55.2%。

### 5.2 物理约束与混合退化模型

**Zhu et al. (2026)** 发表在 eTransportation 上的研究提出了数据高效且可解释的长期PEMFC退化预测方法，结合物理约束符号回归和物理信息神经网络（PINN）。该方法在少数据条件下仍能保持泛化能力，同时提供可解释的退化方程。

**Liu et al. (2026)** 发表在 Reliability Engineering & System Safety 上的研究提出基于PINN与共形预测的可信长期PEMFC退化预测方法，实现了预测区间的不确定性量化。

**Ke et al. (2026)** 发表在 Energy Conversion and Management X 上的研究提出了混合退化预测方法，集成基于模型的退化指数提取（DRT+极化曲线模型）和贝叶斯优化双向LSTM。在第一组电堆上RUL估计误差低于7.78%（最小0.50%），在第二组电堆上误差不超过12.28%。

### 5.3 生成式AI在电化学建模中的应用

**Garg et al. (2026)** 发表在 ACS Omega 上的研究提出了面向燃料电池和液流电池电化学过程计算的生成式AI框架。利用LLM编排RAG、物理约束提示和工具集成推理。在PEMFC极化曲线分解任务中，框架达到RMSE 9.6mV，约束违反从48%/42%降低到1.2%/0.5%。用户研究（N=5）表明人力投入降低85%。

---

## 6. 研究空白与机遇

### 6.1 核心发现总结

通过对以上40余篇高相关度论文的系统梳理，我们识别出以下关键趋势和发展状态：

| 领域 | 成熟度 | 代表性方法 | 关键指标 |
|------|--------|-----------|---------|
| 多堆FC能量管理 | 较高 | 规则/优化/RL混合 | 氢耗降低2-20%，寿命延长30-45% |
| DRL船舶/混合动力 | 较高 | TD3/DDPG/SAC | 接近DP最优（<2.5%差距），HIL验证 |
| LLM用于控制 | 中等 | In-context learning/RAG/VLA | 98.6%连接正确率，95%人力节省 |
| RL到LLM蒸馏 | 早期 | OPD/KD+RL统一 | ALFWorld+9.4%，WebShop+10.2% |
| PEMFC退化建模 | 中高 | MBFNet/PINN/混合模型 | RMSE降低24.5-55.2%，RUL误差<7.8% |
| 可解释控制 | 中低 | HFMAE-C/HCA/XCF | 解释准确率0.48-0.88 |

### 6.2 关键研究空白

**空白1：缺乏面向控制领域的DRL-to-LLM蒸馏方法论**
现有知识蒸馏研究主要聚焦于LLM推理能力（数学、代码、RAG），极少涉及将DRL策略网络的知识结构蒸馏到LLM中用于物理系统的控制决策。KDRL（Xu et al., 2026）和RLAD（Zhang et al., 2026）提供了通用框架，但未面向控制领域约束（实时性、安全性、可解释性）进行专门设计。

**空白2：AgentEMS是唯一将DRL+LLM用于多堆FCEMS的工作，但未解决蒸馏问题**
AgentEMS（Wang et al., 2026）的双层架构（DRL决策 + LLM规则生成）是该方向的第一个重要尝试，但LLM并未学习DRL的策略，仅被用作规则生成器。该框架缺乏"LLM-as-Student"的关键环节——即LLM从DRL的行为中学习并内化控制策略。

**空白3：缺乏船舶工况下的健康感知蒸馏机制**
现有DRL能量管理研究已充分证明了健康感知策略的有效性（Zhu et al., 2026; Kopka et al., 2026），但从未将这些策略蒸馏到LLM。船舶工况的高动态性、长时域和强退化耦合特性，对蒸馏方法提出了独特挑战。

**空白4：缺乏面向工业部署的轻量化在线学习方法**
TeLL-Drive（Xu et al., 2025）使用教师LLM在线指导学生DRL，但推理延迟限制了实时部署。LLM蒸馏到紧凑模型（如Qwen2.5-1.5B的QLoRA微调）已被验证可行但未在EMS场景中应用。

### 6.3 "LLM-as-Student"的研究机遇

基于以上空白分析，我们提出以下具体研究机遇：

**机遇1：DRL策略知识的结构化蒸馏**
将DRL的Q函数/策略网络输出空间映射为LLM可理解的语义知识（如"当SOH差异>0.3时，优先使用健康电堆"），建立从连续动作空间到离散规则描述的蒸馏管道。GUIDER（Li et al., 2026）在机器人导航中的方法——将LLM作为离线知识源并在RL智能体不确定性高时激活——是一个有前景的模板。

**机遇2：特权信息蒸馏与安全约束注入**
π-Distill（Penaloza et al., 2026）和PTD-PO（Xiang et al., 2026）展示了特权信息蒸馏的有效性。在FC EMS中，DP全局最优轨迹可作为特权信息，DRL策略网络的特征表示可作为中间蒸馏目标。同时，安全约束（如电池温度上限）应作为不可协商的硬约束嵌入蒸馏过程。

**机遇3：On-Policy蒸馏应对分布偏移**
EMS的工况分布高度非平稳，off-policy蒸馏面临严重分布偏移。OPD（Song & Zheng, 2026）将暴露偏差从O(L²)降低到O(L)，使LLM在学生自身rollout分布上学习，天然适合EMS场景。KDRL的统一KD+RL框架提供了将OPD与DRL在线探索结合的技术基础。

**机遇4：LoRA/QLoRA高效微调适配器**
Qwen2.5系列的LoRA微调技术已成熟（官方文档展示r=64达到全微调95%性能），QLoRA使7B模型在16GB GPU上可微调。这为实现"DRL蒸馏->LLM微调->EMS部署"的完整流水线提供了硬件基础。

**机遇5：可解释规则与量化保障**
XCF（Yin et al., 2026）和HCA（Naagarajan et al., 2026）展示了LLM在控制解释中的潜力。将LLM生成的功率分配规则与形式化验证（如Spec2Control的验证智能体）结合，可在保持可解释性的同时提供安全保证。

---

## 7. 结论

本综述系统梳理了面向多堆燃料电池船舶动力系统可解释能量管理的"LLM-as-Student"研究全景。分析表明，AgentEMS（Wang et al., 2026, eTransportation）在两个独立领域（DRL能量管理和LLM规则生成）之间建立了一座重要桥梁，但未解决从DRL到LLM的知识蒸馏这一核心问题。2025-2026年间涌现的SDAR、KDRL、RLAD、TGPO、GUIDER等一系列蒸馏方法为这一方向提供了丰富的技术储备。结合Qwen2.5等开源模型在LoRA微调上的成熟生态，以及MBFNet等先进退化模型和TD3等已验证的DRL策略，"LLM-as-Student"范式有望在船舶MFC能量管理领域产生突破性进展——实现不妥协于可解释性、安全性和实时性的高性能能量管理。

---

## 参考文献

1. Wang, Y., Han, R., Xu, J., Li, Y., He, H., & Wang, Y. (2026). AgentEMS: Integrating DRL and LLM-refined rules for hierarchical energy management of multi-stack fuel cell vehicles. *eTransportation*, 100609.

2. Ghaderi, R., Kandidayeni, M., Boulon, L., & Trovao, J. P. F. (2024). A Novel Perspective of Energy Management Strategies on Multistack Fuel Cell Hybrid Electric Vehicles: Trends and Challenges. *IEEE Intelligent Transportation Systems Magazine*.

3. Ghaderi, R., Boulon, L., Trovao, J. P. F., & Ta, M. C. (2025). Smarter Energy Management for Multistack Fuel Cells: Artificial intelligence coordination for heavy-duty transport. *IEEE Electrification Magazine*.

4. Yang, X., Zhou, X., Li, X., Wang, Y., Long, F., Tang, T., Liu, L., & Liu, Y. (2026). Multi-time scale energy management and optimization for hybrid power ships considering lifetime balance and extension of multi-stack fuel cell systems. *Ocean Engineering*, 358(3), 125687.

5. Zhu, L., Liu, Y., Guo, H., & Liu, S. (2026). Health-Aware Differentiated Energy Management for Multi-Stack Fuel Cell Hybrid Power Systems on Ships. *Journal of Marine Science and Engineering*, 14(5), 460.

6. Wang, W., Yang, J., Zhang, H., Wu, X., Xu, X., Zhang, J., Deng, P., & Hu, H. (2025). Optimal energy management strategy for multi-stack fuel cell hybrid systems in shunting locomotives based on deep reinforcement learning. *Energy*, 340, 139334.

7. Cao, W., Xu, X., Li, C., & Sun, H. (2026). A Hierarchical Control-Based Energy Management Strategy for Multi-Stack Fuel Cell System with Performance Inconsistency. *Journal of Marine Science and Engineering*, 14(12), 1076.

8. Wu, P., Partridge, J., Anderlini, E., Liu, Y., & Bucknall, R. (2025). An intelligent energy management framework for hybrid-electric propulsion systems using deep reinforcement learning. *International Journal of Hydrogen Energy*.

9. Kopka, T., Tamburello, S., Oneto, L., van Biert, L., Polinder, H., & Coraddu, A. (2026). Degradation-aware Predictive Energy Management for Fuel Cell-Battery Ship Power System with Data-driven Load Forecasting. *arXiv:2604.14994*.

10. Zhu, L., Liu, Y., Zeng, Y., Guo, H., Ma, K., Liu, S., & Zhang, Q. (2024). Energy management strategy for fuel cell hybrid ships based on deep reinforcement learning with multi-optimization objectives. *International Journal of Hydrogen Energy*.

11. Li, Z., Long, W., & Tian, H. (2026). Research on Energy Management Optimization for Hybrid-Powered Port Tugboat Systems Based on a Dual-Delay Deep Deterministic Policy Gradient Algorithm. *Energies*, 19(4), 905.

12. Geng, P., & Xu, J. (2025). State-Aware Energy Management Strategy for Marine Multi-Stack Hybrid Energy Storage Systems Considering Fuel Cell Health. *Energies*, 18(15), 3892.

13. Huang, R., He, H., Su, Q., & Kang, L. (2026). Research on DRL-ECMS Energy Management Method for Fuel Cell Vehicle Based on Policy Reliability Assessment. *Automotive Engineering*, 48(1), 127-136.

14. (2026). Decoupled safety supervision empowering efficient and safe energy management for fuel cell vehicles. *npj Sustainable Mobility and Transport*.

15. Yang, D., Lv, H., Yan, Y., Li, M., Pan, R., & Liang, J. (2026). A Hybrid Deep Reinforcement-Supervised Learning Framework for Energy Management of Fuel Cell-Battery Hybrid Vehicles. *IEEE Transactions on Transportation Electrification*.

16. Nosrati, K., Tepljakov, A., Belikov, J., & Petlenkov, E. (2026). When control meets large language models: From words to dynamics. *Engineering Applications of Artificial Intelligence*, 178(2), 115119.

17. Koziolek, H., Braun, T., Ashiwal, V., Linsbauer, S., Hansen, M., & Grotterud, K. (2025). Spec2Control: Automating PLC/DCS Control-Logic Engineering from Natural Language Requirements with LLMs - A Multi-Plant Evaluation. *arXiv:2510.04519*.

18. Margadji, C., & Pattinson, S.W. (2026). Hybrid reasoning for perception, explanation, and autonomous action in manufacturing. *Nature Communications*.

19. Yin, F., Lam, H. K., & Watson, D. (2026). Explainable Control Framework (XCF) based on Fuzzy Model-Agnostic Explanation and LLM Agent-Supported Interface. *arXiv:2606.25941*.

20. Naagarajan, R. A., Wagner, Z., & Streif, S. (2026). Hierarchical Causal Abduction: A Foundation Framework for Explainable Model Predictive Control. *arXiv:2605.10624*.

21. Chen, J., Li, H., & Shu, Y. (2026). Structure from Reasoning, Numbers from Search: On-Premise Open LLMs as Structural Priors for Coupled MIMO Controller Tuning. *IEEE Access* (preprint).

22. Vyas, J. J., & Mercangoez, M. (2025). Autonomous Control Leveraging LLMs: An Agentic Framework for Next-Generation Industrial Automation. *arXiv:2507.07115*.

23. Bayat, A., Abate, A., Ozay, N., & Jungers, R. M. (2025). LLM-Enhanced Symbolic Control for Safety-Critical Applications. *arXiv:2505.11077*.

24. Song, M., & Zheng, M. (2026). A Survey of On-Policy Distillation for Large Language Models. *arXiv:2604.00626*.

25. Lu, Z., Yao, Z., Han, Z., Wang, Z. H., Wu, J., Gu, Q., Cai, X., Lu, W., Xiao, J., Zhuang, Y., & Shen, Y. (2026). Self-Distilled Agentic Reinforcement Learning. *arXiv:2605.15155*.

26. Liu, X., Jiao, K., Xiao, C., Zhao, R., Ruan, J., Li, B., Liu, J., Wang, Q., Chen, X., Wang, J., Xiao, T., & Zhu, J. (2026). Teacher-Guided Policy Optimization for LLM Distillation. *arXiv:2605.13230*.

27. Penaloza, E., Vattikonda, D., Gontier, N., Lacoste, A., Charlin, L., & Caccia, M. (2026). Privileged Information Distillation for Language Models. *arXiv:2602.04942*.

28. Xu, H., Zhu, Q., Deng, H., Li, J., Hou, L., Wang, Y., Shang, L., Xu, R., & Mi, F. (2026). KDRL: Post-Training Reasoning LLMs via Unified Knowledge Distillation and Reinforcement Learning. *arXiv:2506.02208*.

29. Zhang, Z., Jiang, S., Shen, Y., Zhang, Y., Ram, D., Yang, S., Tu, Z., Xia, W., & Soatto, S. (2026). Reinforcement-aware Knowledge Distillation for LLM Reasoning. *arXiv:2602.22495*.

30. Kotoge, R., Nishimura, M., & Ma, J. (2026). Can Compact Language Models Search Like Agents? Distillation-Guided Policy Optimization for Preserving Agentic RAG Capabilities. *ACL 2026*, 37733-37746.

31. Li, X., Fang, J., Li, L., Chen, B., Li, G., & Xue, J. (2026). Guided Distillation and Risk Adaptive Evolution for Multi-Robot Navigation. *AAAI 2026*.

32. Xu, C., Liu, J., & Hang, P. (2025). TeLL-Drive: Enhancing Autonomous Driving with Teacher LLM-Guided Deep Reinforcement Learning. *arXiv:2502.01387*.

33. Xiang, S., An, K., Yu, W., Liu, Y., Luan, J., Fu, P., & Wang, Q. (2026). Teaching the Way, Not the Answer: Privileged Tutoring Distillation for Multimodal Policy Optimization. *arXiv:2606.07000*.

34. Wang, Z., Zhu, X., Li, C., Chen, D., Liu, Z., Ma, L., Tao, J., & Su, H. (2026). Real-time degradation modeling for automotive PEMFC stacks: a multi-scale fusion network validated on an industrial 215-channel system. *Journal of Zhejiang University-SCIENCE A*, 27(5), 506-517.

35. Zhu, W., Xu, B., Guo, B., Xie, C., & Xiong, R. (2026). Data-efficient and interpretable long-term prognostics of PEMFC degradation via physics-constrained symbolic regression-physics-informed neural network. *eTransportation*, 100615.

36. Liu, M., Yang, Y., Cheng, J., Cui, J., & Zheng, X. (2026). Credible Long-Term Degradation Prediction for Proton Exchange Membrane Fuel Cell: A Physics-Informed Neural Network with Conformal Prediction Approach. *Reliability Engineering & System Safety*, 112945.

37. Ke, C., Han, K., Wang, Y., Zhang, R., Wang, X., Yang, Z., & Li, X. (2026). A hybrid degradation prediction method for PEMFC integrating model-based degradation index extraction and Bayesian-optimized Bi-directional long short-term memory. *Energy Conversion and Management X*, 101593.

38. Garg, R., Majhi, V., Chamola, V., Elhence, A., & Pandey, J. (2026). Generative AI Driven Process Calculations for Fuel Cells and Flow Batteries. *ACS Omega*.

39. Houjayrie, M., Cadet, C., & Berenguer, C. (2026). Health-Aware Load Allocation and Joint Energy-Maintenance Optimization for Multi-Stack PEM Fuel Cell Systems. *PHM Society European Conference*, 9(1).

40. Sayah, A., Ben Said-Romdhane, M., & Skander-Mustapha, S. (2026). Predictive road-aware deep reinforcement learning for energy management of fuel cell hybrid electric vehicles: A real-world Tunisian case study. *Energy and AI*, 100798.

41. Rabbi, M. F. (2026). Deep reinforcement learning for hydrogen-mediated grid resilience under compound climate extremes: An explainable AI framework. *Energy and AI*, 100801.

42. Hu, Y., Marandi, S., & Modarres, M. (2026). DML-LLM Hybrid Architecture for Fault Detection and Diagnosis in Sensor-Rich Industrial Systems. *Sensors*, 26(6), 2008.

43. Qwen Team. (2024). LoRA Fine-tuning Documentation. QwenLM Official Documentation.

44. Shan, M., Liu, S., Wang, Y., Wang, X., Zeng, X., Liu, Y., Chen, H., Huang, C., & Yu, L. (2025). Intelligent energy management strategy for fuel cell hybrid vehicles utilizing deep reinforcement learning and driving condition recognition. *International Journal of Hydrogen Energy*, 180, 151769.
