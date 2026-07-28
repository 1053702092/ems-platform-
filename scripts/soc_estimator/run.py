#!/usr/bin/env python3
"""
电池 SOC 估计 DEMO — 主入口
================================
用法:
  python run.py                         标准对比（EKF vs 开环）
  python run.py --fault bias --value 2  偏置故障 2A
  python run.py --fault noise --value 1 噪声故障 σ=1.0
  python run.py --all                   全场景测试
"""
import argparse
import numpy as np
import matplotlib.pyplot as plt
from estimator import OpenLoopEstimator, EKFEstimator, AEKFEstimator
from battery_model import load_cycle_data, simulate_measurements

def main():
    parser = argparse.ArgumentParser(description='电池 SOC 估计 DEMO')
    parser.add_argument('--fault', choices=['bias', 'noise', 'none'], default='none')
    parser.add_argument('--value', type=float, default=0.0)
    parser.add_argument('--all', action='store_true', help='跑全场景对比')
    args = parser.parse_args()

    # ── 加载工况数据 ──
    # TODO: 从 CSV 加载电流/电压数据，或生成模拟数据
    print(">> 加载工况数据 ...")

    # ── 初始化三个估计器 ──
    open_loop = OpenLoopEstimator()
    ekf = EKFEstimator()
    aekf = AEKFEstimator()

    # ── 仿真循环 ──
    # TODO: 逐时间步调用 estimator.step()
    # TODO: 记录SOC真实值/开环值/EKF值/AEKF值
    print(">> 运行仿真 ...")

    # ── 计算指标 ──
    # TODO: SOC_RMSE, 终点误差
    print(">> 计算指标 ...")

    # ── 出图 ──
    # TODO: SOC 轨迹对比图
    print(">> 出图 ...")

    print(">> Done. 结果已保存到 results/")

if __name__ == '__main__':
    main()
