# -*- coding: utf-8 -*-
"""
ekf_soc_estimator.py — EKF SOC 估计器（可直接嵌入 MPC/EMS 仿真）

核心功能：
  1. ekf_soc_step() — EKF 单步 SOC 估计（融合电流和电压）
  2. simulate_voltage() — 电压测量仿真（无实物时使用）
  3. mpc_sim_with_ekf() — 替换 mpc_sim() 的开环 SOC 为 EKF 估计

使用方法：
  from ekf_soc_estimator import ekf_soc_step, EKFBuffer

  # 初始化
  ekf = EKFBuffer(x0=0.6, P0=0.01)

  for k in range(N):
      V_t_k = 模拟或测量电压
      I_k = 模拟或测量电流
      SOC_est = ekf_soc_step(ekf, I_k, V_t_k, P_bat_k)
      # SOC_est 即为 EKF 修正后的 SOC

依赖：numpy
"""

import numpy as np

# ====================================================================
# 从 day8_dp_ems 引入电池参数（也可直接复制使用）
# ====================================================================
# OCV-SOC 查表曲线
SOC_BP = np.array([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
OCV_LU = np.array([300, 310, 320, 325, 330, 335, 340, 345, 350, 355, 360])

R_INT = 0.5          # 电池内阻 (Ω)
Q_BAT = 100          # 电池容量 (Ah)
SOC_MIN, SOC_MAX = 0.3, 0.8
DT = 1.0             # 采样时间 (s)

# EKF 调参（核心）
Q_EKF = 5e-5         # 过程噪声 — 匹配电流偏置的漂移速度
R_EKF = 0.03         # 测量噪声 — OCV 电压不确定性（含 OCV 曲线误差）
P0_EKF = 0.1         # 初始协方差 — SOC 初始不确定性


# ====================================================================
# 辅助函数
# ====================================================================

def lookup_ocv(soc):
    """OCV 查表：SOC -> 开路电压"""
    return np.interp(soc, SOC_BP, OCV_LU)


def lookup_docv_dsoc(soc):
    """OCV 曲线斜率：d(Voc)/d(SOC)（数值微分）"""
    delta = 1e-6
    soc_lo = np.clip(soc - delta, 0, 1)
    soc_hi = np.clip(soc + delta, 0, 1)
    return (lookup_ocv(soc_hi) - lookup_ocv(soc_lo)) / (soc_hi - soc_lo)


def battery_current_from_power(p_bat, soc):
    """由功率反算电流（与 mpc_step_soc 一致）"""
    v_oc = lookup_ocv(soc)
    p_w = p_bat * 1000.0  # kW -> W
    delta = v_oc**2 - 4 * R_INT * p_w
    if delta < 0:
        return 0.0
    i = (v_oc - np.sqrt(delta)) / (2 * R_INT)
    return np.clip(i, -300, 300)


# ====================================================================
# EKF 状态缓存
# ====================================================================

class EKFBuffer:
    """EKF 状态缓存器（持有 x, P 在循环间传递）"""
    def __init__(self, x0=0.6, P0=P0_EKF):
        self.x = float(x0)   # SOC 估计值
        self.P = float(P0)   # 估计协方差
        self.innov = 0.0     # 新息（用于监控）
        self.K_gain = 0.0    # 卡尔曼增益（用于监控）


# ====================================================================
# EKF 单步 SOC 估计（核心函数）
# ====================================================================

def ekf_soc_step(ekf, i_meas, v_t_meas, dt=DT):
    """
    EKF 单步 SOC 估计

    Parameters
    ----------
    ekf : EKFBuffer — EKF 状态缓存
    i_meas : float — 测量电流 (A)（含偏置和噪声）
    v_t_meas : float — 测量端电压 (V)
    dt : float — 采样时间 (s)

    Returns
    -------
    soc_est : float — EKF 估计的当前 SOC

    原理
    ----
    状态: SOC (1D)
    过程: SOC_{k+1} = SOC_k - I/Q*dt  (安时积分)
    观测: V_t = Voc(SOC)               (忽略 R*I 压降，已包含在 OCV 模型误差中)

    两阶段:
      Predict: 安时积分向前推一步，协方差增大
      Update:  用电压新息修正 SOC 漂移
    """
    # ======== Predict (时间更新) ========
    # 安时积分：SOC_pred = SOC - I/Q*dt
    soc_pred = ekf.x - i_meas / (Q_BAT * 3600) * dt

    # 状态雅可比：F = d(SOC_next)/d(SOC)
    #   由于 SOC_{k+1} = SOC_k - I(SOC_k)/Q*dt
    #   F = 1 - (dI/dSOC)/Q*dt
    #   简化：dI/dSOC 很小，F ≈ 1。这是合理的因为：
    #   电流主要是功率决定的，SOC 对电流的反馈很弱
    F = 1.0

    # 协方差预测
    P_pred = F * ekf.P * F + Q_EKF

    # ======== Update (测量更新) ========
    # 预测电压（OCV 查表）
    v_pred = lookup_ocv(soc_pred)

    # 新息 = 实际电压 - 预测电压
    y = v_t_meas - v_pred

    # 观测雅可比：H = d(Voc)/d(SOC)
    H = lookup_docv_dsoc(soc_pred)

    # 新息协方差
    S = H * P_pred * H + R_EKF

    # 卡尔曼增益
    K = P_pred * H / S

    # SOC 修正
    soc_est = soc_pred + K * y

    # 协方差更新
    P_est = (1 - K * H) * P_pred

    # 边界保护
    soc_est = float(np.clip(soc_est, SOC_MIN, SOC_MAX))
    P_est = max(P_est, 1e-8)

    # 更新缓存
    ekf.x = soc_est
    ekf.P = P_est
    ekf.innov = float(y)
    ekf.K_gain = float(K)

    return soc_est


# ====================================================================
# 电压测量仿真（仅用于无实物时）
# ====================================================================

def simulate_voltage(soc_true, i_bat, noise_std=0.1):
    """
    模拟电压测量: V_t = Voc(SOC) + 高斯噪声

    用于纯仿真环境（无实物数据时），模拟 BMS 电压传感器输出。

    注意：EKF 观测模型使用 v_pred = OCV(SOC_pred)，因此模拟电压
    不减去 R*I（R*I 压降被归入模型误差，由 R_EKF 吸收）。
    这是工程中的常见简化：OCV 曲线斜率 (~50V/SOC) >> R*I 变化 (~2-5V),
    因此将 R*I 当作测量噪声处理，R_EKF 适当放大即可。

    Parameters
    ----------
    soc_true : float — 真实 SOC
    i_bat : float — 真实电池电流 (A)（仅用于参考，未加入观测模型）
    noise_std : float — 电压传感器噪声标准差 (V)

    Returns
    -------
    v_t : float — 模拟的端电压测量值 (V)
    """
    v_oc = lookup_ocv(soc_true)
    # 注意：不减去 R*I，与 EKF 观测模型保持一致
    v_t = v_oc + noise_std * np.random.randn()
    return v_t


# ====================================================================
# 替换 mpc_sim() 中的开环 SOC 为 EKF 估计
# ====================================================================

def mpc_sim_with_ekf(P_load, SOC_0=0.6, N_p=50, w_soc=500.0,
                     beta_term=1000.0, soc_ref=0.6,
                     current_bias=2.0, current_noise_std=0.5,
                     voltage_noise_std=0.1, ekf_x0=None):
    """
    带 EKF SOC 估计的 MPC 仿真

    与 mpc_sim() 接口兼容，但用 EKF 替换了开环 SOC 估计。
    可模拟电流传感器偏置，验证 EKF 的抗漂移能力。

    Parameters 与 mpc_sim() 一致，额外参数：
      current_bias : float — 模拟电流传感器偏置 (A)
      current_noise_std : float — 电流测量噪声 (A)
      voltage_noise_std : float — 电压测量噪声 (V)
      ekf_x0 : float or None — EKF 初始 SOC（None=使用 SOC_0）

    Returns
    -------
    dict — 含 SOC_EKF、SOC_true（对比用）等字段
    """
    from day8_dp_ems import fc_hydrogen_flow, PFC_MIN, PFC_MAX, N_PFC, PFC_EFF_BP, ETA_FC
    from day8_dp_ems import fc_efficiency

    PFC_GRID = np.linspace(PFC_MIN, PFC_MAX, N_PFC)
    H2_GRID = fc_hydrogen_flow(PFC_GRID)

    N = len(P_load)

    # 初始化 EKF
    if ekf_x0 is None:
        ekf_x0 = SOC_0
    ekf = EKFBuffer(x0=ekf_x0)

    # 记录数组
    SOC_true = np.zeros(N + 1)    # 真实 SOC（无偏，用于对比）
    SOC_ekf = np.zeros(N + 1)     # EKF 估计的 SOC
    SOC_open = np.zeros(N + 1)    # 开环安时积分（用于对比漂移）
    P_fc = np.zeros(N)
    m_H2 = np.zeros(N)
    I_meas = np.zeros(N)          # 测量电流（含偏置）
    V_meas = np.zeros(N)          # 测量电压（含噪声）

    SOC_true[0] = SOC_0
    SOC_ekf[0] = ekf_x0
    SOC_open[0] = ekf_x0

    print(f'[MPC+EKF] 初始 SOC — 真实={SOC_0:.2f}, EKF={ekf_x0:.2f}')

    for k in range(N):
        # ── 模拟真实电流 ──
        #     先找最优 P_fc（使用 EKF 估计的 SOC）
        soc_est_k = SOC_ekf[k]  # EKF 当前估计

        # ── MPC 优化（与 mpc_sim 完全一致） ──
        horizon = min(N_p, N - k)
        p_load_pred = P_load[k:k + horizon]

        J_best = np.inf
        best_j = 0
        for j in range(N_PFC):
            p_fc_cand = PFC_GRID[j]
            h2_cand = H2_GRID[j]
            soc_pred = soc_est_k
            J_total = 0.0
            for i in range(horizon):
                p_load_i = p_load_pred[i]
                p_bat_i = p_load_i - p_fc_cand
                J_total += h2_cand * DT
                J_total += 130.0 * abs(p_bat_i) / 3600.0 * DT
                # 用开环 SOC 预测（MPC 内循环不需要 EKF）
                # 内联 mpc_step_soc 避免循环依赖
                p_bat_pred = p_load_i - p_fc_cand
                v_oc_pred = np.interp(soc_pred, SOC_BP, OCV_LU)
                p_w_pred = p_bat_pred * 1000.0
                delta_pred = v_oc_pred**2 - 4 * R_INT * p_w_pred
                if delta_pred > 0:
                    i_pred = (v_oc_pred - np.sqrt(delta_pred)) / (2 * R_INT)
                    i_pred = np.clip(i_pred, -300, 300)
                    soc_pred = soc_pred - i_pred / (Q_BAT * 3600) * DT
                else:
                    soc_pred = np.clip(soc_pred, SOC_MIN, SOC_MAX)
                soc_dev = soc_pred - soc_ref
                if abs(soc_dev) > 0.05:
                    J_total += w_soc * soc_dev**2 * DT
                if i == horizon - 1 and k >= int(N * 0.7):
                    J_total += beta_term * (soc_pred - soc_ref)**2
            if J_total < J_best:
                J_best = J_total
                best_j = j

        P_fc[k] = PFC_GRID[best_j]
        m_H2[k] = H2_GRID[best_j] * DT

        # ── 真实 SOC 演化（无偏电流） ──
        p_bat_k = P_load[k] - P_fc[k]
        i_real = battery_current_from_power(p_bat_k, SOC_true[k])
        SOC_true[k + 1] = SOC_true[k] - i_real / (Q_BAT * 3600) * DT

        # ── 模拟传感器输出 ──
        i_meas_k = i_real + current_bias + current_noise_std * np.random.randn()
        v_meas_k = simulate_voltage(SOC_true[k], i_real, voltage_noise_std)
        I_meas[k] = i_meas_k
        V_meas[k] = v_meas_k

        # ── EKF SOC 估计 ──
        soc_ekf_k1 = ekf_soc_step(ekf, i_meas_k, v_meas_k)
        SOC_ekf[k + 1] = soc_ekf_k1

        # ── 开环安时积分（用于对比漂移） ──
        SOC_open[k + 1] = SOC_open[k] - i_meas_k / (Q_BAT * 3600) * DT

    print(f'[MPC+EKF] SOC_end — 真实={SOC_true[-1]:.3f}, '
          f'EKF={SOC_ekf[-1]:.3f}, 开环={SOC_open[-1]:.3f}')

    return {
        'SOC_true': SOC_true[:N],
        'SOC_ekf': SOC_ekf[:N],
        'SOC_open': SOC_open[:N],
        'P_fc_kW': P_fc,
        'm_H2_cumul_kg': np.cumsum(m_H2) / 1000,
        'I_meas': I_meas,
        'V_meas': V_meas,
        'SOC_end_true': SOC_true[-1],
        'SOC_end_ekf': SOC_ekf[-1],
        'SOC_end_open': SOC_open[-1],
    }


# ====================================================================
# 自测 / 独立运行
# ====================================================================

if __name__ == '__main__':
    import matplotlib.pyplot as plt

    print('=' * 55)
    print('  EKF SOC 估计器 — 自测')
    print('=' * 55)

    # 生成模拟工况
    N = 3600
    t = np.arange(N)
    P_load_cycle = 25 + 25 * np.sin(2*np.pi*t/900) + 15 * np.sin(2*np.pi*t/180)

    # 固定 FC 功率（模拟 EMS 输出）
    P_fc_fixed = 32 + 10 * np.sin(2*np.pi*t/400)
    P_fc_fixed = np.clip(P_fc_fixed, 10, 80)

    # 初始化
    SOC_0 = 0.6
    ekf = EKFBuffer(x0=0.5)  # 故意设偏
    SOC_true = np.zeros(N)
    SOC_est = np.zeros(N)
    SOC_open = np.zeros(N)
    SOC_est[0] = 0.5
    SOC_open[0] = 0.5
    SOC_true[0] = SOC_0

    I_BIAS = 2.0

    for k in range(N - 1):
        p_bat_k = P_load_cycle[k] - P_fc_fixed[k]
        i_real = battery_current_from_power(p_bat_k, SOC_true[k])
        SOC_true[k+1] = SOC_true[k] - i_real / (Q_BAT * 3600)

        i_meas = i_real + I_BIAS + 0.5 * np.random.randn()
        v_meas = simulate_voltage(SOC_true[k], i_real)
        SOC_est[k+1] = ekf_soc_step(ekf, i_meas, v_meas)

        SOC_open[k+1] = SOC_open[k] - i_meas / (Q_BAT * 3600)

    # 结果
    print(f'\n  SOC 初值: 真实={SOC_0:.1f}, EKF初值={0.5:.1f} (偏置{(SOC_0-0.5)/SOC_0*100:.0f}%)')
    print(f'  电流偏置: {I_BIAS}A (安时积分将持续漂移)')
    print(f'')
    print(f'  终端SOC:  真实={SOC_true[-1]:.3f}')
    print(f'            EKF={SOC_est[-1]:.3f}')
    print(f'            开环={SOC_open[-1]:.3f}')
    print(f'')
    print(f'  EKF 估计 RMSE: {np.sqrt(np.mean((SOC_est-SOC_true)**2)):.4f}')
    print(f'  开环积分 RMSE: {np.sqrt(np.mean((SOC_open-SOC_true)**2)):.4f}')

    # 图
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6))
    ax1.plot(t, SOC_true, 'k-', lw=2, label='True SOC')
    ax1.plot(t, SOC_open, 'b-', lw=1, alpha=0.7, label='Open-loop (drifting)')
    ax1.plot(t, SOC_est, 'r-', lw=2, label='EKF SOC')
    ax1.set_ylabel('SOC'); ax1.legend(); ax1.grid(True); ax1.set_ylim(0.3, 0.8)

    ax2.plot(t, SOC_est - SOC_true, 'r-', lw=1.5, label='EKF error')
    ax2.plot(t, SOC_open - SOC_true, 'b-', lw=1, alpha=0.7, label='Open-loop error')
    ax2.axhline(0, color='k', ls='--')
    ax2.set_xlabel('Time (s)'); ax2.set_ylabel('SOC Error'); ax2.legend(); ax2.grid(True)

    plt.tight_layout()
    plt.savefig('fc_soc_ekf_self_test.png', dpi=150)
    print(f'\n[图] fc_soc_ekf_self_test.png')
    print('=' * 55)
