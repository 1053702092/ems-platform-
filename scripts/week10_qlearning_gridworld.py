#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Week 10 — Q-learning: 无模型 GridWorld
======================================
对比 Week 9 Part 8 值迭代（DP）：
  值迭代：知道环境模型 P，直接算
  Q-learning：不知道 P，靠试错学

环境：4x4 GridWorld（和你 Week 9 的 GridWorld 完全一样）
  起点 (0,0), 终点 (3,3) +1, 陷阱 (1,1) -1
  动作：↑ ↓ ← →, 80% 走对, 20% 滑到其他方向
"""

import numpy as np
import random
import os

# ===================== 环境定义 =====================
SIZE = 4
N_STATES = SIZE * SIZE
N_ACTIONS = 4
GOAL_IDX = 15
TRAP_IDX = 5
GAMMA = 0.9
RESULTS_DIR = r'F:\CLAUDE\research\ems-platform\results'

ACTION_DELTA = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # ↑ ↓ ← →
ACTION_SYMBOLS = {0: '↑', 1: '↓', 2: '←', 3: '→'}

def is_valid(r, c):
    return 0 <= r < SIZE and 0 <= c < SIZE

def step(s, a):
    """
    执行动作，返回 (s_next, reward, done)
    模拟 80% 目标方向 / 20% 随机滑走
    """
    global GOAL_IDX, TRAP_IDX
    r, c = divmod(s, SIZE)   #坐标值

    # 80% 走选的方向
    if random.random() < 0.8:
        dr, dc = ACTION_DELTA[a]
    else:
        # 20% 随机滑到其他 3 个方向之一
        other_actions = [i for i in range(N_ACTIONS) if i != a]
        a2 = random.choice(other_actions)
        dr, dc = ACTION_DELTA[a2]

    nr, nc = r + dr, c + dc
    if not is_valid(nr, nc):
        nr, nc = r, c  # 撞墙留在原地

    s_next = nr * SIZE + nc

    if s_next == GOAL_IDX:
        reward = 1.0
    elif s_next == TRAP_IDX:
        reward = -1.0
    else:
        reward = 0.0

    done = (s_next == GOAL_IDX or s_next == TRAP_IDX)
    return s_next, reward, done


# ===================== Q-learning 算法 =====================
def q_learning(episodes=5000, lr=0.1, epsilon_start=1.0, epsilon_end=0.01, epsilon_decay=0.998):
    """
    Q-learning 主函数
    参数:
        episodes: 训练局数
        lr: 学习率
        epsilon_start: 初始探索率
        epsilon_end: 最小探索率
        epsilon_decay: 探索率衰减系数
    """
    # 初始化 Q 表: [16 状态 × 4 动作]
    Q = np.zeros((N_STATES, N_ACTIONS))

    # 记录训练过程
    episode_rewards = []      # 每局总奖励
    episode_steps = []        # 每局步数
    epsilon = epsilon_start

    print(f'Q-learning 开始训练: {episodes} 局')
    print(f'  学习率 lr = {lr}')
    print(f'  探索率 ε = {epsilon_start} → {epsilon_end} (decay={epsilon_decay})')
    print(f'  折扣因子 γ = {GAMMA}')
    print()

    for ep in range(1, episodes + 1):
        s = 0           # 起点 (0,0)
        total_reward = 0
        steps = 0

        while True:
            # ε-贪心选动作  epsilon属于0-1
            if random.random() < epsilon:
                a = random.randint(0, N_ACTIONS - 1)    # 探索
            else:
                a = int(np.argmax(Q[s]))                 # 利用

            # 执行动作
            s_next, reward, done = step(s, a)

            # Q-learning 更新公式：
            # Q(s,a) ← Q(s,a) + lr · [ r + γ·max Q(s',·) - Q(s,a) ]
            td_target = reward + GAMMA * np.max(Q[s_next]) * (not done)
            td_error = td_target - Q[s, a]
            Q[s, a] += lr * td_error

            total_reward += reward
            steps += 1
            s = s_next

            if done:
                break

        episode_rewards.append(total_reward)
        episode_steps.append(steps)

        # ε 衰减
        epsilon = max(epsilon_end, epsilon * epsilon_decay)

        # 每 500 局打印进度
        if ep % 500 == 0:
            avg_reward = np.mean(episode_rewards[-100:])
            avg_steps = np.mean(episode_steps[-100:])
            print(f'  第 {ep:4d}/{episodes} 局 | ε={epsilon:.3f} | '
                  f'平均奖励={avg_reward:+.4f} | 平均步数={avg_steps:.1f}')

    # 提取最优策略
    policy = np.argmax(Q, axis=1)

    return Q, policy, episode_rewards, episode_steps


# ===================== 结果展示 =====================
def print_results(Q, policy, episode_rewards, episode_steps):
    print()
    print('=' * 50)
    print('Q-learning 训练结果')
    print('=' * 50)

    # Q 表摘要
    print(f'\nQ 表形状: {Q.shape}  ({N_STATES} 状态 × {N_ACTIONS} 动作)')
    print(f'起点 Q(s=0):  ↑={Q[0,0]:.3f}  ↓={Q[0,1]:.3f}  ←={Q[0,2]:.3f}  →={Q[0,3]:.3f}')
    print(f'终点 Q(s=15): ↑={Q[15,0]:.3f}  ↓={Q[15,1]:.3f}  ←={Q[15,2]:.3f}  →={Q[15,3]:.3f}')
    print(f'陷阱 Q(s=5):  ↑={Q[5,0]:.3f}  ↓={Q[5,1]:.3f}  ←={Q[5,2]:.3f}  →={Q[5,3]:.3f}')
    print(f'\n起点 V(0) = max_a Q(0,a) = {np.max(Q[0]):.4f}')
    print(f'终点 V(15) = max_a Q(15,a) = {np.max(Q[15]):.4f}')
    print(f'陷阱 V(5) = max_a Q(5,a) = {np.max(Q[5]):.4f}')

    # 最优策略
    print(f'\n最优策略（箭头=往哪走, G=终点, X=陷阱）:')
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

    # 训练曲线摘要
    print(f'\n训练统计:')
    print(f'  总局数: {len(episode_rewards)}')
    print(f'  最后 100 局平均奖励: {np.mean(episode_rewards[-100:]):+.4f}')
    print(f'  最后 100 局平均步数: {np.mean(episode_steps[-100:]):.1f}')
    print(f'  最小步数到达终点: {min(episode_steps[-500:])} 步')
    print(f'  单局最多步数: {max(episode_steps[-500:])} 步')


def save_results(Q, policy, episode_rewards, episode_steps):
    """保存结果到文件"""
    os.makedirs(RESULTS_DIR, exist_ok=True)

    # 保存训练数据
    path_csv = os.path.join(RESULTS_DIR, 'week10_qlearning_training.csv')
    with open(path_csv, 'w', encoding='utf-8') as f:
        f.write('episode,reward,steps\n')
        for i, (r, s) in enumerate(zip(episode_rewards, episode_steps)):
            f.write(f'{i+1},{r:.4f},{s}\n')
    print(f'\n训练数据已保存: {path_csv}')

    # 保存 Q 表
    path_q = os.path.join(RESULTS_DIR, 'week10_qlearning_qtable.csv')
    with open(path_q, 'w', encoding='utf-8') as f:
        f.write('state,action_up,action_down,action_left,action_right,best_action\n')
        for s in range(N_STATES):
            best = int(np.argmax(Q[s]))
            f.write(f'{s},{Q[s,0]:.4f},{Q[s,1]:.4f},{Q[s,2]:.4f},{Q[s,3]:.4f},{best}\n')
    print(f'Q 表已保存: {path_q}')


# ===================== 主程序 =====================
if __name__ == '__main__':
    print('=' * 60)
    print('  Week 10 — Q-learning GridWorld')
    print('  环境: 4x4 GridWorld, 起点(0,0), 终点(3,3)+1, 陷阱(1,1)-1')
    print('  动作: ↑↓←→, 80% 走对, 20% 滑走, γ=0.9')
    print('  DP 参考值: 值迭代 V(0) = 3.3419 (Week 9 Part 8)')
    print('=' * 60)
    print()

    # 训练
    Q, policy, rewards, steps = q_learning(
        episodes=5000,
        lr=0.1,
        epsilon_start=1.0,
        epsilon_end=0.01,
        epsilon_decay=0.998
    )

    # 展示结果
    print_results(Q, policy, rewards, steps)

    # 保存结果
    save_results(Q, policy, rewards, steps)

    print()
    print('=' * 60)
    print('  和值迭代（Week 9 Part 8）的对比:')
    print('    值迭代:  知道 P, 133 轮直接算完, V(0)=3.3419')
    print('    Q-learning: 不知道 P, 5000 局试出来, V(0)=',
          f'{np.max(Q[0]):.4f}')
    print('    殊途同归: 两种方法找到的最优策略基本一致')
    print('=' * 60)
