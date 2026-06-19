/**
 * ems_basics/01_fc_hydrogen_model.cpp
 *
 * 燃料电池氢耗模型 — C++ 实现
 * 对应 Python day8_dp_ems.py 中的 fc_hydrogen_flow / fc_efficiency
 *
 * 学习要点：
 * - vector/array 基本操作
 * - 线性插值（interp）实现
 * - 函数指针/回调的用法
 *
 * 编译：g++ -std=c++17 -o build/01_fc_hydrogen_model 01_fc_hydrogen_model.cpp && ./build/01_fc_hydrogen_model
 */

#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <cassert>

using namespace std;

// ====== 燃料电池参数 ======
const double LHV_H2 = 120e6;  // J/kg
const vector<double> PFC_EFF_BP = {0, 2, 5, 8, 10, 15, 20, 25, 30};      // kW
const vector<double> ETA_FC     = {0, 0.28, 0.40, 0.48, 0.50, 0.55, 0.53, 0.48, 0.40};

// ====== 线性插值 ======
double interp(double x, const vector<double>& xp, const vector<double>& fp) {
    // 边界处理
    if (x <= xp.front()) return fp.front();
    if (x >= xp.back())  return fp.back();

    // 找区间
    auto it = upper_bound(xp.begin(), xp.end(), x);
    int idx = it - xp.begin() - 1;

    // 线性插值
    double t = (x - xp[idx]) / (xp[idx+1] - xp[idx]);
    return fp[idx] + t * (fp[idx+1] - fp[idx]);
}

// ====== FC 效率 ======
double fc_efficiency(double P_fc_kW) {
    return interp(P_fc_kW, PFC_EFF_BP, ETA_FC);
}

// ====== FC 氢耗 [g/s] ======
double fc_hydrogen_flow(double P_fc_kW) {
    if (P_fc_kW <= 0) return 0.0;

    double eta = fc_efficiency(P_fc_kW);
    // P_fc [kW] * 1000 [W/kW] / (eta * LHV_H2 [J/kg]) * 1000 [g/kg]
    return P_fc_kW * 1000.0 / (eta * LHV_H2) * 1000.0;
}

// ====== 电池 SOC 转移（简化版） ======
double state_transition(double SOC_k, double P_fc_kW, double P_load_kW, double dt = 1.0) {
    const double Q_BAT = 50.0;  // Ah
    const double R_INT = 0.05;  // Ohm
    const vector<double> SOC_BP = {0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9, 1.0};
    const vector<double> OCV_LU = {320, 330, 338, 345, 352, 358, 362, 368, 380};

    double P_bat_kW = P_load_kW - P_fc_kW;

    if (std::abs(P_bat_kW) < 0.01) return SOC_k;

    double V_oc = interp(SOC_k, SOC_BP, OCV_LU);
    double P_w = P_bat_kW * 1000.0;  // W

    double delta = V_oc * V_oc - 4.0 * R_INT * P_w;
    if (delta < 0) return SOC_k;

    double I = (V_oc - sqrt(delta)) / (2.0 * R_INT);
    I = std::clamp(I, -300.0, 300.0);

    double SOC_next = SOC_k - I / (Q_BAT * 3600.0) * dt;
    return std::clamp(SOC_next, 0.2, 0.9);
}

// ====== 主函数 ======
int main() {
    cout << "=== FC 氢耗模型 (C++) ===" << endl;
    cout << "LHV_H2 = " << LHV_H2 / 1e6 << " MJ/kg" << endl;
    cout << endl;

    // 效率比较
    cout << "--- FC 效率 ---" << endl;
    for (double p : {0, 2, 5, 10, 15, 20, 30}) {
        printf("  P_fc = %5.1f kW → η = %.2f%%, H2 = %.3f g/s\n",
               p, fc_efficiency(p) * 100, fc_hydrogen_flow(p));
    }

    // 氢耗曲线验证（和 Python 输出对比）
    cout << "\n--- 验证：与 Python fc_hydrogen_flow 一致性 ---" << endl;
    double h2_10 = fc_hydrogen_flow(10);
    double h2_15 = fc_hydrogen_flow(15);
    double h2_20 = fc_hydrogen_flow(20);
    printf("  fc_hydrogen_flow(10)  = %.4f g/s\n", h2_10);
    printf("  fc_hydrogen_flow(15)  = %.4f g/s\n", h2_15);
    printf("  fc_hydrogen_flow(20)  = %.4f g/s\n", h2_20);

    // SOC 转移验证
    cout << "\n--- SOC 状态转移 ---" << endl;
    double soc = 0.6;
    double p_load = 20.0;
    cout << "  SOC_0 = " << soc << ", P_load = " << p_load << " kW" << endl;
    for (double p_fc : {0.0, 10.0, 20.0, 30.0}) {
        double soc_next = state_transition(soc, p_fc, p_load);
        printf("    P_fc = %5.1f kW → P_bat = %5.1f kW → SOC_next = %.4f\n",
               p_fc, p_load - p_fc, soc_next);
    }

    return 0;
}
