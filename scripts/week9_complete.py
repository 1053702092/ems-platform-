#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Week 9 — PyTorch + RL 基础 完整通关
====================================
PyTorch 篇 (Part 1-4)
  Part 1: Tensor 基础
  Part 2: Autograd 自动求导
  Part 3: nn.Module + MLP
  Part 4: MLP 功率预测（FC 功率预测）

RL 基础篇 (Part 5-8)
  Part 5: MDP 五元组 — GridWorld
  Part 6: Bellman 方程
  Part 7: 策略迭代
  Part 8: 值迭代

前置: pip install torch, numpy, matplotlib
输出: results/week9_complete_*.png
"""

import os, sys, itertools, argparse

# 强制 stdout/err 用 UTF-8，避免 Windows GBK 终端 Unicode 报错
if sys.stdout.encoding and sys.stdout.encoding.upper() in ('GBK', 'GB2312', 'CP936'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding and sys.stderr.encoding.upper() in ('GBK', 'GB2312', 'CP936'):
    sys.stderr.reconfigure(encoding='utf-8')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'results')
os.makedirs(RESULTS_DIR, exist_ok=True)

# ── 命令行参数 ──
parser = argparse.ArgumentParser(description='Week 9 — PyTorch + RL 基础 逐 Part 学习')
parser.add_argument('--part', type=int, default=0, choices=[0,1,2,3,4,5,6,7,8],
                    help='跑指定 Part (1-8)，默认 0=跑全部')
args = parser.parse_args()

def should_run(part_num):
    """判断当前 Part 是否需要执行。"""
    return args.part == 0 or args.part == part_num

# 中文字体（Windows）
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun']
plt.rcParams['axes.unicode_minus'] = False


# ═══════════════════════════════════════════════════════════════
# Part 1: Tensor 基础
# ═══════════════════════════════════════════════════════════════
def part1_tensor_basics():
    """PyTorch Tensor 的创建与基本操作."""
    import torch

    # 从列表创建
    t1 = torch.tensor([[1, 2], [3, 4]])
    print(f"t1:\n{t1}, dtype={t1.dtype}, shape={t1.shape}")

    # 从 numpy 创建
    a = np.array([1.0, 2.0, 3.0])
    t2 = torch.from_numpy(a)
    print(f"t2: {t2}")

    # 特殊张量
    zeros = torch.zeros(2, 3)
    ones = torch.ones(2, 3)
    rand = torch.randn(3, 3)  # 标准正态
    print(f"zeros: {zeros.shape}, ones: {ones.shape}, randn: {rand.shape}")

    # 设备
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # 在指定设备上创建
    t_gpu = torch.tensor([1, 2, 3], device=device)

    # 索引、切片、形状操作
    t = torch.randn(4, 5)
    print(f"t[0]: {t[0].shape}, t[:, :3]: {t[:, :3].shape}")
    print(f"t.view(-1): {t.view(-1).shape}")       # 展平
    print(f"t.reshape(2, 10): {t.reshape(2, 10).shape}")  # 重塑

    # 广播运算
    a = torch.tensor([[1], [2], [3]])  # (3,1)
    b = torch.tensor([10, 20, 30])     # (3,)
    print(f"broadcast add:\n{a + b}")

    return device


# ═══════════════════════════════════════════════════════════════
# Part 2: Autograd 自动求导
# ═══════════════════════════════════════════════════════════════
def part2_autograd():
    """自动求导机制 — 理解 backward() 和梯度."""
    import torch

    # 基本用法：requires_grad=True
    x = torch.tensor([2.0, 3.0], requires_grad=True)
    y = x ** 2 + 3 * x
    loss = y.sum()
    loss.backward()  # 反向传播
    print(f"x: {x}")
    print(f"y: {y}")
    print(f"loss: {loss.item()}")
    print(f"gradient dy/dx: {x.grad}")
    # 理论: dy/dx = 2x + 3, 在 x=[2,3] 处 = [7, 9] ✓

    # 清除梯度
    x.grad.zero_()

    # 链式法则示例
    a = torch.tensor(2.0, requires_grad=True)
    b = torch.tensor(3.0, requires_grad=True)
    z = (a ** 2) * torch.sin(b)
    z.backward()
    print(f"dz/da = {a.grad:.4f}")  # 2*a*sin(b) = 4*0.1411
    print(f"dz/db = {b.grad:.4f}")  # a^2*cos(b) = 4*(-0.99)

    # no_grad 模式：推理时不需要梯度
    with torch.no_grad():
        y_eval = x ** 2 + 3 * x
        print(f"no_grad: {y_eval}")


# ═══════════════════════════════════════════════════════════════
# Part 3: nn.Module + MLP
# ═══════════════════════════════════════════════════════════════
def part3_mlp_module():
    """用 nn.Module 构建一个多层感知机."""
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    class MLP(nn.Module):
        """两层 MLP: input -> hidden (ReLU) -> output."""
        def __init__(self, input_dim, hidden_dim, output_dim):
            super().__init__()
            self.fc1 = nn.Linear(input_dim, hidden_dim)
            self.fc2 = nn.Linear(hidden_dim, output_dim)

        def forward(self, x):
            x = F.relu(self.fc1(x))
            x = self.fc2(x)
            return x

    # 实例化
    model = MLP(input_dim=4, hidden_dim=32, output_dim=1)
    print(f"Model:\n{model}")
    print(f"Parameters: {sum(p.numel() for p in model.parameters())}")

    # 前向传播
    x = torch.randn(10, 4)  # batch=10, features=4
    y = model(x)
    print(f"Input: {x.shape}, Output: {y.shape}")

    return model


# ═══════════════════════════════════════════════════════════════
# Part 4: MLP 功率预测（燃料电池功率预测）
# ═══════════════════════════════════════════════════════════════
def part4_power_prediction():
    """
    用 PyTorch MLP 做 FC 功率预测。
    任务：根据历史功率序列，预测下一时刻的燃料电池功率。
    """
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    # ---- 生成模拟数据 ----
    np.random.seed(42)
    t = np.linspace(0, 100, 1000)
    power = 30 + 15 * np.sin(0.1 * t) + 5 * np.sin(0.5 * t) + np.random.randn(1000) * 2
    power = np.clip(power, 10, 80)

    # ---- 构建时序样本 ----
    def create_sequences(data, seq_len=10):
        X, y = [], []
        for i in range(len(data) - seq_len):
            X.append(data[i:i + seq_len])
            y.append(data[i + seq_len])
        return np.array(X), np.array(y)

    SEQ_LEN = 10
    X, y = create_sequences( power, SEQ_LEN)
    split = int(0.8 * len(X))
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    #unsqueeze 加一个维度
    X_train_t = torch.tensor(X_train, dtype=torch.float32).unsqueeze(-1)
    y_train_t = torch.tensor(y_train, dtype=torch.float32).unsqueeze(-1)
    X_test_t = torch.tensor(X_test, dtype=torch.float32).unsqueeze(-1)
    y_test_t = torch.tensor(y_test, dtype=torch.float32).unsqueeze(-1)
    print(f"Train: {X_train_t.shape}, Test: {X_test_t.shape}")

    # ---- 定义 MLP 模型 ----
    class PowerPredictor(nn.Module):
        def __init__(self, seq_len, hidden=64):
            super().__init__()
            self.fc1 = nn.Linear(seq_len, hidden)
            self.fc2 = nn.Linear(hidden, hidden)
            self.fc3 = nn.Linear(hidden, 1)
            self.dropout = nn.Dropout(0.1)

        def forward(self, x):
            x = x.view(x.size(0), -1)
            x = F.relu(self.fc1(x))
            x = self.dropout(x)
            x = F.relu(self.fc2(x))
            x = self.fc3(x)
            return x

    model = PowerPredictor(SEQ_LEN, hidden=64)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    loss_fn = nn.MSELoss()

    # ---- 训练 ----
    n_epochs = 200
    train_losses = []
    for epoch in range(n_epochs):
        model.train()
        optimizer.zero_grad()
        y_pred = model(X_train_t)
        loss = loss_fn(y_pred, y_train_t)
        loss.backward()
        optimizer.step()
        train_losses.append(loss.item())
        if (epoch + 1) % 50 == 0:
            model.eval()
            with torch.no_grad():  #测试
                test_loss = loss_fn(model(X_test_t), y_test_t)
            print(f"Epoch {epoch+1:3d}: train_loss={loss.item():.6f}, test_loss={test_loss.item():.6f}")

    # ---- 评估 ----
    model.eval()
    with torch.no_grad():
        y_pred = model(X_test_t).numpy().flatten()
        y_true = y_test
    mae = np.mean(np.abs(y_pred - y_true))
    rmse = np.sqrt(np.mean((y_pred - y_true) ** 2))
    print(f"\nTest MAE: {mae:.3f} kW, RMSE: {rmse:.3f} kW")

    # ---- 可视化 ----
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))
    axes[0].plot(train_losses)
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("MSE Loss")
    axes[0].set_title("Training Loss")
    axes[0].grid(True)
    axes[1].plot(y_true[:200], label="True", alpha=0.7)
    axes[1].plot(y_pred[:200], label="Predicted", alpha=0.7)
    axes[1].set_xlabel("Time Step")
    axes[1].set_ylabel("FC Power (kW)")
    axes[1].set_title(f"FC Power Prediction (MAE={mae:.2f} kW, RMSE={rmse:.2f} kW)")
    axes[1].legend()
    axes[1].grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, "week9_complete_mlp_power_prediction.png"), dpi=150)
    plt.close()
    print(f"Saved: {RESULTS_DIR}/week9_complete_mlp_power_prediction.png")

    return model


# ═══════════════════════════════════════════════════════════════
# Part 5: MDP 五元组 — GridWorld
# ═══════════════════════════════════════════════════════════════
def part5_mdp_gridworld():
    """
    GridWorld MDP:
      4×4 网格, 起点 (0,0), 终点 (3,3) +1, 陷阱 (1,1) -1
      动作: ↑ ↓ ← →   (随机移动: 80% 目标方向, 20% 随机)
      折扣因子 γ = 0.9
    """
    SIZE = 4
    n_states = SIZE * SIZE
    actions = ['↑', '↓', '←', '→']
    n_actions = len(actions)
    gamma = 0.9

    GOAL = (3, 3)
    TRAP = (1, 1)
    GOAL_IDX = GOAL[0] * SIZE + GOAL[1] #15  pos_to_idx
    TRAP_IDX = TRAP[0] * SIZE + TRAP[1] #5   pos_to_idx

    action_delta = {
        '↑': (-1, 0), '↓': (1, 0),
        '←': (0, -1), '→': (0, 1),
    }

    def pos_to_idx(r, c):
        return r * SIZE + c

    def is_valid(r, c):
        return 0 <= r < SIZE and 0 <= c < SIZE

    R = {s: {a: 0.0 for a in range(n_actions)} for s in range(n_states)}
    P = {s: {a: {} for a in range(n_actions)} for s in range(n_states)}

    for r, c in itertools.product(range(SIZE), range(SIZE)):  #双重遍历16
        s = pos_to_idx(r, c)
        if s == GOAL_IDX or s == TRAP_IDX:
            for a in range(n_actions):
                R[s][a] = 1.0 if s == GOAL_IDX else -1.0
                P[s][a][s] = 1.0
            continue
        for a_idx, (action_name, (dr, dc)) in enumerate(action_delta.items()):
            nr, nc = r + dr, c + dc
            if not is_valid(nr, nc):
                nr, nc = r, c
            target_s = pos_to_idx(nr, nc)
            R[s][a_idx] = 0.0
            P[s][a_idx][target_s] = P[s][a_idx].get(target_s, 0) + 0.8
            for other_dr, other_dc in action_delta.values():
                if (other_dr, other_dc) == (dr, dc):
                    continue
                nr2, nc2 = r + other_dr, c + other_dc
                if not is_valid(nr2, nc2):
                    nr2, nc2 = r, c
                other_s = pos_to_idx(nr2, nc2)
                P[s][a_idx][other_s] = P[s][a_idx].get(other_s, 0) + 0.2 / 3

    print(f'[Part 5] GridWorld MDP: {n_states} 状态 × {n_actions} 动作')
    print(f'  起点 (0,0), 终点 {GOAL} (+1), 陷阱 {TRAP} (-1)')
    print(f'  折扣因子 γ = {gamma}')
    print(f'  随机转移: 80% 目标方向, 20% 随机方向')

    return {
        'SIZE': SIZE, 'n_states': n_states, 'n_actions': n_actions,
        'actions': actions, 'gamma': gamma,
        'GOAL_IDX': GOAL_IDX, 'TRAP_IDX': TRAP_IDX,
        'R': R, 'P': P, 'pos_to_idx': pos_to_idx,
    }


# ═══════════════════════════════════════════════════════════════
# Part 6: Bellman 方程
# ═══════════════════════════════════════════════════════════════
def part6_bellman(mdp):
    """用 Bellman 方程计算 V(s) 和 Q(s,a)"""
    n_states = mdp['n_states']   #16
    n_actions = mdp['n_actions'] #4
    gamma = mdp['gamma']
    R = mdp['R']
    P = mdp['P']

    # 随机策略  4个0.25
    policy = np.ones((n_states, n_actions)) / n_actions

    # 策略评估：迭代求解 V^π
    V = np.zeros(n_states)
    theta = 1e-6
    max_iter = 1000  #迭代轮次最大值
    for i in range(max_iter):
        delta = 0
        for s in range(n_states):
            v_old = V[s]
            v_new = 0
            for a in range(n_actions):
                p_a = policy[s, a]  #a是代表动作，有80%几率走对，20%几率走错方向
                if p_a == 0:
                    continue
                bellman_sum = R[s][a]
                for s_next, prob in P[s][a].items():
                    bellman_sum += gamma * prob * V[s_next]  #下一步方向可能性*衰减系数
                v_new += p_a * bellman_sum
            V[s] = v_new
            delta = max(delta, abs(v_old - v_new))
        if delta < theta:
            break
#外层 p_a是"我有多大概率选这个动作"，内层 prob是"选了之后环境有多大概率把我送到某个状态"
    # 最优值函数 V*
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
            V_opt[s] = max(q_values)  #可以选择方向
            delta = max(delta, abs(v_old - V_opt[s]))
        if delta < theta:
            break

    print(f'\n[Part 6] Bellman 方程')
    print(f'  随机策略 V(s) 收敛于 {i+1} 次迭代')
    print(f'  起点 V(0)     = {V[0]:.4f}')
    print(f'  最优 V*(0)    = {V_opt[0]:.4f}')

    # ---- 画 V(s) heatmap ----
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
    path = os.path.join(RESULTS_DIR, 'week9_complete_bellman_value.png')
    plt.savefig(path, dpi=150)
    plt.close()
    print(f'  图: {path}')

    return {'V_pi': V, 'V_opt': V_opt}


# ═══════════════════════════════════════════════════════════════
# Part 7: 策略迭代
# ═══════════════════════════════════════════════════════════════
def part7_policy_iteration(mdp):
    """策略迭代: 策略评估 → 策略改进 → 直到收敛"""
    n_states = mdp['n_states']
    n_actions = mdp['n_actions']
    gamma = mdp['gamma']
    R = mdp['R']
    P = mdp['P']
    #随机初始化策略。对每个状态随机选一个动作（0-3），是确定性策略
    policy = np.random.randint(0, n_actions, size=n_states)
    V = np.zeros(n_states)

    def policy_evaluation(policy, V, theta=1e-6):
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
        policy_stable = True
        for s in range(n_states):
            old_action = policy[s]
            q_values = []
            for a in range(n_actions):
                q = R[s][a]
                for s_next, prob in P[s][a].items():
                    q += gamma * prob * V[s_next]
                q_values.append(q)
            policy[s] = int(np.argmax(q_values))  #选 Q 值最大的动作。
            if old_action != policy[s]:
                policy_stable = False
        return policy, policy_stable

    print(f'\n[Part 7] 策略迭代')
    for iteration in range(50):
        V = policy_evaluation(policy, V)
        policy, stable = policy_improvement(policy, V)
        if stable:
            print(f'  第 {iteration+1} 轮: 收敛 [OK]')
            break
        else:
            print(f'  第 {iteration+1} 轮: 策略改进中...')

    action_symbols = {0: '↑', 1: '↓', 2: '←', 3: '→'}
    SIZE = mdp['SIZE']
    print(f'\n  最优策略:')
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

    # ---- 画最优策略 ----
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
    path = os.path.join(RESULTS_DIR, 'week9_complete_optimal_policy.png')
    plt.savefig(path, dpi=150)
    plt.close()
    print(f'  图: {path}')

    return {'policy': policy, 'V': V}


# ═══════════════════════════════════════════════════════════════
# Part 8: 值迭代
# ═══════════════════════════════════════════════════════════════
def part8_value_iteration(mdp):
    """值迭代: 直接迭代 Bellman 最优方程"""
    n_states = mdp['n_states']
    n_actions = mdp['n_actions']
    gamma = mdp['gamma']
    R = mdp['R']
    P = mdp['P']

    V = np.zeros(n_states)
    theta = 1e-6

    print(f'\n[Part 8] 值迭代')
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
    SIZE = mdp['SIZE']
    print(f'  最优策略:')
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

    print(f'\n  值迭代 V*(0) = {V[0]:.4f}')

    return {'V': V, 'policy': policy}


# ═══════════════════════════════════════════════════════════════
# Extra: 收敛过程可视化
# ═══════════════════════════════════════════════════════════════
def extra_convergence_plot():
    """演示值迭代收敛速度"""
    mdp = part5_mdp_gridworld()
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
    axes[0].plot(V_track[:, 0], 'b-', linewidth=1.5, label='Start (0,0)')
    axes[0].plot(V_track[:, mdp['GOAL_IDX']], 'g-', linewidth=1.5, label=f'Goal {mdp["GOAL_IDX"]}')
    axes[0].plot(V_track[:, mdp['TRAP_IDX']], 'r-', linewidth=1.5, label=f'Trap {mdp["TRAP_IDX"]}')
    axes[0].set_xlabel('Iteration')
    axes[0].set_ylabel('V(s)')
    axes[0].set_title('Value Iteration Convergence')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    deltas = [np.max(np.abs(V_track[i+1] - V_track[i])) for i in range(len(V_track)-1)]
    axes[1].plot(deltas, 'k-', linewidth=1.0)
    axes[1].set_xlabel('Iteration')
    axes[1].set_ylabel('Max ΔV')
    axes[1].set_title('Convergence: Max Change per Iteration')
    axes[1].set_yscale('log')
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(RESULTS_DIR, 'week9_complete_value_iteration_convergence.png')
    plt.savefig(path, dpi=150)
    plt.close()
    print(f'\n[Convergence] 图: {path}')
    print(f'  值迭代 {len(V_track)} 次收敛, 起点 V(0): {V_track[-1,0]:.4f}')


# ═══════════════════════════════════════════════════════════════
# 主程序
# ═══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    # 通知模式
    if args.part > 0:
        print(f'>> 单 Part 模式: 只跑 Part {args.part}\n')
    else:
        print('=' * 60)
        print('  Week 9 — PyTorch + RL 基础 完整通关')
        print('  Part 1-4: PyTorch 入门')
        print('  Part 5-8: RL 基础 (MDP / Bellman / 策略迭代 / 值迭代)')
        print('=' * 60)

    # 占位变量（处理 Part 间依赖）
    mdp = None; pi_result = None; vi_result = None

    # ── PyTorch 篇 ──
    if should_run(1):
        print('\n' + '=' * 60)
        print('Part 1: Tensor 基础')
        print('=' * 60)
        device = part1_tensor_basics()

    if should_run(2):
        print('\n' + '=' * 60)
        print('Part 2: Autograd 自动求导')
        print('=' * 60)
        part2_autograd()

    if should_run(3):
        print('\n' + '=' * 60)
        print('Part 3: nn.Module + MLP')
        print('=' * 60)
        model = part3_mlp_module()

    if should_run(4):
        print('\n' + '=' * 60)
        print('Part 4: MLP 功率预测')
        print('=' * 60)
        predictor = part4_power_prediction()

    # ── RL 基础篇 ──
    if should_run(5):
        print('\n' + '=' * 60)
        print('Part 5: MDP 五元组 — GridWorld')
        print('=' * 60)
        mdp = part5_mdp_gridworld()

    # Part 6-8 依赖 Part 5 的 mdp；单独跑时自动触发 Part 5
    if args.part in (6, 7, 8) and mdp is None:
        print('\n  [auto] Part 6-8 依赖 Part 5 的 MDP，先跑 Part 5...')
        mdp = part5_mdp_gridworld()

    if should_run(6):
        print('\n' + '=' * 60)
        print('Part 6: Bellman 方程')
        print('=' * 60)
        values = part6_bellman(mdp)

    if should_run(7):
        print('\n' + '=' * 60)
        print('Part 7: 策略迭代')
        print('=' * 60)
        pi_result = part7_policy_iteration(mdp)

    if should_run(8):
        print('\n' + '=' * 60)
        print('Part 8: 值迭代')
        print('=' * 60)
        vi_result = part8_value_iteration(mdp)

    # ── Extra（仅全部跑时附带；单 Part 模式不跑）──
    if args.part == 0:
        print('\n' + '=' * 60)
        print('Extra: 收敛过程可视化')
        print('=' * 60)
        extra_convergence_plot()

    # ── 验证（仅全部跑或同时有 Part 7+8）──
    if args.part == 0 or (args.part in (7, 8) and pi_result and vi_result):
        if pi_result and vi_result:
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
                print('  ⚠️ 有偏差, 检查收敛容差')

    print(f'\n  Part {args.part if args.part > 0 else "1-8"} 完成！[OK]')
