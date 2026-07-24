#!/usr/bin/env python3
"""
一键下载公开实船功率/能耗数据集
目标：NAUTILUS SOFC+Battery 实测数据 + Shifts 货船功率预测 + TU Delft Ch.3 LPF-EMS
"""

import os, sys, json, zipfile
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

SAVE_DIR = Path(__file__).parent / 'datasets'
SAVE_DIR.mkdir(exist_ok=True)

UA = 'Mozilla/5.0'

def download_file(url, filename, desc=''):
    path = SAVE_DIR / filename
    if path.exists():
        print(f'  ✓ 已存在: {filename} ({path.stat().st_size / 1024 / 1024:.1f} MB)')
        return path
    print(f'  ↓ 下载 {desc or filename} ...', end=' ', flush=True)
    try:
        req = Request(url, headers={'User-Agent': UA})
        resp = urlopen(req, timeout=120)
        total = int(resp.headers.get('Content-Length', 0))
        downloaded = 0
        with open(path, 'wb') as f:
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    print(f'\r  ↓ 下载 {desc or filename} ... {pct}% ({downloaded/1024/1024:.1f}/{total/1024/1024:.1f} MB)', end='', flush=True)
        print(f'\r  ✓ {desc or filename} ({path.stat().st_size / 1024 / 1024:.1f} MB)')
        return path
    except URLError as e:
        print(f'\n  ✗ 下载失败: {e.reason}')
        return None
    except Exception as e:
        print(f'\n  ✗ 下载失败: {e}')
        return None


def main():
    print('=' * 60)
    print('  公开实船功率/能耗数据集 — 一键下载')
    print('=' * 60)
    print()

    success = []

    # ── 1. NAUTILUS SOFC + Battery ──
    print('[1/3] NAUTILUS SOFC+电池实测数据')
    print('      平台: Zenodo | 许可: CC BY 4.0')
    print('      说明: 60kWe SOFC + 40kWh 锂电池，2024年游轮负荷实测')

    # 先获取文件列表
    api_url = 'https://zenodo.org/api/records/14643552'
    try:
        req = Request(api_url, headers={'User-Agent': UA})
        resp = urlopen(req, timeout=15)
        meta = json.loads(resp.read())
        files = meta.get('files', [])
        if not files:
            print('  ! API返回空文件列表')
        else:
            for f in files:
                fn = f['key']
                fsize = f['size'] / 1024 / 1024
                furl = f['links']['self']
                print(f'    发现: {fn} ({fsize:.1f} MB)')
                result = download_file(furl, f'NAUTILUS_{fn}', f'NAUTILUS: {fn}')
                if result:
                    success.append(result)
    except URLError as e:
        print(f'  ✗ 无法连接 Zenodo (API): {e.reason}')
        print('    提示: Zenodo 在某些网络环境下被屏蔽，请手动下载:')
        print('    https://zenodo.org/records/14643552')
    except Exception as e:
        print(f'  ✗ NAUTILUS 下载错误: {e}')
    print()

    # ── 2. Shifts Marine Cargo Vessel ──
    print('[2/3] Shifts Marine Cargo Vessel 功率预测数据集')
    print('      平台: Zenodo | 许可: CC BY-NC-SA 4.0')
    print('      说明: 营运货船4年每分钟采样传感器数据')

    shifts_doi = '7057666'
    try:
        api_url = f'https://zenodo.org/api/records/{shifts_doi}'
        req = Request(api_url, headers={'User-Agent': UA})
        resp = urlopen(req, timeout=15)
        meta = json.loads(resp.read())
        files = meta.get('files', [])
        if not files:
            print('  ! API返回空文件列表')
        else:
            for f in files:
                fn = f['key']
                fsize = f['size'] / 1024 / 1024
                furl = f['links']['self']
                print(f'    发现: {fn} ({fsize:.1f} MB)')
                result = download_file(furl, f'Shifts_{fn}', f'Shifts: {fn}')
                if result:
                    success.append(result)
    except URLError as e:
        print(f'  ✗ 无法连接 Zenodo (API): {e.reason}')
        print('    提示: 请手动下载:')
        print('    https://zenodo.org/record/7057666')
    except Exception as e:
        print(f'  ✗ Shifts 下载错误: {e}')
    print()

    # ── 3. TU Delft Ch.3 LPF-EMS ──
    print('[3/3] TU Delft Ch.3 LPF-EMS (SH2IPDRIVE)')
    print('      平台: 4TU.ResearchData | 许可: CC BY 4.0')
    print('      说明: FC-电池电动船低通滤波EMS + 退化评估')

    url_4tu = 'https://data.4tu.nl/ndownloader/items/589dc384-b5bf-450b-bba2-c6cd1d33e378/versions/1'
    result = download_file(url_4tu, 'TU_Delft_Ch3_LPF_EMS.zip', 'TU Delft Ch.3')
    if result:
        # 验证 ZIP
        try:
            with zipfile.ZipFile(result) as zf:
                contents = zf.namelist()
            print(f'    ✓ ZIP 验证通过，内含 {len(contents)} 个文件')
            for c in contents[:10]:
                print(f'      - {c}')
            if len(contents) > 10:
                print(f'      ... 及另外 {len(contents)-10} 个文件')
            success.append(result)
        except zipfile.BadZipFile:
            print('    ✗ ZIP 文件损坏，请重新下载')
            result.unlink()
    print()

    # ── 汇总 ──
    print('=' * 60)
    print(f'  下载完成: {len(success)} / 3 个数据集')
    print(f'  保存路径: {SAVE_DIR}')
    print('=' * 60)
    print()

    if success:
        print('下载的文件:')
        for s in success:
            print(f'  • {s.name} ({s.stat().st_size/1024/1024:.1f} MB)')

    print()
    print('提示: 如果 Zenodo (NAUTILUS/Shifts) 下载失败，请手动访问:')
    print('  • NAUTILUS: https://zenodo.org/records/14643552')
    print('  • Shifts:   https://zenodo.org/record/7057666')
    print('  • TU Delft: https://data.4tu.nl/datasets/589dc384-b5bf-450b-bba2-c6cd1d33e378/1')


if __name__ == '__main__':
    main()
