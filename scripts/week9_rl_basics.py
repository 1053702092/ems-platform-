#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Week 9 — 强化学习基础
=====================
Part 1: MDP 五元组 — GridWorld 示例
Part 2: Bellman 方程 — V(s) 与 Q(s,a)
Part 3: 策略迭代 — 策略评估 + 策略改进
Part 4: 值迭代 — 收敛到最优

前置: numpy, matplotlib
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'results')
os.makedirs(RESULTS_DIR, exist_ok=True)

# 中文字体设置（Windows）
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun']
plt.rcParams['axes.unicode_minus'] = False


# ============================================================
# Part 1: MDP 五元组 — GridWorld
# ============================================================
def part1_mdp_gridworld():
    """
    GridWorld MDP:
      4×4 网格, 起点 (0,0), 终点 (3,3) +1, 陷阱 (1,1) -1
      动作: ↑ ↓ ← →   (随机移动: 80% 目标方向, 20% 随机)
      折扣因子 γ = 0.9
    """
    import itertools

    # ── 网格参数 ──
    SIZE = 4
    n_states = SIZE * SIZE          # 16 个状态
    actions = ['↑', '↓', '←', '→']  # 4 个动作
    n_actions = len(actions)
    gamma = 0.9                     # 折扣因子

    # 特殊格子
    GOAL = (3, 3)   # 终点 +1
    TRAP = (1, 1)   # 陷阱 -1
    GOAL_IDX = GOAL[0] * SIZE + GOAL[1]
    TRAP_IDX = TRAP[0] * SIZE + TRAP[1]

    # 动作 → (dr, dc) 偏移
    action_delta = {
        '↑': (-1, 0),
        '↓': (1, 0),
        '←': (0, -1),
        '→': (0, 1),
    }

    def pos_to_idx(r, c):
        return r * SIZE + c

    def is_valid(r, c):
        """检查格子是否在网格内"""
        return 0 <= r < SIZE and 0 <= c < SIZE

    # ── 构建奖励 R(s,a) 和转移 P(s'|s,a) ──
    # 用字典表示: R[s][a] = 即时奖励, P[s][a][s'] = 转移概率
    R = {s: {a: 0.0 for a in range(n_actions)} for s in range(n_states)}
    P = {s: {a: {} for a in range(n_actions)} for s in range(n_states)}

    for r, c in itertools.product(range(SIZE), range(SIZE)):
        s = pos_to_idx(r, c)
        if s == GOAL_IDX or s == TRAP_IDX:
            # 终点/陷阱: 吸收态, 停在原地
            for a in range(n_actions):
                R[s][a] = 1.0 if s == GOAL_IDX else -1.0
                P[s][a][s] = 1.0
            continue

        for a_idx, (action_name, (dr, dc)) in enumerate(action_delta.items()):
            # 80% 概率朝目标方向
            nr, nc = r + dr, c + dc
            if not is_valid(nr, nc):
                nr, nc = r, c  # 撞墙停在原地

            target_s = pos_to_idx(nr, nc)
            R[s][a_idx] = 0.0  # 普通格子无即时奖励
            P[s][a_idx][target_s] = P[s][a_idx].get(target_s, 0) + 0.8

            # 20% 概率随机动作（等概率分配到其他 3 个方向）
            for other_dr, other_dc in action_delta.values():
                if (other_dr, other_dc) == (dr, dc):
                    continue
                nr2, nc2 = r + other_dr, c + other_dc
                if not is_valid(nr2, nc2):
                    nr2, nc2 = r, c
                other_s = pos_to_idx(nr2, nc2)
                P[s][a_idx][other_s] = P[s][a_idx].get(other_s, 0) + 0.2 / 3

    print(f'[Part 1] GridWorld MDP: {n_states} 状态 × {n_actions} 动作')
    print(f'  起点 (0,0), 终点 {GOAL} (+1), 陷阱 {TRAP} (-1)')
    print(f'  折扣因子 γ = {gamma}')
    print(f'  随机转移: 80% 目标方向, 20% 随机方向')
    print(f'  吸收态: s={GOAL_IDX} (终点) 和 s={TRAP_IDX} (陷阱) 停在那里不动')

    return {
        'SIZE': SIZE, 'n_states': n_states, 'n_actions': n_actions,
        'actions': actions, 'gamma': gamma,
        'GOAL_IDX': GOAL_IDX, 'TRAP_IDX': TRAP_IDX,
        'R': R, 'P': P, 'pos_to_idx': pos_to_idx,
    }


# ============================================================
# Part 2: Bellman 方程
# ============================================================
def part2_bellman(mdp):
    """用 Bellman 方程计算 V(s) 和 Q(s,a)"""

    n_states = mdp['n_states']
    n_actions = mdp['n_actions']
    gamma = mdp['gamma']
    R = mdp['R']
    P = mdp['P']

    # ── 随机策略: 每个状态均匀随机选动作 ──
    # π(a|s) = 1/n_actions
    policy = np.ones((n_states, n_actions)) / n_actions

    # ── Bellman 期望方程: V^π(s) = Σ_a π(a|s)[R(s,a) + γ Σ_{s'} P(s'|s,a) V^π(s')] ──
    # 迭代求解（策略评估）
    V = np.zeros(n_states)
    theta = 1e-6
    max_iter = 1000

    for i in range(max_iter):
        delta = 0
        for s in range(n_states):
            v_old = V[s]
            v_new = 0
            for a in range(n_actions):
                # π(a|s) × [R(s,a) + γ × Σ P(s'|s,a) × V(s')]
                p_a = policy[s, a]
                if p_a == 0:
                    continue
                bellman_sum = R[s][a]
                for s_next, prob in P[s][a].items():
                    bellman_sum += gamma * prob * V[s_next]
                v_new += p_a * bellman_sum
            V[s] = v_new
            delta = max(delta, abs(v_old - v_new))
        if delta < theta:
            break

    # ── Bellman 最优方程: V*(s) = max_a [R(s,a) + γ Σ P(s'|s,a) V*(s')] ──
    V_opt = np.zeros(n_states)
    for i in range(max_iter):
        delta = 0
        for s in range(n_states):
            v_old = V_opt[s]
            q_values = []
            for a in range(n_actions):
                q = R[s][a]
                for s_next, prob in P[s][a].items():
                    q += gamma * prob * V_opt[s_next]
                q_values.append(q)
            V_opt[s] = max(q_values)  # 最优 = 取 max
            delta = max(delta, abs(v_old - V_opt[s]))
        if delta < theta:
            break

    print(f'\n[Part 2] Bellman 方程')
    print(f'  随机策略 V(s) 收敛于 {i+1} 次迭代')
    print(f'  终点 V({mdp["GOAL_IDX"]})    = {V[mdp["GOAL_IDX"]]:.4f}')
    print(f'  陷阱 V({mdp["TRAP_IDX"]})    = {V[mdp["TRAP_IDX"]]:.4f}')
    print(f'  起点 V(0)     = {V[0]:.4f}')
    print(f'  最优 V*(0)    = {V_opt[0]:.4f}')
    print(f'  最优 V* 范围: {V_opt.min():.4f} ~ {V_opt.max():.4f}')

    # ── 画 V(s) heatmap ──
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    SIZE = mdp['SIZE']

    im0 = axes[0].imshow(V.reshape(SIZE, SIZE), cmap='RdYlBu_r', vmin=-1, vmax=1)
    axes[0].set_title('V^π(s) — 随机策略')
    for r in range(SIZE):
        for c in range(SIZE):
            axes[0].text(c, r, f'{V[r*SIZE+c]:.2f}', ha='center', va='center', fontsize=8)

    im1 = axes[1].imshow(V_opt.reshape(SIZE, SIZE), cmap='RdYlBu_r', vmin=-1, vmax=1)
    axes[1].set_title('V*(s) — 最优值函数')
    for r in range(SIZE):
        for c in range(SIZE):
            axes[1].text(c, r, f'{V_opt[r*SIZE+c]:.2f}', ha='center', va='center', fontsize=8)

    plt.tight_layout()
    path = os.path.join(RESULTS_DIR, 'week9_bellman_value.png')
    plt.savefig(path, dpi=150)
    plt.close()
    print(f'  图: {path}')

    return {'V_pi': V, 'V_opt': V_opt}

# ============================================================
# Part 3: 策略迭代
# ============================================================
def part3_policy_iteration(mdp):
    """策略迭代: 策略评估 → 策略改进 → 直到收敛"""
    n_states = mdp['n_states']
    n_actions = mdp['n_actions']
    gamma = mdp['gamma']
    R = mdp['R']
    P = mdp['P']

    # 初始随机策略
    policy = np.random.randint(0, n_actions, size=n_states)  # 确定性策略
    V = np.zeros(n_states)

    def policy_evaluation(policy, V, theta=1e-6):
        """策略评估: 解 Bellman 期望方程 V^π"""
        for _ in range(1000):
            delta = 0
            for s in range(n_states):
                v_old = V[s]
                a = policy[s]
                v_new = R[s][a]
                for s_next, prob in P[s][a].items():
                    v_new += gamma * prob * V[s_next]
                V[s] = v_new
                delta = max(delta, abs(v_old - v_new))
            if delta < theta:
                break
        return V

    def policy_improvement(policy, V):
        """策略改进: 贪心选择 Q(s,a) 最大的动作"""
        policy_stable = True
        for s in range(n_states):
            old_action = policy[s]
            q_values = []
            for a in range(n_actions):
                q = R[s][a]
                for s_next, prob in P[s][a].items():
                    q += gamma * prob * V[s_next]
                q_values.append(q)
            policy[s] = int(np.argmax(q_values))
            if old_action != policy[s]:
                policy_stable = False
        return policy, policy_stable

    # ── 策略迭代主循环 ──
    print(f'\n[Part 3] 策略迭代')
    for iteration in range(50):
        V = policy_evaluation(policy, V)
        policy, stable = policy_improvement(policy, V)
        if stable:
            print(f'  第 {iteration+1} 轮: 收敛 [OK]')
            break
        else:
            print(f'  第 {iteration+1} 轮: 策略改进中...')

    action_symbols = {0: '↑', 1: '↓', 2: '←', 3: '→'}
    print(f'\n  最优策略:')
    SIZE = mdp['SIZE']
    for r in range(SIZE):
        row_str = '  '
        for c in range(SIZE):
            s = r * SIZE + c
            if s == mdp['GOAL_IDX']:
                row_str += ' G  '
            elif s == mdp['TRAP_IDX']:
                row_str += ' X  '
            else:
                row_str += f' {action_symbols[policy[s]]}  '
        print(row_str)

    print(f'\n  起点 (0,0) 策略: {action_symbols[policy[0]]}')
    print(f'  策略总参数量: {n_states} 个 (每状态一个动作索引)')

    # ── 画最优策略 ──
    fig, ax = plt.subplots(figsize=(5, 5))
    grid = V.reshape(SIZE, SIZE)
    ax.imshow(grid, cmap='RdYlBu_r', vmin=-1, vmax=1)
    for r in range(SIZE):
        for c in range(SIZE):
            s = r * SIZE + c
            if s == mdp['GOAL_IDX']:
                ax.text(c, r, 'GOAL', ha='center', va='center', fontsize=12, fontweight='bold')
            elif s == mdp['TRAP_IDX']:
                ax.text(c, r, 'TRAP', ha='center', va='center', fontsize=12, fontweight='bold')
            else:
                ax.text(c, r, action_symbols[policy[s]], ha='center', va='center', fontsize=16)
    ax.set_title('Optimal Policy (Policy Iteration)')
    plt.tight_layout()
    path = os.path.join(RESULTS_DIR, 'week9_optimal_policy.png')
    plt.savefig(path, dpi=150)
    plt.close()
    print(f'  图: {path}')

    return {'policy': policy, 'V': V}


# ============================================================
# Part 4: 值迭代
# ============================================================
def part4_value_iteration(mdp):
    """值迭代: 直接迭代 Bellman 最优方程 V*(s) = max_a Q(s,a)"""
    n_states = mdp['n_states']
    n_actions = mdp['n_actions']
    gamma = mdp['gamma']
    R = mdp['R']
    P = mdp['P']

    V = np.zeros(n_states)
    theta = 1e-6

    print(f'\n[Part 4] 值迭代')
    for iteration in range(1000):
        delta = 0
        for s in range(n_states):
            v_old = V[s]
            q_max = -np.inf
            for a in range(n_actions):
                q = R[s][a]
                for s_next, prob in P[s][a].items():
                    q += gamma * prob * V[s_next]
                if q > q_max:
                    q_max = q
            V[s] = q_max
            delta = max(delta, abs(v_old - V[s]))
        if delta < theta:
            print(f'  收敛于第 {iteration+1} 次迭代')
            break

    # 从最优 V* 提取策略
    policy = np.zeros(n_states, dtype=int)
    for s in range(n_states):
        q_values = []
        for a in range(n_actions):
            q = R[s][a]
            for s_next, prob in P[s][a].items():
                q += gamma * prob * V[s_next]
            q_values.append(q)
        policy[s] = int(np.argmax(q_values))

    action_symbols = {0: '↑', 1: '↓', 2: '←', 3: '→'}
    print(f'  最优策略:')
    SIZE = mdp['SIZE']
    for r in range(SIZE):
        row_str = '  '
        for c in range(SIZE):
            s = r * SIZE + c
            if s == mdp['GOAL_IDX']:
                row_str += ' G  '
            elif s == mdp['TRAP_IDX']:
                row_str += ' X  '
            else:
                row_str += f' {action_symbols[policy[s]]}  '
        print(row_str)

    # 对比 Part 3 策略
    print(f'\n  值迭代 V*(0) = {V[0]:.4f}')
    print(f'  策略迭代 V(0) 应与值迭代一致（验证正确性）')

    return {'V': V, 'policy': policy}


# ============================================================
# 可视化：V(s) 收敛过程
# ============================================================
def plot_convergence():
    """演示值迭代收敛速度"""
    # 复用 Part 1 的 MDP
    mdp = part1_mdp_gridworld()
    n_states = mdp['n_states']
    n_actions = mdp['n_actions']
    gamma = mdp['gamma']
    R = mdp['R']
    P = mdp['P']

    V_track = []
    V = np.zeros(n_states)
    theta = 1e-6

    for iteration in range(100):
        delta = 0
        for s in range(n_states):
            v_old = V[s]
            q_max = -np.inf
            for a in range(n_actions):
                q = R[s][a]
                for s_next, prob in P[s][a].items():
                    q += gamma * prob * V[s_next]
                if q > q_max:
                    q_max = q
            V[s] = q_max
            delta = max(delta, abs(v_old - V[s]))
        V_track.append(V.copy())
        if delta < theta:
            break

    V_track = np.array(V_track)

    fig, axes = plt.subplots(2, 1, figsize=(10, 8))

    # 起点 V 值收敛
    axes[0].plot(V_track[:, 0], 'b-', linewidth=1.5, label='Start (0,0)')
    axes[0].plot(V_track[:, mdp['GOAL_IDX']], 'g-', linewidth=1.5, label=f'Goal {mdp["GOAL_IDX"]}')
    axes[0].plot(V_track[:, mdp['TRAP_IDX']], 'r-', linewidth=1.5, label=f'Trap {mdp["TRAP_IDX"]}')
    axes[0].set_xlabel('Iteration')
    axes[0].set_ylabel('V(s)')
    axes[0].set_title('Value Iteration Convergence')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # V(s) 变化量
    deltas = [np.max(np.abs(V_track[i+1] - V_track[i])) for i in range(len(V_track)-1)]
    axes[1].plot(deltas, 'k-', linewidth=1.0)
    axes[1].set_xlabel('Iteration')
    axes[1].set_ylabel('Max ΔV')
    axes[1].set_title('Convergence: Max Change per Iteration')
    axes[1].set_yscale('log')
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(RESULTS_DIR, 'week9_value_iteration_convergence.png')
    plt.savefig(path, dpi=150)
    plt.close()
    print(f'\n[Convergence] 图: {path}')
    print(f'  值迭代 {len(V_track)} 次收敛')
    print(f'  起点 V(0): {V_track[-1,0]:.4f} (初值 {V_track[0,0]:.4f})')



if __name__ == '__main__':
    print('=' * 60)
    print('Part 1: MDP 五元组 — GridWorld')
    print('=' * 60)
    mdp = part1_mdp_gridworld()

    print('\n' + '=' * 60)
    print('Part 2: Bellman 方程')
    print('=' * 60)
    values = part2_bellman(mdp)

    print('\n' + '=' * 60)
    print('Part 3: 策略迭代')
    print('=' * 60)
    pi_result = part3_policy_iteration(mdp)

    print('\n' + '=' * 60)
    print('Part 4: 值迭代')
    print('=' * 60)
    vi_result = part4_value_iteration(mdp)

    print('\n' + '=' * 60)
    print('Extra: 收敛过程可视化')
    print('=' * 60)
    plot_convergence()

    # 验证一致性
    print('\n' + '=' * 60)
    print('验证: 策略迭代 vs 值迭代')
    print('=' * 60)
    s0_pi = pi_result['V'][0]
    s0_vi = vi_result['V'][0]
    print(f'  策略迭代 V(0) = {s0_pi:.4f}')
    print(f'  值迭代   V(0) = {s0_vi:.4f}')
    print(f'  差值     ΔV   = {abs(s0_pi - s0_vi):.6f}')
    if abs(s0_pi - s0_vi) < 1e-4:
        print('  [OK] 一致！策略迭代与值迭代收敛到同一最优值函数')
    else:
        print('  [!] 有偏差, 检查收敛容差')

    print('\n[OK] Week 9 RL 基础完成！下一步：Week 10 DQN/SAC 概念')
