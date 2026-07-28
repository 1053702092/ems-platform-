#!/usr/bin/env python3
"""
电池模型 — OCV-SOC 曲线 + 测量值仿真
========================================
用多项式拟合典型 NMC 锂电池的 OCV-SOC 关系。
"""
import numpy as np


# ====================================================================
# OCV-SOC 查找表
# ====================================================================
# 典型 NMC 电池 OCV-SOC 曲线 (25°C, 0.5C 放电)
# SOC: 0.0 ~ 1.0, OCV: 对应开路电压 (V)
_OCV_TABLE = {
    'soc': [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    'ocv': [3.20, 3.45, 3.55, 3.62, 3.68, 3.72, 3.77, 3.85, 3.96, 4.10, 4.20],
}


def lookup_ocv(soc):
    """通过线性插值查 OCV-SOC 表返回开路电压 (V)"""
    # TODO: np.interp(soc, _OCV_TABLE['soc'], _OCV_TABLE['ocv'])
    return 3.7  # placeholder


def lookup_docv_dsoc(soc):
    """dOCV/dSOC 在 soc 处的数值导数（观测雅可比 H）"""
    # TODO: 用 np.gradient 或差分近似
    return 0.5  # placeholder


# ====================================================================
# 端电压仿真
# ====================================================================
def simulate_terminal_voltage(soc, current, R0=0.005):
    """
    仿真端电压: V_t = OCV(SOC) - I*R0 + 噪声

    参数:
      soc:     真实 SOC
      current: 电流 (A), 放电为正
      R0:      欧姆内阻 (Ω)
    返回:
      v_t:     端电压 (V)
    """
    ocv = lookup_ocv(soc)
    # TODO: V_t = OCV - I*R0 + 小噪声
    return ocv


# ====================================================================
# 工况数据加载
# ====================================================================
def load_cycle_data(cycle_name='wltc'):
    """
    加载或生成电流/电压数据

    返回:
      time:  时间序列 (s)
      i:     电流序列 (A)
      v_t:   端电压序列 (V)
      soc_true: 真实 SOC 序列 (用于对比)
    """
    # TODO: 从已有 CSV 或数据集加载
    # 临时生成模拟数据
    N = 1800
    t = np.arange(N)
    i = 10 + 20 * np.sin(2 * np.pi * t / 600)  # 模拟电流
    v_t = 3.7 - i * 0.005 + np.random.normal(0, 0.002, N)  # 模拟端电压
    soc_true = 0.6 - np.cumsum(i) / (Q_BAT * 3600)  # 由电流积分得到
    soc_true = np.clip(soc_true, 0.2, 0.9)
    return t, i, v_t, soc_true
