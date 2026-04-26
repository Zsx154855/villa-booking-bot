#!/usr/bin/env python3
"""
Taimili Villa Booking System - Report Handler
报表命令处理模块

提供 /report 命令处理，支持日报表、周报表、月报表的生成与导出
"""

import os
import sys
import logging
import asyncio
from datetime import datetime, date, timedelta
from typing import Dict, Optional, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ============ 模块导入 ============
def get_analytics_modules():
    """延迟导入analytics模块，避免循环依赖"""
    try:
        from src.services.analytics import ReportGenerator, ChartGenerator, ExcelExporter
        return ReportGenerator, ChartGenerator, ExcelExporter
    except ImportError as e:
        logger.error(f"导入analytics模块失败: {e}")
        return None, None, None


# ============ 命令处理器 ============

async def report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    /report 命令处理器 - 显示报表菜单
    """
    keyboard = [
        [
            InlineKeyboardButton("📅 今日报表", callback_data="report_daily"),
            InlineKeyboardButton("📆 本周报表", callback_data="report_weekly"),
        ],
        [
            InlineKeyboardButton("📊 本月报表", callback_data="report_monthly"),
            InlineKeyboardButton("📋 综合报表", callback_data="report_all"),
        ],
        [
            InlineKeyboardButton("📥 导出Excel", callback_data="report_export_menu"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📊 *数据报表中心*\n\n"
        "请选择您要查看的报表类型：",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return 0


async def report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    处理报表回调按钮
    """
    query = update.callback_query
    await query.answer()
    
    # 获取回调数据
    data = query.data
    
    # 延迟导入
    ReportGenerator, ChartGenerator, ExcelExporter = get_analytics_modules()
    
    if ReportGenerator is None:
        await query.edit_message_text(
            "❌ 报表模块未安装，请联系管理员"
        )
        return -1
    
    generator = ReportGenerator()
    report_date = date.today()
    
    try:
        if data == 'report_daily':
            await _show_daily_report(query, generator, report_date)
        elif data == 'report_weekly':
            await _show_weekly_report(query, generator, report_date)
        elif data == 'report_monthly':
            await _show_monthly_report(query, generator, report_date)
        elif data == 'report_all':
            await _show_all_reports(query, generator, report_date)
        elif data.startswith('report_export_'):
            await _handle_export(query, context, data, generator, report_date)
        else:
            await query.edit_message_text(
                "❌ 未知操作"
            )
    except Exception as e:
        logger.error(f"生成报表失败: {e}")
        await query.edit_message_text(
            f"❌ 生成报表失败: {str(e)}"
        )
    
    return -1


async def _show_daily_report(query, generator: Any, report_date: date):
    """显示日报表"""
    report = generator.get_daily_report(report_date)
    text = generator.format_daily_report_text(report)
    
    keyboard = [
        [InlineKeyboardButton("📥 导出Excel", callback_data="report_export_daily")],
        [InlineKeyboardButton("🔙 返回菜单", callback_data="report_back")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def _show_weekly_report(query, generator: Any, report_date: date):
    """显示周报表"""
    report = generator.get_weekly_report(report_date)
    text = generator.format_weekly_report_text(report)
    
    keyboard = [
        [InlineKeyboardButton("📥 导出Excel", callback_data="report_export_weekly")],
        [InlineKeyboardButton("🔙 返回菜单", callback_data="report_back")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def _show_monthly_report(query, generator: Any, report_date: date):
    """显示月报表"""
    report = generator.get_monthly_report(report_date.year, report_date.month)
    text = generator.format_monthly_report_text(report)
    
    keyboard = [
        [InlineKeyboardButton("📥 导出Excel", callback_data="report_export_monthly")],
        [InlineKeyboardButton("🔙 返回菜单", callback_data="report_back")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def _show_all_reports(query, generator: Any, report_date: date):
    """显示所有报表"""
    daily = generator.get_daily_report(report_date)
    weekly = generator.get_weekly_report(report_date)
    monthly = generator.get_monthly_report(report_date.year, report_date.month)
    
    text = (
        "📊 *综合运营报表*\n\n"
        f"*{daily['date_display']}*\n"
        f"📈 预订: `{daily['total_bookings']}` 单 | "
        f"💰 收入: `¥{daily['total_revenue']:,.2f}`\n\n"
        f"*{weekly['date_range_display']} (本周)*\n"
        f"📈 预订: `{weekly['total_bookings']}` 单 | "
        f"💰 收入: `¥{weekly['total_revenue']:,.2f}`\n\n"
        f"*{monthly['month_display']}*\n"
        f"📈 预订: `{monthly['total_bookings']}` 单 | "
        f"💰 收入: `¥{monthly['total_revenue']:,.2f}`\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("📥 导出综合Excel", callback_data="report_export_all")],
        [InlineKeyboardButton("🔙 返回菜单", callback_data="report_back")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def _handle_export(query, context: ContextTypes.DEFAULT_TYPE, data: str, generator: Any, report_date: date):
    """处理Excel导出"""
    try:
        from src.services.analytics import ExcelExporter
        exporter = ExcelExporter()
        
        await query.edit_message_text("⏳ 正在生成Excel报表...")
        
        if data == 'report_export_daily':
            report = generator.get_daily_report(report_date)
            output_path = exporter.export_daily_report(report)
        elif data == 'report_export_weekly':
            report = generator.get_weekly_report(report_date)
            output_path = exporter.export_weekly_report(report)
        elif data == 'report_export_monthly':
            report = generator.get_monthly_report(report_date.year, report_date.month)
            output_path = exporter.export_monthly_report(report)
        elif data == 'report_export_all':
            daily = generator.get_daily_report(report_date)
            weekly = generator.get_weekly_report(report_date)
            monthly = generator.get_monthly_report(report_date.year, report_date.month)
            output_path = exporter.export_comprehensive_report(daily, weekly, monthly)
        else:
            output_path = None
        
        if output_path and os.path.exists(output_path):
            # 发送文件
            with open(output_path, 'rb') as f:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=f,
                    filename=os.path.basename(output_path),
                    caption="📥 Excel报表已生成"
                )
            
            keyboard = [[InlineKeyboardButton("🔙 返回菜单", callback_data="report_back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "✅ 报表已发送！",
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text(
                "❌ 报表生成失败，请稍后重试"
            )
    
    except ImportError as e:
        logger.error(f"Excel导出失败: {e}")
        await query.edit_message_text(
            "❌ Excel导出模块未安装\n"
            "请运行: pip install openpyxl"
        )
    except Exception as e:
        logger.error(f"导出Excel失败: {e}")
        await query.edit_message_text(
            f"❌ 导出失败: {str(e)}"
        )


# ============ 管理命令 ============

async def admin_report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    /adminreport 命令 - 管理员生成指定日期报表
    用法: /adminreport daily 2024-01-15
    """
    if not context.args:
        await update.message.reply_text(
            "📊 *管理报表生成*\n\n"
            "用法:\n"
            "• `/adminreport daily [日期]` - 生成日报表\n"
            "• `/adminreport weekly [日期]` - 生成周报表\n"
            "• `/adminreport monthly [年] [月]` - 生成月报表\n\n"
            "示例:\n"
            "• `/adminreport daily 2024-01-15`\n"
            "• `/adminreport monthly 2024 1`",
            parse_mode='Markdown'
        )
        return 0
    
    try:
        ReportGenerator, ChartGenerator, ExcelExporter = get_analytics_modules()
        
        if ReportGenerator is None:
            await update.message.reply_text("❌ 报表模块未安装")
            return -1
        
        generator = ReportGenerator()
        subcmd = context.args[0].lower()
        
        if subcmd == 'daily':
            report_date = datetime.strptime(context.args[1], '%Y-%m-%d').date() if len(context.args) > 1 else date.today()
            report = generator.get_daily_report(report_date)
            text = generator.format_daily_report_text(report)
        
        elif subcmd == 'weekly':
            report_date = datetime.strptime(context.args[1], '%Y-%m-%d').date() if len(context.args) > 1 else date.today()
            report = generator.get_weekly_report(report_date)
            text = generator.format_weekly_report_text(report)
        
        elif subcmd == 'monthly':
            year = int(context.args[1]) if len(context.args) > 1 else date.today().year
            month = int(context.args[2]) if len(context.args) > 2 else date.today().month
            report = generator.get_monthly_report(year, month)
            text = generator.format_monthly_report_text(report)
        
        else:
            await update.message.reply_text("❌ 未知子命令")
            return -1
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"生成管理报表失败: {e}")
        await update.message.reply_text(f"❌ 生成报表失败: {str(e)}")
    
    return -1


# ============ 命令注册 ============

def register_report_handlers(application):
    """注册报表相关命令处理器"""
    from telegram.ext import CommandHandler, CallbackQueryHandler
    
    # /report 命令
    application.add_handler(CommandHandler('report', report_cmd))
    
    # 回调处理器
    application.add_handler(CallbackQueryHandler(report_callback, pattern='^report_'))
    
    # 管理员命令
    application.add_handler(CommandHandler('adminreport', admin_report_cmd))
    
    logger.info("✅ 报表命令处理器已注册")


# ============ 直接运行 ============

if __name__ == '__main__':
    # 测试报表生成
    print("🧪 测试报表生成...\n")
    
    ReportGenerator, _, _ = get_analytics_modules()
    
    if ReportGenerator:
        generator = ReportGenerator()
        
        print("📅 日报表:")
        report = generator.get_daily_report()
        print(generator.format_daily_report_text(report))
        print()
        
        print("📆 周报表:")
        report = generator.get_weekly_report()
        print(generator.format_weekly_report_text(report))
        print()
        
        print("📊 月报表:")
        report = generator.get_monthly_report()
        print(generator.format_monthly_report_text(report))
    else:
        print("❌ 报表模块不可用")
