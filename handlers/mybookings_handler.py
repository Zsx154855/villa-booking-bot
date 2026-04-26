"""
预订历史处理器 - /mybookings
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# 导入数据库模块
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database

# ============ 预订状态常量 ============
(BOOKING_LIST, BOOKING_DETAIL) = range(2)

# ============ 计算住宿天数 ============
def calculate_nights(checkin, checkout):
    """计算住宿天数"""
    from datetime import datetime
    try:
        d1 = datetime.strptime(checkin, "%Y-%m-%d")
        d2 = datetime.strptime(checkout, "%Y-%m-%d")
        return (d2 - d1).days
    except:
        return 0

# ============ 预订历史命令 ============
async def mybookings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """我的预订命令"""
    try:
        user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id
        bookings = database.get_user_bookings(str(user_id))
        
        if not bookings:
            keyboard = [
                [InlineKeyboardButton("📝 去预订", callback_data="cmd_book")],
                [InlineKeyboardButton("🔙 返回主菜单", callback_data="main_menu")]
            ]
            text = (
                "📋 *我的预订*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "😔 您还没有任何预订记录\n\n"
                "快去预订一间心仪的别墅吧！"
            )
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
            return
        
        # 状态emoji映射
        status_emoji = {
            'pending': '⏳',
            'confirmed': '✅',
            'cancelled': '❌',
            'completed': '🏁'
        }
        
        status_text = {
            'pending': '待确认',
            'confirmed': '已确认',
            'cancelled': '已取消',
            'completed': '已完成'
        }
        
        # 地区emoji
        region_emoji = {"芭提雅": "🏖️", "曼谷": "🏙️", "普吉岛": "🏝️"}
        
        text = (
            "📋 *我的预订*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 共 {len(bookings)} 条预订记录\n\n"
        )
        
        keyboard = []
        
        for i, booking in enumerate(bookings[:10], 1):  # 最多显示10条
            villa_id = booking.get('villa_id', '')
            villa_name = booking.get('villa_name', villa_id)
            checkin = booking.get('checkin', '')
            checkout = booking.get('checkout', '')
            status = booking.get('status', 'pending')
            region = booking.get('villa_region', '')
            emoji = region_emoji.get(region, "📍")
            
            nights = calculate_nights(checkin, checkout)
            status_icon = status_emoji.get(status, '❓')
            status_desc = status_text.get(status, '未知')
            
            text += (
                f"{i}. {status_icon} *{villa_name}*\n"
                f"   {emoji} {region} | {checkin} → {checkout}\n"
                f"   📌 状态：{status_desc} | {nights}晚\n\n"
            )
            
            keyboard.append([InlineKeyboardButton(
                f"📋 {villa_name[:15]}...", 
                callback_data=f"booking_detail_{booking.get('booking_id', '')}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 返回主菜单", callback_data="main_menu")])
        
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
        logger.error(f"加载预订列表失败: {e}")
        error_text = "❌ 加载预订列表失败，请稍后重试"
        if update.message:
            await update.message.reply_text(error_text)
        elif update.callback_query:
            await update.callback_query.edit_message_text(error_text)


async def mybookings_detail_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """预订详情命令"""
    try:
        query = update.callback_query
        await query.answer()
        
        # 从callback_data中提取booking_id
        # 格式: booking_detail_xxxxx
        booking_id = query.data.replace("booking_detail_", "")
        
        booking = database.get_booking(booking_id)
        
        if not booking:
            await query.edit_message_text(
                "❌ 未找到该预订记录",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 返回", callback_data="cmd_mybookings")]])
            )
            return
        
        villa_id = booking.get('villa_id', '')
        villa_name = booking.get('villa_name', villa_id)
        checkin = booking.get('checkin', '')
        checkout = booking.get('checkout', '')
        guests = booking.get('guests', 0)
        contact_name = booking.get('contact_name', '')
        contact_phone = booking.get('contact_phone', '')
        contact_note = booking.get('contact_note', '')
        price_per_night = float(booking.get('price_per_night', 0))
        total_price = float(booking.get('total_price', 0))
        status = booking.get('status', 'pending')
        region = booking.get('villa_region', '')
        
        nights = calculate_nights(checkin, checkout)
        
        status_emoji = {
            'pending': '⏳',
            'confirmed': '✅',
            'cancelled': '❌',
            'completed': '🏁'
        }
        
        status_text = {
            'pending': '待确认',
            'confirmed': '已确认',
            'cancelled': '已取消',
            'completed': '已完成'
        }
        
        region_emoji = {"芭提雅": "🏖️", "曼谷": "🏙️", "普吉岛": "🏝️"}
        emoji = region_emoji.get(region, "📍")
        status_icon = status_emoji.get(status, '❓')
        status_desc = status_text.get(status, '未知')
        
        detail_text = (
            "📋 *预订详情*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔖 预订编号：{booking_id}\n\n"
            f"{emoji} *{villa_name}*\n"
            f"🏷️ 别墅编号：{villa_id}\n\n"
            f"📅 入住日期：{checkin}\n"
            f"📅 退房日期：{checkout}\n"
            f"🌙 住宿天数：{nights} 晚\n"
            f"👤 入住人数：{guests} 人\n\n"
            f"💰 房价：฿{price_per_night:,.0f}/晚\n"
            f"💰 *总价：฿{total_price:,.0f}*\n\n"
            f"👤 联系人：{contact_name}\n"
            f"📞 联系电话：{contact_phone}\n"
            f"📝 备注：{contact_note or '无'}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 当前状态：{status_icon} {status_desc}\n"
        )
        
        keyboard = []
        
        # 根据状态显示不同按钮
        if status == 'pending':
            keyboard.append([InlineKeyboardButton("❌ 取消预订", callback_data=f"cancel_booking_{booking_id}")])
        elif status == 'completed':
            keyboard.append([InlineKeyboardButton("⭐ 立即评价", callback_data=f"review_booking_{booking_id}")])
        
        if status in ['confirmed', 'completed']:
            keyboard.append([InlineKeyboardButton("📞 联系客服", callback_data="cmd_contact")])
        
        keyboard.append([InlineKeyboardButton("🔙 返回预订列表", callback_data="cmd_mybookings")])
        
        await query.edit_message_text(
            detail_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"加载预订详情失败: {e}")
        await update.callback_query.edit_message_text("❌ 加载预订详情失败")


def register_mybookings_handlers(application):
    """注册预订历史相关处理器"""
    from telegram.ext import CommandHandler, CallbackQueryHandler
    application.add_handler(CommandHandler("mybookings", mybookings_cmd))
    application.add_handler(CallbackQueryHandler(mybookings_detail_cmd, pattern="^booking_detail_"))
