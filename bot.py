#!/usr/bin/env python3
"""Taimili Villa Booking Telegram Bot"""

import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '🏠 欢迎来到Taimili别墅预订助手！\n\n'
        '我可以帮你：\n'
        '• 查询别墅信息\n'
        '• 预订房间\n'
        '• 了解周边景点\n\n'
        '请告诉我你需要什么帮助？'
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '📋 帮助信息\n\n'
        '/start - 开始使用\n'
        '/help - 查看帮助\n'
        '/info - 别墅信息\n'
        '/book - 预订房间'
    )

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '🏠 Taimili度假别墅\n\n'
        '📍 位置：芭提雅 | 曼谷 | 普吉岛\n'
        '🛏️ 房型：豪华套房、家庭房、标准间\n'
        '🏊 设施：私人泳池、烧烤区、停车场\n'
        '✨ 100+高端别墅可选\n\n'
        '📩 私信询价或直接预订！'
    )

async def book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '📝 预订流程\n\n'
        '1. 告诉我你的出行日期\n'
        '2. 选择房型和人数\n'
        '3. 确认预订信息\n\n'
        '请先告诉我：计划什么时候入住？'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    logger.info(f"收到消息: {msg}")
    await update.message.reply_text(f"收到：{msg}\n\n客服会尽快回复您！")

def main():
    if not TOKEN:
        logger.error("未设置 TELEGRAM_BOT_TOKEN")
        return
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("book", book))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 Bot 启动...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
