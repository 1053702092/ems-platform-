#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Week 11 Step 3: Actor-Critic (演员-评委)
============================================
解决了 REINFORCE 的核心问题：

  REINFORCE: 跑完一整局 → 算 G_t → 更新（慢、方差大）
  Actor-Critic: 每走一步 → 用 Critic 估计好坏 → 更新（快、方差小）

架构：
  Actor（演员）:   π_φ(s) → [μ, σ] → 采样动作（和 REINFORCE 一样）
  Critic（评委）:  V_θ(s) → 预测这个状态能拿多少回报

  Advantage = r + γ·V(s') - V(s)  ← "这一步比预期好多少？"
  Actor 更新: loss = -log π(a|s) × Advantage
  Critic 更新: loss = MSE(V(s), r + γ·V(s'))
"""

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torch.distributions as dist
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

RESULTS_DIR = r'F:\CLAUDE\research\ems-platform\results'

# ===================== 环境（同上） =====================
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


# ===================== Actor 和 Critic 网络 =====================
class Actor(nn.Module):
    """策略网络：π(s) → [μ, σ] → 输出动作分布"""
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
        """选动作（无梯度）"""
        with torch.no_grad():
            s = torch.FloatTensor(state).unsqueeze(0)
            mean, std = self.forward(s)
            m = dist.Normal(mean, std)
            a = m.sample()
            a = a.clamp(0, 1)
            return a.item()

    def evaluate(self, state, action):
        """算 log_prob（带梯度，用于训练）"""
        mean, std = self.forward(state)
        m = dist.Normal(mean, std)
        log_prob = m.log_prob(action)
        return log_prob


class Critic(nn.Module):
    """
    价值网络：V(s) → 标量值

    REINFORCE 没有这个——它要等整局跑完才知道好坏。
    Critic 的作用是"预估"当前状态值多少钱，不用等到整局结束。
    """
    def __init__(self, state_dim=2, hidden=64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 1)  # 输出一个标量 V(s)
        )

    def forward(self, x):
        return self.net(x)


# ===================== Actor-Critic 算法 =====================
def actor_critic(episodes=500, lr=0.001):
    """
    Actor-Critic 算法

    每步流程：
      1. Actor 采样动作 a（和 REINFORCE 一样）
      2. 执行 a，得到 s', r
      3. 用 Critic 算 V(s) 和 V(s')
      4. 算 Advantage = r + γ·V(s') - V(s)
      5. Actor 更新: loss = -log π(a|s) × Advantage
      6. Critic 更新: loss = MSE(V(s), r + γ·V(s'))

    和 REINFORCE 的对比：
      REINFORCE: 用"整局的真实回报 G"评价动作好坏
                 没有 Critic，全靠实际结果
      AC:        用"Critic 估计的 Advantage"评价动作好坏
                 每步都能更新，不用等整局结束
    """
    env = EMSEnv()
    actor = Actor()
    critic = Critic()
    actor_opt = optim.Adam(actor.parameters(), lr=lr)
    critic_opt = optim.Adam(critic.parameters(), lr=lr * 2)  # Critic 学快一点
    loss_fn = nn.MSELoss()

    episode_rewards = []
    episode_lengths = []

    print(f"Actor-Critic 开始训练: {episodes} 局")
    print(f"  Actor: {2}维状态 → {64}隐藏 → [μ, σ] → 采样动作")
    print(f"  Critic: {2}维状态 → {64}隐藏 → V(s)")
    print(f"  学习率 lr = {lr}")
    print()

    gamma = 0.99

    for ep in range(1, episodes + 1):
        s = env.reset()
        total_reward = 0
        steps = 0
        done = False

        while not done:
            # ---- 1. Actor 选动作 ----
            a = actor.get_action(s)

            # ---- 2. 执行 ----
            sp, reward, done, _ = env.step(a)

            # ---- 3. 转成 tensor ----
            s_t = torch.FloatTensor(s).unsqueeze(0)
            sp_t = torch.FloatTensor(sp).unsqueeze(0)
            a_t = torch.FloatTensor([a]).unsqueeze(0)
            r_t = torch.FloatTensor([reward])

            # ---- 4. 算 Advantage ----
            #  A = r + γ·V(s') - V(s)
            #  如果 A > 0：这一步比预期好 → 增大这个动作的概率
            #  如果 A < 0：这一步比预期差 → 减小这个动作的概率
            V_s = critic(s_t)
            with torch.no_grad():
                V_sp = critic(sp_t)
                advantage = r_t + gamma * V_sp * (not done) - V_s
                #   ↑ TD error = 实际奖励 + 未来估值 - 当前估值

            # ---- 5. 更新 Actor ----
            log_prob = actor.evaluate(s_t, a_t)
            actor_loss = -(log_prob * advantage.detach()).mean()
            #   ↑ 和 REINFORCE 一模一样，只是 G_t 换成了 Advantage

            actor_opt.zero_grad()
            actor_loss.backward()
            actor_opt.step()

            # ---- 6. 更新 Critic ----
            #  让 V(s) 接近 r + γ·V(s')
            with torch.no_grad():
                td_target = r_t + gamma * V_sp * (not done)
            critic_loss = loss_fn(V_s, td_target)

            critic_opt.zero_grad()
            critic_loss.backward()
            critic_opt.step()

            total_reward += reward
            steps += 1
            s = sp

        episode_rewards.append(total_reward)
        episode_lengths.append(steps)

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
        for t in range(200):
            a = actor.get_action(s)
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


# ===================== 画图 =====================
def plot_results(rewards, label='Actor-Critic'):
    plt.figure(figsize=(10, 4))
    plt.subplot(1, 2, 1)
    plt.plot(rewards, alpha=0.3, color='green')
    window = 20
    smoothed = np.convolve(rewards, np.ones(window)/window, mode='valid')
    plt.plot(smoothed, color='green', linewidth=2)
    plt.xlabel('局数')
    plt.ylabel('总奖励')
    plt.title(f'{label} 训练曲线')
    plt.grid(alpha=0.3)

    plt.subplot(1, 2, 2)
    chunk = 50
    means = [np.mean(rewards[i:i+chunk]) for i in range(0, len(rewards), chunk)]
    plt.bar(range(len(means)), means, color='green', alpha=0.7)
    plt.xlabel(f'每{chunk}局')
    plt.ylabel('平均奖励')
    plt.title(f'{label} 每{chunk}局平均')
    plt.grid(alpha=0.3)

    plt.tight_layout()
    path = os.path.join(RESULTS_DIR, 'week11_ac_training.png')
    plt.savefig(path, dpi=150)
    print(f"\n训练曲线已保存: {path}")
    plt.close()


# ===================== 主程序 =====================
if __name__ == '__main__':
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║  Week 11 Step 3: Actor-Critic                     ║")
    print("║  每步更新，不用等到整局结束                       ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()

    actor, rewards, lengths = actor_critic(episodes=500, lr=0.001)
    test_policy(actor)
    plot_results(rewards)

    print()
    print("=" * 65)
    print("  REINFORCE vs Actor-Critic 对比")
    print("=" * 65)
    print("""
    REINFORCE:      AC:
      π(s) → a        π(s) → a      ← Actor 一样
      无 Critic       V(s)          ← Critic 是新加的
      G_t = Σr         A = r+γV-V   ← 评价方式不同
      整局更新        每步更新      ← 更新频率不同

    AC 的优点：每步都更新，方差比 REINFORCE 小很多
    AC 的缺点：Critic 的估计不准，可能有偏差
    PPO 在 AC 基础上加了"clip"来解决 AC 的另一个问题
    """)
    print()
