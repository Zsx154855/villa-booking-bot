# 数据库备份工具

本目录包含 Taimili 别墅预订系统的数据库备份与恢复工具。

## 📁 文件说明

| 文件 | 说明 |
|------|------|
| `backup.py` | 主备份脚本 |
| `restore.py` | 恢复脚本 |
| `schedule_backup.sh` | Shell 调度脚本 |

## 🚀 快速开始

### 1. 执行备份

```bash
# 每日备份（默认）
python scripts/backup.py --type daily

# 每周完整备份
python scripts/backup.py --type weekly

# 月度归档备份
python scripts/backup.py --type monthly
```

### 2. 查看可用备份

```bash
python scripts/restore.py --list-backups
```

### 3. 恢复数据库

```bash
# 从最新备份恢复
python scripts/restore.py data/backups/villas_daily_latest.db

# 从指定备份恢复
python scripts/restore.py data/backups/villas_daily_20260427_020000.db
```

### 4. 验证备份

```bash
python scripts/restore.py backups/villas_daily_latest.db --verify-only
```

## ⚙️ 配置环境变量

```bash
# 数据库路径
export DB_PATH=data/villas.db

# 备份目录
export BACKUP_DIR=data/backups

# GitHub 配置（用于云端同步）
export GITHUB_TOKEN=ghp_xxxxx
export GITHUB_REPO=username/villa-booking-bot
```

## ⏰ 自动化配置

### Render Cron Jobs

```bash
# 每日备份
render cron create \
  --name=daily-db-backup \
  --schedule="0 2 * * *" \
  --command="python scripts/backup.py --type daily" \
  --service=taimili-villa-bot
```

### GitHub Actions

在 `.github/workflows/backup.yml` 中配置自动备份：
- 每天 UTC 02:00 自动执行
- 支持手动触发

## 📊 备份策略

| 类型 | 频率 | 保留时间 |
|------|------|----------|
| 每日备份 | 每天 | 7天 |
| 每周备份 | 每周日 | 4周 |
| 月度备份 | 每月1日 | 12个月 |

## 🔒 安全提示

1. **GITHUB_TOKEN**: 使用 Personal Access Token，不要使用密码
2. **定期检查**: 定期验证备份是否成功上传
3. **恢复测试**: 定期测试恢复流程确保备份可用

## 📝 示例输出

```
============================================================
🏠 Taimili 别墅预订系统 - 数据库备份
============================================================
数据库路径: data/villas.db
备份目录: data/backups
备份类型: daily
📊 数据库统计:
   - villas: 15 条记录
   - bookings: 2 条记录
   - 总大小: 64.0 KB
✅ 备份成功: villas_daily_20260427_020000.db
   大小: 64.00 KB
   校验和: 3f4fe927a459354270174cb33cc819c7
============================================================
✅ 备份任务完成
============================================================
```

## 🆘 故障排除

### 备份失败
- 检查数据库文件是否存在
- 检查备份目录是否有写入权限
- 查看 `data/backups/backup.log` 日志

### 恢复失败
- 确保备份文件完整未损坏
- 运行 `--verify-only` 检查备份有效性
- 检查目标路径是否有写入权限

### GitHub 上传失败
- 确认 GITHUB_TOKEN 有效且有 repo 权限
- 检查 GITHUB_REPO 格式正确（owner/repo）
