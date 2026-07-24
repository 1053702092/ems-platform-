"""
Autograd 逐步拆解 — 看清 PyTorch 内部怎么记账的
"""
import torch

print("=" * 60)
print("准备: x = torch.tensor([2.0, 3.0], requires_grad=True)")
x = torch.tensor([2.0, 3.0], requires_grad=True)
print(f"  x = {x}")
print(f"  x.grad_fn = {x.grad_fn}")     # None — 直接创建的，没有"父母"
print(f"  x.is_leaf = {x.is_leaf}")      # True — 叶子节点
print()

# ── Step 1: x ** 2 ──
print("=" * 60)
print("Step 1: pow_result = x ** 2")
pow_result = x ** 2
print(f"  pow_result = {pow_result}")
print(f"  pow_result.grad_fn = {pow_result.grad_fn}  ← 类型: {type(pow_result.grad_fn)}")
print(f"  这个 grad_fn 的 next_functions (输入来源):")
for i, nf in enumerate(pow_result.grad_fn.next_functions):
    print(f"    [{i}] {nf}")
print(f"  → 说明: PowBackward0 记住了它的输入是 x (叶子节点)")
print()

# ── Step 2: 3 * x ──
print("=" * 60)
print("Step 2: mul_result = 3 * x")
mul_result = 3 * x
print(f"  mul_result = {mul_result}")
print(f"  mul_result.grad_fn = {mul_result.grad_fn}")
print(f"  这个 grad_fn 的 next_functions (输入来源):")
for i, nf in enumerate(mul_result.grad_fn.next_functions):
    print(f"    [{i}] {nf}")
print(f"  → 说明: MulBackward0 记住了它的输入是 x 和常数 3")
print()

# ── Step 3: 加法 ──
print("=" * 60)
print("Step 3: y = pow_result + mul_result")
y = pow_result + mul_result
print(f"  y = {y}")
print(f"  y.grad_fn = {y.grad_fn}")
print(f"  这个 grad_fn 的 next_functions (输入来源):")
for i, nf in enumerate(y.grad_fn.next_functions):
    print(f"    [{i}] {nf}")
print(f"  → 说明: AddBackward0 记住了两个输入: pow_result 和 mul_result")
print()

# ── 内部日记检查 ──
print("=" * 60)
print("PyTorch 内部记账本（计算图的拓扑）：")
print(f"")
print(f"  x (叶子, grad_fn=None)")
print(f"   ├──→ PowBackward0 ──→ pow_result")
print(f"   │                    └ grad_fn.next_functions = {pow_result.grad_fn.next_functions}")
print(f"   │")
print(f"   ├──→ MulBackward0  ──→ mul_result")
print(f"   │                    └ grad_fn.next_functions = {mul_result.grad_fn.next_functions}")
print(f"   │")
print(f"   └──→ AddBackward0  ──→ y （最终输出）")
print(f"                        └ grad_fn.next_functions = {y.grad_fn.next_functions}")
print()

# ── 反向传播 ──
print("=" * 60)
print("反向传播: y.sum().backward()")
print(f"  调用前 x.grad = {x.grad}")
loss = y.sum()
loss.backward()
print(f"  调用后 x.grad = {x.grad}")
print(f"  理论值: dy/dx = 2x + 3 在 x=[2,3] 处 = [7, 9]")
print(f"  结果一致! OK")
print()

# ── 扩展验证：多个加法看编号 ──
print("=" * 60)
print("验证: 连续两次加法，编号是什么？")
a = torch.tensor(1.0, requires_grad=True)
c1 = a + 2          # 第1次加法
c2 = c1 + 3         # 第2次加法
print(f"  c1.grad_fn = {c1.grad_fn}")   # AddBackward0
print(f"  c2.grad_fn = {c2.grad_fn}")   # 还是 AddBackward0，不是 1！
print(f"  → 说明: 0 不是顺序计数器，是操作类型版本号")
print()

# ── grad_fn 是一个对象，不是字符串 ──
print("=" * 60)
print("关键认知:")
print(f"  grad_fn 的类型 = {type(y.grad_fn)}")
print(f"  grad_fn 是一个 Python 对象，它存了: ")
print(f"    - 输入来源 (next_functions)")
print(f"    - 如何反向求导 (backward 方法)")
print(f"  grad_fn 的类名打印出来是 AddBackward0，但它不是字符串")
