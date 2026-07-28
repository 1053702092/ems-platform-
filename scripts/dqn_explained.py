#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DQN 逐行拆解 — 从 Q-learning 出发，改一行就是 DQN
====================================================
你不会的是"为什么 Q 表换成网络之后，训练方法也得变"对吧？
这个文件从你会的 Q-learning 代码出发，一步步改成 DQN。

结构：
  Part 1: Q-learning 复习（你会的）
  Part 2: Q 表 → 神经网络（核心改变）
  Part 3: 改完之后出了什么问题（两个坑）
  Part 4: 填坑 → 完整 DQN
  Part 5: 边跑边打印内部状态
"""

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import random
import os

RESULTS_DIR = r'F:\CLAUDE\research\ems-platform\results'

# =====================================================================
# 环境：4x4 GridWorld（和之前一样，确保你只用关注算法变化）
# =====================================================================
SIZE = 4
N_STATES = SIZE * SIZE
N_ACTIONS = 4
GOAL = 15
TRAP = 5
GAMMA = 0.9

# 动作：上(0) 下(1) 左(2) 右(3)
ACTION_DELTA = [(-1, 0), (1, 0), (0, -1), (0, 1)]
ACTION_NAMES = ['↑', '↓', '←', '→']

def is_valid(r, c):
    return 0 <= r < SIZE and 0 <= c < SIZE

def step(s, a):
    """和 Q-learning 完全一样的环境"""
    r, c = divmod(s, SIZE)
    if random.random() < 0.8:
        dr, dc = ACTION_DELTA[a]
    else:
        other = [i for i in range(N_ACTIONS) if i != a]
        dr, dc = ACTION_DELTA[random.choice(other)]
    nr, nc = r + dr, c + dc
    if not is_valid(nr, nc):
        nr, nc = r, c
    sp = nr * SIZE + nc
    reward = 1.0 if sp == GOAL else (-1.0 if sp == TRAP else 0.0)
    done = (sp == GOAL or sp == TRAP)
    return sp, reward, done


# =====================================================================
# PART 1: Q-learning 复习 — 一句话
# =====================================================================
def part1_qlearning_review():
    """你会的 Q-learning，核心就 3 行："""
    print("=" * 70)
    print("Part 1: Q-learning 复习")
    print("=" * 70)
    print("""
    Q = np.zeros((16, 4))        # ← Q 表
    for episode in range(5000):
        s = 0
        while not done:
            a = argmax Q[s]       # 查表
            sp, r, done = step(s, a)
            Q[s][a] += lr * (r + GAMMA * max(Q[sp]) - Q[s][a])  # 改表格的一个格子
    """)
    print("Q 表 = 16 行 × 4 列的数组，每行存一个状态的 4 个 Q 值。")
    print("更新 = 只改其中一格。")
    print()


# =====================================================================
# PART 2: 核心改变 — Q 表换成神经网络
# =====================================================================
class TinyDQN(nn.Module):
    """极简 DQN 网络

    输入：状态 s（整数 0-15），这里用 one-hot 编码（16 维）
    输出：4 个 Q 值（对应 ↑↓←→）

    和 Q 表的对照：
        Q 表：   Q[s][a] → 查 16×4 数组第 s 行第 a 列
        网络：   net(s)  → 前向传播算出 4 个值，取第 a 个
    """
    def __init__(self):
        super().__init__()
        # 一个隐藏层就够了，因为 GridWorld 很简单
        self.fc1 = nn.Linear(16, 32)   # 16维 → 32维
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(32, 4)    # 32维 → 4维（4个Q值）

    def forward(self, x):
        # x: 状态 s 的 one-hot 编码 [batch, 16]
        return self.fc2(self.relu(self.fc1(x)))

def state_to_onehot(s):
    """把状态 s（0-15）转成 one-hot 向量

    为什么用 one-hot？
        因为 16 个状态之间没有"大小关系"。
        格子 3 不是格子 2 的"一半"，所以不能用数字 0-15 直接输入网络。
        one-hot 告诉网络：每个状态是独立的类别。
    """
    x = torch.zeros(16)
    x[s] = 1.0
    return x.unsqueeze(0)  # shape [1, 16]，加 batch 维度


def part2_qtable_to_network():
    print("=" * 70)
    print("Part 2: Q 表 → 神经网络")
    print("=" * 70)

    print("\n【对照】Q 表和 DQN 网络存 Q 值的方式：")
    print()

    # --- Q 表版本 ---
    Q_table = np.zeros((N_STATES, N_ACTIONS))
    Q_table[0] = [0.1, 0.2, 0.3, 0.4]  # 格子0：↑=0.1, ↓=0.2, ←=0.3, →=0.4
    Q_table[1] = [0.5, 0.1, 0.2, 0.3]

    print("Q 表版本：")
    print(f"  Q[格子0] = {Q_table[0]}  ← 直接存 4 个数字")
    print(f"  Q[格子1] = {Q_table[1]}")
    print(f"  选动作: a = argmax Q[格子0] → →（因为 → 的 Q 值最大 = 0.4）")
    print()

    # --- 网络版本 ---
    net = TinyDQN()
    print("网络版本（刚初始化，还没训练）：")
    with torch.no_grad():
        q0 = net(state_to_onehot(0)).numpy()[0]
        q1 = net(state_to_onehot(1)).numpy()[0]
    print(f"  net(格子0) = {np.array_str(q0, precision=3)}  ← 网络算出来的 4 个值")
    print(f"  net(格子1) = {np.array_str(q1, precision=3)}")
    print(f"  选动作: a = argmax net(格子0) → 选 Q 值最大的那个动作")
    print()

    print("【关键理解】两种方式输出格式完全一样：都是 [Q↑, Q↓, Q←, Q→]")
    print("  不同的只是内部存储方式：")
    print("    Q 表：  直接查数组（64 个可调参数，每个格子独立）")
    print("    DQN：   网络前向传播（644 个参数共享，相邻状态互相影响）")
    print()

    # 展示共享参数的效果
    print("【网络的好处：泛化】")
    with torch.no_grad():
        for s in [0, 1, 4, 5]:
            q = net(state_to_onehot(s)).numpy()[0]
            print(f"  net(格子{s}) = {np.array_str(q, precision=3)}")
    print("  格子0和格子1、格子4的输出是相关的（参数共享），")
    print("  而 Q 表里格子0和格子1完全独立。")
    print()


# =====================================================================
# PART 3: 换网络之后出了什么问题（两个坑）
# =====================================================================
def part3_two_problems():
    print("=" * 70)
    print("Part 3: 换网络带来的两个大坑")
    print("=" * 70)

    print("""
    如果你直接把 Q 表换成网络，按 Q-learning 的方式训练：

        # Q-learning 的更新（改一个格子）：
        Q[s][a] += lr * (target - Q[s][a])

        # 你天真地改成网络版（梯度下降）：
        loss = MSE(net(s)[a], target)
        loss.backward()
        optimizer.step()

    这样改会出两个问题：""")

    print("━" * 50)
    print("坑 1：数据相关性 — 网络学不会（需要经验回放）")
    print("━" * 50)
    print("""
    Q-learning 用 Q 表时，样本是按顺序来的：
        格子0 → 格子4 → 格子5(Trap!) → 重置 → 格子0 → ...

    顺序数据对 Q 表没问题：每次只改一个格子，不受顺序影响。
    但网络一次更新所有参数，相邻的样本高度相关：
        - 连续 10 步都在格子0附近，网络就"过拟合"到格子0附近
        - 突然跳到格子10，网络反应不过来

    类比：你连续做 10 道"鸡兔同笼"，第 11 道改"相遇问题"脑子转不过来。
          如果 10 道题随机混着，你就能适应。

    解决：经验回放（Experience Replay）
        把经验存到缓冲区，训练时随机采样，打乱顺序。
    """)

    print("━" * 50)
    print("坑 2：目标不稳定 — 网络追自己尾巴（需要目标网络）")
    print("━" * 50)
    print("""
    Q-learning 的 target = r + GAMMA * max Q(sp)
    这里 Q 和 Q(s,a) 是同一个 Q 表。

    在 Q 表里，改一个格子对其他格子影响很小 → 没问题。

    但在网络里，一次梯度下降可能改变所有状态的输出！
        第 1 步：target = r + 0.9 * 0.5 = 0.95（Q_target(sp)=0.5）
        第 2 步：梯度下降更新 net，net 变了
        第 3 步：再用 net 算 max Q(sp)，发现变成了 0.7
                → 之前算的 target=0.95 现在不对了！
        第 4 步：再算新 target...
                → 永远追不上自己的尾巴！

    类比：你射箭，靶子绑在你的箭上。箭飞出去，靶子也跟着飞。

    解决：目标网络（Target Network）
        再复制一个网络专门算 target，它不频繁更新。
        这样 target 相对稳定，在线网络去追一个"不太会跑"的靶子。
    """)

    print("━" * 50)
    print("结论：DQN = Q-learning + 神经网络 + 经验回放 + 目标网络")
    print("━" * 50)
    print('  后面两个（经验回放、目标网络）都是因为"用神经网络"才需要的新技术。')
    print()


# =====================================================================
# PART 4: 完整 DQN（但加了巨多打印，让你看清每一步）
# =====================================================================

def dqn_verbose(episodes=200):
    """边训练边打印内部状态，让你看到网络学习的全过程"""

    print("=" * 70)
    print("Part 4: DQN 边跑边看（200 局）")
    print("=" * 70)

    # --- 初始化 ---
    q_net = TinyDQN()
    target_net = TinyDQN()
    target_net.load_state_dict(q_net.state_dict())  # 初始参数一样

    optimizer = optim.Adam(q_net.parameters(), lr=0.01)
    loss_fn = nn.MSELoss()

    replay_buffer = []
    BUFFER_SIZE = 1000
    BATCH_SIZE = 8  # 小一点，更容易看清

    epsilon = 1.0

    # 记录训练过程
    all_q_values = []  # 存每局开始的 Q 值，看变化

    for ep in range(1, episodes + 1):
        s = 0
        total_reward = 0
        steps = 0

        # --- 每 50 局打印一次网络的 Q 值 ---
        if ep % 50 == 1:
            print(f"\n第 {ep} 局开始前，各状态的 Q 值：")
            with torch.no_grad():
                for state in [0, 4, 8, 12]:
                    q = q_net(state_to_onehot(state)).numpy()[0]
                    best_a = int(np.argmax(q))
                    print(f"  格子{state:2d}: {np.array_str(q, precision=3)}  "
                          f"→ 选 {ACTION_NAMES[best_a]} (Q={q[best_a]:.3f})")
            print(f"  ε={epsilon:.3f}")
            print()

        episode_data = []

        while True:
            # --- 选动作 ---
            if random.random() < epsilon:
                a = random.randint(0, N_ACTIONS - 1)
                action_source = "随机"
            else:
                with torch.no_grad():
                    q_values = q_net(state_to_onehot(s))
                    a = int(torch.argmax(q_values).item())
                action_source = "网络"

            sp, reward, done = step(s, a)

            # 存到缓冲区
            replay_buffer.append((s, a, reward, sp, done))
            if len(replay_buffer) > BUFFER_SIZE:
                replay_buffer.pop(0)

            episode_data.append((s, a, reward, sp, done, action_source))

            # --- 训练 ---
            if len(replay_buffer) >= BATCH_SIZE:
                batch = random.sample(replay_buffer, BATCH_SIZE)

                # 整理 batch
                states = torch.zeros(BATCH_SIZE, 16)
                next_states = torch.zeros(BATCH_SIZE, 16)
                actions = torch.zeros(BATCH_SIZE, dtype=torch.long)
                rewards = torch.zeros(BATCH_SIZE)
                dones = torch.zeros(BATCH_SIZE)

                for i, (s_i, a_i, r_i, ns_i, d_i) in enumerate(batch):
                    states[i] = state_to_onehot(s_i)
                    next_states[i] = state_to_onehot(ns_i)
                    actions[i] = a_i
                    rewards[i] = r_i
                    dones[i] = 1.0 if d_i else 0.0

                # [核心] 用目标网络算 target
                with torch.no_grad():
                    next_q = target_net(next_states)
                    max_next_q = torch.max(next_q, dim=1).values
                    td_targets = rewards + GAMMA * max_next_q * (1 - dones)

                # [核心] 用在线网络算当前 Q 值
                current_q = q_net(states)
                current_q_a = current_q.gather(1, actions.unsqueeze(1)).squeeze()

                loss = loss_fn(current_q_a, td_targets)

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

            total_reward += reward
            steps += 1
            s = sp

            if done:
                break

        # --- 每局结束时打印这局的关键事件 ---
        if ep <= 5 or (ep <= 20 and ep % 5 == 0) or (ep <= 100 and ep % 20 == 0):
            # 打印这局的路径
            path_str = " → ".join([
                f"格{s}" if a_src != "随机" else f"格{s}(随机)"
                for s, a, r, sp, d, a_src in episode_data[:10]
            ])
            if len(episode_data) >= 10:
                path_str += " → ..."
            total_steps = len(episode_data)
            print(f"  第{ep:3d}局 | ε={epsilon:.3f} | 奖励={total_reward:+.1f} | "
                  f"{total_steps}步 | 路径: {path_str}")

            # 第 1 局额外显示一次更新细节
            if ep == 1 and len(replay_buffer) >= BATCH_SIZE:
                print(f"    【训练细节】batch_size={BATCH_SIZE}, replay_buffer大小={len(replay_buffer)}")
                print(f"    target = r + GAMMA * max(Q(sp))  （目标网络提供稳定的 target）")
                print(f"    loss = MSE(Q_net(s,a), target)")
                print(f"    ← 梯度下降更新所有 644 个参数")

        # 更新 epsilon
        epsilon = max(0.01, epsilon * 0.995)

        # 每 20 局更新目标网络
        if ep % 20 == 0:
            target_net.load_state_dict(q_net.state_dict())

            # 展示 Q 值的变化
            print(f"\n  >>> 第 {ep} 局结束，更新目标网络 <<<")
            with torch.no_grad():
                q_before = q_net(state_to_onehot(0)).numpy()[0]
                q_target = target_net(state_to_onehot(0)).numpy()[0]
                print(f"  格子0: 在线网络 Q={np.array_str(q_before, precision=3)}")
                print(f"         目标网络 Q={np.array_str(q_target, precision=3)}（← 同步了）")
            print()

    # --- 最终策略 ---
    print("\n" + "=" * 70)
    print("训练结束！最终策略：")
    print("=" * 70)

    policy = np.zeros(N_STATES, dtype=int)
    with torch.no_grad():
        for s in range(N_STATES):
            q = q_net(state_to_onehot(s))
            policy[s] = int(torch.argmax(q).item())

    for r in range(SIZE):
        row = "  |"
        for c in range(SIZE):
            s = r * SIZE + c
            if s == GOAL:
                row += " G |"
            elif s == TRAP:
                row += " X |"
            else:
                row += f" {ACTION_NAMES[policy[s]]} |"
        print(row)
        print("  " + "-" * 19)

    return policy


# =====================================================================
# PART 5: Q-learning vs DQN 实时对比（同一环境，同一局）
# =====================================================================
def part5_side_by_side():
    """同一个环境、同一步，看 Q 表和网络怎么不同"""
    print("=" * 70)
    print("Part 5: Q-learning vs DQN 实时对比")
    print("=" * 70)
    print("让 Q-learning 和 DQN 同时走同一局，看它们的 Q 值有什么不同。")
    print()

    # Q-learning 的 Q 表
    Q = np.zeros((N_STATES, N_ACTIONS))
    lr_q = 0.1

    # DQN 的网络
    q_net = TinyDQN()
    target_net = TinyDQN()
    target_net.load_state_dict(q_net.state_dict())
    optimizer = optim.Adam(q_net.parameters(), lr=0.01)
    loss_fn = nn.MSELoss()

    replay_buffer = []
    epsilon = 1.0
    BUFFER_SIZE = 500
    BATCH_SIZE = 8

    # 固定随机种子，让两个方法走同样的路
    random.seed(42)

    print("准备就绪！下面打印第 1 局、第 10 局、第 50 局的内部状态对比。")
    print()

    compare_eps = {1, 10, 50, 100}

    for ep in range(1, 101):
        s = 0
        done = False

        while not done:
            # 两个方法用同一个 ε
            if random.random() < epsilon:
                a = random.randint(0, N_ACTIONS - 1)
            else:
                # Q-learning 查表
                a_q = int(np.argmax(Q[s]))
                # DQN 跑网络
                with torch.no_grad():
                    q_vals = q_net(state_to_onehot(s)).numpy()[0]
                a_dqn = int(np.argmax(q_vals))
                a = a_q  # 两个方法选同一个动作（Q-learning 的），公平比较

            sp, reward, done = step(s, a)

            # --- Q-learning 更新 ---
            td_error = reward + GAMMA * np.max(Q[sp]) - Q[s][a]
            Q[s][a] += lr_q * td_error

            # --- DQN 更新 ---
            replay_buffer.append((s, a, reward, sp, done))
            if len(replay_buffer) > BUFFER_SIZE:
                replay_buffer.pop(0)

            if len(replay_buffer) >= BATCH_SIZE:
                batch = random.sample(replay_buffer, BATCH_SIZE)

                states = torch.zeros(BATCH_SIZE, 16)
                next_states = torch.zeros(BATCH_SIZE, 16)
                actions = torch.zeros(BATCH_SIZE, dtype=torch.long)
                rewards = torch.zeros(BATCH_SIZE)
                dones = torch.zeros(BATCH_SIZE)

                for i, (si, ai, ri, nsi, di) in enumerate(batch):
                    states[i] = state_to_onehot(si)
                    next_states[i] = state_to_onehot(nsi)
                    actions[i] = ai
                    rewards[i] = ri
                    dones[i] = 1.0 if di else 0.0

                with torch.no_grad():
                    next_q = target_net(next_states)
                    max_next_q = torch.max(next_q, dim=1).values
                    td_targets = rewards + GAMMA * max_next_q * (1 - dones)

                current_q = q_net(states)
                current_q_a = current_q.gather(1, actions.unsqueeze(1)).squeeze()

                loss = loss_fn(current_q_a, td_targets)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

            s = sp

        epsilon = max(0.01, epsilon * 0.97)

        if ep % 20 == 0:
            target_net.load_state_dict(q_net.state_dict())

        # 在指定局数打印对比
        if ep in compare_eps:
            print(f"第 {ep} 局结束后的 Q 值对比（格子 0, 4, 8）:")
            print(f"{'状态':>6} | {'Q-learning Q[↑ ↓ ← →]':<30} | {'DQN Q[↑ ↓ ← →]':<30}")
            print("-" * 75)
            for state in [0, 4, 8, 12]:
                q_q = Q[state]
                with torch.no_grad():
                    q_dqn = q_net(state_to_onehot(state)).numpy()[0]
                best_q = ACTION_NAMES[int(np.argmax(q_q))]
                best_dqn = ACTION_NAMES[int(np.argmax(q_dqn))]
                print(f"  格子{state} | "
                      f"{np.array_str(q_q, precision=3):<30} "
                      f"→ {best_q}  | "
                      f"{np.array_str(q_dqn, precision=3):<30} "
                      f"→ {best_dqn}")
            print(f"  Q 表大小: 64 个参数 | DQN: 644 个参数")
            print()

    print("对比结论：")
    print("  1. 在小问题（GridWorld）上，Q-learning 学得更快（参数少，直接改）")
    print("  2. DQN 虽然参数多，但学到的策略应该差不多")
    print("  3. DQN 的价值在真正的大问题（图像、连续状态）上才体现")
    print()


# =====================================================================
# PART 6: 亲手调参数 — 看看 DQN 内部到底在干嘛
# =====================================================================
def part6_peek_inside():
    """用极简的设定，让你手动追踪 DQN 的一步更新"""
    print("=" * 70)
    print("Part 6: DQN 一步更新的完整流程追踪")
    print("=" * 70)

    # --- 初始化一个极简场景 ---
    q_net = TinyDQN()
    target_net = TinyDQN()
    target_net.load_state_dict(q_net.state_dict())

    print("\n【设定】")
    print("  状态 s = 0（左上角），动作 a = 3（→），走到 sp = 1")
    print("  奖励 r = 0（没到终点），done = False")
    print()

    s, a, r, sp, done = 0, 3, 0.0, 1, False

    # --- 第 1 步：网络前向传播，看 Q 值 ---
    with torch.no_grad():
        q_s = q_net(state_to_onehot(s)).numpy()[0]
        q_sp = q_net(state_to_onehot(sp)).numpy()[0]
        q_target_sp = target_net(state_to_onehot(sp)).numpy()[0]

    print("【第 1 步：网络前向传播（和查 Q 表一样）】")
    print(f"  net(格子{s}) = {np.array_str(q_s, precision=3)}")
    print(f"    Q(格子{s}, →) = {q_s[3]:.4f}  ← 我们要更新这个值")
    print(f"  net(格子{sp}) = {np.array_str(q_sp, precision=3)}")
    print(f"    max Q(格子{sp}) = {np.max(q_sp):.4f}  （选 Q 值最大的动作）")
    print()

    # --- 第 2 步：算 target ---
    target = r + GAMMA * np.max(q_target_sp)
    print("【第 2 步：算 target（用目标网络！不是在线网络）】")
    print(f"  目标网络 net_target(格子{sp}) = {np.array_str(q_target_sp, precision=3)}")
    print(f"  max Q_target(格子{sp}) = {np.max(q_target_sp):.4f}")
    print(f"  target = r + GAMMA × max_Q_target(sp)")
    print(f"         = {r} + {GAMMA} × {np.max(q_target_sp):.4f}")
    print(f"         = {target:.4f}")
    print()

    # --- 第 3 步：算 loss ---
    current_q_val = q_s[a]
    loss = (current_q_val - target) ** 2
    print("【第 3 步：算 loss（均方误差 MSE）】")
    print(f"  当前 Q(s,a) = Q(格子{s}, →) = {current_q_val:.4f}")
    print(f"  target = {target:.4f}")
    print(f"  误差 = target - Q(s,a) = {target - current_q_val:.4f}")
    print(f"  loss = (target - Q(s,a))**2 = {loss:.4f}")
    print()

    print("【第 4 步：梯度下降（更新所有参数！）】")
    print(f"  🔑 Q-learning: Q[{s}][{a}] += lr × (target - Q[{s}][{a}]) = 改 1 个格子")
    print(f"  🔑 DQN:        loss.backward() + optimizer.step() = 改全部 644 个参数")
    print()
    print("  这次更新后，不只是格子0的Q(→)变了，")
    print("  格子1、格子4、格子8...所有状态的 Q 值都可能变了！")
    print("  （因为参数共享——这是网络的好处，也是训练的难点）")
    print()

    # --- 实际做一次更新 ---
    states = state_to_onehot(s)  # [1, 16]
    next_states = state_to_onehot(sp)

    with torch.no_grad():
        next_q = target_net(next_states)
        max_next_q = torch.max(next_q, dim=1).values
        td_target = r + GAMMA * max_next_q

    current_q = q_net(states)
    current_q_a = current_q.gather(1, torch.tensor([[a]]))

    loss_fn = nn.MSELoss()
    loss_val = loss_fn(current_q_a.squeeze(), td_target)

    optimizer = optim.Adam(q_net.parameters(), lr=0.01)
    optimizer.zero_grad()
    loss_val.backward()

    # 看看梯度
    print("【梯度信息：每个参数要改多少】")
    total_grad = 0
    for name, param in q_net.named_parameters():
        grad = param.grad
        if grad is not None:
            g_norm = torch.norm(grad).item()
            total_grad += g_norm
            print(f"  {name}: 梯度范数 = {g_norm:.6f}（{grad.numel()} 个参数）")
    print(f"  总梯度范数 = {total_grad:.6f}")
    print(f'  物理意义: 644 个参数同时往【让 Q(格子0,右箭头) 更接近 target】的方向调整')

    optimizer.step()

    # --- 更新后看看变化 ---
    with torch.no_grad():
        q_s_after = q_net(state_to_onehot(s)).numpy()[0]
        q_sp_after = q_net(state_to_onehot(sp)).numpy()[0]

    print()
    print("【第 5 步：更新后的 Q 值】")
    print(f"  Q(格子0, →) 更新前: {current_q_val:.4f}")
    print(f"  Q(格子0, →) 更新后: {q_s_after[3]:.4f}")
    print(f"  变化: {q_s_after[3] - current_q_val:+.4f}")
    print()
    print(f"  注意格子{sp}的 Q 值也变了（因为参数共享）：")
    print(f"    Q(格子{sp}, →) 更新前: {q_sp[3]:.4f}")
    print(f"    Q(格子{sp}, →) 更新后: {q_sp_after[3]:.4f}")
    print(f"    变化: {q_sp_after[3] - q_sp[3]:+.4f}")
    print()

    print("【这就是 DQN 的核心直觉】")
    print("  一次更新 = 644 个参数同时微调")
    print("  → 网络学会「泛化」：学过格子0，格子1、格子4...也跟着变好")
    print("  → 但也更难训练：一步更新可能让某些状态变差（所以需要经验回放和目标网络）")
    print()


# =====================================================================
# 主函数
# =====================================================================
if __name__ == '__main__':
    print()
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║    DQN 逐行拆解 — 从 Q-learning 出发               ║")
    print("  ║    不理解的地方，看 Part 6 最清楚                   ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print()

    # 可以单独跑每一部分
    part1_qlearning_review()
    part2_qtable_to_network()
    part3_two_problems()

    # Part 4 跑 200 局 DQN，看训练过程
    dqn_verbose(episodes=200)

    # Part 5 对比 Q-learning 和 DQN
    part5_side_by_side()

    # Part 6 手动追踪一步更新
    part6_peek_inside()

    print()
    print("=" * 70)
    print("总结：DQN 到底改了啥？")
    print("=" * 70)
    print("""
    从 Q-learning 到 DQN 只改了 3 件事：

    1️⃣  Q 表 → 神经网络  (Part 2)
        查表变前向传播，改格子变梯度下降

    2️⃣  加经验回放缓冲区  (Part 3 — 坑1)
        解决顺序数据让网络过拟合的问题

    3️⃣  加目标网络  (Part 3 — 坑2)
        解决训练目标不稳定、网络追自己尾巴的问题

    其他所有东西（ε-贪心、奖励函数、贝尔曼公式）完全没变！

    所以说：DQN = Q-learning + 神经网络 + 经验回放 + 目标网络
                      ↑ 核心改动      ↑ 填坑1       ↑ 填坑2
    """)
