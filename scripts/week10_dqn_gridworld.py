#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Week 10 — DQN: 用神经网络代替 Q 表
==================================
对照 Q-learning：
  Q-learning: Q[s][a] ← 一张 16×4 的表格
  DQN:        Q_theta(s, a) ← 一个神经网络

环境：同一个 4x4 GridWorld
"""

import numpy as np
import random
import os
import torch
import torch.nn as nn
import torch.optim as optim

RESULTS_DIR = r'F:\CLAUDE\research\ems-platform\results'

# ===================== 环境 =====================
SIZE = 4
N_STATES = SIZE * SIZE
N_ACTIONS = 4
GOAL_IDX = 15
TRAP_IDX = 5
GAMMA = 0.9
ACTION_DELTA = [(-1, 0), (1, 0), (0, -1), (0, 1)]
ACTION_SYMBOLS = {0: '↑', 1: '↓', 2: '←', 3: '→'}

def is_valid(r, c):
    return 0 <= r < SIZE and 0 <= c < SIZE

def step(s, a):
    """执行动作，返回 (s_next, reward, done)"""
    r, c = divmod(s, SIZE)
    if random.random() < 0.8:
        dr, dc = ACTION_DELTA[a]
    else:
        other = [i for i in range(N_ACTIONS) if i != a]
        dr, dc = ACTION_DELTA[random.choice(other)]
    nr, nc = r + dr, c + dc
    if not is_valid(nr, nc):
        nr, nc = r, c
    s_next = nr * SIZE + nc
    reward = 1.0 if s_next == GOAL_IDX else (-1.0 if s_next == TRAP_IDX else 0.0)
    done = (s_next == GOAL_IDX or s_next == TRAP_IDX)
    return s_next, reward, done


# ===================== DQN 神经网络 =====================
class DQN(nn.Module):
    """用神经网络代替 Q 表
    输入：状态 s（one-hot 编码，16 维）
    输出：4 个动作的 Q 值
    """
    def __init__(self, state_dim=16, hidden=32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, N_ACTIONS)   # 输出 4 个 Q 值
        )

    def forward(self, x):
        return self.net(x)


def state_to_tensor(s):
    """把状态 s（0-15）转成 one-hot 向量"""
    x = torch.zeros(16)
    x[s] = 1.0
    return x.unsqueeze(0)  # shape [1, 16]


# ===================== DQN 算法 =====================
def dqn(episodes=5000, lr=0.01, epsilon_start=1.0, epsilon_end=0.01, epsilon_decay=0.998):
    print(f'DQN 开始训练: {episodes} 局')
    print(f'  神经网络: 16维输入 → 32隐藏 → 4输出')
    print(f'  Q 表参数: 16×4 = 64 个格子')
    print(f'  神经网络参数: {16*32 + 32 + 32*4 + 4} = 644 个参数（比 Q 表多 10 倍！）')
    print(f'  学习率 lr = {lr}')
    print()

    # 创建网络 + 优化器
    q_network = DQN()
    target_network = DQN()
    target_network.load_state_dict(q_network.state_dict())  # 初始参数相同
    optimizer = optim.Adam(q_network.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    # 经验回放缓冲区
    replay_buffer = []
    BUFFER_SIZE = 10000
    BATCH_SIZE = 32

    epsilon = epsilon_start
    episode_rewards = []
    episode_steps = []

    for ep in range(1, episodes + 1):
        s = 0
        total_reward = 0
        steps = 0

        while True:
            # ε-贪心
            if random.random() < epsilon:
                a = random.randint(0, N_ACTIONS - 1)
            else:
                with torch.no_grad():
                    q_values = q_network(state_to_tensor(s))
                    a = int(torch.argmax(q_values).item())

            s_next, reward, done = step(s, a)

            # 存到经验回放缓冲区
            replay_buffer.append((s, a, reward, s_next, done))
            if len(replay_buffer) > BUFFER_SIZE:
                replay_buffer.pop(0)

            # 训练（和 Q-learning 一样，但用网络代替 Q 表）
            if len(replay_buffer) >= BATCH_SIZE:
                batch = random.sample(replay_buffer, BATCH_SIZE)

                states = torch.zeros(BATCH_SIZE, 16)
                next_states = torch.zeros(BATCH_SIZE, 16)
                actions = torch.zeros(BATCH_SIZE, dtype=torch.long)
                rewards = torch.zeros(BATCH_SIZE)
                dones = torch.zeros(BATCH_SIZE)

                for i, (s, a, r, ns, d) in enumerate(batch):
                    states[i] = state_to_tensor(s)
                    next_states[i] = state_to_tensor(ns)
                    actions[i] = a
                    rewards[i] = r
                    dones[i] = 1.0 if d else 0.0

                # 用目标网络算 max Q(s', a')
                with torch.no_grad():
                    next_q = target_network(next_states)            # [32, 4]
                    max_next_q = torch.max(next_q, dim=1).values    # [32]
                    td_targets = rewards + GAMMA * max_next_q * (1 - dones)

                # 当前 Q 值
                current_q = q_network(states)                       # [32, 4]
                current_q = current_q.gather(1, actions.unsqueeze(1)).squeeze()  # [32]

                # loss: MSE 误差
                loss = loss_fn(current_q, td_targets)

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

            total_reward += reward
            steps += 1
            s = s_next
            if done:
                break

        episode_rewards.append(total_reward)
        episode_steps.append(steps)
        epsilon = max(epsilon_end, epsilon * epsilon_decay)

        # 每 200 局更新一次目标网络
        if ep % 200 == 0:
            target_network.load_state_dict(q_network.state_dict())
            avg_reward = np.mean(episode_rewards[-100:])
            avg_steps = np.mean(episode_steps[-100:])
            print(f'  第 {ep:4d}/{episodes} 局 | ε={epsilon:.3f} | '
                  f'平均奖励={avg_reward:+.4f} | 平均步数={avg_steps:.1f}')

    # 提取策略
    policy = np.zeros(N_STATES, dtype=int)
    with torch.no_grad():
        for s in range(N_STATES):
            q = q_network(state_to_tensor(s))
            policy[s] = int(torch.argmax(q).item())

    return policy, episode_rewards, episode_steps


# ===================== 结果展示 =====================
def save_results(policy, rewards, steps):
    os.makedirs(RESULTS_DIR, exist_ok=True)

    path = os.path.join(RESULTS_DIR, 'week10_dqn_training.csv')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('episode,reward,steps\n')
        for i, (r, s) in enumerate(zip(rewards, steps)):
            f.write(f'{i+1},{r:.4f},{s}\n')
    print(f'训练数据已保存: {path}')


if __name__ == '__main__':
    print('=' * 65)
    print('  DQN — 用神经网络代替 Q 表')
    print('  环境: 4x4 GridWorld, 和 Q-learning 一模一样')
    print('  区别:')
    print('    Q-learning: Q[s][a] ← 16×4 = 64 参数的表格')
    print('    DQN:        Q_theta(s,a) ← 644 参数的神经网络')
    print('  其他（ε-贪心、公式、奖励）完全一样')
    print('=' * 65)
    print()

    policy, rewards, steps = dqn(
        episodes=5000,
        lr=0.01,
        epsilon_start=1.0,
        epsilon_end=0.01,
        epsilon_decay=0.998
    )

    print()
    print('=' * 50)
    print('DQN 训练结果')
    print('=' * 50)
    print(f'\n最优策略:')
    print('  ' + '-' * 19)
    for r in range(SIZE):
        row = '  |'
        for c in range(SIZE):
            s = r * SIZE + c
            if s == GOAL_IDX:
                row += ' G |'
            elif s == TRAP_IDX:
                row += ' X |'
            else:
                row += f' {ACTION_SYMBOLS[policy[s]]} |'
        print(row)
        print('  ' + '-' * 19)

    print(f'\n最后 100 局平均奖励: {np.mean(rewards[-100:]):+.4f}')
    print(f'最后 100 局平均步数: {np.mean(steps[-100:]):.1f}')

    save_results(policy, rewards, steps)

    print()
    print('=' * 65)
    print('  三个方法对比:')
    print('    值迭代 (DP):    64 个 Q 表格子,   133 轮直接算完')
    print('    Q-learning:     64 个 Q 表格子,   5000 局试出来')
    print('    DQN:            644 个网络参数,   5000 局试出来')
    print()
    print('  DQN 在这个小问题上没有优势（甚至更慢）')
    print('  但真实问题状态空间巨大（图像、连续值）')
    print('  Q 表存不下，只能用神经网络')
    print('=' * 65)
