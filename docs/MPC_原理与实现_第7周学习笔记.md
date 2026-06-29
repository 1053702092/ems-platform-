# MPC 模型预测控制在燃料电池 EMS 中的应用

> 第7周学习笔记 | 2026-06-29
> 与 DP/ECMS 对齐同一个 EMS 模型，便于后续四方法对比

---

## 1. MPC 是什么？一句话理解

MPC（Model Predictive Control，模型预测控制）的核心思想是：

> **"每次做决策时，都往未来看 N 步，选一条让总代价最小的控制序列。每走一步，重新往未来看。"**

这和 DP 的区别：
- **DP**：看**整个**未来（全局），需要**已知**全部工况
- **MPC**：看**有限**未来（预测），可以**在线滚动**更新

ECMS 是"看一步"，DP 是"看全部"，MPC 是"看 N 步"。

---

## 2. MPC 数学框架

### 2.1 优化问题表述

在每个时刻 k，MPC 求解以下优化问题：

```
min J = Σ_{i=0}^{N_p-1} L(P_fc[k+i], SOC[k+i]) + V(SOC[k+N_p])

约束：
  SOC[k+i+1] = f(SOC[k+i], P_fc[k+i], P_load[k+i])   状态方程
  P_fc_min ≤ P_fc[k+i] ≤ P_fc_max                      控制约束
  SOC_min ≤ SOC[k+i] ≤ SOC_max                         状态约束
  SOC[k] = SOC_current                                 初始条件
```

其中：
- **N_p** = 预测时域（prediction horizon），通常 10~100 步
- **L** = 瞬时代价（instantaneous cost），即氢耗率
- **V** = 终端代价（terminal cost），近似未来剩余代价
- **N_t** = 控制时域（control horizon），通常 N_t ≤ N_p

### 2.2 瞬时代价函数

```
L(P_fc[k], SOC[k]) = ṁ_H2(P_fc[k]) + w_soc · (SOC[k] - SOC_ref)²
```

- ṁ_H2 = P_fc / (η_fc · LHV_H2) — 氢耗率 [g/s]
- w_soc — SOC 维持惩罚权重（类似 DP 中的 α）

### 2.3 预测模型

使用与 DP/ECMS 相同的电池模型：

```
P_bat[k] = P_load[k] - P_fc[k]
V_oc = f(SOC[k])               # 开路电压查表
I[k] = (V_oc - √(V_oc² - 4·R_int·P_bat[k]·1000)) / (2·R_int)
SOC[k+1] = SOC[k] - I[k] / (Q_bat · 3600) · Δt
```

**关键区别**：MPC 需要在每个时刻同时预测多步的状态转移，因此预测模型需要**向量化**。

### 2.4 预测工况 — MPC 的灵魂

MPC 需要一个**未来功率需求的预测值** P_load_predicted[0:N_p]。常见来源：

| 预测方式 | 精度 | 复杂度 | 适用场景 |
|---------|------|--------|---------|
| **已知工况（离线）** | 最高 | 低 | 仿真验证、与 DP/ECMS 对比 |
| **匀速+加速度外推** | 低 | 低 | 实时性要求高 |
| **历史窗口平滑** | 中 | 中 | 周期性工况（如公交路线） |
| **LSTM/Transformer** | 高 | 高 | 算力充足的嵌入式平台 |

**第7周实现采用"已知工况"**（与 DP/ECMS 公平对比），后续可扩展。

---

## 3. MPC 求解方法

### 3.1 方法选择

| 方法 | 适用性 | 说明 |
|------|--------|------|
| **网格搜索（离散优化）** | ✅ 适合本场景 | 与 DP/ECMS 一致，在 P_fc 网格上搜索最优 |
| **SQP（序列二次规划）** | ✅ 高效 | 连续优化器，适合实时部署 |
| **CasADi + IPOPT** | ✅ 通用 | 符号优化，灵活但依赖重 |
| **直接法（NLP）** | ✅ 工业标准 | 将连续问题离散化为非线性规划 |

**第7周实现采用网格搜索法**，与 DP/ECMS 对齐，便于理解 MPC 与 DP/ECMS 的本质区别。

### 3.2 网格搜索 MPC 伪代码

```python
for k in range(N):
    # 1. 获取当前 SOC 和预测工况
    soc_k = soc_current
    p_load_pred = p_load[k : k + N_p]    # 未来 N_p 步预测
    
    # 2. 枚举所有可能的控制序列（简化：只选当前步 P_fc）
    best_j = argmin_j J_total
    for each j in P_fc_grid:
        # 向前仿真 N_p 步
        soc_pred = [soc_k]
        J_total = 0
        for i in range(N_p):
            p_fc_pred = j  # 简化：整段预测期用同一控制量
            p_bat_pred = p_load_pred[i] - p_fc_pred
            soc_next = step_model(soc_pred[-1], p_fc_pred, p_load_pred[i])
            
            # 累计代价
            h2 = hydrogen_flow(p_fc_pred)
            soc_penalty = w_soc * (soc_next - soc_ref)**2
            J_total += h2 + soc_penalty
        
        # 加终端 SOC 惩罚
        J_total += V_terminal(soc_pred[-1])
        
        if J_total < J_best:
            J_best = J_total
            best_j = j
    
    # 3. 只取第一步（receding horizon）
    p_fc[k] = P_FC_GRID[best_j]
    soc[k+1] = update(soc[k], p_fc[k], p_load[k])
```

**关键理解**：
- 上面是"简化版"MPC：每步只优化当前时刻的 P_fc
- 完整版 MPC 会同时优化未来 N_t 步的 P_fc 序列（N_t × N_p 维优化）
- 但在能量管理场景中，由于工况预测精度有限，N_t=1 通常就够了

---

## 4. MPC vs DP vs ECMS 对比

### 4.1 核心差异

| 特性 | DP | MPC | ECMS |
|------|----|-----|------|
| 时域 | 全局（全部 N 步） | 有限（N_p 步） | 瞬时（1 步） |
| 工况需求 | 完整已知 | 预测值 | 不需要 |
| 在线性 | ❌ 离线 | ⚠️ 滚动优化 | ✅ 实时 |
| 最优性 | 全局最优 | 次优（取决于预测） | 近似最优 |
| 计算量 | 高 | 中 | 低 |
| 等效因子 | 无 | 无 | 有（s 或 s(k)） |
| 实时部署 | 不现实 | 可行（简化后） | 最合适 |

### 4.2 统一视角：Hamiltonian 最小化

三种方法本质上都等价于最小化 Hamiltonian：

```
H = ṁ_H2(P_fc) + λ · f_SOC(SOC, P_fc, P_load)
```

- **DP**：λ = ∂J*/∂SOC（精确 costate，后向递推得到）
- **MPC**：λ = ∂V/∂SOC（终端代价的梯度）
- **ECMS**：λ = s（恒定的等效因子）
- **A-ECMS**：λ = s(k)（自适应等效因子 = s₀ + Kp·(SOC_ref - SOC)）

**洞察**：自适应 ECMS 的 s(k) 实际上是在**在线估计** MPC 的 costate λ！

---

## 5. MPC 的关键设计选择

### 5.1 预测时域 N_p 的选择

- **N_p < 10**：太短，看不出预测优势，退化为类似 ECMS
- **N_p = 30~60**：推荐，覆盖典型功率波动周期
- **N_p → ∞**：趋近 DP，但计算量爆炸

**经验**：N_p ≈ N/10 ~ N/5 时性价比最优（N 为工况总长度）。

### 5.2 终端代价 V(SOC)

MPC 需要终端代价来"引导"预测期末尾的 SOC 走向。常用选择：

```
V(SOC) = β · (SOC - SOC_ref)²
```

- β = 0：没有终端引导（MPC 可能"短视"）
- β > 0：类似 DP 的终端惩罚
- β 的选取影响 MPC 的全局性能，经验值 β ∈ [500, 2000]

### 5.3 工况预测误差的影响

这是 MPC 与 DP/ECMS 最根本的差异：

| 预测误差 | 对 MPC 的影响 |
|---------|-------------|
| 无误差（已知工况）| MPC ≈ DP（N_p → N 时）|
| 小误差（±10%）| MPC 氢耗增加 1~3% |
| 大误差（±30%）| MPC 氢耗增加 5~10% |
| 完全错误 | MPC 可能比 ECMS 还差 |

**这就是为什么实际车辆上，ECMS 比 MPC 更稳健**：ECMS 不依赖预测，自然不受预测误差影响。

---

## 6. MPC 的优缺点总结

### 优点
1. **在线可用**：可以滚动优化，适应工况变化
2. **约束处理**：天然支持状态/控制约束
3. **可扩展**：预测模型可以加燃料电池寿命项、电池热模型等
4. **理论清晰**：NLP 框架，有成熟的求解器

### 缺点
1. **依赖预测精度**：预测错了，优化也白搭
2. **计算负担**：每一步都要解优化问题，嵌入式平台可能吃力
3. **调参多**：N_p、N_t、权重、终端代价都要调
4. **不是全局最优**：局部滚动 ≠ 全局最优

### 与 ECMS 的关系

| 场景 | 推荐 |
|------|------|
| 工况可精确预测（固定路线）| MPC > ECMS |
| 工况随机性强 | ECMS > MPC |
| 算力充足 | MPC（可加更多约束/模型） |
| 算力有限 + 鲁棒性 | ECMS |
| 两者结合 | **MPC 提供参考等效因子 → A-ECMS 执行** |

---

## 7. 本实现的技术方案

### 7.1 模型

复用 `day8_dp_ems.py` 的：
- `vehicle_power` — 功率需求
- `state_transition` — 电池 SOC 转移
- `fc_hydrogen_flow` — 氢耗模型

### 7.2 预测模型

**已知工况预测**：`p_load_pred[i] = p_load[k + i]`（未来 N_p 步直接取真实值）

### 7.3 优化方法

**单步网格搜索**：在 P_fc 网格上枚举，选择使预测期总代价最小的控制量。

### 7.4 关键参数

```python
N_P = 50          # 预测时域（可扫描）
W_SOC = 100.0     # SOC 维持惩罚权重
BETA_TERM = 500.0  # 终端 SOC 惩罚系数
```

### 7.5 输出

与 DP/ECMS 一致的仿真结果：SOC、P_fc、P_bat、氢耗累积，并绘制对比图。

---

## 8. 扩展方向（后续周）

1. **MPC + 工况预测**：用历史窗口均值/LSTM 替代已知工况
2. **多目标 MPC**：加入 FC 寿命约束（功率变化率惩罚）
3. **鲁棒 MPC**：考虑预测不确定性区间
4. **MPC 参考等效因子**：MPC 计算出 s_ref → A-ECMS 跟踪

---

## 参考文献

1. Sciarretta, M., & Guzzella, L. (2007). *Control of Hybrid Electric Vehicles*. European Journal of Control.
   - MPC 能量管理的经典框架
2. Errqaz, M., et al. (2018). *Long-Short Term Memory for Speed and Load Forecasting in FCEV Energy Management*. 
   - MPC + LSTM 预测的实用方案
3. Zhang, Y., et al. (2022). *Model Predictive Control for Fuel Cell Hybrid Electric Vehicles: A Review*.
   - FCEV MPC 综述，对比各种预测模型和求解器

---

*文档生成：2026-06-29 | 第7周 MPC 学习*
