#!/usr/bin/env python3
"""Taimili Villa Booking Telegram Bot - Koyeb Ready"""

import os
import logging
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '6789145161:AAGk0esn72A4kim6l4LcJqW17c9lqibwZhc')
PORT = int(os.environ.get('PORT', 8080))

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = '{"status": "ok", "bot": "Taimili Villa Booking Bot"}'
        self.wfile.write(response.encode())
    
    def log_message(self, format, *args):
        pass

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

def run_http_server():
    server = HTTPServer(('0.0.0.0', PORT), HealthHandler)
    logger.info(f"HTTP服务器启动在端口 {PORT}")
    server.serve_forever()

def main():
    # 启动HTTP服务器（后台线程）
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # 启动Bot
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("book", book))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 Bot 启动...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
