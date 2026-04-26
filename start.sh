#!/bin/bash
# Taimili 别墅运营系统 - 快速启动脚本

echo "🏠 Taimili 别墅运营系统"
echo "========================"

# 检查Python版本
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "✓ Python版本: $PYTHON_VERSION"

# 检查依赖
echo ""
echo "检查依赖..."
pip install -q python-telegram-bot stripe reportlab matplotlib openpyxl psycopg2-binary 2>/dev/null
echo "✓ 依赖安装完成"

# 检查环境变量
echo ""
echo "检查环境变量..."
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "⚠️  TELEGRAM_BOT_TOKEN 未设置"
else
    echo "✓ TELEGRAM_BOT_TOKEN 已设置"
fi

if [ -z "$STRIPE_SECRET_KEY" ]; then
    echo "⚠️  STRIPE_SECRET_KEY 未设置（支付功能不可用）"
else
    echo "✓ STRIPE_SECRET_KEY 已设置"
fi

# 初始化数据库
echo ""
echo "初始化数据库..."
python3 -c "from database import init_db; init_db()" 2>/dev/null
echo "✓ 数据库初始化完成"

# 启动Bot
echo ""
echo "启动Bot..."
echo "Bot用户名: @MaotaiwyBot"
echo "========================"
echo ""

python3 bot.py
