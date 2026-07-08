#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Week 9 — PyTorch 入门
====================
Part 1: Tensor 基础
Part 2: Autograd 自动求导
Part 3: nn.Module + MLP
Part 4: 用 MLP 做 FC 功率预测

前置: pip install torch
"""

import numpy as np

# ============================================================
# Part 1: Tensor 基础
# ============================================================
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


# ============================================================
# Part 2: Autograd 自动求导
# ============================================================
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


# ============================================================
# Part 3: nn.Module + MLP
# ============================================================
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


# ============================================================
# Part 4: MLP 功率预测（燃料电池功率预测）
# ============================================================
def part4_power_prediction():
    """
    用 PyTorch MLP 做 FC 功率预测。
    任务：根据历史功率序列，预测下一时刻的燃料电池功率。
    """
    import torch
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    # ---- 生成模拟数据 ----
    # 用正弦波 + 噪声模拟 FC 功率信号
    np.random.seed(42)
    t = np.linspace(0, 100, 1000)
    power = 30 + 15 * np.sin(0.1 * t) + 5 * np.sin(0.5 * t) + np.random.randn(1000) * 2
    power = np.clip(power, 10, 80)  # FC 功率范围 [10, 80] kW

    # ---- 构建时序样本 ----
    def create_sequences(data, seq_len=10):
        X, y = [], []
        for i in range(len(data) - seq_len):
            X.append(data[i:i + seq_len])
            y.append(data[i + seq_len])
        return np.array(X), np.array(y)

    SEQ_LEN = 10
    X, y = create_sequences(power, SEQ_LEN)

    # 划分训练/测试
    split = int(0.8 * len(X))
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    # 转为 tensor
    X_train_t = torch.tensor(X_train, dtype=torch.float32).unsqueeze(-1)  # (N, seq, 1)
    y_train_t = torch.tensor(y_train, dtype=torch.float32).unsqueeze(-1)
    X_test_t = torch.tensor(X_test, dtype=torch.float32).unsqueeze(-1)
    y_test_t = torch.tensor(y_test, dtype=torch.float32).unsqueeze(-1)

    print(f"Train: {X_train_t.shape}, Test: {X_test_t.shape}")

    # ---- 定义 MLP 模型 ----
    class PowerPredictor(nn.Module):
        """用过去 SEQ_LEN 步预测下一步 FC 功率."""
        def __init__(self, seq_len, hidden=64):
            super().__init__()
            self.fc1 = nn.Linear(seq_len, hidden)
            self.fc2 = nn.Linear(hidden, hidden)
            self.fc3 = nn.Linear(hidden, 1)
            self.dropout = nn.Dropout(0.1)

        def forward(self, x):
            x = x.view(x.size(0), -1)  # flatten
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
            with torch.no_grad():
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

    # 损失曲线
    axes[0].plot(train_losses)
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("MSE Loss")
    axes[0].set_title("Training Loss")
    axes[0].grid(True)

    # 预测 vs 真实
    axes[1].plot(y_true[:200], label="True", alpha=0.7)
    axes[1].plot(y_pred[:200], label="Predicted", alpha=0.7)
    axes[1].set_xlabel("Time Step")
    axes[1].set_ylabel("FC Power (kW)")
    axes[1].set_title(f"FC Power Prediction (MAE={mae:.2f} kW, RMSE={rmse:.2f} kW)")
    axes[1].legend()
    axes[1].grid(True)

    plt.tight_layout()
    plt.savefig("results/week9_mlp_power_prediction.png", dpi=150)
    print("Saved: results/week9_mlp_power_prediction.png")

    return model


if __name__ == "__main__":
    print("=" * 60)
    print("Part 1: Tensor 基础")
    print("=" * 60)
    device = part1_tensor_basics()

    print("\n" + "=" * 60)
    print("Part 2: Autograd 自动求导")
    print("=" * 60)
    part2_autograd()

    print("\n" + "=" * 60)
    print("Part 3: nn.Module + MLP")
    print("=" * 60)
    model = part3_mlp_module()

    print("\n" + "=" * 60)
    print("Part 4: MLP 功率预测")
    print("=" * 60)
    predictor = part4_power_prediction()

    print("\n✅ Week 9 Part 1-4 done! 下一步：RL 基础 (MDP/Bellman)")
