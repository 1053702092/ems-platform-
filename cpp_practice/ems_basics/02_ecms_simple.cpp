/**
 * ems_basics/02_ecms_simple.cpp
 *
 * ECMS 简化实现 — C++ 版
 * 对应 Python day9_ecms_ems.py 的核心逻辑
 *
 * 功能：给定功率需求序列，用 ECMS 计算最优 FC 功率分配
 *
 * 学习要点：
 * - vector 操作（遍历、索引）
 * - 数组最小值查找（argmin）
 * - 面向过程 → 面向对象转换思路
 *
 * 编译：g++ -std=c++17 -o build/02_ecms_simple 02_ecms_simple.cpp && ./build/02_ecms_simple
 */

#define _USE_MATH_DEFINES
#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <cassert>

using namespace std;

// ====== 参数（内联 01_fc_hydrogen_model 的核心函数，避免链接冲突） ======
const double LHV_H2 = 120e6;
const vector<double> PFC_EFF_BP_VEC = {0, 2, 5, 8, 10, 15, 20, 25, 30};
const vector<double> ETA_FC_VEC     = {0, 0.28, 0.40, 0.48, 0.50, 0.55, 0.53, 0.48, 0.40};
const vector<double> SOC_BP_VEC = {0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9, 1.0};
const vector<double> OCV_LU_VEC = {320, 330, 338, 345, 352, 358, 362, 368, 380};

const double SOC_MIN = 0.2, SOC_MAX = 0.9;
const double SOC_REF = 0.6;
const double PFC_MIN = 0.0, PFC_MAX = 30.0;
const int    N_PFC = 60;
const double DT = 1.0;

// ====== 内联辅助函数（从 01_fc_hydrogen_model） ======
double interp2(double x, const vector<double>& xp, const vector<double>& fp) {
    if (x <= xp.front()) return fp.front();
    if (x >= xp.back())  return fp.back();
    auto it = upper_bound(xp.begin(), xp.end(), x);
    int idx = it - xp.begin() - 1;
    double t = (x - xp[idx]) / (xp[idx+1] - xp[idx]);
    return fp[idx] + t * (fp[idx+1] - fp[idx]);
}

double fc_efficiency2(double P_fc_kW) {
    return interp2(P_fc_kW, PFC_EFF_BP_VEC, ETA_FC_VEC);
}

double fc_hydrogen_flow2(double P_fc_kW) {
    if (P_fc_kW <= 0) return 0.0;
    double eta = fc_efficiency2(P_fc_kW);
    return P_fc_kW * 1000.0 / (eta * LHV_H2) * 1000.0;
}

double state_transition2(double SOC_k, double P_fc_kW, double P_load_kW, double dt=1.0) {
    const double Q_BAT = 50.0, R_INT = 0.05;
    double P_bat_kW = P_load_kW - P_fc_kW;
    if (std::abs(P_bat_kW) < 0.01) return SOC_k;
    double V_oc = interp2(SOC_k, SOC_BP_VEC, OCV_LU_VEC);
    double P_w = P_bat_kW * 1000.0;
    double delta = V_oc * V_oc - 4.0 * R_INT * P_w;
    if (delta < 0) return SOC_k;
    double I = (V_oc - sqrt(delta)) / (2.0 * R_INT);
    I = std::clamp(I, -300.0, 300.0);
    double SOC_next = SOC_k - I / (Q_BAT * 3600.0) * dt;
    return std::clamp(SOC_next, 0.2, 0.9);
}

// ====== ECMS：单步最优控制 ======
struct ECMSResult {
    vector<double> SOC;
    vector<double> P_fc;
    vector<double> P_bat;
    vector<double> m_H2_cumul_kg;
    double total_H2_kg;
    double SOC_end;
};

ECMSResult ecms_sim(const vector<double>& P_load,
                     double SOC_0 = 0.6,
                     double s_factor = 130.0) {
    int N = P_load.size();
    ECMSResult res;
    res.SOC.resize(N + 1, 0.0);
    res.P_fc.resize(N, 0.0);
    res.P_bat.resize(N, 0.0);
    res.m_H2_cumul_kg.resize(N, 0.0);

    res.SOC[0] = SOC_0;

    // 预计算 FC 功率网格和氢耗
    vector<double> PFC_GRID(N_PFC);
    vector<double> H2_GRID(N_PFC);
    for (int j = 0; j < N_PFC; j++) {
        PFC_GRID[j] = PFC_MIN + j * (PFC_MAX - PFC_MIN) / (N_PFC - 1);
        H2_GRID[j] = fc_hydrogen_flow2(PFC_GRID[j]);
    }

    for (int k = 0; k < N; k++) {
        // 瞬时优化：找等效氢耗最小的 FC 功率
        double best_H_eq = 1e10;
        double best_P_fc = PFC_GRID[N_PFC / 2];  // fallback

        for (int j = 0; j < N_PFC; j++) {
            double P_bat_candidate = P_load[k] - PFC_GRID[j];
            double SOC_next = state_transition2(res.SOC[k], PFC_GRID[j], P_load[k]);

            // SOC 约束
            if (SOC_next < SOC_MIN + 0.01 || SOC_next > SOC_MAX - 0.01)
                continue;

            // ★ 等效氢耗：实际氢耗 + 电池等效氢耗（用 |P_bat| 确保充放电都正成本）
            double H_eq = H2_GRID[j] + s_factor * std::abs(P_bat_candidate) / 3600.0;

            if (H_eq < best_H_eq) {
                best_H_eq = H_eq;
                best_P_fc = PFC_GRID[j];
            }
        }

        // 更新状态
        res.P_fc[k] = best_P_fc;
        res.P_bat[k] = P_load[k] - best_P_fc;
        res.m_H2_cumul_kg[k] = (k > 0 ? res.m_H2_cumul_kg[k-1] : 0.0)
                                + fc_hydrogen_flow2(best_P_fc) * DT / 1000.0;
        res.SOC[k + 1] = state_transition2(res.SOC[k], best_P_fc, P_load[k]);
    }

    res.total_H2_kg = res.m_H2_cumul_kg[N - 1];
    res.SOC_end = res.SOC[N];
    return res;
}

// ====== 简单工况生成器（用于测试） ======
vector<double> generate_wltc_like() {
    // 生成一个 WLTC 风格的小型工况（简化版，仅 100 步）
    vector<double> load(100);
    for (int i = 0; i < 100; i++) {
        // 模拟加减速循环
        double t = i / 100.0;
        load[i] = 5.0 + 20.0 * (0.5 + 0.5 * sin(t * 4 * M_PI));
    }
    return load;
}

// ====== 测试 ======
int main() {
    cout << "=== ECMS 简化实现 (C++) ===" << endl;
    cout << endl;

    // 简单功率序列
    vector<double> P_load = generate_wltc_like();

    cout << "功率范围: " << *min_element(P_load.begin(), P_load.end())
         << " ~ " << *max_element(P_load.begin(), P_load.end()) << " kW" << endl;
    cout << "步数: " << P_load.size() << endl;
    cout << endl;

    // 扫描不同 s 值
    cout << "--- ECMS 等效因子扫描 ---" << endl;
    printf("  %12s  %10s  %10s  %10s\n", "s [g/kWh]", "H2 [kg]", "SOC_end", "P_fc_mean");
    for (double s : {80.0, 100.0, 120.0, 130.0, 140.0, 160.0, 200.0}) {
        auto res = ecms_sim(P_load, 0.6, s);

        double P_fc_mean = 0;
        for (double p : res.P_fc) P_fc_mean += p;
        P_fc_mean /= res.P_fc.size();

        printf("  %10.0f  %10.4f  %10.4f  %10.1f\n",
               s, res.total_H2_kg, res.SOC_end, P_fc_mean);
    }

    cout << "\n推荐 s ≈ 120-140 g/kWh (平衡氢耗和 SOC 维持)" << endl;

    return 0;
}
