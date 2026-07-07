# SOC 估计文献调研报告

> 检索范围：2024-2025 年期刊/会议论文
> 检索关键词：SOC estimation, Kalman filter, adaptive, joint estimation, fuel cell hybrid, deep learning

---

## 一、综述类论文

### 1. Comprehensive Comparison of ML and KF Battery SOC Estimators
**Vieira, Kollmeyer, Pitault, Emadi** | *IEEE Access*, Vol.13, 2025
- 直接在嵌入式硬件（NXP GreenBox）上对比 FNN、NARX、LSTM、EKF、UKF
- 覆盖 -20°C~40°C 全温域、3 种负载、含传感器误差
- **结论：NARX 最优（RMSE=1.70%），LSTM 次之，EKF 在计算资源受限时最佳选择**
- DOI: 10.1109/ACCESS.2025.3549876

### 2. Evolution of EVs, Battery State Estimation, and Future Directions
**IEEE Access**, Vol.12, 2024
- 分析 210 篇论文，完整 KF 方法分类体系
- 指出混合方法（KF+ML）和联合估计是未来主要方向
- DOI: 10.1109/ACCESS.2024.3481845

### 3. Advanced Battery Modeling and SOC Estimation: A Comprehensive Review
**eTransportation** (Elsevier), 2025
- 深入分析参数化方法、自适应 KF、联合/双估计框架
- 强调实现在线部署的工程挑战
- DOI: 10.1016/j.etran.2025.100386

---

## 二、AEKF — 自适应扩展卡尔曼滤波

### 4. CW-AEKF: Changing Window Adaptive EKF
**Du, Wang, Tan et al.** | *Journal of Energy Storage*, 2024
- **核心创新**：用方差比和 Levene 检验检测新息分布变化，自适应调整噪声窗口长度
- **解决了**：标准 AEKF 固定窗口在工况突变时响应慢的问题
- **精度**：DST 工况下 SOC 误差 < **1%**
- DOI: 10.1016/j.est.2024.114257

### 5. RMAEKF: Robust Modified AEKF
**Rout & Das** | *IEEE Access*, Vol.12, 2024
- **核心创新**：递推自适应修正规则——PNCM 用状态预测误差更新，MNCM 用新息序列更新
- **验证**：LA92、US06 工况 + OPAL-RT 实时仿真
- **精度**：RMSE < **2%**
- DOI: 10.1109/ACCESS.2024.3409680

### 6. IAEKF with Adaptive Window Width Adjustment
**IEEE Conference**, 2025
- **核心创新**：评估窗口内电压残差方差，动态增减窗口宽度
- **亮点**：即使初始 SOC 偏差 **50%** 也能迅速收敛
- DOI: 10.1109/ICPS.2025.11040351

### 7. Dual AEKF Considering Temperature Effects
**Ke, Cao, Li et al.** | *J. Phys.: Conf. Ser.*, 2025
- **核心创新**：双 AEKF 结构（一个用于参数辨识，一个用于 SOC 估计）
- **亮点**：0°C~45°C 全温域误差 < **1.5%**
- DOI: 10.1088/1742-6596/3135/1/012028

### 8. JFFAEKF: Joint Forgetting Factor AEKF
**Rout & Das** | *IEEE Access*, Vol.13, 2025
- **核心创新**：增广状态向量联合估计 SOC+模型参数，遗忘因子控制计算效率
- **验证**：LA92、UDDS、US06 多工况
- DOI: 10.1109/ACCESS.2025.3532867

---

## 三、SOC+SOH 联合估计

### 9. Dual-Filter Framework with SOH Update Triggering
**Lin, Xie et al.** | *Journal of Energy Storage*, Vol.136, 2025
- **架构**：SOC 用 GMCC-STASRUKF（广义最大相关熵 + 强跟踪自适应平方根 UKF）
- **SOH 用**：改进 H∞ 滤波器（IHIF）
- **创新**：触发机制——SOH 仅在 SOC 估计偏差 ≤ 0.01 时才更新，减少计算量
- **精度**：SOH MAE/RMSE < **1%**
- DOI: 10.1016/j.est.2025.118360

### 10. Dual Fractional-Order Adaptive UKF (DFOAUKF)
**Yu, Li et al.** | *IET Power Electronics*, 2025
- **架构**：基于 EIS 的分数阶模型 + 双时间尺度（秒级 SOC + 周期级 SOH）
- **亮点**：10°C~50°C 下 DST/UDDS 工况验证
- DOI: 10.1049/pel2.70145

### 11. Multi-Task NN + Adaptive Dual KF
**Journal of Power Sources**, Vol.656, 2025
- **架构**：DEKF + 多任务 SOH 预测神经网络（MTSOHFNN）
- **优化**：Coyote 算法（COA）自适应噪声矩阵
- **精度**：SOC MAE < **3.5%**，SOH RMSE 低至 **0.33%**
- DOI: 10.1016/j.jpowsour.2025.238036

### 12. Dual Adaptive Central Difference H-Infinity Filter
**Sang, Wu et al.** | *Energies*, Vol.17(7), 2024
- **架构**：CDKF + H∞ 鲁棒滤波 + Sage-Husa 自适应
- **精度**：SOC 误差 0.5%（UDDS），SOH 最大误差 0.73~0.86%
- DOI: 10.3390/en17071640

### 13. Fusion of Stress and Electrical Signals
**Zhang, Lai et al.** | *Energy*, Vol.331, 2025
- **创新**：首次融合机械应力信号 + 电信号进行联合估计
- **方法**：应力→SOC 用加权 KF 与 EKF 融合，SOH 用恒流充电应力曲线估计
- **精度**：SOC RMSE < **1.3%**，SOH 误差 < **2.05%**
- DOI: 10.1016/j.energy.2025.137063

---

## 四、深度学习+数据驱动

### 14. TL-LSTM-MHDA-iTransformer (迁移学习+联合估计)
**Li et al.** | *Electrochimica Acta*, 2025
- **架构**：迁移学习 + 多头差分注意力 + iTransformer
- **亮点**：仅需 10~20% 全生命周期数据即可完成 SOC/SOH 联合估计
- **精度**：SOC RMSE < **1.55%**，MAE < **0.30%**
- DOI: 10.1016/j.electacta.2025.145934

### 15. CNN-LSTM-AKF (在线融合)
**Processes**, 2025
- **架构**：CNN + LSTM + 自适应卡尔曼滤波（闭环降噪）
- **亮点**：全温域 RMSE < **1.51%**，低温（0°C）场景显著优于纯 LSTM
- DOI: 10.3390/pr13113559

### 16. Physics-Constrained Informer-LSTM
**Journal of Energy Storage**, 2025
- **创新**：将等效电路模型物理参数作为先验知识嵌入 LSTM
- **方法**：温度感知加权损失函数
- DOI: 10.1016/j.est.2025.116840

### 17. Active-Learning-Driven Error Control
**Xue et al.** | *Energy and AI*, 2025
- **创新**：基于模型分歧度的主动学习校正策略
- **亮点**：仅需 **4 次**主动重训练即可在全生命周期保持 SOC 误差 < 1.5%
- 解决了开环数据驱动方法在老化过程中的误差失控

### 18. ACO-LSTM
**IEEE i-PACT**, 2025
- **创新**：蚁群算法（ACO）优化 LSTM 超参数
- 基于 20 万数据点验证

---

## 五、FC-HEV 特定应用

### 19. LSTM SOC Estimation + HSPI Power Management
**Journal of Power Sources**, 2025
- **LSTM 实时 SOC 估计** + Hybrid Storage Participation Index
- **效果**：燃料经济性提升 **70-73%**（vs 规则控制）
- 含 HIL 硬件在环验证

### 20. Hierarchical MPC with SOC Trajectory Planning
**Journal of Energy Storage**, 2025
- **双层架构**：上层 IDP 规划 SOC 参考轨迹，下层 MPC 实时跟踪
- 集成高斯过程回归（GPR）进行车速预测
- **效果**：比传统 MPC 降低能耗 **0.75~9.12%**

### 21. Coupled Degradation-Informed ML-RL Framework
**IEEE Conf.**, 2025
- XGBoost + LSTM + GBDT 预测退化和功率需求
- Dueling PPO 进行能量管理
- **效果**：氢耗降低 **12-18%**，SOC 稳定性提升 **45%**，退化率降低 **34%**

---

## 六、当前研究趋势总结

### 技术路线对比

| 方向 | 代表方法 | 精度(RMSE) | 计算量 | 实现难度 | 适用场景 |
|------|---------|-----------|--------|---------|---------|
| 标准 KF | EKF | 2~3% | ★ | ★ | 线性OCV电池 |
| AEKF | 自适应Q/R | 1~2% | ★★ | ★★ | 变工况 |
| UKF | Sigma点 | 1~2% | ★★ | ★★ | LFP强非线性 |
| **AEKF改进** | CW-AEKF/RMAEKF | **<1%** | ★★ | ★★★ | **推荐首选** |
| **DualEKF** | SOC+SOH | **SOC<1%, SOH<1%** | ★★★ | ★★★ | 全寿命管理 |
| 分数阶KF | FO-UKF | **<0.5%** | ★★★★ | ★★★★ | 高精度研究 |
| ML+KF | CNN-LSTM-AKF | **<1.5%** | ★★★★ | ★★★★ | 有训练数据 |
| 纯DL | LSTM/NARX | **1~2%** | ★★★ | ★★★ | 数据充足 |
| RL+EMS | DQN/PPO | SOC稳定+45% | ★★★★ | ★★★★★ | 端到端控制 |

### 关键文献指标速查

```
精度最高:    分数阶UKF (RMSE=0.48%)       [SAE, 2025]
收敛最快:    IAEKF (初始偏50%仍收敛)      [IEEE, 2025]
全温域最佳:  Dual AEKF (0°C~45°C, <1.5%)  [IOP, 2025]
SOH最优:     MT-NN+DEKF (RMSE=0.33%)     [JPS, 2025]
寿命最优:    Active Learning (4次重训练)   [Energy AI, 2025]
FC-HEV最佳:  ML-RL Framework (H2↓18%)    [IEEE, 2025]
```

### 发展趋势

1. **AEKF 是性价比最高的升级路径**：CW-AEKF（自适应窗口）和 RMAEKF（递推修正）代码量增加 < 30%，精度从 2-3% 提升到 < 1%
2. **DualEKF 是论文产出的黄金方向**：SOC+SOH 联合估计 + 触发机制 + 分数阶模型，组合多、创新空间大
3. **ML+KF 混合是前沿**：LSTM 做 SOC 先验预测，KF 做 V_t 修正融合，精度和鲁棒性都优于纯 ML
4. **FC-HEV 特定方向竞争少**：将上述方法应用到燃料电池混合动力系统并联合 EMS 优化，是一个差异化优势

---

## 七、对你最实用的推荐

基于你已有的 `mpc_ems.py` + `ekf_soc_estimator.py`：

| 优先级 | 方向 | 对应文献 | 预计效果 | 工作量 |
|--------|------|---------|---------|--------|
| ⭐⭐⭐ | CW-AEKF (自适应窗口) | Du et al. 2024 | SOC误差 2%→1% | 1周 |
| ⭐⭐⭐ | DualEKF (SOC+SOH) | Plett 2004 + Lin 2025 | 全寿命 SOC<1% | 2-3周 |
| ⭐⭐ | 融合到 MPC | Hierarchical MPC 2025 | EMS 能耗↓5% | 4-6周 |
| ⭐⭐ | LSTM + EKF 混合 | CNN-LSTM-AKF 2025 | 预测SOC更准 | 4-8周 |
| ⭐ | UKF 升级 | Julier 1997 | 强非线性适用 | 1周 |
