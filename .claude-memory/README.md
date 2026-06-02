# Claude Code 记忆同步

此目录用于跨设备同步 Claude Code 的记忆（memory）和上下文。

## 使用方式

### 设备 A（关机前）

```bash
# 更新进度
git add -A && git commit -m "update: progress"
git push

# 同步记忆（可选）
python sync_memory.py --save
```

### 设备 B（开机后）

```bash
# 拉取最新代码
git pull

# 同步记忆（可选）
python sync_memory.py --load
```

## 记忆文件说明

- `project-context.md` — 项目背景和约束
- `user-preference.md` — 用户偏好和习惯
- `learning-progress.md` — 学习进度记录
- `technical-decisions.md` — 技术决策记录

## 注意

- `.claude/memory/` 目录位于 `C:\Users\<用户名>\.claude\projects\F--CLAUDE-research\memory\`
- 每次切换设备前运行 `--save`，切换后运行 `--load`
- 如果只在同一设备工作，不需要运行同步脚本
