#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Week 11 Step 1: 连续动作环境 — EMS 简化版
============================================
和之前 GridWorld（16 个离散状态、4 个离散动作）不同，
这个环境是：

  状态:   [SOC, P_load]       ← 2 维连续值
  动作:   P_fc ∈ [0, 1]       ← 1 维连续值（归一化，对应 0-30 kW）
  奖励:   -fuel_cost - penalty ← 连续值

对比 DQN 在这个环境上为什么会失败。
"""

import random
import argparse

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from week11_common import set_seed

# ===================== 连续动作环境 =====================
class EMSEnv:
    """
    简化 EMS 环境

    物理意义：
      SOC（电池电量）会随着负载用电和燃料电池供电而变化。
      P_fc（燃料电池功率）是我们要控制的变量。
      目标是：用最少的燃料（最小化 P_fc），同时维持 SOC 在合理范围。
    """
    def __init__(self):
        # 状态空间
        self.soc_min = 0.2
        self.soc_max = 0.9
        self.state_dim = 2   # [SOC, P_load]
        self.action_dim = 1  # P_fc (归一化 0~1)

        # 电池参数
        self.battery_capacity = 50  # kWh
        self.dt = 1/60  # 每步 = 1 分钟

        # 重置
        self.reset()

    def reset(self):
        """重置环境，返回初始状态"""
        self.soc = 0.6  # 初始 SOC = 60%
        self.p_load = 0.5  # 初始负载（KW）
        self.steps = 0
        self.max_steps = 200
        return self._get_state()

    def _get_state(self):
        """返回当前状态 [SOC, P_load]"""
        return np.array([self.soc, self.p_load], dtype=np.float32)

    def step(self, action):
        """
        执行动作 action = P_fc (归一化 0~1)

        返回: (next_state, reward, done, info)
        """
        # 动作 = P_fc，反归一化到 0-30 kW
        p_fc = float(np.clip(action, 0, 1)) * 30.0  # [0, 30] kW

        # 负载功率（模拟变化）
        self.p_load = 0.3 + 0.4 * (0.5 + 0.5 * np.sin(self.steps * 0.1))

        # SOC 变化 = (P_fc - P_load) / 容量 × dt
        # P_fc > P_load → 充电，SOC ↑
        # P_fc < P_load → 放电，SOC ↓
        power_diff = p_fc - self.p_load  # kW
        soc_change = power_diff / self.battery_capacity  # 归一化变化量
        self.soc = np.clip(self.soc + soc_change, self.soc_min, self.soc_max)

        # 计算奖励
        # 1) 燃料成本：P_fc 越大，燃料越多 → 负奖励
        fuel_cost = -0.01 * p_fc

        # 2) SOC 惩罚：远离 0.6 时惩罚
        soc_penalty = -0.5 * (self.soc - 0.6) ** 2

        # 3) SOC 越界惩罚
        soc_bound_penalty = 0.0
        if self.soc <= self.soc_min or self.soc >= self.soc_max:
            soc_bound_penalty = -1.0

        reward = fuel_cost + soc_penalty + soc_bound_penalty

        # 判断结束
        self.steps += 1
        done = (self.steps >= self.max_steps or
                self.soc <= self.soc_min or
                self.soc >= self.soc_max)

        return self._get_state(), reward, done, {
            'p_fc': p_fc,
            'fuel_cost': fuel_cost,
            'soc': self.soc
        }

    def render(self):
        """文字渲染"""
        bar_len = 20
        soc_bar = int((self.soc - self.soc_min) / (self.soc_max - self.soc_min) * bar_len)
        bar = '█' * soc_bar + '░' * (bar_len - soc_bar)
        print(f"Step {self.steps:3d} | SOC [{bar}] {self.soc:.2f} | Load {self.p_load:.2f}")


# ===================== DQN 硬上连续动作的失败尝试 =====================
class DQN_Continuous(nn.Module):
    """
    DQN 强行用在连续动作上——
    输出层只有一个神经元（P_fc），
    但 Q-learning 需要 argmax，对连续值没法 argmax！

    这里"假装"能行：直接输出 Q 值然后取为动作。
    但这是错的——后面会看到为什么。
    """
    def __init__(self, state_dim=2, hidden=64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 1)  # 输出 1 个连续动作值
        )

    def forward(self, x):
        return self.net(x)


def demo_dqn_failure():
    """
    演示 DQN 强行用在连续动作上会怎么样

    为什么失败？
      DQN 的核心是：输出每个动作的 Q 值 → argmax 选最大的
      连续动作有无限个可能值，没法 argmax！

    这里"假装"让 DQN 直接输出动作值（不是 Q 值），
    但这本质上是监督学习（输入状态 → 输出动作），不是强化学习。
    """
    print("=" * 65)
    print("  DQN 强行用在连续动作上 — 演示为什么不行")
    print("=" * 65)
    print()

    env = EMSEnv()
    q_net = DQN_Continuous()
    optimizer = optim.Adam(q_net.parameters(), lr=0.01)
    loss_fn = nn.MSELoss()

    print("问题 1: 没法 argmax")
    print("  DQN 选动作: a = argmax Q(s, a) ← 需要遍历所有动作")
    print("  连续动作:    a ∈ [0, 1]，有无穷多个值")
    print("  遍历不了 → 没法用 argmax → Q-learning 公式失效")
    print()

    print("问题 2: 即使强行输出一个动作值，更新公式也不对")
    print("  Q-learning 的 target = r + γ·max Q(s', a')")
    print("  连续空间里 max Q(s', a') 没法算")
    print()

    print("做个实验：让网络直接输出动作（不是 Q 值）")
    print("跑 50 局看看效果：")
    print()

    for ep in range(1, 51):
        s = env.reset()
        total_reward = 0

        for t in range(200):
            s_tensor = torch.FloatTensor(s).unsqueeze(0)

            # 网络直接输出一个值（0~1），当做动作
            with torch.no_grad():
                a = float(torch.sigmoid(q_net(s_tensor)).item())

            sp, reward, done, _ = env.step(a)

            # 尝试用 Q-learning 公式更新——但这里 max Q(sp) 算不了
            # 因为连续动作没有"max"
            # 所以这根本就不是 DQN 了，只是瞎更新

            total_reward += reward
            s = sp
            if done:
                break

        if ep % 10 == 0:
            print(f"  第{ep:3d}局 | 总奖励={total_reward:.3f} | "
                  f"无意义——因为没有正确的更新公式")

    print()
    print("结论：")
    print("  DQN 从数学结构上就无法处理连续动作。")
    print("  这不是调参能解决的，是 Q-learning 的 argmax 决定的。")
    print("  要处理连续动作，必须换方法——策略梯度。")
    print()


# ===================== 测试环境是否正常 =====================
def test_env():
    print("=" * 65)
    print("  连续动作环境测试")
    print("=" * 65)
    print()

    env = EMSEnv()
    s = env.reset()
    print(f"初始状态: SOC={s[0]:.2f}, P_load={s[1]:.2f}")
    print()
    print("随机策略跑一局:")
    print()

    total_reward = 0
    for t in range(10):
        a = random.random()
        sp, reward, done, info = env.step(a)
        total_reward += reward
        print(f"  步{t+1:2d}: P_fc={info['p_fc']:5.1f}kW | SOC={info['soc']:.3f} | "
              f"奖励={reward:+.4f}")
        s = sp

    print(f"\n10 步总奖励: {total_reward:+.4f}")
    print()
    print("状态维度:", env.state_dim, "(连续)")
    print("动作维度:", env.action_dim, "(连续)")
    print("状态范围: SOC=[0.2, 0.9], P_load=[0.3, 0.7]")
    print("动作范围: P_fc=[0, 1] 归一化 → [0, 30] kW")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description='Week 11 simplified continuous-action EMS environment demo')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    parser.add_argument('--skip-dqn-demo', action='store_true', help='Only run the environment smoke test')
    args = parser.parse_args()

    set_seed(args.seed)

    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║  Week 11 Step 1: 连续动作环境                     ║")
    print("║  从离散（GridWorld 4×4）到连续（EMS 简化版）      ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()

    test_env()
    if not args.skip_dqn_demo:
        demo_dqn_failure()


if __name__ == '__main__':
    main()
