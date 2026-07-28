#!/usr/bin/env python3
"""
SOC 估计器实现
================================
三种方法:
  - OpenLoopEstimator:   开环安时积分（基准线）
  - EKFEstimator:        扩展卡尔曼滤波（核心）
  - AEKFEstimator:       自适应扩展卡尔曼滤波（进阶）
"""
import numpy as np

SOC_MIN = 0.2
SOC_MAX = 0.9
Q_BAT = 40.0  # Ah


# ====================================================================
# 基类
# ====================================================================
class SOCEstimator:
    """SOC 估计器基类"""
    def __init__(self, x0=0.6):
        self.x = float(x0)

    def step(self, i_meas, v_t_meas, dt=1.0):
        """单步SOC估计，子类重写"""
        raise NotImplementedError

    def reset(self, x0=0.6):
        self.x = float(x0)


# ====================================================================
# 开环安时积分
# ====================================================================
class OpenLoopEstimator(SOCEstimator):
    """开环安时积分 — 无测量修正"""
    def step(self, i_meas, v_t_meas, dt=1.0):
        # TODO: SOC_{k+1} = SOC_k - I/Q * dt
        # TODO: 限幅到 [SOC_MIN, SOC_MAX]
        soc_next = self.x
        return soc_next


# ====================================================================
# EKF（扩展卡尔曼滤波）
# ====================================================================
class EKFEstimator(SOCEstimator):
    """
    EKF SOC 估计器

    状态: SOC (1维)
    过程模型: SOC_{k+1} = SOC_k - I/Q * dt  (安时积分)
    观测模型: V_t = OCV(SOC) + 噪声           (端电压测量)
    两阶段: Predict(时间更新) → Update(测量修正)
    """
    def __init__(self, x0=0.6, P0=0.01, Q=1e-5, R=0.001):
        super().__init__(x0)
        self.P = float(P0)   # 协方差
        self.Q = float(Q)    # 过程噪声
        self.R = float(R)    # 测量噪声

    def step(self, i_meas, v_t_meas, dt=1.0):
        # ── Predict ──
        # TODO: soc_pred = x - I/Q*dt
        # TODO: P_pred = P + Q
        # (提示: F = 1.0 因为 SOC 是一维线性传递)
        soc_pred = self.x
        P_pred = self.P

        # ── Update ──
        # TODO: v_pred = lookup_ocv(soc_pred)
        # TODO: y = v_t_meas - v_pred            (新息)
        # TODO: H = lookup_docv_dsoc(soc_pred)   (观测雅可比)
        # TODO: K = P_pred * H / (H*P_pred*H + R) (卡尔曼增益)
        # TODO: x_est = soc_pred + K * y          (状态修正)
        # TODO: P_est = (1 - K*H) * P_pred        (协方差更新)
        x_est = soc_pred
        P_est = P_pred

        self.x = float(np.clip(x_est, SOC_MIN, SOC_MAX))
        self.P = max(P_est, 1e-8)
        return self.x


# ====================================================================
# AEKF（自适应扩展卡尔曼滤波）
# ====================================================================
class AEKFEstimator(SOCEstimator):
    """
    AEKF — 在 EKF 基础上自适应调整 Q/R

    改进:
      1. R 自适应：用滑动窗口新息方差估算测量噪声
      2. Q 自适应：用残差方差估算过程噪声
      3. 工况变化时自动调整信任权重
    """
    def __init__(self, x0=0.6, P0=0.01, Q0=1e-5, R0=0.001, window=50):
        super().__init__(x0)
        self.P = float(P0)
        self.Q = float(Q0)
        self.R = float(R0)
        self.window = window
        self.innov_buffer = []

    def step(self, i_meas, v_t_meas, dt=1.0):
        # TODO: 同 EKF 的 Predict + Update
        # TODO: 将新息加入 innov_buffer
        # TODO: 用 innov_buffer 方差自适应调整 R
        # TODO: 用残差自适应调整 Q
        return self.x
