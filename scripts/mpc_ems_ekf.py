# -*- coding: utf-8 -*-
"""
mpc_ems_ekf.py — MPC + EKF/AEKF SOC 估计的燃料电池 EMS 能量管理

核心改进：
  1. 在 mpc_ems_optimized.py 的基础上，引入 EKF 替代开环 SOC 估计
  2. 可选 AEKF（自适应扩展卡尔曼滤波），自动调节噪声协方差
  3. 模拟电流传感器偏置，验证 EKF 的抗漂移能力
  4. 保留 SOC 软约束、FC 功率变化惩罚等全部优化版功能

用法：
    python scripts/mpc_ems_ekf.py                          # 默认 MPC+EKF, WLTC
    python scripts/mpc_ems_ekf.py --soc-estimator ekf      # 显式指定 EKF
    python scripts/mpc_ems_ekf.py --soc-estimator aekf     # 使用 AEKF
    python scripts/mpc_ems_ekf.py --soc-estimator openloop # 关闭 EKF (降级为优化版)
    python scripts/mpc_ems_ekf.py --current-bias 5.0       # 模拟 5A 电流偏置
    python scripts/mpc_ems_ekf.py --compare --scan          # 四方法对比 + N_p 扫描

依赖：numpy, pandas, matplotlib
"""

import os, sys, argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PROJECT_ROOT, 'results')
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, 'scripts')
sys.path.insert(0, SCRIPTS_DIR)

from day8_dp_ems import (
    fc_hydrogen_flow, fc_efficiency, vehicle_power, state_transition,
    load_drive_cycle, run_rule_controller,
    SOC_MIN, SOC_MAX, PFC_MIN, PFC_MAX,
    N_SOC, N_PFC, DT, LHV_H2, PFC_EFF_BP, ETA_FC,
    SOC_BP, OCV_LU, Q_BAT, R_INT,
)

# ====================================================================
# MPC 参数（同优化版）
# ====================================================================
N_P_DEFAULT = 50
S_MPC = 130.0
W_SOC = 1200.0
BETA_TERM = 5000.0
SOC_DEADBAND = 0.015
SOC_SOFT_MIN = 0.57
W_SOC_LOW = 20000.0
SOC_FINAL_TOL = 0.01
W_FINAL_SOC = 80000.0
W_PFC_SLEW = 0.001
PFC_GRID = np.linspace(PFC_MIN, PFC_MAX, N_PFC)
SOC_REF = 0.6

# EKF 默认参数
Q_EKF_DEFAULT = 5e-5          # 过程噪声   物理含义：安时积分模型的不确定性。
R_EKF_DEFAULT = 0.03          # 测量噪声   物理含义：安时积分模型的不确定性。
P0_EKF_DEFAULT = 0.1          # 初始协方差 物理含义：初始 SOC 估计的不确定性

# 传感器噪声默认值（仿真环境）
CURRENT_BIAS_DEFAULT = 2.0    # 电流传感器偏置 (A)
CURRENT_NOISE_STD = 0.5       # 电流测量噪声 (A)
VOLTAGE_NOISE_STD = 0.1       # 电压测量噪声 (V)

# 预计算氢耗网格
H2_GRID = fc_hydrogen_flow(PFC_GRID)


# ====================================================================
# 电池参数辅助
# ====================================================================
def lookup_ocv(soc):
    """OCV 查表（供 EKF 使用）"""
    return np.interp(soc, SOC_BP, OCV_LU)


def lookup_docv_dsoc(soc):
    """OCV 曲线斜率 d(Voc)/d(SOC)（数值微分）"""
    delta = 1e-6
    soc_lo = np.clip(soc - delta, 0, 1)
    soc_hi = np.clip(soc + delta, 0, 1)
    return (lookup_ocv(soc_hi) - lookup_ocv(soc_lo)) / (soc_hi - soc_lo)


def battery_current(soc, p_bat):
    """根据 SOC 和电池功率计算电流（与 day8 一致但返回纯量）"""
    v_oc = lookup_ocv(soc)
    p_w = p_bat * 1000.0
    delta = v_oc ** 2 - 4 * R_INT * p_w
    if delta < 0:
        return 0.0
    i = (v_oc - np.sqrt(delta)) / (2 * R_INT)
    return float(np.clip(i, -300, 300))


# ====================================================================
# SOC 估计器基类
# ====================================================================
class SOCEstimator:
    """SOC 估计器基类（多态接口）"""
    def __init__(self, x0=0.6):
        self.x = float(x0)   # SOC 估计值

    def step(self, i_meas, v_t_meas, dt=DT):
        """单步 SOC 估计，子类需重写"""
        raise NotImplementedError


class OpenLoopEstimator(SOCEstimator):
    """开环安时积分（无测量修正，= mpc_step_soc 的开环版本）"""
    def step(self, i_meas, v_t_meas, dt=DT):
        soc_next = self.x - i_meas / (Q_BAT * 3600) * dt
        self.x = float(np.clip(soc_next, SOC_MIN, SOC_MAX))
        return self.x


class EKFEstimator(SOCEstimator):
    """
    EKF SOC 估计器

    状态: SOC (1D)
    过程: SOC_{k+1} = SOC_k - I/Q×dt  (安时积分)
    观测: V_t = Voc(SOC)
    两阶段: Predict(安时积分) → Update(电压新息修正)
    """
    def __init__(self, x0=0.6, P0=P0_EKF_DEFAULT,
                 Q=Q_EKF_DEFAULT, R=R_EKF_DEFAULT):
        super().__init__(x0)
        self.P = float(P0)
        self.Q = float(Q)
        self.R = float(R)
        self.innov = 0.0
        self.K_gain = 0.0

    def step(self, i_meas, v_t_meas, dt=DT):
        # ── Predict (时间更新) ──
        soc_pred = self.x - i_meas / (Q_BAT * 3600) * dt
        F = 1.0  # 雅可比简化：d(SOC_next)/d(SOC) ≈ 1
        P_pred = self.P + self.Q  # F*P*F^T + Q, F=1

        # ── Update (测量更新) ──
        v_pred = lookup_ocv(soc_pred)
        y = v_t_meas - v_pred           # 新息
        H = lookup_docv_dsoc(soc_pred)  # 观测雅可比
        S = H * P_pred * H + self.R     # 新息协方差
        K = P_pred * H / S              # 卡尔曼增益
        x_est = soc_pred + K * y        # SOC 修正
        P_est = (1 - K * H) * P_pred    # 协方差更新

        self.x = float(np.clip(x_est, SOC_MIN, SOC_MAX))
        self.P = max(P_est, 1e-8)
        self.innov = float(y)
        self.K_gain = float(K)
        return self.x


class AEKFEstimator(SOCEstimator):
    """
    AEKF (自适应扩展卡尔曼滤波) SOC 估计器

    相比标准 EKF 的改进:
      1. R 自适应：用滑动窗口新息方差估算测量噪声
      2. Q 自适应：用残差方差估算过程噪声
      3. 工况变化时自动调整信任权重，更鲁棒
    """
    def __init__(self, x0=0.6, P0=P0_EKF_DEFAULT,
                 Q0=Q_EKF_DEFAULT, R0=R_EKF_DEFAULT,
                 window=50):
        super().__init__(x0)
        self.P = float(P0)
        self.Q = float(Q0)
        self.R = float(R0)
        self.window = window
        self.innov_buffer = []
        self.innov = 0.0
        self.K_gain = 0.0

    def step(self, i_meas, v_t_meas, dt=DT):
        # ── Predict ──
        soc_pred = self.x - i_meas / (Q_BAT * 3600) * dt
        P_pred = self.P + self.Q

        # ── Update ──
        v_pred = lookup_ocv(soc_pred)
        y = v_t_meas - v_pred
        H = lookup_docv_dsoc(soc_pred)
        S = H * P_pred * H + self.R
        K = P_pred * H / S
        x_est = soc_pred + K * y
        P_est = (1 - K * H) * P_pred

        self.x = float(np.clip(x_est, SOC_MIN, SOC_MAX))
        self.P = max(P_est, 1e-10)

        # ── 自适应更新 R-Q（基于新息滑动窗口） ──
        self.innov_buffer.append(y)
        if len(self.innov_buffer) > self.window:
            self.innov_buffer.pop(0)

        if len(self.innov_buffer) >= 10:
            innov_var = float(np.var(self.innov_buffer))
            self.R = max(innov_var - H * P_pred * H, 0.001)
            self.Q = max(K * innov_var * K, 1e-8)

        self.innov = float(y)
        self.K_gain = float(K)
        return self.x


def build_estimator(method, x0=0.6, **kwargs):
    """工厂方法：根据名称创建 SOC 估计器"""
    if method == 'openloop':
        return OpenLoopEstimator(x0=x0)
    elif method == 'ekf':
        return EKFEstimator(x0=x0,
                            Q=kwargs.get('Q_ekf', Q_EKF_DEFAULT),
                            R=kwargs.get('R_ekf', R_EKF_DEFAULT))
    elif method == 'aekf':
        return AEKFEstimator(x0=x0,
                             Q0=kwargs.get('Q_ekf', Q_EKF_DEFAULT),
                             R0=kwargs.get('R_ekf', R_EKF_DEFAULT))
    else:
        raise ValueError(f"Unknown estimator: {method}")


# ====================================================================
# 仿真电压（模拟 BMS 电压传感器）
# ====================================================================
def simulate_voltage(soc_true, noise_std=VOLTAGE_NOISE_STD):
    """模拟端电压测量: V_t = Voc(SOC) + 高斯噪声"""
    return lookup_ocv(soc_true) + noise_std * np.random.randn()


# ====================================================================
# SOC 等效氢耗修正
# ====================================================================
def soc_equivalent_h2(raw_h2_kg, soc_end, soc_ref=SOC_REF, s_factor=S_MPC):
    """将 SOC 终点偏差折算为等效氢耗，用于公平比较"""
    delta_soc = soc_ref - soc_end
    e_bat_kwh = Q_BAT * np.mean(OCV_LU) * delta_soc / 1000.0
    return raw_h2_kg + s_factor * e_bat_kwh / 1000.0


# ====================================================================
# SOC 跟踪惩罚（同优化版）
# ====================================================================
def soc_tracking_penalty(soc, is_terminal, is_route_end,
                         w_soc=W_SOC, beta_term=BETA_TERM,
                         soc_ref=SOC_REF, soc_deadband=SOC_DEADBAND,
                         soc_soft_min=SOC_SOFT_MIN, w_soc_low=W_SOC_LOW,
                         soc_final_tol=SOC_FINAL_TOL, w_final_soc=W_FINAL_SOC):
    """SOC 维持代价（含死区、软下限、滚动终端、终点欠差罚）"""
    abs_dev = abs(soc - soc_ref)
    excess = max(abs_dev - soc_deadband, 0.0)
    penalty = w_soc * excess ** 2 * DT

    low_gap = max(soc_soft_min - soc, 0.0)
    penalty += w_soc_low * low_gap ** 2 * DT

    if is_terminal:
        penalty += beta_term * excess ** 2

    if is_route_end:
        final_shortfall = max((soc_ref - soc_final_tol) - soc, 0.0)
        penalty += w_final_soc * final_shortfall ** 2

    return penalty


# ====================================================================
# 单步状态转移
# ====================================================================
def mpc_step_soc(soc_k, p_fc, p_load_k, dt=DT):
    """单步 SOC 状态转移（同优化版：不可行时返回 None）"""
    p_bat = p_load_k - p_fc
    v_oc = np.interp(soc_k, SOC_BP, OCV_LU)
    p_w = p_bat * 1000.0

    delta = v_oc ** 2 - 4 * R_INT * p_w
    if delta < 0:
        return None

    i = (v_oc - np.sqrt(delta)) / (2 * R_INT)
    i = np.clip(i, -300, 300)
    soc_next = soc_k - i / (Q_BAT * 3600) * dt
    if not np.isfinite(soc_next) or soc_next < SOC_MIN or soc_next > SOC_MAX:
        return None
    return soc_next


# ====================================================================
# MPC 主仿真（带 EKF/AEKF SOC 估计）
# ====================================================================
def mpc_sim(P_load, SOC_0=0.6, N_p=N_P_DEFAULT, w_soc=W_SOC,
            beta_term=BETA_TERM, soc_ref=SOC_REF, s_factor=S_MPC,
            soc_deadband=SOC_DEADBAND, soc_soft_min=SOC_SOFT_MIN,
            w_soc_low=W_SOC_LOW, soc_final_tol=SOC_FINAL_TOL,
            w_final_soc=W_FINAL_SOC, w_pfc_slew=W_PFC_SLEW,
            soc_estimator='ekf',
            current_bias=CURRENT_BIAS_DEFAULT,
            current_noise_std=CURRENT_NOISE_STD,
            voltage_noise_std=VOLTAGE_NOISE_STD,
            ekf_x0=None, ekf_P0=P0_EKF_DEFAULT,
            ekf_Q=Q_EKF_DEFAULT, ekf_R=R_EKF_DEFAULT):
    """
    MPC 仿真 — 网格搜索 + receding horizon + EKF/AEKF SOC 估计

    与 mpc_ems_optimized.mpc_sim 接口兼容，额外参数：
      soc_estimator  : str — 'openloop'(无EKF) / 'ekf' / 'aekf'
      current_bias   : float — 模拟电流传感器偏置 (A)
      current_noise_std : float — 电流测量噪声标准差 (A)
      voltage_noise_std : float — 电压测量噪声标准差 (V)
      ekf_x0         : float or None — EKF 初始 SOC (None=使用 SOC_0)
      ekf_P0/Q/R     : float — EKF 协方差参数

    Returns
    -------
    dict — 包含 SOC_true, SOC_est, SOC_open 等字段
    """
    N = len(P_load)

    # ── 分配数组 ──
    SOC_true = np.zeros(N + 1)   # 真实 SOC（无偏，用于对比评估）
    SOC_est_arr = np.zeros(N + 1)  # 估计 SOC（EKF 修正后的值，用于控制决策）
    SOC_open = np.zeros(N + 1)    # 开环安时积分（用于观察漂移）
    P_fc = np.zeros(N)
    P_bat = np.zeros(N)
    m_H2 = np.zeros(N)

    # 初值
    SOC_true[0] = SOC_0
    x0_ekf = SOC_0 if ekf_x0 is None else ekf_x0
    SOC_est_arr[0] = x0_ekf
    SOC_open[0] = x0_ekf

    # ── 创建 SOC 估计器 ──
    if soc_estimator == 'openloop':
        estimator = OpenLoopEstimator(x0=x0_ekf)
    elif soc_estimator == 'ekf':
        estimator = EKFEstimator(x0=x0_ekf, P0=ekf_P0, Q=ekf_Q, R=ekf_R)
    elif soc_estimator == 'aekf':
        estimator = AEKFEstimator(x0=x0_ekf, P0=ekf_P0, Q0=ekf_Q, R0=ekf_R)
    else:
        raise ValueError(f"Unknown soc_estimator: {soc_estimator}")

    print(f'[MPC+{soc_estimator.upper()}] N_p={N_p}, s={s_factor}, '
          f'w_soc={w_soc}, bias={current_bias}A, '
          f'SOC_true_0={SOC_0:.2f}, SOC_est_0={x0_ekf:.2f}')
    print(f'[MPC+{soc_estimator.upper()}] 开始仿真... ({N} 步)')

    for k in range(N):
        soc_est_k = SOC_est_arr[k]   # 使用 EKF 估计的 SOC 做控制决策

        # ── 预测工况 ──
        horizon = min(N_p, N - k)
        p_load_pred = P_load[k: k + horizon]

        # ── 网格搜索 ──
        J_best = np.inf
        best_j = None
        p_fc_prev = P_fc[k - 1] if k > 0 else np.clip(P_load[k], PFC_MIN, PFC_MAX)

        for j in range(N_PFC):
            p_fc_cand = PFC_GRID[j]
            h2_cand = H2_GRID[j]

            soc_pred = soc_est_k   # 从当前估计 SOC 开始预测
            J_total = 0.0
            J_total += w_pfc_slew * (p_fc_cand - p_fc_prev) ** 2

            feasible = True
            for i in range(horizon):
                p_load_i = p_load_pred[i]
                p_bat_i = p_load_i - p_fc_cand

                # 氢耗
                J_total += h2_cand * DT
                # 等效电池能量惩罚
                J_total += s_factor * abs(p_bat_i) / 3600.0 * DT

                # 向前一步
                soc_pred_next = mpc_step_soc(soc_pred, p_fc_cand, p_load_i)
                if soc_pred_next is None:
                    feasible = False
                    break
                soc_pred = soc_pred_next

                # SOC 惩罚
                is_terminal = i == horizon - 1
                is_route_end = k + i + 1 >= N
                J_total += soc_tracking_penalty(
                    soc_pred,
                    is_terminal=is_terminal,
                    is_route_end=is_route_end,
                    w_soc=w_soc, beta_term=beta_term,
                    soc_ref=soc_ref, soc_deadband=soc_deadband,
                    soc_soft_min=soc_soft_min, w_soc_low=w_soc_low,
                    soc_final_tol=soc_final_tol, w_final_soc=w_final_soc,
                )

            if feasible and J_total < J_best:
                J_best = J_total
                best_j = j

        # ── 后备策略（同优化版） ──
        if best_j is None:
            one_step_feasible = []
            for j, p_fc_cand in enumerate(PFC_GRID):
                soc_next = mpc_step_soc(soc_est_k, p_fc_cand, P_load[k])
                if soc_next is not None:
                    one_step_feasible.append((abs(soc_next - soc_ref), j))
            if one_step_feasible:
                best_j = min(one_step_feasible)[1]
            else:
                best_j = int(np.argmin(np.abs(PFC_GRID - np.clip(P_load[k], PFC_MIN, PFC_MAX))))

        # ── 执行最优控制 ──
        P_fc[k] = PFC_GRID[best_j]
        P_bat[k] = P_load[k] - P_fc[k]
        m_H2[k] = fc_hydrogen_flow(P_fc[k]) * DT

        # ── 真实 SOC 演化（无偏电流） ──
        i_real = battery_current(SOC_true[k], P_bat[k])
        SOC_true[k + 1] = SOC_true[k] - i_real / (Q_BAT * 3600) * DT

        # ── 模拟传感器测量（含偏置和噪声） ──
        i_meas_k = i_real + current_bias + current_noise_std * np.random.randn()
        v_meas_k = simulate_voltage(SOC_true[k], voltage_noise_std)

        # ── SOC 估计（EKF/AEKF/开环） ──
        soc_est_k1 = estimator.step(i_meas_k, v_meas_k)
        SOC_est_arr[k + 1] = soc_est_k1

        # ── 开环安时积分（对比基准） ──
        SOC_open[k + 1] = SOC_open[k] - i_meas_k / (Q_BAT * 3600) * DT

        if k % 300 == 0:
            print(f'  Step {k}/{N}: SOC_true={SOC_true[k]:.3f}, '
                  f'SOC_est={SOC_est_arr[k]:.3f}, '
                  f'SOC_open={SOC_open[k]:.3f}')

    # ── 结果 ──
    raw_h2_kg = np.cumsum(m_H2)[-1] / 1000
    h2_eq_kg = soc_equivalent_h2(raw_h2_kg, SOC_true[-1], soc_ref=soc_ref, s_factor=s_factor)

    # SOC 估计误差统计
    soc_rmse = np.sqrt(np.mean((SOC_est_arr[:N] - SOC_true[:N]) ** 2))
    soc_open_rmse = np.sqrt(np.mean((SOC_open[:N] - SOC_true[:N]) ** 2))

    print(f'[MPC+{soc_estimator.upper()}] 完成.')
    print(f'  SOC: true_end={SOC_true[-1]:.3f}, est_end={SOC_est_arr[-1]:.3f}, '
          f'open_end={SOC_open[-1]:.3f}')
    print(f'  SOC RMSE: EKF={soc_rmse:.4f}, OpenLoop={soc_open_rmse:.4f}')
    print(f'  H2: raw={raw_h2_kg:.4f} kg, eq={h2_eq_kg:.4f} kg')

    p_fc_arr = P_fc
    eff_arr = fc_efficiency(p_fc_arr)

    return {
        'time': np.arange(N),
        'SOC': SOC_true[:N],               # 默认 SOC = 真实值（与基础版接口一致）
        'SOC_est': SOC_est_arr[:N],        # EKF 估计 SOC（新增）
        'SOC_true': SOC_true[:N],          # 真实 SOC（新增）
        'SOC_open': SOC_open[:N],          # 开环积分 SOC（新增）
        'SOC_end_true': SOC_true[-1],
        'SOC_end_est': SOC_est_arr[-1],
        'SOC_rmse': soc_rmse,
        'SOC_open_rmse': soc_open_rmse,
        'P_fc_kW': P_fc,
        'P_bat_kW': P_bat,
        'm_H2_g': m_H2,
        'm_H2_cumul_kg': np.cumsum(m_H2) / 1000,
        'H2_raw_kg': raw_h2_kg,
        'H2_eq_kg': h2_eq_kg,
        'fc_efficiency': eff_arr,
        'config': {
            'N_p': N_p,
            's_factor': s_factor,
            'w_soc': w_soc,
            'beta_term': beta_term,
            'soc_deadband': soc_deadband,
            'soc_soft_min': soc_soft_min,
            'w_soc_low': w_soc_low,
            'soc_final_tol': soc_final_tol,
            'w_final_soc': w_final_soc,
            'w_pfc_slew': w_pfc_slew,
            'soc_estimator': soc_estimator,
            'current_bias': current_bias,
        },
    }


# ====================================================================
# N_p 敏感性扫描
# ====================================================================
def mpc_n_p_scan(P_load, N_p_values=None, SOC_0=0.6, **mpc_kwargs):
    if N_p_values is None:
        N_p_values = [10, 20, 30, 50, 80, 120, 200]

    print(f'\n[MPC N_p 扫描] 范围: {N_p_values}')
    results = []

    for n_p in N_p_values:
        if n_p > len(P_load):
            continue

        res = mpc_sim(P_load, SOC_0=SOC_0, N_p=n_p, **mpc_kwargs)
        results.append({
            'N_p': n_p,
            'H2_kg': res['H2_raw_kg'],
            'SOC_end_true': res['SOC_end_true'],
            'SOC_end_est': res['SOC_end_est'],
            'H2_eq_kg': res['H2_eq_kg'],
            'SOC_rmse': res['SOC_rmse'],
            'SOC_open_rmse': res['SOC_open_rmse'],
        })
        print(f'  N_p={n_p:4d}: H2={res["H2_raw_kg"]:.4f} kg, '
              f'SOC_end={res["SOC_end_true"]:.3f}, '
              f'H2_eq={res["H2_eq_kg"]:.4f} kg, '
              f'SOC_RMSE={res["SOC_rmse"]:.4f}')

    return pd.DataFrame(results)


# ====================================================================
# 绘图函数（扩展版）
# ====================================================================
def plot_four_way(t, v, P_load, rule, dp, ecms, mpc_result, cycle_name='wltc'):
    """四种方法（Rule / DP / ECMS / MPC）五合一对比图（同优化版基线）"""
    t_min = t / 60
    fig, axes = plt.subplots(5, 1, figsize=(16, 14), sharex=True)

    colors = {'Rule': 'orange', 'DP': 'g', 'ECMS': 'b', 'MPC': 'r'}
    linestyles = {'Rule': '--', 'DP': '-', 'ECMS': '-.', 'MPC': ':'}

    # (1) 速度 + SOC 对比
    ax = axes[0]
    ax.plot(t_min, v, 'b-', linewidth=0.8, alpha=0.4, label='Speed (km/h)')
    ax.set_ylabel('Speed (km/h)', color='b')
    ax2 = ax.twinx()
    for name in ['Rule', 'DP', 'ECMS', 'MPC']:
        r = {'Rule': rule, 'DP': dp, 'ECMS': ecms, 'MPC': mpc_result}[name]
        ls = linestyles[name]
        c = colors[name]
        lw = 1.3 if ls == '-' else (0.8 if ls == '--' else 1.0)
        ax2.plot(t_min, r['SOC'], color=c, linewidth=lw, linestyle=ls, label=name)
    ax2.set_ylabel('SOC')
    ax2.set_ylim(0.2, 0.9)
    ax.set_title(f'{cycle_name.upper()} — Rule vs DP vs ECMS vs MPC (with EKF)')
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=7, ncol=4)
    ax.grid(True, alpha=0.3)

    # (2) 功率分配
    ax = axes[1]
    ax.fill_between(t_min, 0, P_load, alpha=0.15, color='gray', label='Load')
    ax.plot(t_min, dp['P_fc_kW'], 'g-', linewidth=1.0, label='DP FC')
    ax.plot(t_min, mpc_result['P_fc_kW'], 'r-', linewidth=1.0, label='MPC FC')
    ax.fill_between(t_min, 0, mpc_result['P_bat_kW'],
                    where=mpc_result['P_bat_kW'] > 0,
                    alpha=0.3, color='green', label='MPC Bat Discharge')
    ax.fill_between(t_min, 0, mpc_result['P_bat_kW'],
                    where=mpc_result['P_bat_kW'] < 0,
                    alpha=0.3, color='orange', label='MPC Bat Charge')
    ax.set_ylabel('Power (kW)')
    ax.legend(loc='upper right', fontsize=7, ncol=3)
    ax.grid(True, alpha=0.3)

    # (3) SOC 对比 + EKF 估计
    ax = axes[2]
    for name in ['Rule', 'DP', 'ECMS', 'MPC']:
        r = {'Rule': rule, 'DP': dp, 'ECMS': ecms, 'MPC': mpc_result}[name]
        ax.plot(t_min, r['SOC'], color=colors[name], linewidth=1.0,
                linestyle=linestyles[name], label=name)
    # 额外：EKF 估计 SOC（如可用）和开环积分
    if 'SOC_est' in mpc_result:
        ax.plot(t_min, mpc_result['SOC_est'], 'm-', linewidth=0.7,
                alpha=0.7, label='MPC SOC_est')
    if 'SOC_open' in mpc_result:
        ax.plot(t_min, mpc_result['SOC_open'], 'c-', linewidth=0.7,
                alpha=0.5, label='MPC SOC_open')
    ax.axhline(y=SOC_REF, color='gray', linestyle=':', alpha=0.5, label=f'SOC_ref={SOC_REF}')
    ax.set_ylabel('SOC')
    ax.set_ylim(0.2, 0.9)
    ax.legend(loc='lower right', fontsize=6)
    ax.grid(True, alpha=0.3)

    # (4) 累计氢耗
    ax = axes[3]
    for name in ['Rule', 'DP', 'ECMS', 'MPC']:
        r = {'Rule': rule, 'DP': dp, 'ECMS': ecms, 'MPC': mpc_result}[name]
        h2_val = r['m_H2_cumul_kg'][-1]
        ax.plot(t_min, r['m_H2_cumul_kg'], color=colors[name], linewidth=1.0,
                linestyle=linestyles[name], label=f'{name} ({h2_val:.3f} kg)')
    ax.set_ylabel('Cumul. H₂ (kg)')
    ax.legend(loc='upper left', fontsize=7)
    ax.grid(True, alpha=0.3)

    # (5) FC 效率直方图
    ax = axes[4]
    bins = np.linspace(0, 0.6, 25)
    for name in ['Rule', 'DP', 'ECMS', 'MPC']:
        r = {'Rule': rule, 'DP': dp, 'ECMS': ecms, 'MPC': mpc_result}[name]
        eff = r.get('fc_efficiency', fc_efficiency(r['P_fc_kW']))
        ax.hist(eff, bins=bins, alpha=0.4, color=colors[name],
                label=f'{name} (mean={eff.mean():.1%})')
    ax.set_xlabel('FC Efficiency')
    ax.set_ylabel('Count')
    ax.legend(loc='upper right', fontsize=7)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    png_path = os.path.join(RESULTS_DIR, f'FourWay_compare_ekf_{cycle_name}.png')
    plt.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f'[图] {png_path}')
    plt.close()


def plot_soc_estimation(t, v, mpc_result, cycle_name='wltc'):
    """SOC 估计效果对比图（EKF vs 开环 vs 真实）"""
    if 'SOC_true' not in mpc_result:
        return

    t_min = t / 60
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

    # (1) SOC 轨迹对比
    ax = axes[0]
    ax.plot(t_min, mpc_result['SOC_true'], 'k-', lw=2, label='True SOC')
    ax.plot(t_min, mpc_result['SOC_est'], 'r-', lw=1.5, label=f'EKF (RMSE={mpc_result["SOC_rmse"]:.4f})')
    ax.plot(t_min, mpc_result['SOC_open'], 'b--', lw=1, alpha=0.6, label=f'Open-loop (RMSE={mpc_result["SOC_open_rmse"]:.4f})')
    ax.axhline(SOC_REF, color='gray', ls=':', alpha=0.5)
    ax.set_ylabel('SOC')
    ax.set_ylim(0.2, 0.9)
    config = mpc_result.get('config', {})
    bias = config.get('current_bias', 0)
    ax.set_title(f'{cycle_name.upper()} — SOC Estimation (bias={bias}A)')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    # (2) SOC 误差对比
    ax = axes[1]
    err_ekf = mpc_result['SOC_est'] - mpc_result['SOC_true']
    err_open = mpc_result['SOC_open'] - mpc_result['SOC_true']
    ax.plot(t_min, err_ekf, 'r-', lw=1.2, label=f'EKF error')
    ax.plot(t_min, err_open, 'b-', lw=1, alpha=0.6, label='Open-loop error')
    ax.axhline(0, color='k', ls='-', lw=0.5)
    ax.fill_between(t_min, 0, err_ekf, alpha=0.1, color='red')
    ax.set_ylabel('SOC Error')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    # (3) 速度（时间轴参考）
    ax = axes[2]
    ax.plot(t_min, v, 'b-', lw=0.8, alpha=0.5)
    ax.set_xlabel('Time (min)')
    ax.set_ylabel('Speed (km/h)')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    png_path = os.path.join(RESULTS_DIR, f'SOC_estimation_{cycle_name}_ekf.png')
    plt.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f'[图] {png_path}')
    plt.close()


def plot_np_sensitivity(np_df, dp_H2, cycle_name='wltc'):
    """N_p 敏感性曲线（含 SOC_RMSE）"""
    fig, axes = plt.subplots(3, 1, figsize=(10, 11), sharex=False)

    # (1) 氢耗 vs N_p
    ax1 = axes[0]
    ax1.plot(np_df['N_p'], np_df['H2_kg'], 'ro-', linewidth=1.5, markersize=6, label='MPC raw')
    if 'H2_eq_kg' in np_df.columns:
        ax1.plot(np_df['N_p'], np_df['H2_eq_kg'], 'mo--', linewidth=1.2, markersize=5, label='MPC SOC-corrected')
    ax1.axhline(y=dp_H2, color='g', linestyle='--', linewidth=1.0, label=f'DP ({dp_H2:.4f} kg)')
    ax1.set_xlabel('N_p (prediction horizon)')
    ax1.set_ylabel('Total H₂ (kg)')
    ax1.set_title(f'{cycle_name.upper()} — MPC N_p Sensitivity (with EKF)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # (2) SOC_end vs N_p
    ax2 = axes[1]
    ax2.plot(np_df['N_p'], np_df['SOC_end_true'], 'bo-', linewidth=1.5, markersize=6, label='True SOC_end')
    if 'SOC_end_est' in np_df.columns:
        ax2.plot(np_df['N_p'], np_df['SOC_end_est'], 'mo--', linewidth=1.2, markersize=5, label='EKF SOC_end')
    ax2.axhline(y=SOC_REF, color='gray', linestyle=':', linewidth=1.0, label=f'SOC_ref={SOC_REF}')
    ax2.set_xlabel('N_p (prediction horizon)')
    ax2.set_ylabel('SOC_end')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # (3) SOC RMSE vs N_p（新增）
    ax3 = axes[2]
    if 'SOC_rmse' in np_df.columns:
        ax3.plot(np_df['N_p'], np_df['SOC_rmse'], 'rs-', linewidth=1.5, markersize=6, label='EKF RMSE')
    if 'SOC_open_rmse' in np_df.columns:
        ax3.plot(np_df['N_p'], np_df['SOC_open_rmse'], 'b^--', linewidth=1.2, markersize=5, label='Open-loop RMSE')
    ax3.set_xlabel('N_p (prediction horizon)')
    ax3.set_ylabel('SOC RMSE')
    ax3.set_title(f'{cycle_name.upper()} — SOC Estimation RMSE vs N_p')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    png_path = os.path.join(RESULTS_DIR, f'MPC_np_sensitivity_ekf_{cycle_name}.png')
    plt.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f'[图] {png_path}')
    plt.close()


# ====================================================================
# 指标打印
# ====================================================================
def print_four_way_metrics(rule, dp, ecms, mpc_result, P_load):
    """打印四种方法的对比指标（含 SOC 估计精度）"""
    print()
    print('=' * 85)
    print(f'  {"指标":<22} {"规则控制器":>12} {"DP":>12} {"ECMS":>12} {"MPC":>12}')
    print('=' * 85)

    rule_H2 = rule['m_H2_cumul_kg'][-1]
    dp_H2 = dp['m_H2_cumul_kg'][-1]
    ecms_H2 = ecms['m_H2_cumul_kg'][-1]
    mpc_H2 = mpc_result['m_H2_cumul_kg'][-1]

    rule_SOC_end = rule['SOC'][-1]
    dp_SOC_end = dp['SOC'][-1]
    ecms_SOC_end = ecms['SOC'][-1]
    mpc_SOC_end = mpc_result.get('SOC_end_true', mpc_result.get('SOC_end', mpc_result['SOC'][-1]))
    rule_H2_eq = soc_equivalent_h2(rule_H2, rule_SOC_end)
    dp_H2_eq = soc_equivalent_h2(dp_H2, dp_SOC_end)
    ecms_H2_eq = soc_equivalent_h2(ecms_H2, ecms_SOC_end)
    mpc_H2_eq = soc_equivalent_h2(mpc_H2, mpc_SOC_end)

    rule_eff = fc_efficiency(rule['P_fc_kW'])
    dp_eff = dp.get('fc_efficiency', fc_efficiency(dp['P_fc_kW']))
    ecms_eff = ecms.get('fc_efficiency', fc_efficiency(ecms['P_fc_kW']))
    mpc_eff = mpc_result.get('fc_efficiency', fc_efficiency(mpc_result['P_fc_kW']))

    rows = [
        ('总氢耗 (kg)', f'{rule_H2:.4f}', f'{dp_H2:.4f}', f'{ecms_H2:.4f}', f'{mpc_H2:.4f}'),
        ('SOC 初值→终值', f'0.60→{rule_SOC_end:.3f}', f'0.60→{dp_SOC_end:.3f}',
         f'0.60→{ecms_SOC_end:.3f}', f'0.60→{mpc_SOC_end:.3f}'),
        ('SOC修正氢耗 (kg)', f'{rule_H2_eq:.4f}', f'{dp_H2_eq:.4f}',
         f'{ecms_H2_eq:.4f}', f'{mpc_H2_eq:.4f}'),
        ('FC 平均效率', f'{rule_eff.mean():.1%}', f'{dp_eff.mean():.1%}',
         f'{ecms_eff.mean():.1%}', f'{mpc_eff.mean():.1%}'),
        ('FC 最大功率 (kW)', f'{rule["P_fc_kW"].max():.1f}', f'{dp["P_fc_kW"].max():.1f}',
         f'{ecms["P_fc_kW"].max():.1f}', f'{mpc_result["P_fc_kW"].max():.1f}'),
        ('总能量需求 (kWh)', f'{np.trapezoid(P_load, dx=DT)/3600:.2f}', '', '', ''),
    ]

    if 'SOC_rmse' in mpc_result:
        rows.append(('SOC 估计 RMSE', '', '', '',
                     f'{mpc_result["SOC_rmse"]:.4f}'))
    if 'SOC_open_rmse' in mpc_result:
        rows.append(('开环 SOC RMSE', '', '', '',
                     f'{mpc_result["SOC_open_rmse"]:.4f}'))

    for row in rows:
        print(f'  {row[0]:<22} {row[1]:>12} {row[2]:>12} {row[3]:>12} {row[4]:>12}')
    print('=' * 85)

    self_consumed = ''
    print(f'\n  相对 DP 的氢耗差距:')
    print(f'    Rule:  +{(rule_H2 - dp_H2) / dp_H2 * 100:.1f}%')
    print(f'    ECMS:  +{(ecms_H2 - dp_H2) / dp_H2 * 100:.1f}%')
    print(f'    MPC:   +{(mpc_H2 - dp_H2) / dp_H2 * 100:.1f}%')
    print(f'  相对 DP 的 SOC 修正氢耗差距:')
    print(f'    Rule:  {(rule_H2_eq - dp_H2_eq) / dp_H2_eq * 100:+.1f}%')
    print(f'    ECMS:  {(ecms_H2_eq - dp_H2_eq) / dp_H2_eq * 100:+.1f}%')
    print(f'    MPC:   {(mpc_H2_eq - dp_H2_eq) / dp_H2_eq * 100:+.1f}%')
    print('=' * 85)


# ====================================================================
# 主程序
# ====================================================================
def main():
    parser = argparse.ArgumentParser(description='MPC+EKF 模型预测控制 EMS 仿真')
    parser.add_argument('--cycle', choices=['wltc', 'nedc', 'cltc'], default='wltc')
    parser.add_argument('--np', type=int, default=N_P_DEFAULT,
                        help=f'预测时域 (default: {N_P_DEFAULT})')
    parser.add_argument('--s-factor', type=float, default=S_MPC)
    parser.add_argument('--w-soc', type=float, default=W_SOC)
    parser.add_argument('--beta-term', type=float, default=BETA_TERM)
    parser.add_argument('--soc-soft-min', type=float, default=SOC_SOFT_MIN)
    parser.add_argument('--w-soc-low', type=float, default=W_SOC_LOW)
    parser.add_argument('--soc-final-tol', type=float, default=SOC_FINAL_TOL)
    parser.add_argument('--w-final-soc', type=float, default=W_FINAL_SOC)
    parser.add_argument('--w-pfc-slew', type=float, default=W_PFC_SLEW)

    # SOC 估计器选项
    parser.add_argument('--soc-estimator', choices=['openloop', 'ekf', 'aekf'],
                        default='ekf',
                        help='SOC 估计方法: openloop / ekf / aekf (default: ekf)')
    parser.add_argument('--current-bias', type=float, default=CURRENT_BIAS_DEFAULT,
                        help=f'模拟电流传感器偏置 A (default: {CURRENT_BIAS_DEFAULT})')
    parser.add_argument('--current-noise', type=float, default=CURRENT_NOISE_STD,
                        help=f'电流测量噪声 std A (default: {CURRENT_NOISE_STD})')
    parser.add_argument('--voltage-noise', type=float, default=VOLTAGE_NOISE_STD,
                        help=f'电压测量噪声 std V (default: {VOLTAGE_NOISE_STD})')
    parser.add_argument('--ekf-x0', type=float, default=None,
                        help='EKF 初始 SOC (default: 同 SOC_0)')
    parser.add_argument('--ekf-q', type=float, default=Q_EKF_DEFAULT,
                        help=f'EKF 过程噪声 Q (default: {Q_EKF_DEFAULT})')
    parser.add_argument('--ekf-r', type=float, default=R_EKF_DEFAULT,
                        help=f'EKF 测量噪声 R (default: {R_EKF_DEFAULT})')

    parser.add_argument('--scan', action='store_true', help='跑 N_p 敏感性扫描')
    parser.add_argument('--compare', action='store_true', help='四方法对比')
    parser.add_argument('--plot-only', action='store_true', help='只看已有结果')
    parser.add_argument('--seed', type=int, default=42, help='随机种子')

    args = parser.parse_args()
    np.random.seed(args.seed)

    cycle = args.cycle
    n_p = args.np

    mpc_kwargs = {
        's_factor': args.s_factor,
        'w_soc': args.w_soc,
        'beta_term': args.beta_term,
        'soc_soft_min': args.soc_soft_min,
        'w_soc_low': args.w_soc_low,
        'soc_final_tol': args.soc_final_tol,
        'w_final_soc': args.w_final_soc,
        'w_pfc_slew': args.w_pfc_slew,
        'soc_estimator': args.soc_estimator,
        'current_bias': args.current_bias,
        'current_noise_std': args.current_noise,
        'voltage_noise_std': args.voltage_noise,
        'ekf_x0': args.ekf_x0,
        'ekf_Q': args.ekf_q,
        'ekf_R': args.ekf_r,
    }

    print('=' * 55)
    print(f'  MPC {args.soc_estimator.upper()} — 模型预测控制 EMS 仿真')
    print(f'  工况: {cycle.upper()}, N_p: {n_p}')
    print(f'  SOC 估计: {args.soc_estimator}, 电流偏置: {args.current_bias}A')
    print('=' * 55)

    # 1. 加载工况
    t, v = load_drive_cycle(cycle)
    P_load = vehicle_power(v, DT)
    N = len(t)
    print(f'  功率需求范围: {P_load.min():.1f} ~ {P_load.max():.1f} kW')

    # 2. 规则控制器
    print(f'\n[1/4] 规则控制器...')
    rule = run_rule_controller(P_load)

    # 3. DP
    print(f'\n[2/4] DP 后向 Rollout...')
    from day8_dp_ems import backward_dp, forward_rollout
    J, pi = backward_dp(P_load)
    dp = forward_rollout(P_load, pi)

    # 4. ECMS
    if args.compare:
        print(f'\n[3/4] ECMS (标准 s=130)...')
        from day9_ecms_ems import ecms_sim
        S_FACTOR_DEFAULT = 130.0
        ecms = ecms_sim(P_load, SOC_0=0.6, s_factor=S_FACTOR_DEFAULT)
        ecms['fc_efficiency'] = fc_efficiency(ecms['P_fc_kW'])
    else:
        ecms = None

    # 5. MPC + EKF
    print(f'\n[3/4] MPC+{args.soc_estimator.upper()} (N_p={n_p}, bias={args.current_bias}A)...')
    mpc_result = mpc_sim(P_load, SOC_0=0.6, N_p=n_p, **mpc_kwargs)

    # 6. 打印指标
    print(f'\n[4/4] 对比结果:')
    if args.compare and ecms is not None:
        print_four_way_metrics(rule, dp, ecms, mpc_result, P_load)
        plot_four_way(t, v, P_load, rule, dp, ecms, mpc_result, cycle)
    else:
        print()
        print('=' * 55)
        print(f'  {"指标":<22} {"规则控制器":>12} {"DP":>12} {"MPC":>12}')
        print('=' * 55)
        rule_H2 = rule['m_H2_cumul_kg'][-1]
        dp_H2 = dp['m_H2_cumul_kg'][-1]
        mpc_H2 = mpc_result['m_H2_cumul_kg'][-1]
        rows = [
            ('总氢耗 (kg)', f'{rule_H2:.4f}', f'{dp_H2:.4f}', f'{mpc_H2:.4f}'),
            ('SOC 初值→终值', f'0.60→{rule["SOC"][-1]:.3f}',
             f'0.60→{dp["SOC"][-1]:.3f}',
             f'0.60→{mpc_result["SOC_end_true"]:.3f}'),
            ('SOC修正氢耗 (kg)',
             f'{soc_equivalent_h2(rule_H2, rule["SOC"][-1]):.4f}',
             f'{soc_equivalent_h2(dp_H2, dp["SOC"][-1]):.4f}',
             f'{mpc_result["H2_eq_kg"]:.4f}'),
            ('FC 平均效率', f'{fc_efficiency(rule["P_fc_kW"]).mean():.1%}',
             f'{fc_efficiency(dp["P_fc_kW"]).mean():.1%}',
             f'{fc_efficiency(mpc_result["P_fc_kW"]).mean():.1%}'),
            ('SOC 估计 RMSE', '', '',
             f'{mpc_result["SOC_rmse"]:.4f}'),
        ]
        for row in rows:
            print(f'  {row[0]:<22} {row[1]:>12} {row[2]:>12} {row[3]:>12}')
        print('=' * 55)

        # 绘图
        if not args.plot_only:
            t_min = t / 60
            fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True)
            ax = axes[0]
            ax.plot(t_min, v, 'b-', linewidth=0.8, alpha=0.4, label='Speed')
            ax.set_ylabel('Speed (km/h)')
            ax2 = ax.twinx()
            for name, r, c, ls in [('Rule', rule, 'orange', '--'),
                                     ('DP', dp, 'g', '-'),
                                     ('MPC', mpc_result, 'r', ':')]:
                ax2.plot(t_min, r['SOC'], color=c, linewidth=1.0, linestyle=ls, label=name)
            ax2.set_ylabel('SOC')
            ax2.set_ylim(0.2, 0.9)
            ax.legend(loc='upper right', fontsize=8)
            ax.set_title(f'{cycle.upper()} — Rule vs DP vs MPC+EKF')
            ax.grid(True, alpha=0.3)

            ax = axes[1]
            ax.fill_between(t_min, 0, P_load, alpha=0.15, color='gray', label='Load')
            ax.plot(t_min, dp['P_fc_kW'], 'g-', linewidth=1.0, label='DP FC')
            ax.plot(t_min, mpc_result['P_fc_kW'], 'r-', linewidth=1.0, label='MPC FC')
            ax.set_ylabel('Power (kW)')
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)

            ax = axes[2]
            ax.plot(t_min, rule['SOC'], 'orange', linewidth=1.0, linestyle='--', label='Rule')
            ax.plot(t_min, dp['SOC'], 'g-', linewidth=1.0, label='DP')
            ax.plot(t_min, mpc_result['SOC'], 'r-', linewidth=1.0, label='MPC true')
            if 'SOC_est' in mpc_result:
                ax.plot(t_min, mpc_result['SOC_est'], 'm-', linewidth=0.7, alpha=0.6, label='MPC est')
            ax.set_ylabel('SOC')
            ax.set_ylim(0.2, 0.9)
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)

            ax = axes[3]
            for name, r, c, ls in [('Rule', rule, 'orange', '--'),
                                     ('DP', dp, 'g', '-'),
                                     ('MPC', mpc_result, 'r', ':')]:
                h2v = r['m_H2_cumul_kg'][-1]
                ax.plot(t_min, r['m_H2_cumul_kg'], color=c, linewidth=1.0,
                        linestyle=ls, label=f'{name} ({h2v:.3f} kg)')
            ax.set_ylabel('Cumul. H₂ (kg)')
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)

            plt.tight_layout()
            png_path = os.path.join(RESULTS_DIR, f'MPC_ekf_vs_DP_Rule_{cycle}_np{n_p}.png')
            plt.savefig(png_path, dpi=150, bbox_inches='tight')
            print(f'[图] {png_path}')
            plt.close()

            # SOC 估计对比图
            plot_soc_estimation(t, v, mpc_result, cycle)

    # 7. 保存结果
    df_mpc = pd.DataFrame({
        'time': mpc_result['time'],
        'speed_kmh': v,
        'P_load_kW': P_load,
        'P_fc_kW': mpc_result['P_fc_kW'],
        'P_bat_kW': mpc_result['P_bat_kW'],
        'SOC_true': mpc_result.get('SOC_true', mpc_result['SOC']),
        'SOC_est': mpc_result.get('SOC_est', mpc_result['SOC']),
        'SOC_open': mpc_result.get('SOC_open', mpc_result['SOC']),
        'm_H2_cumul_kg': mpc_result['m_H2_cumul_kg'],
        'H2_eq_kg': mpc_result['H2_eq_kg'],
    })
    csv_path = os.path.join(RESULTS_DIR, f'mpc_ems_ekf_{cycle}_np{n_p}.csv')
    df_mpc.to_csv(csv_path, index=False)
    print(f'[保存] {csv_path}')

    summary = {
        'cycle': cycle,
        'N_p': n_p,
        'estimator': args.soc_estimator,
        'current_bias': args.current_bias,
        'H2_raw_kg': mpc_result['H2_raw_kg'],
        'SOC_end_true': mpc_result['SOC_end_true'],
        'SOC_end_est': mpc_result.get('SOC_end_est', mpc_result['SOC_end_true']),
        'SOC_ref_minus_end': SOC_REF - mpc_result['SOC_end_true'],
        'H2_eq_kg': mpc_result['H2_eq_kg'],
        'SOC_rmse': mpc_result['SOC_rmse'],
        'SOC_open_rmse': mpc_result['SOC_open_rmse'],
        **mpc_result['config'],
    }
    summary_path = os.path.join(RESULTS_DIR, f'mpc_ems_ekf_{cycle}_np{n_p}_summary.csv')
    pd.DataFrame([summary]).to_csv(summary_path, index=False)
    print(f'[保存] {summary_path}')

    # 8. N_p 敏感性扫描
    if args.scan:
        print(f'\n[MPC N_p 敏感性扫描]')
        np_df = mpc_n_p_scan(P_load, N_p_values=[10, 20, 30, 50, 80, 120, 200], **mpc_kwargs)
        np_df.to_csv(os.path.join(RESULTS_DIR, f'MPC_np_sensitivity_ekf_{cycle}.csv'), index=False)
        plot_np_sensitivity(np_df, dp['m_H2_cumul_kg'][-1], cycle)

    print(f'\n[OK] MPC+{args.soc_estimator.upper()} 仿真完成！')
    print(f'   结果: {csv_path}')


if __name__ == '__main__':
    main()
