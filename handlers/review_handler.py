"""
评价处理器 - /review
"""
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

logger = logging.getLogger(__name__)

# 导入数据库模块
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database

# ============ 评价状态 ============
(SELECT_BOOKING, ENTER_RATING, ENTER_COMMENT, CONFIRM_REVIEW) = range(4)

# ============ 评价命令 ============
async def review_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """评价命令 - 入口"""
    try:
        user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id
        
        # 获取用户已完成的预订
        bookings = database.get_user_bookings(str(user_id))
        completed_bookings = [b for b in bookings if b.get('status') in ['confirmed', 'completed']]
        
        if not completed_bookings:
            keyboard = [
                [InlineKeyboardButton("📋 查看我的预订", callback_data="cmd_mybookings")],
                [InlineKeyboardButton("🔙 返回主菜单", callback_data="main_menu")]
            ]
            text = (
                "⭐ *发表评价*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "😔 您还没有可评价的订单\n\n"
                "完成预订后即可对别墅进行评价"
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
            return ConversationHandler.END
        
        # 显示可评价的预订列表
        region_emoji = {"芭提雅": "🏖️", "曼谷": "🏙️", "普吉岛": "🏝️"}
        
        text = (
            "⭐ *发表评价*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "请选择您要评价的预订：\n\n"
        )
        
        keyboard = []
        for booking in completed_bookings[:5]:
            villa_name = booking.get('villa_name', '')
            booking_id = booking.get('booking_id', '')
            checkin = booking.get('checkin', '')
            region = booking.get('villa_region', '')
            emoji = region_emoji.get(region, "📍")
            
            text += f"• {emoji} {villa_name}\n  {checkin}\n\n"
            keyboard.append([InlineKeyboardButton(
                f"⭐ {villa_name[:15]}...", 
                callback_data=f"review_select_{booking_id}"
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
        
        context.user_data['review_bookings'] = completed_bookings
        return SELECT_BOOKING
        
    except Exception as e:
        logger.error(f"评价命令失败: {e}")
        error_text = "❌ 系统错误，请稍后重试"
        if update.message:
            await update.message.reply_text(error_text)
        elif update.callback_query:
            await update.callback_query.edit_message_text(error_text)
        return ConversationHandler.END


async def review_select_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """选择要评价的预订"""
    query = update.callback_query
    await query.answer()
    
    try:
        booking_id = query.data.replace("review_select_", "")
        bookings = context.user_data.get('review_bookings', [])
        
        # 找到对应的预订
        booking = None
        for b in bookings:
            if b.get('booking_id') == booking_id:
                booking = b
                break
        
        if not booking:
            await query.edit_message_text(
                "❌ 未找到该预订记录",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 返回", callback_data="main_menu")]])
            )
            return ConversationHandler.END
        
        # 保存选择的预订
        context.user_data['review_booking'] = booking
        context.user_data['review_booking_id'] = booking_id
        
        villa_name = booking.get('villa_name', '')
        region = booking.get('villa_region', '')
        region_emoji = {"芭提雅": "🏖️", "曼谷": "🏙️", "普吉岛": "🏝️"}
        emoji = region_emoji.get(region, "📍")
        
        text = (
            f"⭐ *评价 {emoji} {villa_name}*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "请选择您的评分（1-5星）：\n\n"
            "⭐☆☆☆☆ - 较差\n"
            "⭐⭐☆☆☆ - 一般\n"
            "⭐⭐⭐☆☆ - 良好\n"
            "⭐⭐⭐⭐☆ - 很好\n"
            "⭐⭐⭐⭐⭐ - 非常满意\n"
        )
        
        keyboard = [
            [InlineKeyboardButton("⭐☆☆☆☆ 很差", callback_data="rating_1")],
            [InlineKeyboardButton("⭐⭐☆☆☆ 一般", callback_data="rating_2")],
            [InlineKeyboardButton("⭐⭐⭐☆☆ 良好", callback_data="rating_3")],
            [InlineKeyboardButton("⭐⭐⭐⭐☆ 很好", callback_data="rating_4")],
            [InlineKeyboardButton("⭐⭐⭐⭐⭐ 非常满意", callback_data="rating_5")],
            [InlineKeyboardButton("🔙 取消", callback_data="cancel_review")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return ENTER_RATING
        
    except Exception as e:
        logger.error(f"选择评价预订失败: {e}")
        await query.edit_message_text("❌ 系统错误，请稍后重试")
        return ConversationHandler.END


async def review_enter_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """选择评分"""
    query = update.callback_query
    await query.answer()
    
    try:
        if query.data == "cancel_review":
            context.user_data.clear()
            await query.edit_message_text(
                "❌ 已取消评价",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 返回", callback_data="main_menu")]])
            )
            return ConversationHandler.END
        
        rating = int(query.data.replace("rating_", ""))
        context.user_data['review_rating'] = rating
        
        rating_text = "⭐" * rating + "☆" * (5 - rating)
        
        text = (
            f"⭐ 您选择了：{rating_text}\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "📝 请输入您的评价内容（可选）：\n\n"
            "可以分享您的住宿体验、推荐理由等\n"
            "也可以直接发送「跳过」直接提交\n"
        )
        
        keyboard = [
            [InlineKeyboardButton("⏭️ 跳过，直接提交", callback_data="skip_comment")],
            [InlineKeyboardButton("🔙 返回", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return ENTER_COMMENT
        
    except Exception as e:
        logger.error(f"选择评分失败: {e}")
        await query.edit_message_text("❌ 系统错误，请稍后重试")
        return ConversationHandler.END


async def review_enter_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """输入评价内容"""
    query = update.callback_query
    await query.answer()
    
    try:
        if query.data == "skip_comment":
            context.user_data['review_comment'] = ""
        else:
            # 这是一个回调，评价内容需要通过消息输入
            pass
        
        # 显示确认页面
        return await review_confirm(update, context)
        
    except Exception as e:
        logger.error(f"处理评价内容失败: {e}")
        await query.edit_message_text("❌ 系统错误，请稍后重试")
        return ConversationHandler.END


async def review_comment_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理评价内容消息"""
    try:
        comment = update.message.text.strip()
        context.user_data['review_comment'] = comment
        return await review_confirm(update, context)
    except Exception as e:
        logger.error(f"处理评价消息失败: {e}")
        await update.message.reply_text("❌ 系统错误，请稍后重试")
        return ConversationHandler.END


async def review_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """确认评价"""
    try:
        booking = context.user_data.get('review_booking', {})
        villa_name = booking.get('villa_name', '')
        region = booking.get('villa_region', '')
        rating = context.user_data.get('review_rating', 5)
        comment = context.user_data.get('review_comment', '')
        
        region_emoji = {"芭提雅": "🏖️", "曼谷": "🏙️", "普吉岛": "🏝️"}
        emoji = region_emoji.get(region, "📍")
        rating_text = "⭐" * rating + "☆" * (5 - rating)
        
        text = (
            f"⭐ *确认您的评价*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{emoji} 别墅：{villa_name}\n"
            f"⭐ 评分：{rating_text}\n"
        )
        
        if comment:
            text += f"📝 评价：{comment}\n"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━\n\n确认提交此评价？"
        
        keyboard = [
            [InlineKeyboardButton("✅ 确认提交", callback_data="confirm_review")],
            [InlineKeyboardButton("❌ 取消", callback_data="cancel_review")]
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
        
        return CONFIRM_REVIEW
        
    except Exception as e:
        logger.error(f"显示确认页面失败: {e}")
        await update.message.reply_text("❌ 系统错误，请稍后重试")
        return ConversationHandler.END


async def review_submit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """提交评价"""
    query = update.callback_query
    await query.answer()
    
    try:
        if query.data == "cancel_review":
            context.user_data.clear()
            await query.edit_message_text(
                "❌ 已取消评价\n\n感谢您的关注！",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 返回主菜单", callback_data="main_menu")]])
            )
            return ConversationHandler.END
        
        # 获取评价数据
        booking = context.user_data.get('review_booking', {})
        booking_id = context.user_data.get('review_booking_id', '')
        user_id = query.from_user.id
        rating = context.user_data.get('review_rating', 5)
        comment = context.user_data.get('review_comment', '')
        
        villa_name = booking.get('villa_name', '')
        villa_id = booking.get('villa_id', '')
        
        # 保存评价（实际应保存到数据库）
        logger.info(f"用户 {user_id} 提交评价：别墅 {villa_id}, 评分 {rating}, 评论: {comment}")
        
        # 计算奖励积分
        points_reward = rating * 10  # 每星10积分
        
        text = (
            "🎉 *评价提交成功！*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"感谢您的评价！\n\n"
            f"⭐ 您对 {villa_name} 的评价已提交\n"
            f"🎁 获得 +{points_reward} 积分奖励\n\n"
            "您的反馈是我们改进的动力！"
        )
        
        keyboard = [
            [InlineKeyboardButton("📋 查看我的预订", callback_data="cmd_mybookings")],
            [InlineKeyboardButton("🎟️ 我的优惠券", callback_data="cmd_coupons")],
            [InlineKeyboardButton("🏠 返回主菜单", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # 清理用户数据
        context.user_data.clear()
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"提交评价失败: {e}")
        await query.edit_message_text("❌ 提交评价失败，请稍后重试")
        return ConversationHandler.END


def register_review_handlers(application):
    """注册评价相关处理器"""
    from telegram.ext import CommandHandler, ConversationHandler, CallbackQueryHandler, MessageHandler
    
    review_conv = ConversationHandler(
        entry_points=[CommandHandler("review", review_cmd)],
        states={
            SELECT_BOOKING: [
                CallbackQueryHandler(review_select_booking, pattern="^review_select_")
            ],
            ENTER_RATING: [
                CallbackQueryHandler(review_enter_rating, pattern="^rating_"),
                CallbackQueryHandler(review_cmd, pattern="^cancel_review$")
            ],
            ENTER_COMMENT: [
                CallbackQueryHandler(review_enter_comment, pattern="^skip_comment$"),
                CallbackQueryHandler(review_enter_comment),
                MessageHandler(filters.TEXT & ~filters.COMMAND, review_comment_message)
            ],
            CONFIRM_REVIEW: [
                CallbackQueryHandler(review_submit, pattern="^confirm_review$"),
                CallbackQueryHandler(review_submit, pattern="^cancel_review$")
            ]
        },
        fallbacks=[
            CallbackQueryHandler(review_cmd, pattern="^cancel_review$")
        ],
        allow_reentry=True
    )
    
    application.add_handler(review_conv)
