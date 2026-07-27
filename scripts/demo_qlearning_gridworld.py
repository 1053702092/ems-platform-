#!/usr/bin/env python3
"""Q-learning vs 值迭代 对比演示"""
import numpy as np
import random

# ========== 同一个 GridWorld（4x4） ==========
SIZE = 4
n_states = SIZE * SIZE
n_actions = 4
GOAL_IDX = 15
TRAP_IDX = 5
gamma = 0.9

action_delta = [(-1,0), (1,0), (0,-1), (0,1)]  # ↑ ↓ ← →

def is_valid(r, c):
    return 0 <= r < SIZE and 0 <= c < SIZE

# ---- P 和 R（值迭代要用） ----
P = {s: {a: {} for a in range(n_actions)} for s in range(n_states)}
R = {s: {a: 0.0 for a in range(n_actions)} for s in range(n_states)}

for r in range(SIZE):
    for c in range(SIZE):
        s = r * SIZE + c
        if s == GOAL_IDX:
            for a in range(n_actions):
                R[s][a] = 1.0
                P[s][a][s] = 1.0
            continue
        if s == TRAP_IDX:
            for a in range(n_actions):
                R[s][a] = -1.0
                P[s][a][s] = 1.0
            continue
        for a, (dr, dc) in enumerate(action_delta):
            nr, nc = r + dr, c + dc
            if not is_valid(nr, nc):
                nr, nc = r, c
            target = nr * SIZE + nc
            P[s][a][target] = P[s][a].get(target, 0) + 0.8
            for a2, (dr2, dc2) in enumerate(action_delta):
                if a2 == a: continue
                nr2, nc2 = r + dr2, c + dc2
                if not is_valid(nr2, nc2):
                    nr2, nc2 = r, c
                other = nr2 * SIZE + nc2
                P[s][a][other] = P[s][a].get(other, 0) + 0.2 / 3

# ========== 方法 1：值迭代（DP，有模型） ==========
def value_iteration():
    V = np.zeros(n_states)
    for iteration in range(1000):
        delta = 0
        for s in range(n_states):
            v_old = V[s]
            q_max = -np.inf
            for a in range(n_actions):
                q = R[s][a]
                for s_next, prob in P[s][a].items():
                    q += gamma * prob * V[s_next]
                q_max = max(q_max, q)
            V[s] = q_max
            delta = max(delta, abs(v_old - V[s]))
        if delta < 1e-6:
            break
    # 提取策略
    policy = np.zeros(n_states, dtype=int)
    for s in range(n_states):
        q = [R[s][a] + gamma * sum(p * V[ns] for ns, p in P[s][a].items())
             for a in range(n_actions)]
        policy[s] = int(np.argmax(q))
    return V, policy, iteration + 1

# ========== 方法 2：Q-learning（无模型，试出来的） ==========
def q_learning(episodes=3000):
    Q = np.zeros((n_states, n_actions))
    epsilon = 1.0
    steps_per_episode = []

    def step(s, a):
        """真的执行动作，返回 s_next, reward"""
        r, c = divmod(s, SIZE)
        dr, dc = action_delta[a]
        nr, nc = r + dr, c + dc
        # 80% 走对，20% 滑到其他方向（和 P 的定义一致）
        if random.random() < 0.8:
            pass  # 就走选的方向
        else:
            a2 = random.randint(0, 3)
            dr, dc = action_delta[a2]
            nr, nc = r + dr, c + dc
        if not is_valid(nr, nc):
            nr, nc = r, c
        s_next = nr * SIZE + nc
        if s_next == GOAL_IDX:
            reward = 1.0
        elif s_next == TRAP_IDX:
            reward = -1.0
        else:
            reward = 0.0
        return s_next, reward

    for ep in range(episodes):
        s = 0
        steps = 0
        while s != GOAL_IDX and s != TRAP_IDX and steps < 200:
            # ε-贪心
            if random.random() < epsilon:
                a = random.randint(0, 3)
            else:
                a = int(np.argmax(Q[s]))

            s_next, reward = step(s, a)  # ← 真的走一步！

            # Q-learning 更新
            Q[s][a] += 0.1 * (reward + gamma * np.max(Q[s_next]) - Q[s][a])

            s = s_next
            steps += 1

        steps_per_episode.append(steps)
        epsilon = max(0.01, epsilon * 0.995)

    # 提取策略
    policy = np.argmax(Q, axis=1)
    return Q, policy, steps_per_episode

# ========== 打印结果 ==========
sym = {0: '↑', 1: '↓', 2: '←', 3: '→'}

print("=" * 50)
print("方法 1：值迭代（DP）— 知道 P，直接算")
V_dp, pol_dp, iters_dp = value_iteration()
print(f"  收敛于第 {iters_dp} 轮")
print(f"  V(0) = {V_dp[0]:.4f}")
print("  策略：")
for r in range(SIZE):
    row = ""
    for c in range(SIZE):
        s = r * SIZE + c
        if s == GOAL_IDX: row += " G  "
        elif s == TRAP_IDX: row += " X  "
        else: row += f" {sym[pol_dp[s]]}  "
    print(f"  {row}")

print()
print("=" * 50)
print("方法 2：Q-learning（无模型）— 真走 3000 局试出来")
Q, pol_ql, steps = q_learning(3000)
print(f"  V(0) ≈ {np.max(Q[0]):.4f}  (从 Q 表看起点最优值)")
print(f"  策略：")
for r in range(SIZE):
    row = ""
    for c in range(SIZE):
        s = r * SIZE + c
        if s == GOAL_IDX: row += " G  "
        elif s == TRAP_IDX: row += " X  "
        else: row += f" {sym[pol_ql[s]]}  "
    print(f"  {row}")

print()
print("=" * 50)
print("对比：")
print(f"  值迭代 V(0) = {V_dp[0]:.4f}")
print(f"  Q-learning V(0) ≈ {np.max(Q[0]):.4f}")
print(f"  策略一致？{np.array_equal(pol_dp, pol_ql)}")
print()
print("关键理解：")
print("  值迭代：知道 P，不需要和 GridWorld 交互，直接算")
print("  Q-learning：不知道 P，自己走了 3000 局才学会")
print("  但 Q-learning 不需要你知道 P——这才是现实中的情况")
