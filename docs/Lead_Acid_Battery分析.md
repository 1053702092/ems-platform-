# Lead_Acid_Battery 模型分析

> 日期：2026-06-04
> 来源：`env/simulink_models/Lead_Acid_Battery.slx`

## 顶层结构

```
Lead_Acid_Battery (14个顶层模块)
├── Battery_Resistance      ← 电池内阻计算子系统
├── Eu_Caculation           ← 开路电压计算子系统
├── Initial_SOC = 0.9       ← 初始 SOC（90%）
├── Integrator IC=0         ← SOC 积分（安时积分法）
├── Ksoc = -1/3600*3.6      ← SOC 增益系数
├── Rl(负载) = 2             ← 负载电阻
├── Saturation [1, 0]       ← 限幅（上限1，下限0）
├── Product / Product1      ← 乘法器
├── Add / U                 ← 加法器
├── Algebraic Constraint    ← 代数约束
├── Display I               ← 显示电流
└── Display u               ← 显示电压
```

## 特点

- **自包含模型**：自带信号源（Constant Initial_SOC），没有外部输入端口
- **Standalone 模式**：只能独立运行，不能直接集成到更大系统
- **显示输出**：用 Display 模块显示电流(I)和电压(u)，但没配 To Workspace

## 改造方向

要把它集成到 EMS 系统中，需要：

1. 把 `Initial_SOC` 从 Constant 改成外部输入端口
2. 把 `Rl(负载)` 改成外部功率/电流输入
3. 加 To Workspace 记录 SOC、电压、电流
4. 加输出端口供 EMS 使用

## 参考模型情况

源文件：`power_FCHPS_MEA2.slx`

| 组件 | 状态 |
|------|------|
| FC Power Module | ✅ 完整（电堆+控制器） |
| Load Profile | ✅ Lookup Table |
| Battery | ❌ 空子系统 |
| EMS Controller | ❌ 空子系统 |
| Supercapacitor | 有结构 |

参考模型的 Battery 和 EMS 都是空壳，需要我们自己填充。
