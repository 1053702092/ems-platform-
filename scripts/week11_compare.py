#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Week 11 Step 5: 三种连续动作 RL 方法对比
============================================
REINFORCE vs Actor-Critic vs PPO
在同一环境上对比训练曲线和最终性能。

环境修复说明：
  之前的版本 P_load 和 P_fc 量纲不一致导致 SOC 几步就出界。
  这个版本统一了功率量纲（kW），让环境可学。
"""

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torch.distributions as dist
import os, time
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'DejaVu Sans'

RESULTS_DIR = r'F:\CLAUDE\research\ems-platform\results'

# ===================== 修复后的环境 =====================
# P_load: 10-20 kW，P_fc: 0-30 kW（同量纲）
# 电池容量足够大（200 kWh），SOC 变化慢，可学
class EMSEnv:
    def __init__(self):
        self.soc_min = 0.1
        self.soc_max = 0.95
        self.state_dim = 2
        self.action_dim = 1
        self.battery_capacity = 5000  # kWh（大一点让 SOC 变化慢，可学）
        self.max_steps = 200
        self.reset()

    def reset(self):
        self.soc = 0.5
        self.t = 0
        return np.array([self.soc, 0.0], dtype=np.float32)

    def _load_profile(self):
        """负载功率 (kW)，模拟实际工况"""
        return 12.0 + 6.0 * np.sin(self.t * 0.05)

    def step(self, action):
        p_fc = float(np.clip(action, 0, 1)) * 30.0  # 0-30 kW
        p_load = self._load_profile()
        # SOC 变化 = 净功率 / 容量 × dt
        d_soc = (p_fc - p_load) / self.battery_capacity
        self.soc = np.clip(self.soc + d_soc, self.soc_min, self.soc_max)
        self.t += 1

        # 奖励
        fuel_cost = -0.01 * p_fc
        tracking = -0.2 * abs(p_fc - p_load) / 30.0
        soc_penalty = -2.0 * (self.soc - 0.5) ** 2
        done_bonus = 0.0

        done = (self.soc <= self.soc_min or self.soc >= self.soc_max or self.t >= self.max_steps)
        if not done and self.t >= self.max_steps:
            done_bonus = 1.0  # 跑完全程奖励

        reward = fuel_cost + tracking + soc_penalty + done_bonus
        return self._get_state(), reward, done, {'p_fc': p_fc, 'p_load': p_load}

    def _get_state(self):
        return np.array([self.soc, self._load_profile() / 30.0], dtype=np.float32)


# ===================== 共享网络结构 =====================
class Actor(nn.Module):
    def __init__(self, state_dim=2, hidden=64):
        super().__init__()
        self.fc1 = nn.Linear(state_dim, hidden)
        self.fc2 = nn.Linear(hidden, hidden)
        self.mean = nn.Linear(hidden, 1)
        self.log_std = nn.Parameter(torch.zeros(1))

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        m = torch.tanh(self.mean(x))
        m = (m + 1) / 2
        s = torch.exp(self.log_std.clamp(-5, 2))
        return m, s

    def get_action(self, state):
        with torch.no_grad():
            s = torch.FloatTensor(state).unsqueeze(0)
            m, s_ = self(s)
            d = dist.Normal(m, s_)
            a = d.sample().clamp(0, 1)
            return a.item(), d.log_prob(a).item()

    def evaluate(self, state, action):
        m, s = self(state)
        d = dist.Normal(m, s)
        return d.log_prob(action), d.entropy()


class Critic(nn.Module):
    def __init__(self, state_dim=2, hidden=64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, 1)
        )
    def forward(self, x):
        return self.net(x)


# ===================== REINFORCE =====================
def run_reinforce(env_fn, episodes=300, lr=0.001):
    actor = Actor()
    opt = optim.Adam(actor.parameters(), lr=lr)
    rewards_log = []
    t0 = time.time()

    for ep in range(episodes):
        env = env_fn()
        s = env.reset()
        traj = []

        for _ in range(env_fn().max_steps):
            a, lp = actor.get_action(s)
            sp, r, done, _ = env.step(a)
            traj.append((s.copy(), a, r))
            s = sp
            if done:
                break

        ep_ret = sum(t[2] for t in traj)
        rewards_log.append(ep_ret)

        # MC returns
        G = 0
        returns = []
        for _, _, r in reversed(traj):
            G = r + 0.99 * G
            returns.insert(0, G)
        ret_t = torch.FloatTensor(returns)
        if len(ret_t) > 1:
            ret_t = (ret_t - ret_t.mean()) / (ret_t.std() + 1e-8)

        loss = 0
        for (s_i, a_i, _), G_i in zip(traj, ret_t):
            s_t = torch.FloatTensor(s_i).unsqueeze(0)
            a_t = torch.FloatTensor([a_i]).unsqueeze(0)
            lp, _ = actor.evaluate(s_t, a_t)
            loss += -lp * G_i

        opt.zero_grad()
        loss.backward()
        opt.step()

    return rewards_log, time.time() - t0


# ===================== Actor-Critic =====================
def run_ac(env_fn, episodes=300, lr=0.001):
    actor = Actor()
    critic = Critic()
    a_opt = optim.Adam(actor.parameters(), lr=lr)
    c_opt = optim.Adam(critic.parameters(), lr=lr)
    rewards_log = []
    t0 = time.time()

    for ep in range(episodes):
        env = env_fn()
        s = env.reset()
        ep_ret = 0

        for _ in range(env_fn().max_steps):
            a, _ = actor.get_action(s)
            sp, r, done, _ = env.step(a)

            s_t = torch.FloatTensor(s).unsqueeze(0)
            sp_t = torch.FloatTensor(sp).unsqueeze(0)
            a_t = torch.FloatTensor([a]).unsqueeze(0)
            r_t = torch.FloatTensor([r])

            V_s = critic(s_t)
            with torch.no_grad():
                V_sp = critic(sp_t)
                adv = r_t + 0.99 * V_sp * (not done) - V_s

            lp, _ = actor.evaluate(s_t, a_t)
            a_loss = -(lp * adv.detach()).mean()
            a_opt.zero_grad()
            a_loss.backward()
            a_opt.step()

            with torch.no_grad():
                td_target = r_t + 0.99 * V_sp * (not done)
            c_loss = nn.MSELoss()(V_s.squeeze(), td_target.squeeze())
            c_opt.zero_grad()
            c_loss.backward()
            c_opt.step()

            ep_ret += r
            s = sp
            if done:
                break

        rewards_log.append(ep_ret)

    return rewards_log, time.time() - t0


# ===================== PPO =====================
def run_ppo(env_fn, episodes=300, lr=0.0003):
    actor = Actor()
    critic = Critic()
    a_opt = optim.Adam(actor.parameters(), lr=lr)
    c_opt = optim.Adam(critic.parameters(), lr=lr)
    rewards_log = []
    t0 = time.time()

    gamma = 0.99
    lam = 0.95
    clip_eps = 0.2
    train_epochs = 5

    for ep in range(episodes):
        env = env_fn()
        s = env.reset()
        states, actions, rewards, dones, old_lps = [], [], [], [], []

        for _ in range(env_fn().max_steps):
            a, lp = actor.get_action(s)
            sp, r, done, _ = env.step(a)
            states.append(s.copy())
            actions.append(a)
            rewards.append(r)
            dones.append(done)
            old_lps.append(lp)
            s = sp
            if done:
                break

        ep_ret = sum(rewards)
        rewards_log.append(ep_ret)
        n = len(rewards)

        # GAE
        S = torch.FloatTensor(np.array(states))
        A = torch.FloatTensor(actions).unsqueeze(1)
        R = torch.FloatTensor(rewards)
        D = torch.FloatTensor(dones)
        O = torch.FloatTensor(old_lps).unsqueeze(1)

        with torch.no_grad():
            vals = critic(S).squeeze().numpy()
            advs = np.zeros(n)
            gae = 0
            for t_ in reversed(range(n)):
                nv = 0 if t_ == n - 1 else vals[t_ + 1]
                delta = rewards[t_] + gamma * nv * (1 - dones[t_]) - vals[t_]
                gae = delta + gamma * lam * (1 - dones[t_]) * gae
                advs[t_] = gae
            adv_t = torch.FloatTensor(advs)
            ret_t = adv_t + torch.FloatTensor(vals)
            if len(adv_t) > 1:
                adv_t = (adv_t - adv_t.mean()) / (adv_t.std() + 1e-8)

        for _ in range(train_epochs):
            idx = np.random.permutation(n)
            for start in range(0, n, 64):
                i = idx[start:start + 64]
                b_s, b_a, b_adv, b_ret, b_old = S[i], A[i], adv_t[i], ret_t[i], O[i]
                lp_new, ent = actor.evaluate(b_s, b_a)
                ratio = torch.exp(lp_new - b_old)
                surr1 = ratio * b_adv
                surr2 = torch.clamp(ratio, 1 - clip_eps, 1 + clip_eps) * b_adv
                a_loss = -torch.min(surr1, surr2).mean() - 0.01 * ent.mean()
                a_opt.zero_grad()
                a_loss.backward()
                torch.nn.utils.clip_grad_norm_(actor.parameters(), 0.5)
                a_opt.step()

                v_pred = critic(b_s).squeeze()
                c_loss = nn.MSELoss()(v_pred.squeeze(), b_ret.squeeze())
                c_opt.zero_grad()
                c_loss.backward()
                torch.nn.utils.clip_grad_norm_(critic.parameters(), 0.5)
                c_opt.step()

    return rewards_log, time.time() - t0


# ===================== 画对比图 =====================
def plot_comparison(results):
    fig, axes = plt.subplots(2, 2, figsize=(14, 8))

    colors = {'REINFORCE': '#2196F3', 'Actor-Critic': '#4CAF50', 'PPO': '#F44336'}

    # 原始曲线 + 平滑
    for ax in [axes[0, 0], axes[0, 1]]:
        for name, rewards, final, t in results:
            ax.plot(rewards, color=colors[name], alpha=0.2, linewidth=1)
            window = 20
            smooth = np.convolve(rewards, np.ones(window)/window, mode='valid')
            axes[0, 0].plot(smooth, color=colors[name], label=name, linewidth=2)

    axes[0, 0].set_xlabel('局数')
    axes[0, 0].set_ylabel('总奖励')
    axes[0, 0].set_title('训练曲线（平滑）')
    axes[0, 0].legend()
    axes[0, 0].grid(alpha=0.3)

    # 每 50 局平均柱状图
    for name, rewards, final, t in results:
        chunk = 50
        means = [np.mean(rewards[i:i+chunk]) for i in range(0, len(rewards), chunk)]
        axes[0, 1].plot(range(1, len(means) + 1), means, marker='o', label=name,
                       color=colors[name], linewidth=2)
    axes[0, 1].set_xlabel(f'每 50 局')
    axes[0, 1].set_ylabel('平均奖励')
    axes[0, 1].set_title('每 50 局平均奖励')
    axes[0, 1].legend()
    axes[0, 1].grid(alpha=0.3)

    # 最终奖励柱状图
    names = [r[0] for r in results]
    finals = [r[2] for r in results]
    times = [r[3] for r in results]
    colors_list = [colors[n] for n in names]

    axes[1, 0].bar(names, finals, color=colors_list, alpha=0.7)
    axes[1, 0].set_ylabel('平均总奖励（最后 50 局）')
    axes[1, 0].set_title('最终性能')
    axes[1, 0].grid(alpha=0.3)
    for i, v in enumerate(finals):
        axes[1, 0].text(i, v, f'{v:.2f}', ha='center', va='bottom' if v >= 0 else 'top')

    # 训练时间柱状图
    axes[1, 1].bar(names, times, color=colors_list, alpha=0.7)
    axes[1, 1].set_ylabel('训练时间 (s)')
    axes[1, 1].set_title('训练时间')
    axes[1, 1].grid(alpha=0.3)
    for i, v in enumerate(times):
        axes[1, 1].text(i, v, f'{v:.1f}s', ha='center', va='bottom')

    plt.tight_layout()
    path = os.path.join(RESULTS_DIR, 'week11_comparison.png')
    fig.savefig(path, dpi=150)
    print(f'对比图已保存: {path}')
    plt.close()


# ===================== 主程序 =====================
if __name__ == '__main__':
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  Week 11: 连续动作 RL 三种方法对比                     ║")
    print("║  REINFORCE vs Actor-Critic vs PPO                      ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    N = 500  # 每算法 500 局
    results = []

    for name, fn in [('REINFORCE', run_reinforce),
                     ('Actor-Critic', run_ac),
                     ('PPO', run_ppo)]:
        print(f'\n--- {name} 训练中（{N}局）---')
        r, t = fn(EMSEnv, episodes=N)
        final = np.mean(r[-50:]) if len(r) >= 50 else np.mean(r)
        print(f'  用时 {t:.1f}s | 最终平均奖励 = {final:+.3f}')
        results.append((name, t, final, r))

    # 打印汇总
    print(f"\n{'='*60}")
    print(f"  {'方法':<16} {'时间':<10} {'最终奖励':<12} {'特点'}")
    print(f"  {'-'*60}")
    for name, t, final, _ in results:
        features = {
            'REINFORCE': '等整局结束才更新，方差大',
            'Actor-Critic': '每步更新，但可能不稳',
            'PPO': 'clip 限制更新幅度，最稳定'
        }
        print(f"  {name:<16} {t:<8.1f}s{'':>2} {final:<+10.3f}{'':>2} {features.get(name, '')}")

    print()

    # 画对比图
    plot_comparison([(r[0], r[3], r[2], r[1]) for r in results])

    print()
    print("=" * 60)
    print("  Week 11 完成 ✅")
    print("  学习路径：DQN(离散) → REINFORCE(连续MC) → AC(连续TD) → PPO(连续+clip)")
    print("  面试重点：能讲清楚 PPO 的 clip 机制 — 为什么它训练更稳定")
    print("=" * 60)
