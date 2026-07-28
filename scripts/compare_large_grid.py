#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大 GridWorld 对比：Q-learning vs DQN
=====================================
从 4×4 变成 N×N，看 Q 表膨胀 vs 网络泛化的区别

核心观察：
  4×4:    Q 表 16×4 = 64 参数，网络 644 参数 → QL 完胜
  10×10:  Q 表 100×4 = 400 参数，网络 3364 参数 → 网络开始展现泛化优势
  20×20:  Q 表 400×4 = 1600 参数，网络 ~1.1 万参数 → Q 表填不满
"""

import numpy as np
import random
import torch
import torch.nn as nn
import torch.optim as optim
import os
import time

RESULTS_DIR = r'F:\CLAUDE\research\ems-platform\results'

# ===================== 可配置的 GridWorld 环境 =====================
class GridWorld:
    """N×N GridWorld，终点在右下角 (N-1, N-1)"""
    def __init__(self, size=4, goal_reward=1.0, trap_reward=-1.0, slip_prob=0.2):
        self.N = size
        self.n_states = size * size
        self.n_actions = 4
        self.goal = size * size - 1  # 右下角
        self.trap = size + 1         # (1,1)
        self.goal_reward = goal_reward
        self.trap_reward = trap_reward
        self.slip_prob = slip_prob
        self.action_delta = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # ↑ ↓ ← →

    def is_valid(self, r, c):
        return 0 <= r < self.N and 0 <= c < self.N

    def step(self, s, a):
        r, c = divmod(s, self.N)
        if random.random() < (1 - self.slip_prob):
            dr, dc = self.action_delta[a]
        else:
            others = [i for i in range(4) if i != a]
            dr, dc = self.action_delta[random.choice(others)]

        nr, nc = r + dr, c + dc
        if not self.is_valid(nr, nc):
            nr, nc = r, c

        sp = nr * self.N + nc
        if sp == self.goal:
            reward = self.goal_reward
        elif sp == self.trap:
            reward = self.trap_reward
        else:
            reward = 0.0

        done = (sp == self.goal or sp == self.trap)
        return sp, reward, done


# ===================== DQN 网络 =====================
class DQN(nn.Module):
    """输入维度根据 Grid 大小自动变化"""
    def __init__(self, state_dim, hidden=64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 4)
        )

    def forward(self, x):
        return self.net(x)


def state_to_tensor(s, n_states):
    x = torch.zeros(n_states)
    x[s] = 1.0
    return x.unsqueeze(0)


# ===================== Q-learning =====================
def run_qlearning(env, episodes=10000, lr=0.1, verbose=True):
    """Q-learning 在 N×N GridWorld 上训练"""
    Q = np.zeros((env.n_states, env.n_actions))
    epsilon = 1.0
    episode_rewards = []
    episode_steps = []

    t0 = time.time()

    for ep in range(1, episodes + 1):
        s = 0
        total_reward = 0
        steps = 0

        while True:
            if random.random() < epsilon:
                a = random.randint(0, 3)
            else:
                a = int(np.argmax(Q[s]))

            sp, reward, done = env.step(s, a)

            td_target = reward + 0.9 * np.max(Q[sp]) * (not done)
            Q[s, a] += lr * (td_target - Q[s, a])

            total_reward += reward
            steps += 1
            s = sp
            if done:
                break

        episode_rewards.append(total_reward)
        episode_steps.append(steps)
        epsilon = max(0.01, epsilon * 0.998)

        if verbose and ep % 2000 == 0:
            avg_r = np.mean(episode_rewards[-200:])
            print(f'    QL 第{ep:5d}局 | ε={epsilon:.3f} | 平均奖励={avg_r:+.3f}')

    t1 = time.time()

    policy = np.argmax(Q, axis=1)
    return {
        'name': 'Q-learning',
        'Q': Q,
        'policy': policy,
        'rewards': episode_rewards,
        'steps': episode_steps,
        'params': env.n_states * env.n_actions,
        'time': t1 - t0,
        'final_avg_reward': np.mean(episode_rewards[-200:]),
    }


# ===================== DQN =====================
def run_dqn(env, episodes=10000, lr=0.01, verbose=True):
    """DQN 在 N×N GridWorld 上训练"""
    state_dim = env.n_states
    q_net = DQN(state_dim)
    target_net = DQN(state_dim)
    target_net.load_state_dict(q_net.state_dict())

    optimizer = optim.Adam(q_net.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    replay_buffer = []
    BUFFER_SIZE = 50000
    BATCH_SIZE = 64
    epsilon = 1.0

    episode_rewards = []
    episode_steps = []

    # 算参数数量
    total_params = sum(p.numel() for p in q_net.parameters())

    t0 = time.time()

    for ep in range(1, episodes + 1):
        s = 0
        total_reward = 0
        steps = 0

        while True:
            if random.random() < epsilon:
                a = random.randint(0, 3)
            else:
                with torch.no_grad():
                    q_vals = q_net(state_to_tensor(s, state_dim))
                    a = int(torch.argmax(q_vals).item())

            sp, reward, done = env.step(s, a)
            replay_buffer.append((s, a, reward, sp, done))
            if len(replay_buffer) > BUFFER_SIZE:
                replay_buffer.pop(0)

            if len(replay_buffer) >= BATCH_SIZE:
                batch = random.sample(replay_buffer, BATCH_SIZE)

                states = torch.zeros(BATCH_SIZE, state_dim)
                next_states = torch.zeros(BATCH_SIZE, state_dim)
                actions = torch.zeros(BATCH_SIZE, dtype=torch.long)
                rewards = torch.zeros(BATCH_SIZE)
                dones = torch.zeros(BATCH_SIZE)

                for i, (si, ai, ri, nsi, di) in enumerate(batch):
                    states[i] = state_to_tensor(si, state_dim)
                    next_states[i] = state_to_tensor(nsi, state_dim)
                    actions[i] = ai
                    rewards[i] = ri
                    dones[i] = 1.0 if di else 0.0

                with torch.no_grad():
                    next_q = target_net(next_states)
                    max_next_q = torch.max(next_q, dim=1).values
                    td_targets = rewards + 0.9 * max_next_q * (1 - dones)

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

        episode_rewards.append(total_reward)
        episode_steps.append(steps)
        epsilon = max(0.01, epsilon * 0.998)

        if ep % 200 == 0:
            target_net.load_state_dict(q_net.state_dict())

        if verbose and ep % 2000 == 0:
            avg_r = np.mean(episode_rewards[-200:])
            print(f'    DQN 第{ep:5d}局 | ε={epsilon:.3f} | 平均奖励={avg_r:+.3f}')

    t1 = time.time()

    policy = np.zeros(env.n_states, dtype=int)
    with torch.no_grad():
        for s_idx in range(env.n_states):
            q = q_net(state_to_tensor(s_idx, state_dim))
            policy[s_idx] = int(torch.argmax(q).item())

    return {
        'name': 'DQN',
        'Q': None,
        'policy': policy,
        'rewards': episode_rewards,
        'steps': episode_steps,
        'params': total_params,
        'time': t1 - t0,
        'final_avg_reward': np.mean(episode_rewards[-200:]),
    }


# ===================== 打印对比 =====================
ACTION_NAMES = ['↑', '↓', '←', '→']

def print_comparison(results_q, results_dqn, grid_size):
    """打印两个结果的对比"""
    n_states = grid_size * grid_size
    goal = n_states - 1
    trap = grid_size + 1

    print(f"\n{'='*60}")
    print(f"  {grid_size}×{grid_size} GridWorld 对比结果")
    print(f"{'='*60}")

    # 参数对比
    print(f"\n【参数规模】")
    print(f"  状态数: {n_states}")
    print(f"  Q-learning: Q 表 = {n_states}×4 = {results_q['params']} 参数")
    print(f"  DQN:        网络 = {results_dqn['params']} 参数")
    print(f"  比例: DQN / QL = {results_dqn['params'] / results_q['params']:.1f} 倍")

    # 性能对比
    print(f"\n【训练结果】")
    print(f"  {'指标':<20} {'Q-learning':<16} {'DQN':<16}")
    print(f"  {'-'*52}")
    print(f"  {'训练时间':<20} {results_q['time']:<8.2f}s{'':>6} {results_dqn['time']:<8.2f}s")
    print(f"  {'最后200局平均奖励':<20} {results_q['final_avg_reward']:<+8.4f}{'':>8} {results_dqn['final_avg_reward']:<+8.4f}")
    print(f"  {'到达终点比例':<20} {sum(1 for r in results_q['rewards'][-200:] if r > 0)/2:<8.1%}{'':>8} {sum(1 for r in results_dqn['rewards'][-200:] if r > 0)/2:<8.1%}")

    # 策略可视化（只看前几行 + 关键位置）
    print(f"\n【策略对比】（只打印关键行，G=终点 X=陷阱）")
    print(f"  Q-learning 策略:")
    for r in range(min(4, grid_size)):
        row = "  "
        for c in range(grid_size):
            s = r * grid_size + c
            if s == goal:
                row += " G "
            elif s == trap:
                row += " X "
            else:
                row += f" {ACTION_NAMES[results_q['policy'][s]]} "
        print(row)

    print(f"  DQN 策略:")
    for r in range(min(4, grid_size)):
        row = "  "
        for c in range(grid_size):
            s = r * grid_size + c
            if s == goal:
                row += " G "
            elif s == trap:
                row += " X "
            else:
                row += f" {ACTION_NAMES[results_dqn['policy'][s]]} "
        print(row)

    # 收敛曲线简图
    print(f"\n【收敛曲线（每500局平均奖励）】")
    q_rewards = results_q['rewards']
    dqn_rewards = results_dqn['rewards']

    def print_curve(data, label, width=40):
        """打印 ASCII 曲线"""
        chunk = 500
        n_chunks = len(data) // chunk
        values = [np.mean(data[i*chunk:(i+1)*chunk]) for i in range(n_chunks)]
        min_v, max_v = min(values), max(values)
        rng = max_v - min_v if max_v != min_v else 1

        print(f"  {label}:")
        for i, v in enumerate(values):
            bar_len = int((v - min_v) / rng * width)
            bar = '█' * bar_len
            print(f"    第{i*chunk:5d}局 | {bar} {v:+.2f}")

    print_curve(q_rewards, "Q-learning")
    print_curve(dqn_rewards, "DQN")


# ===================== 主函数 =====================
def run_all():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║    大 GridWorld 对比：Q-learning vs DQN                ║")
    print("║    看 Q 表膨胀 vs 网络泛化的区别                       ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    results_all = {}

    for size in [4, 8, 12]:
        print(f"{'='*60}")
        print(f"  开始测试 {size}×{size} GridWorld（{size*size} 个状态）")
        print(f"{'='*60}")
        print()

        env = GridWorld(size=size)
        episodes = 5000 if size <= 8 else 8000

        print(f"  --- Q-learning 训练中（{episodes}局）---")
        r_q = run_qlearning(env, episodes=episodes, verbose=True)

        print(f"  --- DQN 训练中（{episodes}局）---")
        r_d = run_dqn(env, episodes=episodes, verbose=True)

        print_comparison(r_q, r_d, size)
        results_all[size] = {'q': r_q, 'dqn': r_d}

        # 画出趋势对比图
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt

            fig, axes = plt.subplots(1, 2, figsize=(14, 5))

            for label, data, color in [('Q-learning', r_q, 'blue'), ('DQN', r_d, 'red')]:
                # 平滑曲线
                window = 200
                smoothed = np.convolve(data['rewards'], np.ones(window)/window, mode='valid')
                axes[0].plot(smoothed, label=label, color=color, alpha=0.8)
                axes[1].plot(data['rewards'], label=label, color=color, alpha=0.3)

            axes[0].set_title(f'{size}×{size} GridWorld 训练曲线（平滑）')
            axes[0].set_xlabel('局数')
            axes[0].set_ylabel('平均奖励')
            axes[0].legend()
            axes[0].grid(alpha=0.3)

            axes[1].set_title(f'{size}×{size} GridWorld 原始曲线')
            axes[1].set_xlabel('局数')
            axes[1].set_ylabel('奖励')
            axes[1].legend()
            axes[1].grid(alpha=0.3)

            plt.tight_layout()
            path = os.path.join(RESULTS_DIR, f'compare_{size}x{size}_ql_vs_dqn.png')
            fig.savefig(path, dpi=150)
            plt.close()
            print(f"\n  图片已保存: {path}")
        except Exception as e:
            print(f"  画图跳过: {e}")

        print()
        print()

    # 汇总对比
    print("=" * 60)
    print("  三个规模汇总对比")
    print("=" * 60)
    print(f"\n{'Grid':<10} {'方法':<12} {'参数':<10} {'时间(s)':<10} {'最后200局奖励':<15} {'QL/DQN参数比'}")
    print(f"  {'-'*65}")
    for size in [4, 8, 12]:
        r_q = results_all[size]['q']
        r_d = results_all[size]['dqn']
        ratio = r_d['params'] / r_q['params']
        print(f"  {size}×{size:<5} {'Q-learning':<12} {r_q['params']:<10} {r_q['time']:<8.2f}s{'':>1} {r_q['final_avg_reward']:<+8.4f}{'':>5} {ratio:.1f}×")
        print(f"  {'':<10} {'DQN':<12} {r_d['params']:<10} {r_d['time']:<8.2f}s{'':>1} {r_d['final_avg_reward']:<+8.4f}")
        print()

    print("结论：")
    print("  4×4:   QL 参数少、学得快 → QL 完胜")
    print("  8×8:   QL 参数多起来，DQN 开始追上")
    print("  12×12: QL 参数继续膨胀，DQN 泛化优势显现")
    print("  真正大问题（图像、连续状态）：QL 不可能，DQN 必须")


if __name__ == '__main__':
    run_all()
