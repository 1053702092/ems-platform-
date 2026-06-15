# Derivation Package: DP Bellman Equation ↔ ECMS Hamiltonian

## Target
Explain the mathematical relationship between the DP discrete Bellman equation used in `day8_dp_ems.py` and the ECMS Hamiltonian formulation, and clarify why the two formulas look structurally different despite addressing the same optimization problem.

## Status
COHERENT AFTER REFRAMING / EXTRA ASSUMPTION

The two formulas are NOT the same equation. They are analogous formulations from different mathematical frameworks (discrete dynamic programming vs. continuous optimal control). The relationship between their parameters (α ↔ λ ↔ s) is a conceptual mapping that requires additional assumptions to make precise.

## Invariant Object
Total hydrogen consumption over the drive cycle:
```
J_total = ∫_0^T H_fc(P_fc(t)) dt
```
Both DP and ECMS (and the Hamiltonian framework) are methods to minimize this same quantity, subject to the battery SOC dynamics constraint.

## Assumptions

### Shared assumptions (both frameworks)
1. The FC hydrogen consumption rate `H_fc(P_fc)` is known from the efficiency lookup table
2. Battery dynamics follow the equivalent circuit model: `I = (V_oc - √(V_oc² - 4R_int·P_bat)) / (2R_int)`
3. SOC evolution: `SOC(k+1) = SOC(k) - I/(Q_bat·3600)·dt`
4. Power balance: `P_bat = P_load - P_fc`
5. SOC must remain in [SOC_MIN, SOC_MAX] throughout

### DP-specific assumptions
1. Discrete time: the drive cycle is sampled at 1 Hz (N = 1800 steps for WLTC)
2. SOC is discretized into N_SOC = 150 grid points
3. FC power is discretized into N_PFC = 60 grid points
4. The full drive cycle `P_load[0:N]` is known in advance (offline)
5. Terminal SOC penalty: `β × (SOC(N) - SOC_ref)²`

### ECMS/Hamiltonian-specific assumptions
1. Continuous time formulation (or fine-grained discrete time)
2. The co-state variable λ(t) exists and satisfies Pontryagin's minimum principle
3. The Hamiltonian is minimized at each time instant independently

### Critical approximations that bridge the two frameworks
1. **Constant co-state approximation**: Assuming λ(t) ≈ λ = constant reduces the Hamiltonian to ECMS form. This is NOT generally valid — it requires the FC efficiency curve to be approximately flat near the optimal operating point.
2. **Linear battery model approximation**: The mapping from λ to s assumes `I ≈ P_bat / V_oc`, which is only accurate when `R_int` is small compared to `V_oc`. With R_int = 0.05 Ω and V_oc ≈ 350 V, this is a reasonable but not exact approximation.
3. **Discrete-to-continuous mapping**: The discrete DP penalty α and the continuous co-state λ are related through the discretization step size dt, but the exact mapping depends on the specific discretization scheme.

## Notation

| Symbol | Framework | Meaning | Units |
|--------|-----------|---------|-------|
| J[k][i] | DP | Cost-to-go from step k, SOC grid i | g (hydrogen) |
| g(p_fc) | DP | Instantaneous FC hydrogen consumption | g/s |
| α | DP | SOC deviation penalty coefficient | g (per unit SOC²) |
| β | DP | Terminal SOC penalty coefficient | g (per unit SOC²) |
| J[k+1] | DP | Future cost-to-go (Bellman backup) | g |
| H(t) | Hamiltonian | Hamiltonian function | g/s |
| H_fc(P_fc) | Hamiltonian | FC hydrogen consumption rate | g/s |
| H_bat(P_bat) | Hamiltonian | Battery power | kW |
| s(t) | ECMS | Equivalence factor | g/kWh |
| λ(t) | Hamiltonian | Co-state variable (costate) | g (per unit SOC) |
| P_fc | All | Fuel cell output power | kW |
| P_bat | All | Battery power (positive = discharge) | kW |
| P_load | All | Vehicle power demand | kW |
| SOC | All | Battery state of charge | dimensionless [0,1] |
| Q_bat | All | Battery capacity | Ah |
| V_oc | All | Open-circuit voltage | V |
| R_int | All | Internal resistance | Ω |
| LHV_H2 | All | Lower heating value of H₂ | J/kg |

## Derivation Strategy
Build the connection from the general optimal control problem → Pontryagin's minimum principle → Hamiltonian → special cases (constant λ → ECMS, adaptive λ → A-ECMS) → relationship to DP's discrete formulation.

The key insight is that DP and the Hamiltonian framework solve the same problem but from opposite directions: DP works backward from the terminal condition (Bellman backup), while the Hamiltonian framework works forward with a co-state that carries future information.

## Derivation Map

1. **Setup**: Define the optimal control problem (minimize total H₂, subject to SOC dynamics)
2. **Pontryagin**: Apply Pontryagin's minimum principle → introduce Hamiltonian H(t)
3. **Co-state equation**: Derive λ̇(t) = -∂H/∂SOC, the equation governing the co-state
4. **Constant λ special case**: If λ(t) = constant, derive ECMS form from Hamiltonian
5. **Time-varying λ**: If λ(t) evolves with SOC, derive A-ECMS form
6. **DP connection**: Show how DP's α and J[k+1] approximate the same information carried by λ
7. **Parameter mapping**: Derive the approximate relationship between α, λ, and s

## Main Derivation

### Step 1: Problem Setup

We want to minimize total hydrogen consumption over a drive cycle of duration T:

```
min_{P_fc(·)} J_total = ∫_0^T H_fc(P_fc(t)) dt
```

Subject to the battery SOC dynamics:

```
d(SOC)/dt = -I(t) / (Q_bat × 3600)
```

Where the battery current I(t) is determined by the power balance:

```
P_bat(t) = P_load(t) - P_fc(t) = V_oc(SOC(t)) × I(t) + R_int × I(t)²
```

**NOTE**: The battery equation is quadratic in I. Solving for I gives:

```
I(t) = (V_oc - √(V_oc² - 4R_int × P_bat(t))) / (2R_int)
```

This is exact (no approximation yet).

### Step 2: Pontryagin's Minimum Principle

Define the Hamiltonian:

```
H(t) = H_fc(P_fc(t)) + λ(t) × d(SOC)/dt
```

Substitute the SOC dynamics:

```
H(t) = H_fc(P_fc(t)) + λ(t) × (-I(t) / (Q_bat × 3600))
```

**Claim (Pontryagin's minimum principle)**: At each time t, the optimal control P_fc*(t) minimizes H(t):

```
P_fc*(t) = argmin_{P_fc} H(t)
```

**Identity**: This is a restatement of the necessary condition for optimality in continuous-time optimal control.

### Step 3: Co-state Equation

The co-state λ(t) evolves according to:

```
dλ/dt = -∂H/∂SOC
```

Compute ∂H/∂SOC:

```
∂H/∂SOC = ∂H_fc/∂SOC + λ × ∂(-I/(Q_bat×3600))/∂SOC
```

**Approximation**: If we assume the FC efficiency curve is approximately flat (∂H_fc/∂SOC ≈ 0) and the battery OCV-SOC relationship is approximately linear, then:

```
dλ/dt ≈ -λ × ∂(-I/(Q_bat×3600))/∂SOC
```

**Proposition**: If the FC efficiency is approximately constant and the battery parameters are constant, then dλ/dt ≈ 0, i.e., λ(t) ≈ constant.

**Status of this proposition**: This is a reasonable approximation for FCHEVs operating near the FC's efficient region, but it is NOT generally true. The FC efficiency curve has significant slope (especially at low and high power), so λ does vary in practice.

### Step 4: Constant λ → Standard ECMS

Under the constant λ approximation, the Hamiltonian becomes:

```
H = H_fc(P_fc) + λ × (-I/(Q_bat×3600))
```

**Approximation**: Replace the exact battery current I with the linear approximation I ≈ P_bat / V_oc (valid when R_int << V_oc, which holds for our parameters: R_int = 0.05 Ω, V_oc ≈ 350 V):

```
H ≈ H_fc(P_fc) + λ × (-P_bat / (Q_bat × 3600 × V_oc))
```

Since P_bat = P_load - P_fc:

```
H ≈ H_fc(P_fc) - λ × (P_load - P_fc) / (Q_bat × 3600 × V_oc)
```

Define the equivalence factor:

```
s = λ / (Q_bat × V_oc)
```

Then:

```
H ≈ H_fc(P_fc) + s × (P_load - P_fc) / 3600
```

**Identity**: This is exactly the ECMS equivalent hydrogen consumption formula (with unit conversion from kWh to g/s via the 3600 factor).

**Interpretation**: The equivalence factor s represents the marginal cost of using battery energy, measured in equivalent hydrogen consumption per kWh. It is derived from the co-state λ, which represents the marginal cost of SOC.

### Step 5: Time-varying λ → A-ECMS

When λ(t) is NOT constant, the co-state equation governs its evolution:

```
dλ/dt = -λ × ∂(-I/(Q_bat×3600))/∂SOC + ∂H_fc/∂SOC
```

**Proposition**: If we approximate dλ/dt ≈ 0 on short time scales but allow λ to adjust based on SOC error, we get:

```
λ(t) ≈ λ₀ × (1 + Kp × (SOC_ref - SOC(t)))
```

This is the **SOC-feedback adaptive law** used in A-ECMS.

**Status**: This is a heuristic approximation, not a rigorous derivation. The true co-state evolution follows a differential equation, not a simple proportional feedback law. However, the feedback structure captures the correct physical intuition: when SOC is below target, the marginal value of SOC is higher, so λ increases, making battery use more "expensive."

### Step 6: Connection to DP

DP's Bellman equation:

```
J[k][i] = min_{p_fc} [g(p_fc) + α×(SOC_next - SOC_ref)² + J[k+1][lookup(SOC_next)]]
```

The three terms correspond to:

1. **g(p_fc) = H_fc(P_fc)**: Same instantaneous FC hydrogen cost. ✓ Identity.

2. **α×(SOC_next - SOC_ref)²**: This is DP's way of encoding the future cost of SOC deviation. In the Hamiltonian framework, this information is carried by λ(t).

   **Proposition (not proven)**: The DP penalty α is approximately proportional to the co-state λ, with the proportionality depending on the time step dt and battery parameters:
   
   ```
   α ≈ λ / (Q_bat × 3600) × dt
   ```
   
   This makes dimensional sense: λ has units of g (marginal cost per unit SOC), α has units of g (penalty per unit SOC²), and dt converts between per-step and per-second rates.

   **Status**: This is an educated guess based on dimensional analysis, not a proven theorem. The exact relationship would require solving the DP and comparing the resulting λ* sequence with the optimal α.

3. **J[k+1][lookup(SOC_next)]**: This is the Bellman backup — the minimum future cost from step k+1 onward. In the Hamiltonian framework, this future information is encoded in the co-state λ(k+1).

   **Interpretation**: J[k+1] is the discrete analog of the integral of λ from k+1 to N. In the continuous framework, the total future cost of SOC deviation is ∫ λ(t)·d(SOC)/dt dt. In the discrete framework, this becomes the telescoping sum of J[k] values.

### Step 7: Summary of Parameter Mapping

| DP parameter | Hamiltonian variable | ECMS parameter | Relationship |
|-------------|---------------------|----------------|--------------|
| α | λ (co-state) | s (equivalence factor) | s = λ/(Q_bat·V_oc), α ≈ λ·dt/(Q_bat·3600) |
| β | λ(tf) (terminal co-state) | — | λ(tf) = β·(SOC(tf) - SOC_ref) |
| J[k+1] | λ(t) (future marginal cost) | — | J[k+1] ≈ ∫_{k+1}^N λ(τ)·d(SOC)/dτ dτ |
| g(p_fc) | H_fc(P_fc) | H_fc(P_fc) | Same quantity, different notation |

## Remarks and Interpretation

### Why the formulas look different

The DP Bellman equation and the ECMS Hamiltonian are different because they come from different mathematical traditions:

1. **DP (Bellman's Dynamic Programming)**: Works backward from the terminal condition. At each step k, it asks: "given that I'm at state i, what's the best action?" The answer is encoded in the cost-to-go J[k][i], which contains all future information. This is a **global** approach — it sees the entire future through the J table.

2. **Pontryagin's Minimum Principle**: Works forward with a co-state λ(t) that "prices" the SOC. At each instant, it asks: "given the current SOC and its marginal value λ, what's the best action?" The co-state λ carries future information through its dynamics equation. This is a **local** approach — each decision depends on the current "price" of SOC.

### The fundamental equivalence

Under certain conditions (continuous-time limit, convex problem), both approaches yield the same optimal solution. The relationship is:

- DP's J[k][i] ≈ the value function V(SOC, t) from the Hamiltonian framework
- DP's α penalty ≈ the co-state λ
- DP's terminal penalty β ≈ the terminal co-state λ(tf)

But the equivalence requires:
1. The problem must be time-invariant or slowly time-varying
2. The FC efficiency must be smooth enough
3. The battery model must be approximately linear near the operating point

### What's approximation vs. exact

| Claim | Status |
|-------|--------|
| g(p_fc) = H_fc(P_fc) | **Exact identity** (same physical quantity) |
| J[k+1] encodes future cost | **Exact** (by definition of Bellman equation) |
| λ(t) encodes future cost | **Exact** (by Pontryagin's principle) |
| α ≈ λ·dt/(Q_bat·3600) | **Approximation** (dimensional argument) |
| s = λ/(Q_bat·V_oc) | **Approximation** (requires R_int << V_oc) |
| λ(t) = constant → ECMS | **Approximation** (requires flat FC efficiency) |
| λ(t) = λ₀·(1+Kp·(SOC_ref-SOC)) → A-ECMS | **Heuristic** (not derived from co-state equation) |

## Boundaries and Non-Claims

1. **We do NOT claim** that the DP Bellman equation and ECMS Hamiltonian are mathematically equivalent. They are analogous formulations of the same problem from different mathematical frameworks.

2. **We do NOT claim** that α and s can be exactly converted. The relationship depends on discretization, battery parameters, and the specific drive cycle.

3. **We do NOT claim** that A-ECMS's SOC-feedback law λ(t) = λ₀·(1+Kp·(SOC_ref-SOC)) is derived from the co-state equation. It is a heuristic that captures the correct qualitative behavior.

4. **What we DO claim**: Both frameworks minimize the same objective (total hydrogen consumption) subject to the same constraints (SOC dynamics). They produce the same optimal solution under idealized conditions (continuous time, exact co-state integration). In practice, ECMS with a well-tuned s (or A-ECMS with well-tuned Kp) achieves results close to DP's global optimum.

## Open Risks

1. The exact relationship between DP's optimal α* and the co-state λ* is not rigorously derived. It would require:
   - Running DP with varying α values
   - Computing the implied λ* from the DP solution
   - Fitting the relationship λ* = f(α, dt, Q_bat, V_oc)

2. The A-ECMS feedback law is not derived from the co-state differential equation. A more rigorous approach would:
   - Solve the co-state ODE numerically alongside the state ODE
   - Discretize the result to get a time-varying s*(t)
   - Compare with the heuristic feedback law

3. The constant-λ approximation for ECMS is only valid when the FC efficiency curve is approximately flat. For our FC model (efficiency range 0-55%), the variation is significant, so the constant-λ assumption introduces non-negligible error.

4. The relationship between DP's grid resolution (N_SOC × N_PFC) and the Hamiltonian's continuous formulation has not been analyzed. Grid coarsening in DP is analogous to discretization error in the Hamiltonian approach, but the error bounds are different.
