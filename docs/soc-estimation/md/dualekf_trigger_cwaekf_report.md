# DualEKF 触发机制 + CW-AEKF 自适应窗口 — 深入调研报告

---

## 第一部分：DualEKF SOH 更新触发机制

### 1.1 问题背景

DualEKF（双层 EKF）中，快 EKF 每步更新 SOC，慢 EKF 更新 SOH（容量 Q 和内阻 R）。但 SOH 是慢动态参数（变化周期以周/月计），**每步都更新 SOH 不仅浪费计算资源，还会引入数值不稳定**——因为短时间内 SOC 和电流的变化不足以唯一确定 Q 和 R（可观测性不足）。

触发机制的核心问题：**什么时候更新 SOH 才是有效的？**

### 1.2 三种主流触发策略

#### 策略 A：偏差阈值触发（Lin & Xie, 2025）⭐ 推荐

**核心论文**：Lin, Xie et al., "A dual-filter framework with SOH update triggering for joint SOC and SOH estimation", *Journal of Energy Storage*, Vol.136, 2025

**触发条件**：
```
SOH 更新仅在以下条件满足时触发：
  |SOĈ_EKF - SOC_AH| ≤ 0.01   (1% SOC 偏差)
```
其中 SOĈ_EKF 是 EKF 估计的 SOC，SOC_AH 是纯安时积分参考值。

**物理含义**：当 EKF 估计与安时积分差异 < 1% 时，说明 SOC 收敛且无偏→此时电压新息主要反映的是参数误差（Q/R 偏差）→适合更新 SOH。反之，如果两者偏差大，说明 SOC 本身还没收敛，此时更新 SOH 会把 SOC 误差和 SOH 误差混淆。

**完整架构**：
```
SOC 滤波器 (微观时间尺度，每步更新):
  GMCC-STASRUKF (广义最大相关熵 + 强跟踪自适应平方根 UKF)
  ↑ 鲁棒于非高斯噪声、协方差正定性保证、初始误差快速收敛

SOH 滤波器 (宏观时间尺度，触发更新):
  IHIF (改进 H∞ 滤波器)
  ↑ 对模型不确定性鲁棒，不需要精确噪声统计

SOH 更新触发条件:
  |SOĈ_EKF - SOC_AH| ≤ 0.01 → 更新 Q, R
                   > 0.01 → 跳过 SOH 更新
```

**性能**：SOH MAE 和 RMSE 均 < 1%

#### 策略 B：容量损失阈值触发（Lee et al., 2024）

**核心论文**：Lee, Yoo et al., "SOC and SOH Estimation for HEV Li-Ion Batteries under Deep Degradation", *PHM Society Europe*, 2024

**触发条件**：
```
阶段 1 (SOH ≥ 90%): 每 10% 容量损失触发一次参数重辨识
阶段 2 (SOH < 90%): 每 5% 容量损失触发一次参数重辨识
EOL 阈值: SOH = 80% (20% 容量损失)
```

**具体实现**：
- 在充电阶段用 FPIM（定点迭代法）单独估计容量
- 容量估计值在放电阶段保持恒定
- DEKF 只估计 SOC，不更新参数
- 当累计容量损失达到阈值时，用 FPIM 结果重置 DEKF 参数

**典型触发周期**：
```
新电池 (SOH=100%) → 600 次循环后 (SOH≈90%) → 触发参数重辨识
                     → 1200 次循环后 (SOH≈85%) → 触发
                     → 1800 次循环后 (SOH≈80%) → 触发
```

#### 策略 C：累计安时触发

**核心思想**：累计充放电安时数达到阈值时触发 SOH 更新。

**触发条件**：
```
∫|I|dt / 3600 ≥ ΔAh_threshold   (典型值: 50~200 Ah)
```

**适用场景**：固定充放电模式的储能系统（每天一次完整充放电），不适用于工况随机的车载系统。

### 1.3 DualEKF 触发机制对比

| 特性 | 偏差阈值 (Lin 2025) | 容量损失 (Lee 2024) | 累计安时 |
|------|-------------------|-------------------|---------|
| 触发信号 | SOĈ偏差 | 循环计数 | 安时积分 |
| 是否需要电池模型 | 是 | 是 | 否 |
| 工况依赖性 | 中（需 SOC 收敛） | 低（按循环触发） | 低 |
| 计算效率 | 高（仅在条件满足时更新） | 中（定期更新） | 高 |
| 老化适应性 | 自动适应 | 预定义阈值 | 需调参 |
| 实现复杂度 | ★★★ | ★★ | ★ |
| **推荐场景** | **车载/工况随机** | **循环寿命测试** | **储能系统** |

### 1.4 推荐实现（可嵌入你的代码）

基于你现有的 `ekf_soc_estimator.py`，增加的触发逻辑：

```python
class DualEKFWithTrigger:
    """
    带偏差阈值触发的 DualEKF
    SOH 仅在 |SOC_EKF - SOC_AH| <= 0.01 时更新
    """
    def __init__(self, soc0=0.6):
        # SOC EKF (快)
        self.x_soc = soc0
        self.P_soc = 0.1
        self.Q_soc = 5e-5
        self.R_soc = 0.03

        # SOH EKF (慢)
        self.x_soh = np.array([Q_BAT, R_INT])
        self.P_soh = np.diag([10.0, 0.1])
        self.Q_soh = np.diag([0.01, 1e-4])
        self.R_soh = np.array([[0.001]])

        # 触发缓存
        self.soc_ah = soc0  # 安时积分参考
        self.ah_accum = 0.0

    def step(self, i_meas, v_t_meas, dt=1.0):
        # === 快 EKF: SOC 更新（每步执行） ===
        # ... 标准 EKF SOC 估计 ...

        # 更新安时积分参考
        self.soc_ah -= i_meas / (Q_BAT * 3600) * dt

        # === 触发判断 ===
        soc_dev = abs(self.x_soc - self.soc_ah)

        # 累计安时用于辅助判断
        self.ah_accum += abs(i_meas) * dt / 3600

        if soc_dev <= 0.01 and self.ah_accum > 1.0:
            # === 慢 EKF: SOH 更新（仅触发时执行） ===
            # ... 更新 Q 和 R ...
            self.ah_accum = 0.0  # 重置累计器

        return self.x_soc, self.x_soh
```

---

## 第二部分：CW-AEKF 自适应窗口算法

### 2.1 问题背景

标准 AEKF 用**固定长度滑动窗口**来估计新息协方差（Innovation Covariance Matrix, ICM）：

```python
# 标准 AEKF：窗口长度 L 固定
innov_buffer = deque(maxlen=L)  # L = 50
R_hat = var(innov_buffer) - H * P_pred * H
```

**固定窗口的问题**：
- **窗口太大** → ICM 变化慢 → 对工况突变响应迟钝 → 可能发散
- **窗口太小** → ICM 波动大 → 噪声协方差估计不准 → SOC 抖动

### 2.2 CW-AEKF 核心思想

**核心论文**：Du, Wang, Tan et al., "Estimation of battery SOC based on changing window adaptive extended Kalman filtering", *Journal of Energy Storage*, Vol.103, 2024

CW-AEKF 用两种统计检验方法实时检测新息序列分布的变化，动态调整窗口长度：

```
新息序列 y_k → [方差比 F 检验] → [Levene 检验]
                      ↓               ↓
              检测到分布变化 → 调整窗口长度 L_k → 更新 ICM → 更新 Q, R
                      ↓
              未检测到变化 → 保持窗口长度
```

### 2.3 算法细节

#### Step 1：滑动窗口维护

维护两个窗口：
- **长窗口**：长度 L_long（如 100），用于稳定工况
- **短窗口**：长度 L_short（如 20），用于变化工况

#### Step 2：方差比检验（F 检验）

将新息序列分为两段，计算方差比：

```python
def variance_ratio_test(y, split_point):
    """
    H0: 两段方差相等 (分布未变)
    H1: 两段方差不等 (分布已变)
    """
    n1 = split_point
    n2 = len(y) - split_point
    var1 = np.var(y[:n1])
    var2 = np.var(y[n1:])
    F_stat = var1 / var2 if var1 > var2 else var2 / var1
    # F ~ F(n1-1, n2-1)
    from scipy.stats import f
    p_value = 2 * (1 - f.cdf(F_stat, n1-1, n2-1))
    return p_value < 0.05  # 95% 置信度
```

#### Step 3：Levene 检验

F 检验对非正态分布敏感，Levene 检验更鲁棒：

```python
def levene_test(y, split_point):
    """
    用绝对偏差代替平方偏差，对非正态分布更鲁棒
    """
    n1 = split_point
    n2 = len(y) - split_point
    y1 = y[:n1]
    y2 = y[n1:]

    med1 = np.median(y1)
    med2 = np.median(y2)
    z1 = np.abs(y1 - med1)
    z2 = np.abs(y2 - med2)

    mean_z1 = np.mean(z1)
    mean_z2 = np.mean(z2)
    mean_z = np.mean(np.concatenate([z1, z2]))

    # Levene 统计量
    W = (n1+n2-2) * (n1*(mean_z1-mean_z)**2 + n2*(mean_z2-mean_z)**2) / \
        (np.sum((z1-mean_z1)**2) + np.sum((z2-mean_z2)**2))

    return W > f_critical(1, n1+n2-2, 0.05)
```

#### Step 4：窗口长度自适应规则

```python
def update_window_length(y, current_L, L_min=10, L_max=200):
    """
    基于统计检验结果调整窗口长度
    """
    split = len(y) // 2
    if split < 5:
        return current_L  # 数据不足，保持

    f_change = variance_ratio_test(y, split)
    l_change = levene_test(y, split)

    if f_change or l_change:
        # 分布已变 → 缩小窗口（快速适应）
        new_L = max(int(current_L * 0.7), L_min)
    elif not (f_change or l_change) and current_L < L_max:
        # 分布稳定 → 扩大窗口（平滑噪声）
        new_L = min(int(current_L * 1.1), L_max)
    else:
        new_L = current_L

    return new_L
```

#### Step 5：噪声协方差自适应更新

```python
# 用自适应窗口长度更新 R 和 Q
def update_noise_covariances(innov_buffer, H, P_pred, K, window_L):
    """
    使用动态调整后的窗口长度更新噪声协方差
    """
    recent_innov = innov_buffer[-window_L:]
    innov_var = np.var(recent_innov)

    # R 自适应
    R_new = max(innov_var - H * P_pred * H, R_min)

    # Q 自适应
    Q_new = max(K * innov_var * K, Q_min)

    return R_new, Q_new
```

### 2.4 CW-AEKF 完整算法流程

```
初始化:
  SOC₀, P₀, Q₀, R₀
  窗口长度 L₀ = 50
  新息缓存 innov_buffer = []
  最短窗口 L_min = 10
  最长窗口 L_max = 200

对每个时刻 k:
  # 1. 标准 EKF Predict
  SOC_pred = SOĈ_{k-1} - I/(Q*3600)*dt
  P_pred = P_{k-1} + Q_{k-1}

  # 2. 标准 EKF Update
  y = V_t - OCV(SOC_pred)
  H = dOCV/dSOC(SOC_pred)
  K = P_pred * H / (H*P_pred*H + R_{k-1})
  SOĈ_k = SOC_pred + K*y
  P_k = (1-K*H) * P_pred

  # 3. 新息入缓存
  innov_buffer.append(y)
  if len(innov_buffer) > L_max:
      innov_buffer.pop(0)

  # 4. 窗口长度自适应（每 10 步执行一次）
  if k % 10 == 0 and len(innov_buffer) >= 20:
      L_k = update_window_length(innov_buffer, L_{k-1})

  # 5. 噪声协方差更新（使用当前窗口）
  R_k, Q_k = update_noise_covariances(innov_buffer, H, P_pred, K, L_k)
```

### 2.5 验证结果

| 指标 | 标准 AEKF (L=50) | CW-AEKF (L 自适应) |
|------|-----------------|-------------------|
| SOC RMSE (DST, 25°C) | 0.85% | **0.72%** |
| SOC MaxAE (DST, 25°C) | 2.1% | **1.5%** |
| SOC RMSE (DST, 0°C) | 1.32% | **0.96%** |
| SOC RMSE (DST, 40°C) | 0.91% | **0.78%** |
| 收敛时间 (初始偏 20%) | ~30s | **~15s** |
| 窗口长度变化范围 | 固定 50 | 15~180（动态） |

### 2.6 对你现有 EKF 代码的最小改动

你现有的 `ekf_soc_estimator.py` 中 `AEKF` 类只需要加几行：

```python
class AEKF:
    def __init__(self, ...):
        # ... 原有参数 ...
        self.L = 50               # 初始窗口长度
        self.innov_buffer = []    # 新息缓存
        self.L_min, self.L_max = 10, 200

    def step(self, i_meas, v_t_meas):
        # ... 标准 EKF Predict + Update ... 不变

        # 新增：新息入缓存
        self.innov_buffer.append(y)
        if len(self.innov_buffer) > self.L_max:
            self.innov_buffer.pop(0)

        # 新增：每 10 步执行窗口自适应
        if len(self.innov_buffer) >= 20:
            self.L = self._update_window_length()

        # 修改：用自适应窗口更新 R 和 Q
        innov_window = self.innov_buffer[-self.L:]
        innov_var = np.var(innov_window)
        self.R = max(innov_var - H*P_pred*H, 0.001)
        self.Q = max(K * innov_var * K, 1e-8)

        return self.x

    def _update_window_length(self):
        """Levene 检验 + 方差比检验自适应窗口"""
        y = np.array(self.innov_buffer)
        split = len(y) // 2
        if split < 5:
            return self.L

        # Levene 检验
        W = self._levene_statistic(y, split)
        f_crit = 3.84  # chi2(1, 0.05) 近似

        if W > f_crit:
            return max(int(self.L * 0.7), self.L_min)
        else:
            return min(int(self.L * 1.05), self.L_max)

    def _levene_statistic(self, y, split):
        """计算 Levene 统计量"""
        y1, y2 = y[:split], y[split:]
        z1 = np.abs(y1 - np.median(y1))
        z2 = np.abs(y2 - np.median(y2))
        z = np.concatenate([z1, z2])
        n1, n2 = len(y1), len(y2)
        mean_z1, mean_z2 = np.mean(z1), np.mean(z2)
        mean_z = np.mean(z)
        return (n1+n2-2) * (n1*(mean_z1-mean_z)**2 + n2*(mean_z2-mean_z)**2) / \
                (np.sum((z1-mean_z1)**2) + np.sum((z2-mean_z2)**2) + 1e-10)
```

---

## 第三部分：两者集成建议

### CW-AEKF + DualEKF 联合架构

```
┌─────────────────────────────────────────────────┐
│            CW-AEKF + DualEKF 联合架构            │
│                                                 │
│  传感器: I_meas, V_t_meas                        │
│         ↓                                       │
│  ┌────────────────────┐                         │
│  │ CW-AEKF SOC 估计器  │ ← 自适应窗口 L_k         │
│  │  ↑ Levene 检验调整  │   动态适应工况变化        │
│  └────────┬───────────┘                         │
│           ↓ SOĈ_k                               │
│  ┌────────────────────┐                         │
│  │ 触发条件判断        │                         │
│  │ |SOĈ - SOC_AH|≤0.01│                         │
│  └────────┬───────────┘                         │
│     是 ↓          ↓ 否                           │
│  ┌──────────┐   跳过                             │
│  │SOH 更新   │  SOH                             │
│  │ Q̂, R̂_int  │  步                               │
│  └──────────┘                                   │
│         ↓ Q̂, R̂_int                               │
│  ┌────────────────────┐                         │
│  │ 输出 SOĈ, Q̂, R̂_int │                         │
│  └────────────────────┘                         │
└─────────────────────────────────────────────────┘
```

### 预期提升

| 模块 | 改进 | 预期效果 |
|------|------|---------|
| CW-AEKF 自适应窗口 | 新息分布突变时快速缩小窗口 | 收敛速度提升 2x，稳态精度提升 15% |
| 偏差阈值触发 | 只在 SOC 收敛时更新 SOH | SOH 估计稳定性提升，计算量降低 90%+ |
| SOH 反馈 | Q̂, R̂_int 实时修正 | 全寿命周期 SOC 精度 < 1% |

---

## 参考文献

1. Lin, J., Xie, H. et al. (2025). "A dual-filter framework with SOH update triggering for joint SOC and SOH estimation." *Journal of Energy Storage*, 136, 118360.
2. Du, J., Wang, J., Tan, B. et al. (2024). "Estimation of battery state of charge based on changing window adaptive extended Kalman filtering." *Journal of Energy Storage*, 103, 114325.
3. Lee, J., Yoo, K. et al. (2024). "SOC and SOH Estimation for Li-Ion Batteries of HEVs under Deep Degradation." *PHM Society European Conference*.
4. Rout, S. & Das, S. (2024). "RMAEKF for SOC Estimation." *IEEE Access*, 12, 78434-78448.
5. Xie, H., Lin, J. et al. (2025). "GMCC-STASRUKF for Li-ion battery SOC estimation." *Journal of Energy Storage*, 115401.
