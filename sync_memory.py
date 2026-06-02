# -*- coding: utf-8 -*-
"""
sync_memory.py — Claude Code 记忆同步工具

在设备切换时同步 Claude Code 的记忆文件：
  --save   将系统记忆复制到仓库（设备A：关机前运行）
  --load   将仓库记忆恢复到系统（设备B：开机后运行）

用法：
  python sync_memory.py --save
  python sync_memory.py --load
"""

import os
import sys
import shutil
import argparse

# 仓库内的记忆目录
REPO_MEMORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.claude-memory')
# 系统记忆目录
SYS_MEMORY = os.path.expanduser(
    '~/.claude/projects/F--CLAUDE-research/memory'
)


def save():
    """将系统记忆复制到仓库"""
    if not os.path.exists(SYS_MEMORY):
        print(f'[跳过] 系统记忆目录不存在: {SYS_MEMORY}')
        return

    os.makedirs(REPO_MEMORY, exist_ok=True)
    count = 0
    for fname in os.listdir(SYS_MEMORY):
        src = os.path.join(SYS_MEMORY, fname)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(REPO_MEMORY, fname))
            count += 1
    print(f'[OK] {count} 个记忆文件已保存到仓库')
    print(f'  运行 git add -A && git commit -m "sync memory" && git push')


def load():
    """将仓库记忆恢复到系统"""
    if not os.path.exists(REPO_MEMORY):
        print(f'[跳过] 仓库记忆目录不存在: {REPO_MEMORY}')
        return

    os.makedirs(SYS_MEMORY, exist_ok=True)
    count = 0
    for fname in os.listdir(REPO_MEMORY):
        if fname.endswith('.md'):
            src = os.path.join(REPO_MEMORY, fname)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(SYS_MEMORY, fname))
                count += 1
    print(f'[OK] {count} 个记忆文件已恢复到系统')
    print(f'  重启 Claude Code 后生效')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Claude Code 记忆同步')
    parser.add_argument('--save', action='store_true', help='保存系统记忆到仓库')
    parser.add_argument('--load', action='store_true', help='加载仓库记忆到系统')
    args = parser.parse_args()

    if not args.save and not args.load:
        parser.print_help()
        sys.exit(1)

    if args.save:
        save()
    if args.load:
        load()
