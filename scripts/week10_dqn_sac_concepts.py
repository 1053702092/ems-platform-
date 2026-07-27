#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Week 10 — DQN / SAC 概念对照
=============================
Part 1: DQN — Q-Learning + 深度网络 + 经验回放 + 目标网络
Part 2: SAC — 最大熵 + Actor-Critic + 自动温度调节
Part 3: 为什么 EMS 选 PPO/SAC 而不是 DQN

学习目标：能讲清楚概念和面试表达，不做完整项目实现
"""

import numpy as np

# ============================================================
# Part 1: DQN (Deep Q-Network)
# ============================================================
def part1_dqn_concepts():
    """
    DQN = Q-Learning + 深度神经网络

    经典 Q-Learning 的更新公式:
      Q(s,a) ← Q(s,a) + α [ R + γ·max_a' Q(s',a') - Q(s,a) ]

    DQN 用神经网络 Q_θ(s,a) 近似 Q(s,a)，但直接这么用会出两个问题：
    """

    # ── 问题 1: 数据相关性（Data Correlation）──
    print("=" * 60)
    print("问题 1: 数据相关性")
    print("=" * 60)
    print("""
  在 RL 中，连续采集的 (s,a,r,s') 是高度相关的：
    智能体在状态 s₁ 走一步到 s₂，再走一步到 s₃...

  如果按顺序用这些数据训练神经网络，相当于：
    拿一张猫的图片训练 → 稍微变一点 → 又一张猫的图片 → 稍微变一点...
  网络会过拟合到最近的经验上，学不到通用知识。

  监督学习：随机打乱数据 → 样本独立同分布 ✅
  强化学习：连续采集 → 样本高度相关 ❌
    """)

    # ── 解决方案 1: 经验回放（Experience Replay）──
    print("=" * 60)
    print("解决方案 1: 经验回放 (Experience Replay)")
    print("=" * 60)
    print("""
  做法：把 (s,a,r,s') 存到一个大 buffer 里，训练时从中随机采样。

  好处：
  ① 打破数据相关性 — 随机采样的 (s,a,r,s') 之间不相关
  ② 数据利用率高 — 一条经验可以被多次使用（off-policy 的优势）
  ③ 平滑训练 — 减少单条极端经验对网络的影响

  类比：不是当场学，而是先记笔记（buffer），回头随机翻笔记学习。
    """)

    # 模拟经验回放
    np.random.seed(42)
    print("  [模拟] 经验回放 Buffer (capacity=10):")
    buffer = []
    for i in range(5):
        exp = (f"s_{i}", f"a_{i}", float(i),
               f"s_{i+1}", float(i % 2 == 0))
        buffer.append(exp)
    print(f"    Buffer 内经验: {len(buffer)} 条")
    batch = np.random.choice(len(buffer), size=3, replace=False)
    print(f"    随机采样 3 条: 索引 {batch}")
    print()

    # ── 问题 2: 训练目标不稳定 ──
    print("=" * 60)
    print("问题 2: 训练目标不稳定")
    print("=" * 60)
    print("""
  DQN 的损失函数:
    L(θ) = ( R + γ·max_a' Q_θ(s',a') ─ Q_θ(s,a) )²
              └───── target y ──────┘  └── prediction ──┘

  问题：target y 和 prediction 用的是同一个网络 Q_θ！
  每次更新 θ，target y 也跟着变 → 相当于"靶子一直在动"。
  就像射箭时靶子跟着箭跑→永远射不准。

  监督学习：标签是固定的 ✅
  DQN naive：标签随网络参数变化 ❌
    """)

    # ── 解决方案 2: 目标网络（Target Network）──
    print("=" * 60)
    print("解决方案 2: 目标网络 (Target Network)")
    print("=" * 60)
    print("""
  做法：维护两个网络
    Q_θ        — 在线网络（online），负责预测，频繁更新
    Q_θ_target — 目标网络（target），负责计算 target y，不频繁更新

  更新流程：
    ① 用目标网络计算 target: y = R + γ·max_a' Q_θ_target(s',a')
    ② 训练在线网络: L(θ) = (y - Q_θ(s,a))²
    ③ 每 C 步把 θ 复制给 θ_target（硬更新）
       或 每步软更新: θ_target ← τ·θ + (1-τ)·θ_target

  效果：目标网络固定一段时间不更新 → 靶子不动 → 训练稳定。
    """)

    print("  [模拟] 目标网络硬更新 (C=100):")
    print("    Step 1-99:  在线网络更新，目标网络冻结")
    print("    Step 100:    θ_target = θ  (把在线参数复制给目标)")
    print("    Step 101-199: 在线网络更新，目标网络冻结...")
    print()

    # ── DQN 完整算法 ──
    print("=" * 60)
    print("DQN 完整算法流程")
    print("=" * 60)
    print("""
  初始化 Q_θ（在线网络）和 Q_θ_target（目标网络，参数相同）
  初始化 ReplayBuffer D（容量 N）

  for episode in range(M):
      状态 s = env.reset()
      for t in range(T):
          # ε-greedy 探索
          if random() < ε:
              a = random_action()
          else:
              a = argmax_a Q_θ(s,a)

          s', r, done = env.step(a)
          D.push(s, a, r, s', done)     # 存经验

          if len(D) > batch_size:
              # 从 buffer 随机采样一个 batch
              batch = D.sample(batch_size)

              # 用目标网络计算 target
              target = r + γ·max_a' Q_θ_target(s',a') × (1-done)

              # 训练在线网络
              loss = MSE(Q_θ(s,a), target)
              loss.backward()
              optimizer.step()

          # 硬更新目标网络
          if episode % C == 0:
              Q_θ_target.load_state_dict(Q_θ.state_dict())

          s = s'
          if done: break
    """)

    print("  DQN 关键超参数:")
    print("    learning_rate   = 0.0001  (比监督学习小，RL 梯度噪声大)")
    print("    ε               = 1.0→0.01 (探索率，从全随机逐渐降低)")
    print("    buffer_capacity = 100000  (经验池容量)")
    print("    batch_size      = 64")
    print("    γ               = 0.99    (折扣因子)")
    print("    C               = 1000   (目标网络更新频率)")
    print()

    # ── DQN 的局限 ──
    print("=" * 60)
    print("DQN 的 3 个核心局限")
    print("=" * 60)
    print("""
  ① 只能处理离散动作
     DQN 输出每个动作的 Q 值，再取 argmax。如果有 1000 个连续动作值，
     你只能把它们离散化成 1000 个格子。EMS 的 P_fc 是连续值（0-30kW），
     离散化会丢失精度，而且动作越多输出层越大。

  ② max_a Q 会高估（overestimation bias）
     Q(s,a) 本身有估计误差，max 操作会放大正值 → 系统性地高估 Q 值。
     Double DQN 解决了这个问题（用一个网络选动作，另一个网络算 Q）。

  ③ 训练不稳定
     即使是 DQN + 目标网络 + 经验回放，训练波动仍然很大。
     连续动作空间下这个问题更严重。
    """)

    return {
        'key_concepts': ['Q-Learning', 'Experience Replay',
                         'Target Network', 'ε-greedy', 'Off-policy'],
        'limitations': ['Discrete only', 'Overestimation', 'Unstable'],
    }


# ============================================================
# Part 2: SAC (Soft Actor-Critic)
# ============================================================
def part2_sac_concepts():
    """
    SAC = 最大熵 RL + Actor-Critic + 自动温度调节

    SAC 是目前连续控制任务最主流的算法之一（另一个是 PPO）。
    """

    print("=" * 60)
    print("SAC — Soft Actor-Critic 核心思想")
    print("=" * 60)

    # ── 最大熵 RL ──
    print("\n" + "=" * 60)
    print("核心思想 1: 最大熵框架 (Max Entropy RL)")
    print("=" * 60)
    print("""
  标准 RL 的目标:
    max E[ Σ γᵗ · rᵗ ]              — 只最大化累积奖励

  最大熵 RL 的目标:
    max E[ Σ γᵗ · (rᵗ + α·H(π(·|sᵗ))) ]
        ↑           ↑
     累积奖励     策略熵（探索的奖励）

  熵 H(π(·|s)) = -Σ π(a|s)·log π(a|s)
    熵大 → 动作分布均匀 → 探索更多
    熵小 → 动作分布集中 → 确定性高

  α (温度系数) 控制"探索"和"利用"的平衡：
    α=0 → 标准 RL（完全利用，不奖励探索）
    α大 → 鼓励探索（即使奖励不高，只要动作多样就行）

  直觉：Agent 不仅要找到最优路径，还要在找到最优路径后"保持灵活"，
  不要变成一条确定的路线——万一环境变了还有备选方案。
    """)

    # ── Actor-Critic ──
    print("=" * 60)
    print("核心思想 2: Actor-Critic 架构")
    print("=" * 60)
    print("""
  Actor（策略网络 π_φ）：  告诉智能体该做什么动作          → π_φ(s)
  Critic（价值网络 Q_θ）：  评价这个动作好不好              → Q_θ(s,a)

  SAC 有 5 个网络（看起来多，但每个都很简单）：
    π_φ           — Actor，输出动作分布（均值 + 标准差）
    Q_θ1, Q_θ2    — 两个 Critic（Double Q，防止高估）
    Q_θ1_target   — 目标网络（延迟更新）
    Q_θ2_target   — 目标网络

  为什么要两个 Critic？
    取 min(Q1, Q2) 作为 Q 值估计，避免单网络高估。
         → 这叫 Clipped Double Q，是 SAC 稳定性的关键。
    """)

    # ── 自动温度调节 ──
    print("=" * 60)
    print("核心思想 3: 自动温度调节 (Auto Temperature)")
    print("=" * 60)
    print("""
  手动调 α 很麻烦——不同任务最优 α 不同。

  SAC 自动调 α 的方法：
    把 α 当作可训练参数，设一个目标熵 H_target（通常是 -dim_action），
    让 α 自动调整到"当前策略的熵 ≈ 目标熵"。

    如果策略太集中（H < H_target）→ 增大 α → 鼓励探索
    如果策略太分散（H > H_target）→ 减小 α → 专注利用

  不需要手动调参 ✅
    """)

    print("  [对比] SAC vs PPO 的温度参数:")
    print("    SAC: α 自动调节，不需要手设")
    print("    PPO: 用 clip 限制策略更新幅度，不需要熵系数（但也可以加）")
    print()

    # ── SAC 完整算法 ──
    print("=" * 60)
    print("SAC 完整算法流程（简化版）")
    print("=" * 60)
    print("""
  初始化 π_φ, Q_θ1, Q_θ2, Q_θ1_target, Q_θ2_target, α

  循环:
      采集一批经验: s → a ~ π_φ(s) → s', r → 存 buffer
      从 buffer 采样 batch

      # 更新 Critic（Double Q + 目标熵）
      target_v = min(Q_θ1_target(s',a'), Q_θ2_target(s',a')) - α·log π_φ(a'|s')
      target_q = r + γ·target_v
      loss_Q1 = MSE(Q_θ1(s,a), target_q)
      loss_Q2 = MSE(Q_θ2(s,a), target_q)

      # 更新 Actor（最大化 Q + 熵）
      loss_π = α·log π_φ(a|s) - min(Q_θ1(s,a), Q_θ2(s,a))
      loss_π = loss_π.mean()

      # 更新 α（自动温度调节）
      loss_α = -α·(log π_φ(a|s) + H_target).mean()

      # 软更新目标网络
      θ_target ← τ·θ + (1-τ)·θ_target
    """)

    results = {
        'key_concepts': ['Max Entropy', 'Actor-Critic',
                         'Double Q', 'Auto Temperature', 'Off-policy'],
        'strengths': ['Continuous action', 'Stable training',
                      'Auto exploration tuning', 'Sample efficient (off-policy)'],
    }

    print("\n  SAC 关键超参数:")
    print("    learning_rate = 0.0003")
    print("    α (初始)      = 0.2（自动调节）")
    print("    τ (软更新)    = 0.005")
    print("    buffer_size   = 1000000")
    print("    batch_size    = 256")
    print("    γ             = 0.99")

    return results


# ============================================================
# Part 3: 为什么 EMS 选 PPO/SAC 而不是 DQN
# ============================================================
def part3_ems_algorithm_choice():
    """
    面试重点：能讲清楚"为什么 EMS 项目选择 PPO 落地"
    """

    print("=" * 60)
    print("Part 3: EMS 算法选择分析")
    print("=" * 60)

    print("\n" + "-" * 60)
    print("1. EMS 问题的性质")
    print("-" * 60)
    print("""
  燃料电池 EMS 能量管理问题：
    状态 S  = [SOC, P_load]  (连续值)
    动作 A  = P_fc ∈ [0, 30] kW  (连续值)
    奖励 R  = -H₂(s,a) - penalty_on_SOC

  关键特征：
    • 动作空间是连续的（P_fc 可以取 0-30kW 之间任意值）
    • 状态空间连续的（SOC 0.2-0.9，负载连续变化）
    • 实时性要求高（控制器需要在毫秒级做出决策）

  → 连续动作空间 → 排除 DQN
    """)

    print("-" * 60)
    print("2. 算法对比表（面试核心）")
    print("-" * 60)
    print()

    header = f"{'对比维度':<20} {'DQN':<18} {'PPO':<18} {'SAC':<18}"
    print(header)
    print("-" * 74)

    rows = [
        ('动作空间', '离散 ❌', '连续 ✅', '连续 ✅'),
        ('算法类型', 'Value-based', 'Policy-based', 'Actor-Critic'),
        ('采样效率', 'Off-policy 高', 'On-policy 低', 'Off-policy 高'),
        ('训练稳定性', '不稳定 ⚠️', '稳定 ✅（clip）', '较稳定 ✅'),
        ('实现复杂度', '简单', '中等', '较复杂'),
        ('超参数敏感', '一般', '不敏感 ✅', '较敏感'),
        ('调参难度', '低', '中', '较高'),
        ('EMS适用性', '不适用 ❌', '推荐 ✅', '可用 ✅'),
    ]

    for row in rows:
        print(f"{row[0]:<20} {row[1]:<18} {row[2]:<18} {row[3]:<18}")

    print()
    print("-" * 60)
    print("3. 面试回答（30秒版）")
    print("-" * 60)
    print("""
  Q: "为什么你的 EMS 项目用 PPO 而不是 DQN？"

  A: "EMS 的核心决策变量是燃料电池功率 P_fc，它是一个 0-30kW 的连续值。
     DQN 只能处理离散动作，如果我把 P_fc 离散成比如 30 个档位，
     控制精度会损失，而且随着动作维度增加，DQN 的 Q 值输出层会爆炸。

     PPO 通过正态分布直接输出连续动作值，天生适合连续控制。
     而且 PPO 用 clipped surrogate objective 限制策略更新幅度，
     训练比 DQN 稳定得多，不需要目标网络、经验回放这些复杂组件。

     至于为什么不选 SAC——SAC 虽然采样效率更高（off-policy），
     但实现复杂度高、调参更敏感，在秋招时间线限制下，
     跑通 PPO 的闭环是更稳妥的选择。"
    """)

    print("-" * 60)
    print("4. 面试回答（2分钟版 — 技术面深挖）")
    print("-" * 60)
    print("""
  Q: "你觉得 DQN 还有什么问题？"

  A: "主要有三个问题：

     ① Overestimation Bias — DQN 用 max_a Q 计算 target，
        估计误差会被 max 放大，系统性地高估 Q 值。Double DQN 可以缓解，
        但不能完全消除。

     ② 训练不稳定 — 即使有目标网络和经验回放，DQN 的训练损失曲线
        仍然波动很大。在连续动作空间下这个问题更严重。

     ③ 无法输出随机策略 — DQN 本质是确定性策略（argmax_a Q），
        在需要探索的环境里表现不如 PPO/SAC 的随机策略。

     其实我们的 MPC 控制器和 PPO 有相似之处——MPC 在预测时域内
        做滚动优化，PPO 在策略空间内做约束优化。
        两者的共同点都是'不要一步走太远'。"
    """)

    print("-" * 60)
    print("5. EMS 用 DQN 的替代方案（可以提，表现知识广度）")
    print("-" * 60)
    print("""
  如果硬要用 DQN 做 EMS，可以怎么做？

  ① 动作离散化：把 P_fc [0,30]kW → {0, 5, 10, 15, 20, 25, 30} 共 7 档
     但精度损失大，可能跳过了最优功率点

  ② 参数化 DQN：用神经网络输出连续动作的参数（如均值），
     再用这个参数去环境里执行——但这已经不是标准 DQN 了

  ③ DQN 做上层调度 + PID 做底层执行：
     DQN 决定"充/放/保持"的离散模式，PID 负责实际功率跟踪
     这是工业界常见的 hybrid 方案

  但总体而言，PPO 或 SAC 是更自然的选择。"
    """)

    return {
        'choice': 'PPO',
        'reason': 'Continuous action, stable training, simpler than SAC',
        'interview_30s': 'DQN只能处理离散动作，EMS的P_fc是连续值',
    }


if __name__ == '__main__':
    print('\n' + '=' * 70)
    print('  Week 10 — DQN / SAC 概念对照')
    print('=' * 70)
    print('  [INFO] 此脚本只打印概念说明，不跑数值实验')
    print('  学习目标：能讲清楚为什么 EMS 选 PPO 而不是 DQN')
    print('=' * 70)

    print('\n' + '=' * 70)
    print('Part 1: DQN — 深度 Q 网络')
    print('=' * 70)
    part1_dqn_concepts()

    print('\n' + '=' * 70)
    print('Part 2: SAC — Soft Actor-Critic')
    print('=' * 70)
    part2_sac_concepts()

    print('\n' + '=' * 70)
    print('Part 3: EMS 算法选择分析')
    print('=' * 70)
    part3_ems_algorithm_choice()

    print('\n' + '=' * 70)
    print('  Week 10 完成 ✅')
    print('  核心记忆点：')
    print('    DQN = 离散动作 + 经验回放 + 目标网络')
    print('    SAC = 连续动作 + 最大熵 + 自动温度')
    print('    EMS选PPO = 连续动作 + 训练稳定 + 实现简单')
    print('=' * 70)
