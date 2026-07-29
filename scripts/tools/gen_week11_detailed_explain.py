#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 Week 11 四个 py 文件的详细中文逐行分析 docx
每个解释都是段落级别的详细中文。
"""
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
import datetime, os

OUT_DIR = r'F:\CLAUDE\research\ems-platform\docs\notes'

BLUE = RGBColor(0x1F, 0x3A, 0x5F)
GRAY = RGBColor(0x66, 0x66, 0x66)
DGRAY = RGBColor(0x99, 0x99, 0x99)

def build_doc(title, subtitle, sections, filename):
    """sections = list of (type, args...)
       type: 'h1','h2','p','bullet','code','tbl','brk',
             'x'(line,code,explain), 'note','pre'
    """
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Microsoft YaHei'
    style.font.size = Pt(11)
    style.element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')
    style.paragraph_format.line_spacing = 1.35
    style.paragraph_format.space_after = Pt(2)

    # 封面
    for _ in range(3):
        doc.add_paragraph('')
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run(title + '\n')
    r.font.size = Pt(24); r.bold = True; r.font.color.rgb = BLUE
    r = t.add_run(subtitle)
    r.font.size = Pt(13); r.font.color.rgb = GRAY
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run(f'生成日期：{datetime.date.today().isoformat()}')
    r.font.size = Pt(10); r.font.color.rgb = DGRAY
    doc.add_page_break()

    for sec in sections:
        t = sec[0]
        if t == 'h1':
            hd = doc.add_heading(sec[1], level=1)
            for r in hd.runs: r.font.color.rgb = BLUE
        elif t == 'h2':
            hd = doc.add_heading(sec[1], level=2)
            for r in hd.runs: r.font.color.rgb = BLUE
        elif t == 'p':
            pa = doc.add_paragraph()
            pa.paragraph_format.space_after = Pt(3)
            r = pa.add_run(sec[1])
            r.font.name = 'Microsoft YaHei'
            r.font.size = Pt(sec[2] if len(sec) > 2 else 11)
            r.bold = sec[3] if len(sec) > 3 else False
            color = sec[4] if len(sec) > 4 else None
            if color: r.font.color.rgb = color
        elif t == 'bullet':
            pa = doc.add_paragraph(sec[1], style='List Bullet')
            pa.paragraph_format.left_indent = Cm(1.5 + (sec[2] if len(sec) > 2 else 0) * 0.8)
        elif t == 'code':
            for line in sec[1].split('\n'):
                pa = doc.add_paragraph()
                pa.paragraph_format.space_before = Pt(0)
                pa.paragraph_format.space_after = Pt(1)
                pa.paragraph_format.left_indent = Cm(1)
                r = pa.add_run(line)
                r.font.name = 'Consolas'; r.font.size = Pt(9.5)
                r.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
        elif t == 'tbl':
            hdrs, rows = sec[1], sec[2]
            tb = doc.add_table(rows=1, cols=len(hdrs))
            tb.style = 'Table Grid'
            for i, h in enumerate(hdrs):
                r = tb.rows[0].cells[i].paragraphs[0].add_run(h)
                r.bold = True; r.font.size = Pt(10); r.font.name = 'Microsoft YaHei'
            for rd in rows:
                row = tb.add_row()
                for c, txt in enumerate(rd):
                    r = row.cells[c].paragraphs[0].add_run(txt)
                    r.font.size = Pt(10); r.font.name = 'Microsoft YaHei'
        elif t == 'brk':
            doc.add_page_break()
        elif t == 'x':
            pa = doc.add_paragraph()
            pa.paragraph_format.space_before = Pt(6)
            pa.paragraph_format.space_after = Pt(2)
            r = pa.add_run(f'  L{sec[1]}  ')
            r.font.size = Pt(8); r.font.color.rgb = DGRAY
            r = pa.add_run(sec[2])
            r.font.name = 'Consolas'; r.font.size = Pt(10)
            r.bold = True; r.font.color.rgb = BLUE
            pa2 = doc.add_paragraph()
            pa2.paragraph_format.left_indent = Cm(0.8)
            pa2.paragraph_format.space_before = Pt(0)
            pa2.paragraph_format.space_after = Pt(6)
            r = pa2.add_run(sec[3])
            r.font.name = 'Microsoft YaHei'; r.font.size = Pt(10.5)

    path = os.path.join(OUT_DIR, filename)
    doc.save(path)
    print(f'  OK: {path}')


# =====================================================================
# File 1: continuous_env.py
# =====================================================================
build_doc(
    'Step 1: 连续动作环境',
    'week11_continuous_env.py — EMS 简化版 + DQN 为什么不行',
    [
        ('h1', '文件概览'),
        ('p', '这个文件做了两件事：第一，创建了一个连续动作的 EMS 简化环境（状态 2 维、动作 1 维连续），第二，演示了 DQN 为什么处理不了连续动作。这是从 Week 10 的离散 GridWorld 跨越到连续动作 RL 的第一步。'),
        ('p', '核心对比：'),
        ('bullet', 'GridWorld（Week 10）：离散状态 16 个、离散动作 4 个 → DQN 可以用', 0),
        ('bullet', 'EMS 环境（Week 11）：连续状态 [SOC, P_load]、连续动作 P_fc ∈ [0,1] → DQN 不行', 0),

        ('tbl', ['部分', '行号', '内容'], [
            ['EMSEnv 环境类', '26-111', '定义连续状态 + 连续动作 + 奖励函数'],
            ['DQN_Continuous 网络', '115-133', '假 DQN——输出层只有 1 个神经元，不是 4 个 Q 值'],
            ['demo_dqn_failure 演示', '136-203', '展示 DQN 为什么数学上无法处理连续动作'],
            ['test_env 环境测试', '207-235', '随机策略跑一局看看环境是否正常'],
            ['主程序', '238-247', '调用 test_env 和 demo_dqn_failure'],
        ]),

        ('brk',),
        ('h1', 'EMSEnv 环境类 —— 逐行解释（26-111 行）'),

        ('x', 26, 'class EMSEnv:', '定义 EMS 简化环境类。和 GridWorld 最关键的区别有两点：第一，状态是连续向量 [SOC, P_load]（不是离散格子编号 0-15），第二，动作是连续值 P_fc ∈ [0,1]（不是 4 个方向键 ↑↓←→）。这两个区别决定了 DQN 用不了。'),

        ('x', 35, 'def __init__(self):', '初始化环境参数。设定 SOC 范围 0.2-0.9（锂电池安全范围），状态维度 2，动作维度 1。电池容量设了 50 kWh，每步时长 1 分钟。最后调用 self.reset() 初始化状态。'),

        ('x', 39, 'self.state_dim = 2', '状态维度 = 2。状态向量是 [SOC, P_load] 两个连续值。对比 GridWorld 的状态是 16 个离散格子编号，用 one-hot 编码后是 16 维。这里直接用 2 维连续值输入网络——这就是"连续状态"的含义。'),

        ('x', 40, 'self.action_dim = 1', '动作维度 = 1。动作是 P_fc（燃料电池功率），归一化到 [0,1] 范围。对比 GridWorld 的动作是 4 个离散值（上 0、下 1、左 2、右 3）。这里动作是一个连续区间中的任意值——这就是"连续动作"的含义。'),

        ('x', 49, 'def reset(self):', '重置环境到初始状态。SOC 设为 0.6（60%，锂电池最优工作点附近），P_load 设为 0.5 kW。max_steps = 200（一局最多 200 步，防止无限循环）。返回 np.float32 数组。'),

        ('x', 57, 'def _get_state(self):', '返回当前状态 [SOC, P_load]，numpy float32 数组。这个格式直接喂给 PyTorch 网络。和 GridWorld 的 state_to_onehot 不同——那里要把整数编号转成 16 维 one-hot 向量，这里直接用 2 维连续向量。'),

        ('x', 61, 'def step(self, action):', '环境的核心：执行动作。输入 action 是归一化 [0,1] 的 P_fc 值。输出 (next_state, reward, done, info)。和 GridWorld 的 step 接口完全一样，只是状态和动作都从离散变成了连续。'),

        ('x', 68, 'p_fc = float(np.clip(action, 0, 1)) * 30.0', '反归一化。网络输出的动作是 [0,1] 之间的归一化值，这里乘以 30 映射到 [0,30] kW（实际燃料电池的功率范围）。比如 action=0.5 → P_fc=15kW，action=1.0 → P_fc=30kW。np.clip 防止动作越界。'),

        ('x', 71, 'self.p_load = 0.3 + 0.4 * (0.5 + 0.5 * np.sin(self.steps * 0.1))', '生成负载功率（模拟实际工况）。用正弦波让负载在 0.3-0.7 kW 之间波动——模拟实际船舶/车辆运行中负载的变化。这是和 GridWorld 不同的地方：GridWorld 的奖励和转换是固定的概率，而这里的负载是随时间变化的连续值。'),

        ('x', 77, 'soc_change = power_diff / self.battery_capacity', '计算 SOC 变化量。公式很简单：SOC 变化 = 净功率 / 电池容量。P_fc > P_load（发电大于用电）→ SOC 上升（充电）。P_fc < P_load（发电小于用电）→ SOC 下降（放电）。这个变化量累加到当前 SOC 上。'),

        ('x', 82, 'fuel_cost = -0.01 * p_fc', '燃料成本（负奖励）。P_fc 越大，消耗的氢气越多，负奖励越大。这是优化的主要目标——最小化燃料消耗。在 EMS 问题中，这对应着"经济性"指标。'),

        ('x', 85, 'soc_penalty = -0.5 * (self.soc - 0.6) ** 2', 'SOC 偏离惩罚。SOC 偏离 0.6（目标值）越远，惩罚越大。这个惩罚项的目的是让智能体学会维持 SOC，避免电池过充或过放。在 EMS 中，这对应着"安全性"指标。'),

        ('x', 89, 'if self.soc <= self.soc_min or self.soc >= self.soc_max:', 'SOC 越界惩罚。如果 SOC 超出了 [0.2, 0.9] 的安全范围，额外罚 -1.0。这是"硬约束"——在实际系统中，SOC 出界会触发保护机制或者损坏电池。'),

        ('x', 96, 'done = (self.steps >= self.max_steps or ...)', '结束条件：超过最大步数（200），或者 SOC 越界（低于 0.2 或高于 0.9）。在 GridWorld 中是走到终点或陷阱结束。这里是通过控制步数和 SOC 范围来结束。'),

        ('brk',),
        ('h1', 'DQN 为什么不行 —— 逐行解释（115-203 行）'),
        ('p', '这个部分的核心目的：让你亲眼看到 DQN 在处理连续动作时的数学困境。DQN 不行不是调参问题，是数学结构决定的。', 12, True),

        ('h2', 'DQN_Continuous 网络（115-133 行）'),
        ('x', 115, 'class DQN_Continuous(nn.Module):', '定义一个"假 DQN"网络。为什么说假？因为标准 DQN 的输出层有 N 个神经元（N = 离散动作数），每个对应一个动作的 Q 值。但这个网络输出层只有 1 个神经元，直接输出一个连续值——这本质上是个回归网络，不是 DQN。'),

        ('x', 126, 'self.net = nn.Sequential(...)', '网络结构很简单：2 维输入（状态 [SOC, P_load]）→ 64 维隐藏层 → ReLU → 1 维输出。这个输出被当做"动作"直接使用，而不是 Q 值。注意：这和标准 DQN 有本质区别。标准 DQN 的输出是"每个动作的 Q 值"，需要 argmax 选动作。这里直接输出动作值，绕过了 argmax——但也绕过了 Q-learning 的核心机制。'),

        ('h2', 'demo_dqn_failure 演示（136-203 行）'),
        ('x', 136, 'def demo_dqn_failure():', '演示 DQN 为什么不行。核心论点：DQN 的问题不是参数没调好，而是数学结构根本上就无法处理连续动作。'),

        ('x', 157, 'print("问题 1: 没法 argmax")', 'DQN 选动作的核心步骤是 a = argmax Q(s,a)，也就是遍历所有动作，找到 Q 值最大的那个。在 GridWorld 的 4 个离散动作上这很容易。但连续动作有无限多个可能取值（比如 P_fc 可以是 0 kW、0.1 kW、0.01 kW、3.14159 kW……），你没法枚举所有可能性来求 argmax。这就叫"数学结构决定"——不管你怎么调参，argmax 都要求遍历，连续空间没法遍历。'),

        ('x', 163, 'print("问题 2: 即使强行输出一个动作值，更新公式也不对")', 'Q-learning 的更新公式是 target = r + γ·max Q(s\', a\')。max Q(s\', a\') 需要计算"下个状态的最优 Q 值"，这又需要遍历所有可能的 a\'——连续空间里没法算。有人会说"那我把 max 改成其他操作不行吗？"——改了就不叫 Q-learning 了，公式也不收敛了。'),

        ('x', 181, 'a = float(torch.sigmoid(q_net(s_tensor)).item())', '这里强行让网络直接输出动作值。sigmoid 保证输出范围在 [0,1] 之间。但注意：这本质上是监督学习（输入状态 → 输出动作），没有 Q 值的概念，没有贝尔曼公式，不是强化学习。这就像"把方向盘当油门踩——虽然都是踩踏板，但完全不是一回事。"'),

        ('x', 199, 'print("DQN 从数学结构上就无法处理连续动作。")', '整段演示的核心结论。DQN 的两个核心操作——argmax（选动作）和 max（算 target）——都要求遍历动作空间。连续空间有无穷多个点，没法遍历。这不是换个网络结构、调大 hidden layer、加更多训练就能解决的。'),

        ('x', 202, 'print("要处理连续动作，必须换方法——策略梯度。")', '引出下一步：REINFORCE。策略梯度方法不通过 Q 值来选动作，而是直接输出动作分布（均值和标准差），从分布中采样得到动作。这就绕开了 argmax 的限制——不需要枚举所有动作。'),
    ],
    'Week11_Step1_ContinuousEnv_逐行精讲.docx'
)


# =====================================================================
# File 2: reinforce.py
# =====================================================================
build_doc(
    'Step 2: REINFORCE (策略梯度)',
    'week11_reinforce.py — 第一个能处理连续动作的 RL 算法',
    [
        ('h1', '文件概览'),
        ('p', 'REINFORCE（也叫"蒙特卡洛策略梯度"或"Vanilla Policy Gradient"）是第一个能处理连续动作的 RL 算法。和 DQN 的区别：DQN 输出 Q 值→argmax 选离散动作，REINFORCE 直接输出动作分布→采样得连续动作。'),
        ('p', '核心公式：▽J = E[ ▽log π(a|s) × G ]。好动作（G>0）→ 增大被选概率，坏动作（G<0）→ 减小被选概率。', 12, True),

        ('tbl', ['部分', '行号', '内容'], [
            ['环境复用', '28-62', '同 Step 1 一样的 EMS 环境'],
            ['PolicyNet 策略网络', '66-104', 'π(s) → [μ, σ]，和 DQN 的 Q 网络有本质区别'],
            ['REINFORCE 算法', '108-189', '跑一局 → 算 G_t → loss = -Σ logπ × G'],
            ['测试 + 画图', '193-250', '测试学到的策略并画训练曲线'],
        ]),

        ('brk',),
        ('h1', '策略网络 PolicyNet —— DQN 和 REINFORCE 的核心区别（66-104 行）'),
        ('p', '这是理解 REINFORCE 最关键的部分。策略网络的输出不是 Q 值，而是动作分布的参数。', 12, True),

        ('x', 66, 'class PolicyNet(nn.Module):', '策略网络。和第 10 周 DQN 的 TinyDQN 有本质区别：TinyDQN 输出 4 个 Q 值（每个离散动作一个），而 PolicyNet 输出动作分布的参数 [μ, σ]。简单说：DQN 告诉"每个动作值多少钱"，REINFORCE 告诉"应该怎么选动作"。'),

        ('x', 73, 'def __init__(self, state_dim=2, hidden=64, action_dim=1):', '网络结构：2 维输入（状态 [SOC, P_load]）→ 64 维隐藏层 → 64 维隐藏层 → 两路输出。对比 DQN 的 TinyDQN（16 维输入→32 隐藏→4 输出），这里输入更少（2 维连续 vs 16 维 one-hot），但网络更宽（64 vs 32），因为连续动作任务更复杂。'),

        ('x', 78, 'self.mean_head = nn.Linear(hidden, action_dim)', '均值输出头。把 64 维隐藏层映射到 1 维（动作均值 μ）。这个 μ 就是"策略倾向于输出的动作值"。比如 μ=0.6 表示策略倾向于输出 P_fc ≈ 0.6（对应 18 kW）。'),
        ('x', 79, 'self.log_std = nn.Parameter(torch.zeros(action_dim))', '对数标准差 log_std。这是一个可训练的参数（不是网络层的输出）。初始化 log_std=0 表示 std=1。std 的作用是控制探索范围：std 大 → 动作随机性强（多探索），std 小 → 动作集中在 μ 附近（多利用）。训练过程中 log_std 会自动调整。'),

        ('x', 84, 'mean = torch.tanh(self.mean_head(x))', 'tanh 激活函数把输出限制在 [-1, 1] 范围内。为什么要用 tanh？因为动作范围是 [0,1]，而 tanh 的输出是 [-1,1]（以 0 为中心，对称分布），再映射到 [0,1] 更方便。DQN 的 Q 网络用 ReLU 或者不用激活函数（因为 Q 值可以是任意大小），这里用 tanh 是为了控制输出范围。'),
        ('x', 85, 'mean = (mean + 1) / 2', '把 tanh 的 [-1,1] 输出映射到 [0,1]——动作的范围。这是连续动作和离散动作的一个关键区别：离散动作只需要输出一个整数编号，连续动作需要输出一个范围中的值。'),
        ('x', 86, 'std = torch.exp(self.log_std.clamp(-5, 2))', '标准差 = e^(log_std)。指数运算保证 std > 0（标准差必须为正数）。clamp(-5, 2) 把 log_std 限制在 [-5, 2] 之间，防止数值溢出（exp(5) ≈ 148 太大了，exp(-5) ≈ 0.007 太小了）。'),

        ('x', 89, 'def get_action(self, state):', '选动作。这是和 DQN 选动作最不同的地方。DQN：前向传播 → 得到 4 个 Q 值 → argmax 选最大的。这里：前向传播 → 得到 [μ, σ] → 从正态分布 N(μ,σ) 中采样 → 得到连续动作值。不用 argmax，自然能处理连续动作。'),

        ('x', 94, 'm = dist.Normal(mean, std)', '创建正态分布 N(μ, σ)。这是处理连续动作的关键——动作是从分布中采样出来的，不是从有限集合中选出来的。每次采样可能得到不同的值（即使输入相同），这就是"策略的随机性"。'),
        ('x', 95, 'a = m.sample()', '从正态分布中采样一个值作为动作。比如 μ=0.6, σ=0.1，采样结果可能在 0.4-0.8 之间。这个随机性让智能体能够探索——类似于 DQN 中的 ε-贪心。'),
        ('x', 96, 'a = a.clamp(0, 1)', '把采样结果限制在 [0,1] 范围内。正态分布理论上可以采样到任意值（包括负数或大于 1），这些值对环境来说没有意义（P_fc 不能是负数），所以 clamp 到有效范围。'),

        ('x', 99, 'def evaluate(self, state, action):', '给定状态和动作，计算这个动作在当前策略下的 log_prob（对数概率）。这个函数在训练时使用（带梯度），和 get_action 不同（get_action 用于采样，不带梯度）。log_prob 代表"在当前策略 π 下，执行动作 a 的概率的 log 值"。'),

        ('brk',),
        ('h1', 'REINFORCE 算法 —— 逐行解释（108-189 行）'),
        ('p', '核心思想：跑完一整局 → 从后往前算每步的"总回报"G_t → 好动作增大概率、坏动作减小概率。', 12, True),

        ('x', 108, 'def reinforce(episodes=500, lr=0.001):', 'REINFORCE 主函数。参数：500 局（比 DQN 的 5000 局少，因为环境简单）、学习率 0.001（比 DQN 的 0.01 小，因为策略梯度对步长更敏感）。'),

        ('x', 120, 'policy = PolicyNet()', '创建策略网络。这是唯一的网络——REINFORCE 没有价值网络（Critic），也不学 Q 值。它只学一个东西：给定状态 s，应该输出什么动作。对比 DQN：q_network + target_network 两个网络。'),
        ('x', 121, 'optimizer = optim.Adam(policy.parameters(), lr=lr)', 'Adam 优化器，和 DQN 一样。优化目标不一样：DQN 优化的是 Q 值预测的准确性（MSE loss），REINFORCE 优化的是策略（让好动作概率变大、坏动作概率变小）。'),

        ('x', 137, 'transitions = []  # 存 (状态, 动作, 奖励)', '创建一个列表来记录这一局的所有 (状态, 动作, 奖励) 三元组。注意这里不存 Q 值——REINFORCE 不依赖 Q 值更新，它用实际的整局回报 G_t 来评价动作好坏。'),

        ('x', 141, 'a, trace = policy.get_action(s)', '每一轮的第一步：用当前策略选动作。注意返回的是一个连续值（比如 0.63），不是离散的动作编号。这就是 REINFORCE 能处理连续动作的原因——输出是连续值。DQN 做不到这一点。'),
        ('x', 143, 'sp, reward, done, _ = env.step(a)', '第二步：执行动作，环境返回新的状态和奖励。接口和 DQN 完全一样——不管动作是离散的还是连续的，env.step(a) 的使用方式一致。'),

        ('x', 148, '# 第 2 步：算 G_t（从后往前累加）', '这是 REINFORCE 和 DQN/AC 最不同的地方。DQN 用 Q 值（预测）、AC 用 Advantage（Critic 估计），而 REINFORCE 用"真实"的累积回报 G_t。这个 G_t 要等整局走完才知道——这就是"蒙特卡洛"（Monte Carlo）的含义。'),

        ('x', 151, 'for r in reversed(rewards):', '从最后一步开始往前遍历。为什么从后往前？因为 G_t = r_t + γ·r_{t+1} + γ²·r_{t+2}+...，后面的奖励要先算出来才能加给前面的。从后往前累加比从前往后算更高效。'),
        ('x', 152, 'G = r + 0.99 * G', '核心公式：G_t = r_t + γ × G_{t+1}。0.99 是折扣因子 γ。从最后一步开始：最后一步 G = r_last，倒数第二步 G = r_{prev} + 0.99 * r_last，依此类推。这就算出了"从这一步开始到整局结束，总共能拿多少奖励"。'),

        ('x', 158, 'returns_t = (returns_t - returns_t.mean()) / (returns_t.std() + 1e-8)', '标准化（normalize）。把所有 G_t 变成均值为 0、标准差为 1 的分布。为什么要标准化？因为不同局的 G_t 大小差异很大，标准化后正负分界清晰：G>0 → 好动作（增大概率），G<0 → 坏动作（减小概率）。如果不标准化，可能所有 G_t 都是正数或都是负数，导致"所有动作一起增大概率"这种没意义的更新。'),

        ('x', 164, 'for (s_i, a_i, _), G_i in zip(transitions, returns_t):', '遍历每一步。对于每一步，检查这一步的动作是好是坏。transitions 存了每一步的 (状态, 动作, 奖励)，returns_t 存了对应的 G_t。'),
        ('x', 167, 'log_prob = policy.evaluate(s_t, a_t)', '重新计算 log_prob。注意：get_action 时是"不带梯度"的采样（为了性能），这里重新用"带梯度"的方式计算 log_prob，让梯度流回网络。'),
        ('x', 168, 'loss = loss + (-log_prob * G_i)', '核心公式：loss = -Σ log_prob(a|s) × G。如果 G>0：loss 想让 log_prob 变大（最小化 -log_prob × G → 让 log_prob 上升）→ 这个动作更可能被选。如果 G<0：loss 想让 log_prob 变小 → 这个动作更不可能被选。直观地说就是"好事多干、坏事少干"。'),

        ('x', 174, 'optimizer.zero_grad()', '清空上一轮的梯度。PyTorch 的梯度会累积，不清空的话会加上一轮的梯度。'),
        ('x', 175, 'loss.backward()', '反向传播。计算每个参数的梯度。和 DQN 的 loss.backward() 语法一样，但含义不同：DQN 的梯度让 Q 值预测更准，REINFORCE 的梯度让策略更好。'),
        ('x', 176, 'optimizer.step()', '用梯度更新参数。和 DQN 一样。'),

        ('brk',),
        ('h1', 'REINFORCE vs DQN 核心对照'),
        ('tbl', ['对比维度', 'DQN', 'REINFORCE'], [
            ['网络输出', 'Q(s) → [Q↑, Q↓, Q←, Q→]，每个动作一个 Q 值', 'π(s) → [μ, σ]，动作分布的参数'],
            ['选动作', 'argmax Q(s)，遍历所有动作找最大的', '从 N(μ,σ) 中采样，不用遍历'],
            ['动作类型', '离散，有限个（GridWorld 的 4 个）', '连续，无限个（P_fc ∈ [0,1]）'],
            ['价值估计', 'Q(s,a) 用 TD 学习，每步都能算', 'G_t = 整局实际回报，要等整局结束'],
            ['更新时机', '每一步都更新', '整局跑完后才更新一次'],
            ['更新公式', 'MSE(Q(s,a), r+γ·max Q(sp))', '-Σ log_prob × G'],
            ['网络参数', '644 个（16 维 one-hot 输入）', '~2500 个（2 维连续输入）'],
        ]),
        ('p', 'REINFORCE 的问题：等整局跑完才能更新，方差大、学得慢。下一节 Actor-Critic 解决这个问题——加一个 Critic 网络，每步都能更新。', 11, True),
    ],
    'Week11_Step2_REINFORCE_逐行精讲.docx'
)


# =====================================================================
# File 3: actor_critic.py
# =====================================================================
build_doc(
    'Step 3: Actor-Critic (演员-评委)',
    'week11_actor_critic.py — 每步更新，不用等整局结束',
    [
        ('h1', '文件概览'),
        ('p', 'Actor-Critic 在 REINFORCE 的基础上加了一个 Critic 网络 V(s)，实现了每步都能更新，不用等整局结束。REINFORCE 的 G_t 要等整局跑完才能算，AC 的 Advantage = r + γV(s\') - V(s) 每步都能算。'),

        ('tbl', ['部分', '行号', '内容'], [
            ['环境', '33-65', '同 Step 1 一样的 EMS 环境'],
            ['Actor 网络', '69-101', 'π(s) → [μ, σ]，和 REINFORCE 的 PolicyNet 一样'],
            ['Critic 网络', '104-122', 'V(s) → 标量值，新增的！这是 AC 的核心'],
            ['Actor-Critic 算法', '126-224', '每步算 Advantage → 更新 Actor + 更新 Critic'],
        ]),

        ('brk',),
        ('h1', 'Actor 和 Critic 网络 —— 逐行解释（69-122 行）'),

        ('h2', 'Actor 网络（69-101 行）'),
        ('p', 'Actor 和 REINFORCE 的 PolicyNet 完全一样——输入状态 s，输出动作分布 [μ, σ]，采样得连续动作。', 10, False, GRAY),
        ('x', 69, 'class Actor(nn.Module):', 'Actor（演员）网络。名字叫"演员"是因为它负责做出动作——就像演员在舞台上表演。和 REINFORCE 的 PolicyNet 结构完全一样：输入状态→输出动作分布→采样得动作。'),
        ('x', 86, 'def get_action(self, state):', '选动作。和 REINFORCE 完全一样：前向传播 → Normal(μ,σ) → 采样 → clamp。返回一个连续值 P_fc。'),

        ('h2', 'Critic 网络（104-122 行）'),
        ('p', 'Critic 是 Actor-Critic 相比 REINFORCE 唯一新增的东西。但它解决了核心问题——不用等整局结束就能评价动作好坏。', 11, True),
        ('x', 104, 'class Critic(nn.Module):', 'Critic（评委）网络。名字叫"评委"是因为它评价动作的好坏。REINFORCE 没有这个——它要等整局跑完，用实际的 G_t 来评价。Critic 的工作是预估当前状态值多少钱，不用等实际结果。类比：REINFORCE 是考完试看分数才知道学得怎么样，AC 是边做题边有老师告诉你做得对不对。'),

        ('x', 111, 'def __init__(self, state_dim=2, hidden=64):', '两个隐藏层的 MLP。输入 2 维状态 → 64 隐藏 → ReLU → 64 隐藏 → ReLU → 1 维输出。注意网络结构和 Actor 不同：Actor 输出 [μ, σ] 两个值（分布参数），Critic 输出 1 个标量 V(s)。'),
        ('x', 118, 'nn.Linear(hidden, 1)  # 输出一个标量 V(s)', '输出层只有 1 个神经元。V(s) 是一个数——"当前状态值多少钱"。比如 V(当前状态)=0.5 表示"从这个状态开始，以后能拿到大约 0.5 的总奖励"。这个 V(s) 是 Critic 自己学着估计的，不是真实的值。'),

        ('brk',),
        ('h1', 'Actor-Critic 算法 —— 逐行解释（126-224 行）'),
        ('p', '和 REINFORCE 的本质区别：REINFORCE 等整局跑完才更新，AC 每走一步就更新。这就像：REINFORCE 是游泳教练等你游完整条河才告诉你哪里错了，AC 是每一步都有教练在旁边喊。', 12, True),

        ('x', 144, 'env = EMSEnv()', '创建环境。和 REINFORCE 一样。'),
        ('x', 145, 'actor = Actor()', '创建 Actor 网络。和 REINFORCE 的 PolicyNet 一模一样。'),
        ('x', 146, 'critic = Critic()', '创建 Critic 网络。这是 REINFORCE 没有的！Critic 是 AC 相比 REINFORCE 的唯一新增。'),
        ('x', 147, 'actor_opt = optim.Adam(actor.parameters(), lr=lr)', 'Actor 的优化器。和 REINFORCE 一样。'),
        ('x', 148, 'critic_opt = optim.Adam(critic.parameters(), lr=lr * 2)', 'Critic 的优化器。学习率设为 Actor 的两倍（lr*2），因为 Critic 要学得更快——它需要快速给出准确的评价，Actor 才能学好。'),

        ('x', 170, 'a = actor.get_action(s)', 'Actor 选动作。和 REINFORCE 一样：采样得连续动作值。'),
        ('x', 173, 'sp, reward, done, _ = env.step(a)', '执行动作。和 REINFORCE 一样。'),
        ('x', 185, 'V_s = critic(s_t)', '用 Critic 预估当前状态的 V(s)。这是 AC 相比 REINFORCE 新增的关键步骤。REINFORCE 没有这一步——它不评估当前状态好不好，而是等整局结束回头看。'),

        ('x', 188, 'advantage = r_t + gamma * V_sp * (not done) - V_s', '计算 Advantage（优势函数）。这是 AC 的核心公式：A = r + γV(s\') - V(s)。V(s) 是 Critic 对当前状态的估值，r + γV(s\') 是"实际拿到这步奖励后的更新估值"。（实际奖励 + 未来估值）减去（当前估值），差值就是"这一步比预期好多少"。如果 A > 0：实际结果比预期好 → 鼓励这个动作。如果 A < 0：实际结果比预期差 → 抑制这个动作。'),
        ('p', '这和 REINFORCE 的 G_t 有什么区别？G_t 是"真实的总回报"，要等整局结束才能算。Advantage 是"当前步的 TD 估计"，每步都能算。G_t 准确但慢，Advantage 可能不准但快——这就是速度和精度的权衡。', 10, False, GRAY),

        ('x', 193, 'actor_loss = -(log_prob * advantage.detach()).mean()', '更新 Actor。公式和 REINFORCE 一模一样：loss = -log_prob × advantage。区别就在于 REINFORCE 用 G_t 而这里用 Advantage。G_t 换成 Advantage 之后，每步都能更新——不用再等整局结束了。'),
        ('x', 196, 'actor_loss.backward()', 'Actor 的反向传播。'),
        ('x', 198, 'actor_opt.step()', '更新 Actor 参数。'),

        ('x', 203, 'td_target = r_t + gamma * V_sp * (not done)', 'Critic 的训练目标：r + γV(s\')。这和 DQN 的 target 公式一模一样！Critic 的目标是学会预测"当前状态值多少钱"。'),
        ('x', 204, 'critic_loss = loss_fn(V_s, td_target)', 'Critic 的 loss：MSE(V(s), target)。让 Critic 的预测 V(s) 更接近实际的 r + γV(s\')。这是时序差分学习（TD learning）。'),
        ('x', 207, 'critic_opt.step()', '更新 Critic 参数。'),

        ('brk',),
        ('h1', 'REINFORCE vs Actor-Critic 对比'),
        ('tbl', ['对比维度', 'REINFORCE', 'Actor-Critic'], [
            ['策略网络', 'PolicyNet π(s)→[μ,σ]', 'Actor π(s)→[μ,σ]（一样）'],
            ['价值网络', '无', 'Critic V(s)（新增）'],
            ['评价标准', 'G_t = Σr（整局真实回报）', 'Advantage = r+γV-V\'（TD 估计）'],
            ['更新时机', '整局结束后才更新', '每步都更新'],
            ['方差', '很大（因为 G_t 覆盖整局，波动大）', '较小（Advantage 每步计算，更平滑）'],
            ['学习速度', '慢（等 200 步才能学一次）', '快（每步都在学）'],
            ['偏差', '无偏（G_t 是真实值）', '有偏（V(s) 是估计值，可能不准）'],
        ]),
        ('p', 'Actor-Critic 的优点：每步都更新，方差比 REINFORCE 小很多。缺点：Critic 的估计可能不准，有偏差。PPO 在 AC 基础上加了 clip 机制来解决"一步更新太多搞崩策略"的问题。', 11, True),
    ],
    'Week11_Step3_ActorCritic_逐行精讲.docx'
)


# =====================================================================
# File 4: ppo.py
# =====================================================================
build_doc(
    'Step 4: PPO (Proximal Policy Optimization)',
    'week11_ppo.py — 面试重点，EMS 项目最终选用',
    [
        ('h1', '文件概览'),
        ('p', 'PPO（近端策略优化）在 Actor-Critic 基础上加了 clip 机制——限制策略更新幅度，防止一步改太多搞崩训练。PPO 是 EMS 项目最终选用的算法，面试必问。', 12, True),

        ('tbl', ['部分', '行号', '内容'], [
            ['环境', '36-74', '稍宽松版 EMS 环境（电池容量更大、负载变化更缓）'],
            ['Actor + Critic', '78-125', '和 AC 完全一样的网络结构'],
            ['PPO 算法', '129-273', 'GAE + importance ratio + clip + 多轮更新'],
            ['测试 + 总结', '277-359', '测试 + 三种方法对比'],
        ]),

        ('brk',),
        ('h1', 'PPO 的核心创新 —— clip 机制（240-244 行）'),
        ('p', 'PPO 相比 Actor-Critic 一共多了 3 样东西：① 重要性采样比率（importance ratio）② clip 裁剪 ③ 多轮更新。其中最核心的就是 clip，一行代码，解决了 RL 训练中最大的问题——"一步更新太多把策略搞崩"。', 12, True),

        ('x', 129, 'def ppo(episodes=500, lr=0.0003, clip_eps=0.2, epochs=10, batch_size=64):', 'PPO 主函数。新参数：clip_eps=0.2（裁剪范围 [0.8, 1.2]），epochs=10（同一批数据重用 10 次）。学习率 0.0003 比 AC 的 0.001 更小——PPO 的更新更保守。'),
        ('x', 159, 'gamma = 0.99', '折扣因子。和 AC 一样。'),
        ('x', 160, 'gae_lambda = 0.95', 'GAE 平滑系数。λ=0.95 意味着综合考虑多步信息（不是只看一步，也不是看所有步）。AC 用的简单 TD error（λ=0），PPO 的 GAE 更平滑、更稳定。'),
        ('x', 161, 'entropy_coef = 0.01', '熵奖励系数。作用是"鼓励策略不要过早变成确定性策略"。熵是在衡量策略的随机性：熵高 → 动作分布均匀（探索多），熵低 → 动作集中（利用多）。加熵奖励能让策略保持一定的探索能力，不会过早收敛。'),

        ('brk',),
        ('h1', '第 1 步：采集数据（164-183 行）'),
        ('x', 164, 's = env.reset()', '重置环境。和 REINFORCE、AC 一样。'),
        ('x', 166, 'states, actions, rewards, dones, log_probs_old = [], [], [], [], []', '注意这里比 AC 多了一个 log_probs_old（旧策略下的 log_prob）。这是 PPO 的核心——要和旧策略对比。AC 不需要存这个，因为它每次只用当前策略更新一次。PPO 要对比新旧策略的差异。'),

        ('x', 169, 'a, lp = actor.get_action(s)', 'Actor 选动作，同时记录旧策略的 log_prob。这个 lp 会被存到 log_probs_old 中，后面计算 importance ratio 时会用到——"这个动作在旧策略下有多可能？"'),

        ('brk',),
        ('h1', '第 2 步：GAE —— 更好的 Advantage（185-213 行）'),
        ('p', 'GAE（Generalized Advantage Estimation）比 AC 的简单 TD error 更平滑。它综合了多步信息——就像看一段视频时不是只看每一帧，而是看连续几帧来理解动作。', 10, False),

        ('x', 185, '# 算 GAE (Generalized Advantage Estimation)', 'GAE 的核心思想：不只用一步的 TD error（λ=0），也不用整局的 MC return（λ=1），而是用 λ=0.95 在两者之间取一个平衡。这比 AC 的简单 Advantage 更准确、更稳定。'),
        ('x', 194, 'values = critic(states_t).squeeze()', '用 Critic 算所有状态的 V(s)。注意这里用了 squeeze() 把形状从 [n,1] 变成 [n]——方便后面的逐元素操作。'),
        ('x', 204, 'delta = rewards[t] + gamma * next_value * (1 - dones[t]) - values[t].item()', 'TD error = r + γV(s\') - V(s)。和 AC 的 Advantage 一模一样。'),
        ('x', 205, 'gae = delta + gamma * gae_lambda * (1 - dones[t]) * gae', 'GAE 的核心递推公式。当前步的 GAE = 当前步的 TD error + γλ × 下一步的 GAE。这样 GAE 不仅包含了当前步的信息，还包含了之后多步的信息。λ=0.95 意味着约 20 步后的信息权重降到 1/e。'),

        ('brk',),
        ('h1', '第 3 步：PPO 核心 —— clip 更新（215-264 行）'),
        ('p', '这是 PPO 最重要的部分，面试必问。', 12, True),

        ('x', 218, 'for _ in range(epochs):', '多轮更新。同一个 batch 的数据重复使用 epochs 次（默认 10 次）。AC 每条数据只用一次就扔掉，PPO 用 10 次——这就是 on-policy 和 off-policy 的区别：PPO 通过 importance ratio 来"纠正"多次使用的偏差。'),

        ('x', 232, 'log_probs_new, entropy = actor.evaluate(batch_s, batch_a)', '用当前策略（已经更新了几轮了）重新算 log_prob。注意这个 log_probs_new 和之前存的 old_log_probs 可能已经不同了——因为策略参数更新了。'),
        ('x', 238, 'ratio = torch.exp(log_probs_new - batch_old_lp)', 'importance ratio = π_new(a|s) / π_old(a|s)。如果 ratio > 1：这个动作在当前策略下比旧策略更可能了（概率增加了）。如果 ratio < 1：这个动作现在更不可能了（概率减少了）。ratio = 1：概率没变。比如 ratio=1.5 表示概率增加了 50%，ratio=0.5 表示概率减少了一半。'),

        ('x', 242, 'surr1 = ratio * batch_adv', '未 clip 的目标——和 AC 一样。ratio × A：如果动作更可能了且 Advantage > 0（好动作），目标增加。这是正常的策略梯度目标。'),
        ('x', 243, 'surr2 = torch.clamp(ratio, 1 - clip_eps, 1 + clip_eps) * batch_adv', 'clip 后的目标——PPO 的关键创新！torch.clamp 把 ratio 限制在 [0.8, 1.2] 之间。如果 ratio 超过了这个范围（策略变得太多了），就卡在边界上。比如 ratio=2.0（概率翻倍）会被砍到 1.2。这行代码就是 PPO 的全部创新——用一行 clamp 防止策略突变。'),
        ('p', 'clip 的效果：当 ratio > 1.2 时，surr2 比 surr1 小，min(surr1, surr2) 取 surr2，梯度为 0——不更新了。当 ratio < 0.8 时同理。策略只能"微调"，不能"突变"。', 10, True, GRAY),

        ('x', 244, 'actor_loss = -torch.min(surr1, surr2).mean()', '取 min(surr1, surr2) 作为最终的目标。当 ratio 安全（在 [0.8,1.2] 内），surr1 = surr2，正常更新。当 ratio 超出范围，min 取 surr2（clip 版本），梯度为 0 → 停止更新。这就是"近端"（Proximal）的含义——不让策略走太远。'),

        ('x', 248, 'entropy_loss = -entropy_coef * entropy.mean()', '熵奖励。entropy 衡量策略的随机性（熵高 = 动作分布均匀）。entropy_loss 让 actor 保持一定的随机性，防止过早变成确定性策略。没有这个的话，策略可能很快变得过于确定，不再探索——类似于 DQN 的 ε 太小。'),
        ('x', 255, 'torch.nn.utils.clip_grad_norm_(actor.parameters(), 0.5)', '梯度裁剪。又一个"保险"机制——如果梯度太大，把它缩小到范数 0.5 以内。防止梯度爆炸（gradient explosion）。PPO 有很多这样的安全机制，这也是它训练稳定的原因。'),

        ('brk',),
        ('h1', '三种方法公式对比'),
        ('tbl', ['', 'REINFORCE', 'Actor-Critic', 'PPO'], [
            ['网络输出', 'π(s)→采样', 'π(s)→采样', 'π(s)→采样'],
            ['价值估计', 'G_t = Σr（MC）', 'A = r+γV-V\'（TD）', 'GAE（平滑版 TD）'],
            ['更新时机', '整局结束', '每步', '每局结束，多轮重复'],
            ['核心 loss', '-logπ×G', '-logπ×A', '-min(clip ratio×A)'],
            ['安全机制', '无', '无', 'clip + 梯度裁剪 + 熵奖励'],
            ['方差', '很高', '中等', '低'],
            ['训练速度', '很慢', '中等', '中等（但更稳）'],
        ]),
        ('p', 'PPO 是 EMS 项目最终选用的算法。原因：连续动作 + 训练稳定（clip 防崩）+ 实现复杂度适中（比 SAC 的 5 个网络简单）+ 面试常考。', 12, True, BLUE),
    ],
    'Week11_Step4_PPO_逐行精讲.docx'
)

print('\nAll 4 docs generated successfully!')
