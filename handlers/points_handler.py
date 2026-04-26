"""
积分查询处理器 - /points
"""
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# 导入数据库模块
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database

# ============ 积分命令 ============
async def points_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """我的积分命令"""
    try:
        user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id
        username = update.message.from_user.first_name if update.message else update.callback_query.from_user.first_name
        
        # 获取用户预订记录计算积分
        bookings = database.get_user_bookings(str(user_id))
        
        # 计算已确认/已完成订单的总消费
        total_spent = 0
        for booking in bookings:
            if booking.get('status') in ['confirmed', 'completed']:
                total_spent += float(booking.get('total_price', 0))
        
        # 计算积分（每消费100铢得1积分）
        current_points = int(total_spent / 100)
        
        # 获取本周/本月积分变动
        now = datetime.now()
        week_start = now - timedelta(days=now.weekday())
        month_start = now.replace(day=1)
        
        weekly_points = 0
        monthly_points = 0
        
        for booking in bookings:
            created_at = booking.get('created_at', '')
            if created_at:
                try:
                    if 'T' in created_at:
                        booking_date = datetime.fromisoformat(created_at)
                    else:
                        booking_date = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                    
                    price = float(booking.get('total_price', 0))
                    earned = int(price / 100)
                    
                    if booking_date >= week_start:
                        weekly_points += earned
                    if booking_date >= month_start:
                        monthly_points += earned
                except Exception as e:
                    logger.warning(f"解析日期失败: {created_at}, {e}")
        
        # 计算会员等级
        if current_points >= 5000:
            vip_level = "💎 钻石会员"
            level_icon = "💎"
            next_level = "最高等级"
            points_to_next = 0
        elif current_points >= 2000:
            vip_level = "⭐ 金卡会员"
            level_icon = "⭐"
            next_level = "💎 钻石会员"
            points_to_next = 5000 - current_points
        elif current_points >= 500:
            vip_level = "🎫 银卡会员"
            level_icon = "🎫"
            next_level = "⭐ 金卡会员"
            points_to_next = 2000 - current_points
        else:
            vip_level = "🏷️ 普通会员"
            level_icon = "🏷️"
            next_level = "🎫 银卡会员"
            points_to_next = 500 - current_points
        
        # 积分价值说明
        points_value = current_points * 0.5  # 每积分价值0.5铢
        
        text = (
            "🎁 *我的积分*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 {username} 的积分账户\n\n"
            f"{level_icon} *当前等级：{vip_level}*\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 *当前积分：{current_points:,} 分*\n"
            f"💎 积分价值：约 ฿{points_value:,.0f}\n\n"
            f"📅 本周获得：+{weekly_points} 分\n"
            f"📅 本月获得：+{monthly_points} 分\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
        )
        
        if points_to_next > 0:
            text += (
                f"📈 距离 {next_level} 还差 {points_to_next:,} 积分\n\n"
                "💡 升级后可享受更多专属优惠！\n\n"
            )
        else:
            text += "🎉 您已享受最高等级的会员特权！\n\n"
        
        text += (
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎁 *积分使用规则*\n"
            "• 100积分 = ฿50 抵扣\n"
            "• 可在预订时使用\n"
            "• 可兑换专属优惠券\n\n"
            "输入 /redeem 兑换促销码"
        )
        
        keyboard = [
            [InlineKeyboardButton("🎟️ 查看优惠券", callback_data="cmd_coupons")],
            [InlineKeyboardButton("📜 积分记录", callback_data="cmd_points_history")],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data="main_menu")]
        ]
        
        if update.message:
            await update.message.reply_text(
                text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
    except Exception as e:
        logger.error(f"加载积分失败: {e}")
        error_text = "❌ 加载积分信息失败，请稍后重试"
        if update.message:
            await update.message.reply_text(error_text)
        elif update.callback_query:
            await update.callback_query.edit_message_text(error_text)


def register_points_handlers(application):
    """注册积分相关处理器"""
    from telegram.ext import CommandHandler, CallbackQueryHandler
    application.add_handler(CommandHandler("points", points_cmd))
    application.add_handler(CallbackQueryHandler(points_cmd, pattern="^cmd_points$"))
