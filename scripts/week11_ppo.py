#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Week 11 Step 4: PPO (Proximal Policy Optimization)
====================================================
在 Actor-Critic 基础上加了最关键的一项——clip。

AC 的问题：一步更新可能让策略变化太大，直接崩掉。
PPO 的解决：限制每次更新的幅度，让策略"慢慢走"。

核心公式（就一行）：
  ratio = π_new(a|s) / π_old(a|s)     ← 这个动作的概率变了多少倍？
  L_clip = min(ratio × A, clip(ratio, 0.8, 1.2) × A)
            ↑ 正常更新               ↑ 砍掉太大的改动

效果：ratio 超过 1.2 倍或低于 0.8 倍时，不再奖励/惩罚。
      策略不会一步改太多。
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

# ===================== 环境（稍宽松版） =====================
# 为什么改宽松？因为要展示 PPO 能学到东西。
# REINFORCE 和 AC 在这个环境上只撑了 2-3 步。
# PPO 的 clip 机制应该能学到更稳定的策略。
class EMSEnv:
    def __init__(self, hard=False):
        self.soc_min = 0.1
        self.soc_max = 0.95
        self.state_dim = 2
        self.action_dim = 1
        # 更大的电池容量 → SOC 变化更慢 → 更容易学
        self.battery_capacity = 100 if not hard else 50
        self.reset()

    def reset(self):
        self.soc = 0.5
        self.p_load = 0.5
        self.steps = 0
        self.max_steps = 300
        return np.array([self.soc, self.p_load], dtype=np.float32)

    def step(self, action):
        p_fc = float(np.clip(action, 0, 1)) * 30.0
        self.p_load = 0.35 + 0.3 * (0.5 + 0.5 * np.sin(self.steps * 0.05))
        soc_change = (p_fc - self.p_load) / self.battery_capacity
        self.soc = np.clip(self.soc + soc_change, self.soc_min, self.soc_max)

        # 奖励设计：鼓励 P_fc 跟踪 P_load
        # 让奖励更"平滑"，降低 SOC 边界惩罚的突兀感
        fuel_cost = -0.01 * p_fc
        tracking_bonus = -0.5 * (p_fc - self.p_load) ** 2 / 900  # 鼓励跟踪负载
        soc_penalty = -1.0 * (self.soc - 0.5) ** 2

        reward = fuel_cost + tracking_bonus + soc_penalty

        self.steps += 1
        done = (self.steps >= self.max_steps or
                self.soc <= self.soc_min or self.soc >= self.soc_max)

        return self._get_state(), reward, done, {'p_fc': p_fc}

    def _get_state(self):
        return np.array([self.soc, self.p_load], dtype=np.float32)


# ===================== Actor 和 Critic =====================
class Actor(nn.Module):
    def __init__(self, state_dim=2, hidden=64, action_dim=1):
        super().__init__()
        self.fc1 = nn.Linear(state_dim, hidden)
        self.fc2 = nn.Linear(hidden, hidden)
        self.mean_head = nn.Linear(hidden, action_dim)
        self.log_std = nn.Parameter(torch.zeros(action_dim))

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        mean = torch.tanh(self.mean_head(x))
        mean = (mean + 1) / 2  # [0, 1]
        std = torch.exp(self.log_std.clamp(-5, 2))
        return mean, std

    def get_action(self, state):
        with torch.no_grad():
            s = torch.FloatTensor(state).unsqueeze(0)
            mean, std = self.forward(s)
            m = dist.Normal(mean, std)
            a = m.sample()
            log_prob = m.log_prob(a)
            a = a.clamp(0, 1)
            return a.item(), log_prob.item()

    def evaluate(self, state, action):
        """返回 log_prob 和熵（带梯度）"""
        mean, std = self.forward(state)
        m = dist.Normal(mean, std)
        log_prob = m.log_prob(action)
        entropy = m.entropy()
        return log_prob, entropy


class Critic(nn.Module):
    def __init__(self, state_dim=2, hidden=64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 1)
        )

    def forward(self, x):
        return self.net(x)


# ===================== PPO 算法 =====================
def ppo(episodes=500, lr=0.0003, clip_eps=0.2, epochs=10, batch_size=64):
    """
    PPO 算法

    和 Actor-Critic 的关键区别：
      1. 攒一批数据 → 多轮更新（不是来一条学一条）
      2. 每轮更新时，用 importance sampling ratio 代替直接 log_prob
      3. clip 防止 ratio 跑太远
      4. 加熵奖励鼓励探索

    参数：
      clip_eps: clip 范围 [0.8, 1.2]（ε=0.2）
      epochs: 同一批数据重用几次
    """
    env = EMSEnv()
    actor = Actor()
    critic = Critic()
    actor_opt = optim.Adam(actor.parameters(), lr=lr)
    critic_opt = optim.Adam(critic.parameters(), lr=lr)

    episode_rewards = []
    episode_lengths = []

    print(f"PPO 开始训练: {episodes} 局")
    print(f"  clip_eps = {clip_eps}")
    print(f"  epochs = {epochs}（同一批数据重用 {epochs} 次）")
    print(f"  batch_size = {batch_size}")
    print(f"  学习率 lr = {lr}")
    print()

    gamma = 0.99
    gae_lambda = 0.95  # GAE 平滑系数
    entropy_coef = 0.01  # 熵奖励系数

    for ep in range(1, episodes + 1):
        # ---- 1. 用当前策略跑一局，收集数据 ----
        s = env.reset()
        states, actions, rewards, dones, log_probs_old = [], [], [], [], []

        while True:
            a, lp = actor.get_action(s)
            sp, r, done, _ = env.step(a)

            states.append(s)
            actions.append(a)
            rewards.append(r)
            dones.append(done)
            log_probs_old.append(lp)

            s = sp
            if done:
                break

        episode_rewards.append(sum(rewards))
        episode_lengths.append(len(rewards))

        # ---- 2. 算 GAE (Generalized Advantage Estimation) ----
        # 比简单的 TD error 更平滑
        states_t = torch.FloatTensor(np.array(states))
        actions_t = torch.FloatTensor(actions).unsqueeze(1)
        rewards_t = torch.FloatTensor(rewards)
        dones_t = torch.FloatTensor(dones)
        old_log_probs_t = torch.FloatTensor(log_probs_old).unsqueeze(1)

        with torch.no_grad():
            values = critic(states_t).squeeze()
            # 算 GAE
            advantages = []
            gae = 0
            next_value = 0
            for t in reversed(range(len(rewards))):
                if t == len(rewards) - 1:
                    next_value = 0  # 终点后的 V=0
                else:
                    next_value = values[t + 1].item()
                delta = rewards[t] + gamma * next_value * (1 - dones[t]) - values[t].item()
                gae = delta + gamma * gae_lambda * (1 - dones[t]) * gae
                advantages.insert(0, gae)

            advantages_t = torch.FloatTensor(advantages)
            returns_t = advantages_t + values  # returns = advantage + V(s)

            # 标准化 advantages
            if len(advantages_t) > 1:
                advantages_t = (advantages_t - advantages_t.mean()) / (advantages_t.std() + 1e-8)

        # ---- 3. PPO 核心：多轮 clip 更新 ----
        n = len(states)

        for _ in range(epochs):
            # 打乱顺序，分成 mini-batch
            indices = np.random.permutation(n)

            for start in range(0, n, batch_size):
                idx = indices[start:start + batch_size]

                batch_s = states_t[idx]
                batch_a = actions_t[idx]
                batch_adv = advantages_t[idx]
                batch_ret = returns_t[idx]
                batch_old_lp = old_log_probs_t[idx]

                # 3a. 用当前策略算 log_prob
                log_probs_new, entropy = actor.evaluate(batch_s, batch_a)

                # 3b. 算 importance sampling ratio
                # ratio = π_new / π_old
                # 如果 ratio > 1：这个动作现在更可能了
                # 如果 ratio < 1：这个动作现在更不可能了
                ratio = torch.exp(log_probs_new - batch_old_lp)

                # 3c. PPO clip 核心公式
                # L_clip = min(ratio × A, clip(ratio, 1-ε, 1+ε) × A)
                surr1 = ratio * batch_adv
                surr2 = torch.clamp(ratio, 1 - clip_eps, 1 + clip_eps) * batch_adv
                actor_loss = -torch.min(surr1, surr2).mean()
                #   ↑ 负号是因为我们要最大化，但 PyTorch 是做梯度下降

                # 3d. 熵奖励：鼓励探索
                entropy_loss = -entropy_coef * entropy.mean()

                actor_total = actor_loss + entropy_loss

                actor_opt.zero_grad()
                actor_total.backward()
                # 梯度裁剪：防止梯度爆炸
                torch.nn.utils.clip_grad_norm_(actor.parameters(), 0.5)
                actor_opt.step()

                # 3e. 更新 Critic
                V_pred = critic(batch_s).squeeze()
                critic_loss = nn.MSELoss()(V_pred, batch_ret)
                critic_opt.zero_grad()
                critic_loss.backward()
                torch.nn.utils.clip_grad_norm_(critic.parameters(), 0.5)
                critic_opt.step()

        if ep % 50 == 0:
            avg_r = np.mean(episode_rewards[-50:])
            avg_len = np.mean(episode_lengths[-50:])
            print(f"  第{ep:4d}/{episodes}局 | 平均奖励={avg_r:+.3f} | "
                  f"平均步数={avg_len:.0f} | "
                  f"log_std={actor.log_std.item():.3f}")

    return actor, episode_rewards, episode_lengths


# ===================== 测试 =====================
def test_policy(actor, episodes=10):
    print("\n测试学到的策略:")
    total_rewards = []

    for ep in range(episodes):
        env = EMSEnv()
        s = env.reset()
        total_r = 0
        for t in range(300):
            a, _ = actor.get_action(s)
            sp, r, done, _ = env.step(a)
            total_r += r
            s = sp
            if done:
                break
        total_rewards.append(total_r)
        if ep < 3:
            print(f"  第{ep+1}局: 总奖励={total_r:+.3f} ({t+1}步)")

    print(f"  平均总奖励: {np.mean(total_rewards):+.3f}")
    return np.mean(total_rewards)


# ===================== 画图 =====================
def plot_results(rewards, label='PPO', output_dir: str | Path | None = None):
    plt.figure(figsize=(10, 4))
    plt.subplot(1, 2, 1)
    plt.plot(rewards, alpha=0.3, color='red')
    window = 20
    smoothed = np.convolve(rewards, np.ones(window)/window, mode='valid')
    plt.plot(smoothed, color='red', linewidth=2)
    plt.xlabel('局数')
    plt.ylabel('总奖励')
    plt.title(f'{label} 训练曲线')
    plt.grid(alpha=0.3)

    plt.subplot(1, 2, 2)
    chunk = 50
    means = [np.mean(rewards[i:i+chunk]) for i in range(0, len(rewards), chunk)]
    plt.bar(range(len(means)), means, color='red', alpha=0.7)
    plt.xlabel(f'每{chunk}局')
    plt.ylabel('平均奖励')
    plt.title(f'{label} 每{chunk}局平均')
    plt.grid(alpha=0.3)

    plt.tight_layout()
    path = ensure_results_dir(output_dir) / 'week11_ppo_training.png'
    plt.savefig(path, dpi=150)
    print(f"\n训练曲线已保存: {path}")
    plt.close()


# ===================== 主程序 =====================
def main() -> None:
    parser = argparse.ArgumentParser(description='Week 11 PPO demo on a simplified continuous EMS environment')
    parser.add_argument('--episodes', type=int, default=500, help='Training episodes')
    parser.add_argument('--lr', type=float, default=0.0003, help='Learning rate')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    parser.add_argument('--output-dir', type=Path, default=None, help='Directory for generated figures')
    args = parser.parse_args()

    set_seed(args.seed)

    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║  Week 11 Step 4: PPO                               ║")
    print("║  Proximal Policy Optimization — 面试重点           ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()

    actor, rewards, lengths = ppo(episodes=args.episodes, lr=args.lr)

    test_policy(actor)
    plot_results(rewards, output_dir=args.output_dir)

    print()
    print("=" * 65)
    print("  三种方法对比")
    print("=" * 65)
    print("""
    REINFORCE:    π 直接走完 → Σr → 更新
                  [等整局跑完才知道好坏]

    Actor-Critic: π 走一步 → Critic 当场评价 → 更新
                  [每步都更新，但可能一步改太多搞崩策略]

    PPO:          π 走一步 → Critic 评价 → clip(ratio) → 更新
                  [和 AC 一样每步更新，但加了保险不让策略突变]
    """)
    print("  PPO 是 EMS 项目最终选用的算法。")
    print("  原因：连续动作 + 训练稳定 + 实现复杂度适中")
    print()


if __name__ == '__main__':
    main()
