#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Week 11 Step 2: REINFORCE (策略梯度)
======================================
从 DQN 到策略梯度的跨越：

  DQN:       Q(s) → 4 Q 值 → argmax → 离散动作 ↑↓←→
  REINFORCE:  π(s) → [μ, σ] → 采样 → 连续动作 P_fc

核心公式：∇J = E[ ∇log π(a|s) × G ]
  好动作 → 增大概率，坏动作 → 减小概率
"""

import argparse
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torch.distributions as dist

from week11_common import configure_matplotlib, ensure_results_dir, set_seed

configure_matplotlib()

# ===================== 环境（复用 Step 1） =====================
class EMSEnv:
    def __init__(self):
        self.soc_min = 0.2
        self.soc_max = 0.9
        self.state_dim = 2
        self.action_dim = 1
        self.battery_capacity = 50
        self.reset()

    def reset(self):
        self.soc = 0.6
        self.p_load = 0.5
        self.steps = 0
        self.max_steps = 200
        return np.array([self.soc, self.p_load], dtype=np.float32)

    def step(self, action):
        p_fc = float(np.clip(action, 0, 1)) * 30.0
        self.p_load = 0.3 + 0.4 * (0.5 + 0.5 * np.sin(self.steps * 0.1))
        power_diff = p_fc - self.p_load
        soc_change = power_diff / self.battery_capacity
        self.soc = np.clip(self.soc + soc_change, self.soc_min, self.soc_max)

        fuel_cost = -0.01 * p_fc
        soc_penalty = -0.5 * (self.soc - 0.6) ** 2
        soc_bound_penalty = -1.0 if (self.soc <= self.soc_min or self.soc >= self.soc_max) else 0.0
        reward = fuel_cost + soc_penalty + soc_bound_penalty

        self.steps += 1
        done = (self.steps >= self.max_steps or
                self.soc <= self.soc_min or self.soc >= self.soc_max)
        return self._get_state(), reward, done, {'p_fc': p_fc}

    def _get_state(self):
        return np.array([self.soc, self.p_load], dtype=np.float32)


# ===================== Policy Network =====================
class PolicyNet(nn.Module):
    """
    策略网络 π_θ(s) → [μ, σ]
    和 DQN 的区别：
      DQN 输出 Q 值（每个动作一个值）
      策略网络输出动作分布的参数（μ 和 σ）
    """
    def __init__(self, state_dim=2, hidden=64, action_dim=1):
        super().__init__()
        self.fc1 = nn.Linear(state_dim, hidden)
        self.fc2 = nn.Linear(hidden, hidden)
        # 输出层分成两路：均值 μ + 对数标准差 log_std
        self.mean_head = nn.Linear(hidden, action_dim)
        self.log_std = nn.Parameter(torch.zeros(action_dim))  # 可训练的标准差

    def forward(self, x):  
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        mean = torch.tanh(self.mean_head(x))  # tanh → [-1, 1]
        mean = (mean + 1) / 2  # 映射到 [0, 1]
        std = torch.exp(self.log_std.clamp(-5, 2))  # 保证正数
        return mean, std

    def get_action(self, state):
        """选动作：从策略分布中采样"""
        with torch.no_grad():
            s = torch.FloatTensor(state).unsqueeze(0)
            mean, std = self.forward(s)
            m = dist.Normal(mean, std)
            a = m.sample()
            a = a.clamp(0, 1)
            return a.item(), (state.copy(), a.item())

    def evaluate(self, state, action):
        """给定状态和动作，算 log_prob（用于训练时计算 loss，有梯度）"""
        mean, std = self.forward(state)
        m = dist.Normal(mean, std)
        log_prob = m.log_prob(action)
        return log_prob


# ===================== REINFORCE 算法 =====================
def reinforce(episodes=500, lr=0.001):
    """
    REINFORCE 算法

    每局流程：
      1. 用当前策略 π_θ 跑完一局
      2. 记录每一步的 (s, a, log_prob, reward)
      3. 从后往前算 G_t = 未来奖励总和
      4. loss = -Σ log_prob(a|s) × G_t
      5. 梯度下降更新 θ
    """
    env = EMSEnv()
    policy = PolicyNet()
    optimizer = optim.Adam(policy.parameters(), lr=lr)

    episode_rewards = []
    episode_lengths = []

    print(f"REINFORCE 开始训练: {episodes} 局")
    print(f"  策略网络: {2}维状态 → {64}隐藏 → [μ, σ] → 采样动作")
    print(f"  学习率 lr = {lr}")
    print()

    for ep in range(1, episodes + 1):
        s = env.reset()
        log_probs = []
        rewards = []
        done = False

        transitions = []  # 存 (状态, 动作, 奖励)

        # ---- 1. 跑一局，记录 (s, a, r) ----
        while not done:
            a, trace = policy.get_action(s)
            s_a, a_val = trace
            sp, reward, done, _ = env.step(a)
            transitions.append((s_a, a_val, reward))
            rewards.append(reward)
            s = sp

        # ---- 2. 算 G_t（从后往前累加）----
        G = 0
        returns = []
        for r in reversed(rewards):
            G = r + 0.99 * G
            returns.insert(0, G)

        returns_t = torch.FloatTensor(returns)

        # ---- 3. 标准化 G_t（减均值÷标准差，稳定训练）----
        if len(returns_t) > 1:
            returns_t = (returns_t - returns_t.mean()) / (returns_t.std() + 1e-8)

        # ---- 4. loss = -Σ log_prob(a|s) × G_t ----
        #  关键：把 (s, a) 重新送进网络算 log_prob（带梯度）
        loss = 0
        for (s_i, a_i, _), G_i in zip(transitions, returns_t):
            s_t = torch.FloatTensor(s_i).unsqueeze(0)
            a_t = torch.FloatTensor([a_i]).unsqueeze(0)
            log_prob = policy.evaluate(s_t, a_t)
            loss = loss + (-log_prob * G_i)  # G>0 → 增大概率，G<0 → 减小概率

        loss = loss / len(transitions)
        #    ↑ 如果 G>0（好回报），增大 log_prob（增大这个动作的概率）
        #      如果 G<0（坏回报），减小 log_prob（减小这个动作的概率）

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        episode_rewards.append(sum(rewards))
        episode_lengths.append(len(rewards))

        # ---- 打印进度 ----
        if ep % 50 == 0:
            avg_r = np.mean(episode_rewards[-50:])
            avg_len = np.mean(episode_lengths[-50:])
            print(f"  第{ep:4d}/{episodes}局 | 平均奖励={avg_r:+.3f} | "
                  f"平均步数={avg_len:.0f} | "
                  f"log_std={policy.log_std.item():.3f}")

    return policy, episode_rewards, episode_lengths


# ===================== 测试学到的策略 =====================
def test_policy(policy, episodes=10):
    print("\n测试学到的策略:")
    total_rewards = []

    for ep in range(episodes):
        env = EMSEnv()
        s = env.reset()
        total_r = 0

        for t in range(200):
            a, _ = policy.get_action(s)
            sp, r, done, info = env.step(a)
            total_r += r
            s = sp
            if done:
                break

        total_rewards.append(total_r)
        if ep < 3:
            print(f"  第{ep+1}局: 总奖励={total_r:+.3f}")

    print(f"  平均总奖励: {np.mean(total_rewards):+.3f}")
    return np.mean(total_rewards)


# ===================== 画训练曲线 =====================
def plot_results(rewards, label='REINFORCE', output_dir: str | Path | None = None):
    plt.figure(figsize=(10, 4))

    # 原始曲线
    plt.subplot(1, 2, 1)
    plt.plot(rewards, alpha=0.3, color='blue')
    # 平滑曲线
    window = 20
    smoothed = np.convolve(rewards, np.ones(window)/window, mode='valid')
    plt.plot(smoothed, color='blue', linewidth=2)
    plt.xlabel('局数')
    plt.ylabel('总奖励')
    plt.title(f'{label} 训练曲线')
    plt.grid(alpha=0.3)

    # 每50局平均
    plt.subplot(1, 2, 2)
    chunk = 50
    means = [np.mean(rewards[i:i+chunk]) for i in range(0, len(rewards), chunk)]
    plt.bar(range(len(means)), means, color='blue', alpha=0.7)
    plt.xlabel(f'每{chunk}局')
    plt.ylabel('平均奖励')
    plt.title(f'{label} 每{chunk}局平均')
    plt.grid(alpha=0.3)

    plt.tight_layout()
    path = ensure_results_dir(output_dir) / 'week11_reinforce_training.png'
    plt.savefig(path, dpi=150)
    print(f"\n训练曲线已保存: {path}")
    plt.close()


# ===================== 主程序 =====================
def main() -> None:
    parser = argparse.ArgumentParser(description='Week 11 REINFORCE demo on a simplified continuous EMS environment')
    parser.add_argument('--episodes', type=int, default=500, help='Training episodes')
    parser.add_argument('--lr', type=float, default=0.001, help='Learning rate')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    parser.add_argument('--output-dir', type=Path, default=None, help='Directory for generated figures')
    args = parser.parse_args()

    set_seed(args.seed)

    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║  Week 11 Step 2: REINFORCE (策略梯度)              ║")
    print("║  核心: ∇J = E[ ∇log π(a|s) × G ]                  ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()

    policy, rewards, lengths = reinforce(episodes=args.episodes, lr=args.lr)
    test_policy(policy)
    plot_results(rewards, output_dir=args.output_dir)

    print()
    print("=" * 65)
    print("  和 DQN 的关键区别：")
    print("=" * 65)
    print("""
    DQN:        Q(s) → [Q↑, Q↓, Q←, Q→] → argmax → 选动作
                ↑ 只能处理离散动作

    REINFORCE:  π(s) → [μ, σ] → Normal(μ,σ) → 采样得动作
                ↑ 输出的动作分布，可以取任意连续值
    """)
    print("  REINFORCE 的问题：要等整局跑完才能更新")
    print("  → 下一节 Actor-Critic 解决这个问题")
    print()


if __name__ == '__main__':
    main()
