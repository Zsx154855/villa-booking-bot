#!/bin/bash
# =========================================
# Taimili Villa Booking System - 备份调度脚本
# 
# 使用方法:
#   ./scripts/schedule_backup.sh daily    # 每日备份
#   ./scripts/schedule_backup.sh weekly   # 每周备份
#   ./scripts/schedule_backup.sh monthly  # 月度备份
#   ./scripts/schedule_backup.sh verify   # 验证最新备份
# =========================================

set -e

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_TYPE="${1:-daily}"

cd "$PROJECT_DIR"

echo "=========================================="
echo "🏠 Taimili 别墅预订系统 - 数据库备份"
echo "=========================================="
echo "项目目录: $PROJECT_DIR"
echo "备份类型: $BACKUP_TYPE"
echo "时间: $(date -u '+%Y-%m-%d %H:%M:%S') UTC"
echo "=========================================="

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 python3"
    exit 1
fi

# 检查数据库文件
if [ ! -f "data/villas.db" ]; then
    echo "⚠️  警告: 数据库文件不存在: data/villas.db"
    echo "   将跳过备份"
    exit 0
fi

# 执行备份
case "$BACKUP_TYPE" in
    daily)
        echo "📅 执行每日备份..."
        python3 scripts/backup.py --type daily
        ;;
    weekly)
        echo "📅 执行每周备份..."
        python3 scripts/backup.py --type weekly
        ;;
    monthly)
        echo "📅 执行月度备份..."
        python3 scripts/backup.py --type monthly
        ;;
    verify)
        echo "🔍 验证最新备份..."
        python3 scripts/restore.py --list-backups
        ;;
    restore)
        echo "🔄 恢复数据库..."
        BACKUP_FILE=$(ls -t data/backups/villas_daily_latest.db 2>/dev/null | head -1)
        if [ -n "$BACKUP_FILE" ]; then
            python3 scripts/restore.py "$BACKUP_FILE"
        else
            echo "❌ 未找到可用备份"
            exit 1
        fi
        ;;
    *)
        echo "❌ 未知备份类型: $BACKUP_TYPE"
        echo "可用类型: daily, weekly, monthly, verify, restore"
        exit 1
        ;;
esac

echo "=========================================="
echo "✅ 任务完成"
echo "=========================================="
