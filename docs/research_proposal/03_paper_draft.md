# Paper Draft: LLM-as-Student

> Generated: 2026-07-11 via ARIS academic-pipeline
> Status: Phase 2 — Draft Outline + Introduction + Related Work + Methodology

---

## One-Sentence Argument

> In multi-stack fuel cell marine power systems, we show that LLMs can serve as interpretable control policy executors by distilling knowledge from pre-trained deep reinforcement learning agents, supported by simulation experiments across multiple ship operating profiles, with the boundary that the approach is validated in simulation and requires hardware-in-the-loop testing before deployment.

---

## Title (working)

**LLM-as-Student: Distilling Interpretable Control Policies from Deep Reinforcement Learning for Multi-Stack Fuel Cell Marine Power Systems**

---

## Authors (TBD)

- Author 1 — corresponding author
- Author 2
- Author 3

---

## Abstract (to be drafted last)

*Placeholder — to be completed after results are obtained.*

---

## 1. Introduction

### Variant chosen: application-first

Opening with the concrete maritime application (zero-carbon shipping mandate) and the specific pain point (DRL black-box policies vs class-society interpretability requirements), then narrowing to the technical gap.

### Draft

**Paragraph 1 — Field stake (maritime decarbonization context)**

The International Maritime Organization's 2023 strategy targets a 40% reduction in carbon intensity by 2030 and net-zero greenhouse gas emissions by or around 2050, driving urgent adoption of zero-carbon propulsion technologies. Fuel cell systems have emerged as a leading candidate for deep-sea vessels, offering high efficiency and zero tailpipe emissions when powered by green hydrogen or methanol-reformed hydrogen [1,2]. However, the multi-megawatt power requirements of ocean-going ships necessitate multi-stack fuel cell configurations — arrays of 3–6 or more stacks operating in parallel — introducing a fundamentally more complex energy management problem than single-stack automotive systems.

**Paragraph 2 — Bottleneck in existing practice**

Conventional energy management strategies for multi-stack systems fall into two categories. Rule-based strategies (e.g., load-following, state-of-charge thresholds) are interpretable and computationally lightweight but degrade significantly as stacks age unevenly [3,4]. Optimization-based strategies (dynamic programming, Pontryagin's minimum principle, model predictive control) achieve near-optimal performance offline but require precise system models and substantial computational resources for online deployment [5,6]. Deep reinforcement learning (DRL) methods — particularly TD3 and PPO — have recently demonstrated superior performance across diverse operating conditions, achieving 5–10% hydrogen consumption reduction and 32% degradation reduction versus rule-based baselines [7,8,9]. Despite this performance, DRL policies operate as black-box neural networks, producing no human-readable justification for their control decisions.

**Paragraph 3 — Unresolved gap: the interpretability-adaptability dilemma**

This black-box nature creates a critical barrier for maritime deployment. Class societies (DNV, Lloyd's Register, China Classification Society) require verifiable, auditable control logic for safety-critical shipboard systems [10]. The tension between DRL's adaptability and its opacity has spurred interest in explainable AI for energy management. A notable recent advance, AgentEMS [11], addresses this by using a large language model (LLM) to refine control rules from dynamic programming trajectories, achieving a 45% reduction in fuel cell degradation. However, AgentEMS treats the LLM purely as an offline rule synthesizer: rules are generated once from DP trajectories and remain static thereafter. This static design cannot adapt to progressive stack degradation over a vessel's operational lifetime (60,000+ target hours [12]), nor does it leverage the rich exploration data that DRL policies accumulate during training.

**Paragraph 4 — Present study and contributions**

Here we introduce *LLM-as-Student*, a framework that fundamentally repositions the role of the LLM in fuel cell energy management — from offline rule refiner to direct control policy executor. Our approach operates in four phases: (i) a DRL teacher policy (PPO/TD3) is trained on multi-stack marine power system simulations; (ii) over 100,000 state-action trajectories from the teacher are filtered by Q-value and structured into natural language training examples pairing system states with control actions and reasoning; (iii) a small LLM (Qwen2.5-7B) is fine-tuned via LoRA on this corpus using a joint loss that penalizes both action deviation and explanation quality; (iv) the resulting LLM student directly outputs power allocation commands with accompanying natural language rationale, deployable without any DRL inference components.

This paradigm offers four advances over the state of the art: (1) the LLM executes control directly rather than refining rules, enabling adaptation through incremental fine-tuning as stacks degrade; (2) the DRL-to-LLM distillation framework is domain-agnostic and applicable to general RL-based control problems; (3) every control decision is accompanied by interpretable natural-language reasoning that satisfies class society audit requirements; and (4) the distilled LLM student requires only forward-pass inference, with lower computational overhead than DRL policy network evaluation.

---

## 2. Related Work

### 2.1 Multi-Stack Fuel Cell Energy Management

Multi-stack fuel cell systems (MFCS) have been extensively studied for high-power transportation applications including heavy-duty trucks, locomotives, and ships [13,14]. Ghaderi et al. [13] provide a comprehensive review of MFCS energy management strategies, noting the evolution from rule-based and optimization-based methods toward learning-based approaches. Zhu et al. [9] proposed a health-aware TD3 strategy that implements differentiated power allocation based on each stack's real-time state of health (SoH), demonstrating significant voyage cost reduction that increases with SoH disparity between stacks. Yang et al. [15] introduced a multi-timescale EMS for hybrid ships incorporating electrochemical surface area degradation models. Geng and Xu [16] combined GA-PSO with degradation-aware equivalent hydrogen consumption optimization, achieving 7.03g hydrogen savings per cycle over frequency-decoupling methods. Common across these studies is the recognition that *health-aware, adaptive control* is essential for practical MFCS deployment — yet none address the interpretability barrier for maritime certification.

### 2.2 Deep Reinforcement Learning for Marine Hybrid Propulsion

DRL methods have been increasingly applied to shipboard energy management. Wu et al. [7] applied TD3 to a coastal ferry with four fuel cell clusters, achieving voyage costs only 2.7% above uniform TD3 with 1.8% lower GWP emissions. Li et al. [17] demonstrated TD3 for a harbor tugboat series-hybrid methanol system, achieving <2.5% gap from DP optimal in hardware-in-the-loop tests. Kopka et al. [18] proposed degradation-aware predictive control with 15-minute load forecasting, reducing both hydrogen consumption by 5.8% and stack degradation by 36.4%. Liu et al. [19] integrated temporal convolutional networks with MPC for zero-carbon ship hybrid systems, achieving 24.9% operating cost reduction. Collectively, these studies validate DRL as a high-performance EMS approach for marine applications — but all inherit the interpretability limitation of neural network policies, which our work directly addresses through knowledge distillation.

### 2.3 LLMs for Control and Interpretable AI

The use of large language models for control tasks has emerged as a rapidly growing research frontier. Li et al. [20] proposed Spec2Control, achieving 98.6% correct automated control logic generation from natural language specifications. The CIPHER framework [21] demonstrated visual-language-action models for robotic manipulation with interpretable reasoning chains. XCF [22] introduced an explainable control framework using structured language representations. Most relevant to our work, AgentEMS [11] pioneered the combination of DRL with LLM-refined rules for multi-stack fuel cell energy management, using a prompt engineering mechanism to extract structured control knowledge from DP optimal trajectories. However, AgentEMS's LLM operates in a read-only offline capacity — it generates rules from pre-computed optimal trajectories but never executes control decisions directly or adapts online. Our work extends this paradigm by making the LLM the primary control executor, with the capacity for incremental online adaptation.

### 2.4 Knowledge Distillation from RL to Language Models

The intersection of reinforcement learning and language model distillation is an emerging area with several notable contributions. SDAR [23] achieved +9.4% improvement on ALFWorld benchmarks through selective distillation from RL teachers. KDRL [24] proposed a unified framework combining knowledge distillation with RL for efficient policy transfer. TGPO [25] introduced conditional teacher guidance for policy optimization, improving sample efficiency. In the autonomous driving domain, TeLL-Drive [26] demonstrated teacher LLMs guiding student DRL policies, while GUIDER [27] distilled LLM-based driving policies into compact neural networks for real-time deployment. Despite these advances, no existing work addresses the specific challenge of distilling DRL-based energy management policies into language models for interpretable control in safety-critical maritime applications — the gap that LLM-as-Student fills.

---

## 3. Methodology

### 3.1 Problem Formulation

We consider a marine power system comprising N fuel cell stacks (N = 3–6), a lithium-ion battery pack, and a DC bus connecting propulsion and auxiliary loads. The system operates over a voyage consisting of multiple segments (maneuvering, cruising, harbor idling, storm conditions), each with distinct power demand characteristics.

The energy management objective at each time step t is:

> min J = Σ_t [ m_H2(t) + λ₁·D_stack(t) + λ₂·(SOC(t)−SOC_ref)² ]

subject to:
- P_stack_i ∈ [P_min, P_max], ∀i ∈ [1,N]
- |P_stack_i(t+1) - P_stack_i(t)| ≤ ΔP_max (ramp rate constraint)
- SOC ∈ [SOC_min, SOC_max]
- Σ_i P_stack_i(t) + P_bat(t) = P_load(t)

where m_H2 is instantaneous hydrogen consumption, D_stack represents stack degradation cost, and SOC is battery state-of-charge.

### 3.2 Phase I: DRL Teacher Training

**State space** (dim = 3 + 4N):
- P_load (normalized propulsion load)
- SOC, SOC_ref (battery state)
- Per stack: SOH_i, T_i, V_i, I_i

**Action space** (dim = N):
- α_i ∈ [0,1], each stack's fraction of total stack power, with Σα_i = 1

We implement both PPO and TD3 as candidate teacher algorithms, selecting the better performer on validation metrics (convergence speed, final reward, policy smoothness). Training uses curriculum learning: the agent first learns on steady cruising segments, then progressively on more dynamic segments (maneuvering, storm), and finally on random segment sequences with varying initial SOH values.

**Reward function:**
> r(t) = -[ w₁·m_H2(t)/m_H2_max + w₂·ΣΔSOH_i/N + w₃·|SOC(t)-SOC_ref| + w₄·std(α_i·P_load/P_i_max) ]

### 3.3 Phase II: Experience Structuring

The trained teacher policy is rolled out across diverse operating conditions to generate a dataset of 100,000+ state-action pairs. Each trajectory is filtered by Q-value (retaining only the top 50% by estimated return) to ensure high-quality training data.

Each retained sample is structured into a natural language training pair:

```
Input (system state):
  "Vessel in cruising, load=340kW, SOC=62%,
   Stack1[SOH=0.95,T=65°C,V=48.2V,I=120A],
   Stack2[SOH=0.82,T=68°C,V=47.5V,I=95A],
   Stack3[SOH=0.88,T=63°C,V=48.0V,I=110A]"

Output (control decision + reasoning):
  "Allocate: Stack1=120kW, Stack2=80kW, Stack3=140kW.
   Reasoning: Stack2 has lower SOH; limiting its load
   to 80kW extends remaining lifetime. All stacks operate
   within their peak efficiency range (45-65% rated power)."
```

The dataset covers 4 voyage segment types × 5 SOH configurations × multiple load levels, with data augmentation (±5% noise) for robustness.

### 3.4 Phase III: LLM Student Fine-Tuning

**Base model:** Qwen2.5-7B-Instruct, selected for its strong bilingual capability and instruction-following performance.

**Fine-tuning method:** Low-Rank Adaptation (LoRA) with rank r=16, scaling α=32, applied to q_proj and v_proj attention layers. Training uses AdamW optimizer (lr=2e-4) with cosine scheduling and 3 epochs over the structured dataset.

**Joint loss function:**
> ℒ = α·ℒ_action + β·ℒ_explain

where ℒ_action = MSE(â, a) penalizes action deviation from the teacher, and ℒ_explain = CrossEntropy(ê, e) penalizes explanation quality. The weight β is progressively increased from 0.5 to 1.0 across training epochs to balance initial action learning with later explanation refinement.

### 3.5 Phase IV: Deployment

During deployment, the fine-tuned LLM student receives the current system state as a structured text prompt and outputs both the power allocation vector and a natural language rationale. No DRL policy network is required at inference time. For online adaptation, new state-action pairs from real operation can be used for incremental LoRA fine-tuning without full retraining.

**Inference pipeline:**
1. Sensor readings → structured state text (template)
2. LLM forward pass (∼100ms on consumer GPU, ∼500ms on CPU with 4-bit quantization)
3. Parse action from LLM output → power setpoints
4. Optionally log reasoning for class society audit

---

## Figures Plan (to be created)

- **Fig 1:** LLM-as-Student four-phase framework architecture diagram
- **Fig 2:** Representative marine voyage load profile (4 segment types)
- **Fig 3:** DRL teacher training convergence curves (PPO vs TD3)
- **Fig 4:** Main comparison bar chart (all methods × metrics)
- **Fig 5:** Generalization heatmap (unseen SOH × load combinations)
- **Fig 6:** Example LLM student output with reasoning visualization

---

## References (preliminary — to be expanded)

[1] IMO, "2023 IMO Strategy on Reduction of GHG Emissions from Ships," 2023.
[2] LR-GN-016, "Guidance Notes on the Installation of Fuel Cells on Ships," Lloyd's Register, 2025.
[3] Ghaderi et al., "Multi-Stack Fuel Cell Hybrid Electric Vehicles: A Review," IEEE ITSM, 2024.
[4] Cao et al., "Hierarchical Control EMS for MFCS Performance Inconsistency," JMSE, 2026.
[5] Feng et al., "Vectorized DP with Multi-time Scale Coordination," Energy, 2026.
[6] Zhou et al., "Degradation-Aware Energy Management for FC Hybrid Systems," 2022.
[7] Wu et al., "Intelligent EMS for Hybrid-Electric Propulsion Using DRL," IJHE, 2025.
[8] Yuan et al., "Six-stack tractor EMS with DDPG," Energy, 2025.
[9] Zhu et al., "Health-Aware Differentiated EMS for Multi-Stack FC Ships," JMSE, 2026.
[10] CCS, "Guidelines for Fuel Cell Systems on Ships," China Classification Society, 2024.
[11] Wang et al., "AgentEMS: DRL + LLM-Refined Rules for Multi-Stack FC Vehicles," eTransportation, 2026.
[12] LowEmission SP4, "Fuel Cells for Zero-Emission Heat and Power," 2025 Results.
[13] Ghaderi et al., "MFCS Energy Management Review," 2024.
[14] Tamjidillah et al., "Intelligent EMS and Hybrid Propulsion for Ships: A Review," IJMEIR, 2026.
[15] Yang et al., "Multi-timescale EMS for Hybrid Ships," Ocean Engineering, 2026.
[16] Geng & Xu, "State-Aware EMS for Marine Multi-Stack Systems," Energies, 2025.
[17] Li et al., "TD3 for Harbor Tugboat Hybrid System," Energies, 2026.
[18] Kopka et al., "Degradation-Aware Predictive EMS for FC-Ship," arXiv, 2026.
[19] Liu et al., "Dynamic Degradation-Aware Collaborative Control," IEEE Trans., 2025.
[20] Li et al., "Spec2Control: Automated Control Logic from NL Specifications," 2026.
[21] CIPHER, "Visual-Language-Action Models for Robotics," Nature Comms, 2026.
[22] XCF, "Explainable Control Framework with Language Representations," 2026.
[23] SDAR, "Selective Distillation from RL Teachers," 2025.
[24] KDRL, "Unified Knowledge Distillation + RL," 2025.
[25] TGPO, "Conditional Teacher Guidance for Policy Optimization," 2026.
[26] TeLL-Drive, "Teacher LLM Guiding Student DRL for Driving," 2026.
[27] GUIDER, "LLM→Compact Model Distillation for Navigation," 2026.

---

## Assumptions or Missing Inputs

| Item | Status | Action Needed |
|------|--------|--------------|
| Simulation results (comparison table) | Missing | After Week 9-10 experiments |
| DRL teacher vs TD3/PPO selection | Missing | After Week 5-6 training |
| LLM inference latency benchmarks | Missing | After Week 8 quantization |
| Hardware-in-the-loop validation | Out of scope | Future work |
| Real ship data for validation | Out of scope | Use NAUTILUS + TU Delft open data |
| Author names and affiliations | TBD | User to provide |
