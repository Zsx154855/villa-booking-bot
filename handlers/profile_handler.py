"""
用户画像处理器 - /profile
"""
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# 导入数据库模块
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database

# ============ 用户画像命令 ============
async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """用户画像命令"""
    try:
        user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id
        username = update.message.from_user.username if update.message else update.callback_query.from_user.username
        first_name = update.message.from_user.first_name if update.message else update.callback_query.from_user.first_name
        
        # 获取或创建用户
        user = database.get_or_create_user(str(user_id), username)
        
        # 获取用户预订记录
        bookings = database.get_user_bookings(str(user_id))
        
        # 计算统计信息
        total_bookings = len(bookings)
        confirmed_bookings = len([b for b in bookings if b.get('status') == 'confirmed'])
        completed_bookings = len([b for b in bookings if b.get('status') == 'completed'])
        total_spent = sum(float(b.get('total_price', 0)) for b in bookings if b.get('status') in ['confirmed', 'completed'])
        
        # 计算积分（每消费100元得1积分）
        points = int(total_spent / 100)
        
        # 计算入住天数
        total_nights = 0
        for booking in bookings:
            if booking.get('checkin') and booking.get('checkout'):
                try:
                    d1 = datetime.strptime(booking.get('checkin'), "%Y-%m-%d")
                    d2 = datetime.strptime(booking.get('checkout'), "%Y-%m-%d")
                    total_nights += (d2 - d1).days
                except:
                    pass
        
        # 会员等级
        if total_spent >= 50000:
            vip_level = "💎 钻石会员"
            vip_benefits = "专属折扣、私人管家、优先预订"
        elif total_spent >= 20000:
            vip_level = "⭐ 金卡会员"
            vip_benefits = "9折优惠、免费接机、优先客服"
        elif total_spent >= 5000:
            vip_level = "🎫 银卡会员"
            vip_benefits = "9.5折优惠、生日特惠"
        else:
            vip_level = "🏷️ 普通会员"
            vip_benefits = "新用户首单优惠"
        
        # 注册日期
        created_at = user.get('created_at', '')
        if created_at:
            try:
                reg_date = datetime.fromisoformat(created_at).strftime('%Y-%m-%d')
            except:
                reg_date = created_at[:10] if len(created_at) >= 10 else created_at
        else:
            reg_date = datetime.now().strftime('%Y-%m-%d')
        
        profile_text = (
            "👤 *用户画像*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📛 昵称：{first_name}\n"
            f"🆔 用户ID：{user_id}\n"
            f"📅 注册日期：{reg_date}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "📊 *消费统计*\n"
            f"• 总预订：{total_bookings} 笔\n"
            f"• 已确认：{confirmed_bookings} 笔\n"
            f"• 已完成：{completed_bookings} 笔\n"
            f"• 累计入住：{total_nights} 晚\n"
            f"• 累计消费：฿{total_spent:,.0f}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{vip_level}\n"
            f"✨ 会员权益：{vip_benefits}\n\n"
            f"🎁 积分余额：{points} 分\n"
        )
        
        keyboard = [
            [InlineKeyboardButton("📋 我的预订", callback_data="cmd_mybookings")],
            [InlineKeyboardButton("🎟️ 我的优惠券", callback_data="cmd_coupons")],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data="main_menu")]
        ]
        
        if update.message:
            await update.message.reply_text(
                profile_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                profile_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
    except Exception as e:
        logger.error(f"用户画像加载失败: {e}")
        error_text = "❌ 加载用户画像失败，请稍后重试"
        if update.message:
            await update.message.reply_text(error_text)
        elif update.callback_query:
            await update.callback_query.edit_message_text(error_text)


def register_profile_handlers(application):
    """注册用户画像相关处理器"""
    from telegram.ext import CommandHandler
    application.add_handler(CommandHandler("profile", profile_cmd))
