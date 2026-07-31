#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
方案 A 第一步：pybamm DFN 合成数据 + 现有 EKF 对比
====================================================
流程：
  1. 用 pybamm 的 DFN（电化学物理模型）仿真生成"真实"电压/电流/SOC 序列
  2. 喂给现有 EKF 估计器（docs/soc-estimation/code/ekf_soc_estimator.py）
  3. 对比 DFN 物理模型 SOC vs EKF 等效电路估计 SOC

数据来源说明：
  - 真实 LG HG2 数据集（Mendeley）下载到位前，用 pybamm 内置 Chen2020（NMC）
    参数生成合成数据跑通流程；
  - 数据到位后，本脚本可扩展为加载真实 CSV 直接替换第 1 步。

用法：
  python run_pybamm_synth.py                 # 1C 恒流放电
  python run_pybamm_synth.py --crate 2 --temp -10   # 2C 低温（未来扩展）
"""
import argparse
import sys
from pathlib import Path

import numpy as np

# ── 定位项目根 / 输出目录（复用 Week11 的路径思路）──
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "results" / "soc_pybamm_synth"
sys.path.insert(0, str(PROJECT_ROOT / "docs" / "soc-estimation" / "code"))

try:
    import pybamm
except ImportError:
    print("需要安装 pybamm：pip install pybamm -i https://pypi.tuna.tsinghua.edu.cn/simple")
    sys.exit(1)


def generate_dfn_synth_data(c_rate=1.0, duration_s=1800, param_set="Chen2020"):
    """用 pybamm DFN 模型生成合成充放电数据。

    返回 dict: t, I, V, SOC_true, capacity_Ah
    """
    model = pybamm.lithium_ion.DFN()
    param = pybamm.ParameterValues(param_set)

    # 恒流放电实验：C 倍率放电到截止电压 2.5V，或指定时长
    period = "10 seconds"
    experiment = pybamm.Experiment(
        [f"Discharge at {c_rate}C until 2.5V"],
        period=period,
    )
    sim = pybamm.Simulation(
        model,
        parameter_values=param,
        experiment=experiment,
        output_variables=[
            "Time [s]",
            "Voltage [V]",
            "Current [A]",
            "Discharge capacity [A.h]",
        ],
    )
    sol = sim.solve()

    # 提取数据
    t = np.array(sol["Time [s]"].entries)
    V = np.array(sol["Voltage [V]"].entries)
    I = np.array(sol["Current [A]"].entries)
    cap = np.array(sol["Discharge capacity [A.h]"].entries)

    # 真实 SOC：用放电容量反推（容量 = 1C 放电 1 小时 ≈ 额定 Ah）
    # 用满充（cap 最小）到当前放电容量归一化
    # Chen2020 额定容量约 5 Ah（1C=5A）
    rated_cap = abs(I).max() / c_rate  # Ah，C 率定义反推
    SOC_true = np.clip(1.0 - cap / rated_cap, 0.0, 1.0)

    return {"t": t, "I": I, "V": V, "SOC_true": SOC_true, "capacity_Ah": rated_cap}


def get_ocv_curve(param_set="Chen2020", c_rate=0.05, rated_cap=5.0):
    """从 pybamm 慢速放电（C/20）提取 OCV-SOC 标定曲线。

    等效电路模型的 OCV 表应当从电池数据标定（近似：低电流极化小 ≈ OCV）。
    这一步正是"用物理模型（DFN）数据标定等效电路模型"的关键操作。
    """
    model = pybamm.lithium_ion.DFN()
    param = pybamm.ParameterValues(param_set)
    sim = pybamm.Simulation(
        model,
        parameter_values=param,
        experiment=pybamm.Experiment([f"Discharge at {c_rate}C until 2.5V"], period="1 minute"),
        output_variables=["Voltage [V]", "Discharge capacity [A.h]"],
    )
    sol = sim.solve()
    V = np.array(sol["Voltage [V]"].entries)
    cap = np.array(sol["Discharge capacity [A.h]"].entries)
    soc = np.clip(1.0 - cap / rated_cap, 0.0, 1.0)

    # 建立均匀间隔的 SOC 断点 + 对应 OCV（线性插值到 0~1，间隔 0.05）
    soc_bp = np.linspace(0.0, 1.0, 21)
    ocv_lu = np.interp(soc_bp, soc[::-1], V[::-1])
    return soc_bp, ocv_lu


def run_ekf_on_data(data, dt=10.0):
    """把合成数据喂给现有 EKF 估计器，返回 SOC 估计序列。

    注意：现有 EKF（ekf_soc_estimator.py）写死了 100Ah 电池参数和粗糙的
    300~360 OCV 表（单位错误）。这里做两处关键适配，正是方案 A 的核心：
      1. 对齐容量 Q_BAT 与 SOC 范围（pybamm 小电芯 5 Ah, [0,1]）
      2. 用 pybamm C/20 慢放提取的 OCV 曲线覆盖写死查表（模型标定）
    """
    import ekf_soc_estimator as ekf_mod
    from ekf_soc_estimator import EKFBuffer, ekf_soc_step

    # ── 1. 对齐电芯参数 ──
    ekf_mod.Q_BAT = data["capacity_Ah"]  # Ah
    ekf_mod.SOC_MIN = 0.0
    ekf_mod.SOC_MAX = 1.0

    # ── 2. 用 pybamm 物理模型标定 OCV 表（核心：等效电路需要标定）──
    soc_bp, ocv_lu = get_ocv_curve(rated_cap=data["capacity_Ah"])
    ekf_mod.SOC_BP = soc_bp
    ekf_mod.OCV_LU = ocv_lu

    t = data["t"]
    I = data["I"]
    V = data["V"]
    SOC_true = data["SOC_true"]

    # 初始估计从 0.95 开始（略低于真值 1.0）：
    #   - 避免 soc_pred 越界到 >1.0 触发 lookup_docv_dsoc 的 0/0 nan（现有 EKF 边界 bug）
    #   - 顺便展示 EKF 从初始偏差收敛的能力（对比中更有说服力）
    x0 = 0.95
    ekf = EKFBuffer(x0=x0, P0=0.1)

    soc_ekf = []
    for k in range(len(t)):
        # 电流符号对齐：pybamm 放电为正，EKF 期望放电为负（SOC 递减）
        i_for_ekf = -I[k]
        soc_est = ekf_soc_step(ekf, i_for_ekf, V[k], dt=dt)
        soc_ekf.append(soc_est)

    return np.array(soc_ekf)


def main():
    parser = argparse.ArgumentParser(description="pybamm DFN 合成数据 + EKF 对比")
    parser.add_argument("--crate", type=float, default=1.0, help="放电倍率 (C)")
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    out_dir = Path(args.output_dir) if args.output_dir else RESULTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"参数集: Chen2020 (NMC/graphite), 放电 {args.crate}C")
    print("生成 pybamm DFN 合成数据 ...")
    data = generate_dfn_synth_data(c_rate=args.crate)
    print(f"  时间点: {len(data['t'])}, 放电容量 {data['capacity_Ah']:.2f} Ah")

    print("运行现有 EKF 估计 ...")
    soc_ekf = run_ekf_on_data(data)

    # ── 指标 ──
    soc_true = data["SOC_true"]
    rmse = float(np.sqrt(np.mean((soc_ekf - soc_true) ** 2)))
    end_err = float(abs(soc_ekf[-1] - soc_true[-1]))
    print(f"  EKF SOC RMSE = {rmse:.4f}")
    print(f"  终点 SOC 误差 = {end_err:.4f}")

    # ── 保存 CSV ──
    import csv

    csv_path = out_dir / f"pybamm_dfn_{args.crate}c_synth.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["t_s", "I_A", "V_V", "SOC_true", "SOC_ekf"])
        for k in range(len(data["t"])):
            w.writerow([data["t"][k], data["I"][k], data["V"][k], soc_true[k], soc_ekf[k]])
    print(f"  CSV 已保存: {csv_path}")

    # ── 出图 ──
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    # 中文字体配置（Windows 微软雅黑优先）
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for cand in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "DejaVu Sans"):
        if cand in installed:
            plt.rcParams["font.family"] = cand
            break
    plt.rcParams["axes.unicode_minus"] = False

    fig, axes = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
    axes[0].plot(data["t"], data["V"], label="DFN 端电压", color="tab:blue")
    axes[0].set_ylabel("电压 (V)")
    axes[0].grid(alpha=0.3)
    axes[0].legend()

    axes[1].plot(data["t"], data["I"], label="电流", color="tab:red")
    axes[1].set_ylabel("电流 (A)")
    axes[1].grid(alpha=0.3)
    axes[1].legend()

    axes[2].plot(data["t"], soc_true, label="DFN 真实 SOC", color="tab:green", linewidth=2)
    axes[2].plot(data["t"], soc_ekf, label="EKF 估计 SOC", color="tab:orange", linestyle="--")
    axes[2].set_ylabel("SOC")
    axes[2].set_xlabel("时间 (s)")
    axes[2].grid(alpha=0.3)
    axes[2].legend()

    fig.suptitle(f"pybamm DFN 合成数据 vs 等效电路 EKF ({args.crate}C 放电, RMSE={rmse:.4f})")
    fig.tight_layout()
    png_path = out_dir / f"pybamm_dfn_{args.crate}c_vs_ekf.png"
    plt.savefig(png_path, dpi=150)
    plt.close()
    print(f"  对比图已保存: {png_path}")

    print("\n完成！等 LG HG2 真实数据到位后，把第 1 步替换为真实 CSV 加载即可。")


if __name__ == "__main__":
    main()
