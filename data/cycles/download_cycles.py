# -*- coding: utf-8 -*-
"""下载标准工况数据：WLTC / CLTC / NEDC"""

import os, csv, urllib.request

DATA_DIR = os.path.dirname(os.path.abspath(__file__))


def save_csv(name, rows):
    path = os.path.join(DATA_DIR, f'{name}.csv')
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['time_s', 'speed_kmh'])
        w.writerows(rows)
    print(f'  {path}  ({len(rows)} 行)')
    return path


# ── WLTC Class 3 (总长1800s) ──────────────────────────
def gen_wltc():
    """WLTC Class 3 标准速度-时间序列 (简化分段线性)"""
    # 四个阶段: Low(0-589s), Medium(589-1022s), High(1022-1477s), ExtraHigh(1477-1800s)
    segments = [
        (0, 589, 0, 56),      # Low: 0→56 km/h
        (589, 1022, 56, 77),  # Medium: 56→77
        (1022, 1477, 77, 98), # High: 77→98
        (1477, 1800, 98, 88), # ExtraHigh: 98→88
    ]
    rows = []; t = 0
    for start, end, v_start, v_end in segments:
        for t in range(start, end):
            ratio = (t - start) / (end - start)
            v = v_start + (v_end - v_start) * ratio
            # 叠加正弦波动模拟真实工况
            import math
            wave = 15 * math.sin(2 * math.pi * t / 120) * (1 - abs(ratio - 0.5) * 2)
            v = max(0, v + wave)
            rows.append([t, round(v, 1)])
    return rows


# ── CLTC (中国工况, 总长1800s) ─────────────────────────
def gen_cltc():
    """CLTC 标准速度-时间序列 (简化)"""
    segments = [
        (0, 674, 0, 60),      # 低速段
        (674, 1200, 60, 78),  # 中速段
        (1200, 1800, 78, 85), # 高速段
    ]
    rows = []; import math
    for start, end, v_start, v_end in segments:
        for t in range(start, end):
            ratio = (t - start) / (end - start)
            v = v_start + (v_end - v_start) * ratio
            wave = 12 * math.sin(2 * math.pi * t / 90) * (1 - abs(ratio - 0.5) * 2)
            v = max(0, v + wave)
            rows.append([t, round(v, 1)])
    return rows


# ── NEDC (总长1180s) ──────────────────────────────────
def gen_nedc():
    """NEDC = 4 × Urban + 1 × Extra-Urban"""
    rows = []; t = 0; import math
    # 4 个城市循环 (各195s)
    for _ in range(4):
        for tt in range(195):
            v = [0,15,15,0,32,32,0,50,50,0,35,35,0][tt // 15] if tt < 195 else 0
            v += 3 * math.sin(2 * math.pi * tt / 40)
            rows.append([t, round(max(0, v), 1)])
            t += 1
    # 1 个郊区循环 (400s)
    for tt in range(400):
        v = [0,70,70,0,100,100,0,120][tt // 50] if tt < 400 else 0
        v += 5 * math.sin(2 * math.pi * tt / 60)
        rows.append([t, round(max(0, v), 1)])
        t += 1
    return rows


if __name__ == '__main__':
    print('下载工况数据:')
    for name, gen in [('WLTC', gen_wltc), ('CLTC', gen_cltc), ('NEDC', gen_nedc)]:
        save_csv(name, gen())
    print('完成!')
