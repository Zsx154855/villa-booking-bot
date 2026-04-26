"""
促销码兑换处理器 - /redeem
"""
import logging
import hashlib
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

logger = logging.getLogger(__name__)

# 导入数据库模块
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database

# ============ 兑换状态 ============
(ENTER_CODE,) = range(1)

# ============ 促销码兑换命令 ============
async def redeem_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """促销码兑换命令"""
    try:
        # 检查是否有参数直接传入
        if update.message and context.args:
            code = context.args[0].strip().upper()
            return await process_redeem_code(update, context, code)
        
        # 无参数时进入交互式输入
        text = (
            "🎁 *促销码兑换*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "请输入您获得的促销码进行兑换\n\n"
            "📝 输入格式：促销码（如 SUMMER2026）\n\n"
            "💡 促销码可在以下渠道获取：\n"
            "• 活动页面\n"
            "• 客服赠送\n"
            "• 会员积分兑换\n"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔙 返回主菜单", callback_data="main_menu")]
        ]
        
        if update.message:
            await update.message.reply_text(
                text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ENTER_CODE
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ENTER_CODE
            
    except Exception as e:
        logger.error(f"促销码兑换命令失败: {e}")
        error_text = "❌ 系统错误，请稍后重试"
        if update.message:
            await update.message.reply_text(error_text)
        elif update.callback_query:
            await update.callback_query.edit_message_text(error_text)
        return ConversationHandler.END


async def process_redeem_code(update: Update, context: ContextTypes.DEFAULT_TYPE, code: str):
    """处理促销码兑换"""
    try:
        # 验证促销码
        result = _validate_promo_code(code)
        
        if not result['valid']:
            keyboard = [
                [InlineKeyboardButton("🔙 返回主菜单", callback_data="main_menu")]
            ]
            await update.message.reply_text(
                f"❌ *兑换失败*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"促销码 `{code}` 无效或已过期\n\n"
                f"请检查后重新输入或联系客服",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ConversationHandler.END
        
        # 兑换成功
        user_id = update.message.from_user.id
        coupon = result['coupon']
        
        success_text = (
            "🎉 *兑换成功！*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✨ 恭喜您获得：\n"
            f"🎫 *{coupon['name']}*\n\n"
            f"💰 优惠内容：减免 ฿{coupon['discount']:,.0f}\n"
            f"📋 使用条件：满 ฿{coupon['min_amount']:,.0f}\n"
            f"📅 有效期至：{coupon['expire_date']}\n\n"
            f"💡 优惠券已存入您的账户\n"
            f"📋 请在预订时使用"
        )
        
        keyboard = [
            [InlineKeyboardButton("🎟️ 查看我的优惠券", callback_data="cmd_coupons")],
            [InlineKeyboardButton("📝 立即预订", callback_data="cmd_book")],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data="main_menu")]
        ]
        
        logger.info(f"用户 {user_id} 成功兑换促销码 {code}")
        
        if update.message:
            await update.message.reply_text(
                success_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                success_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"处理促销码失败: {e}")
        await update.message.reply_text("❌ 兑换处理失败，请稍后重试")
        return ConversationHandler.END


def _validate_promo_code(code: str) -> dict:
    """验证促销码"""
    # 示例促销码库（实际应从数据库获取）
    promo_codes = {
        'SUMMER2026': {
            'name': '夏季特惠券',
            'discount': 300,
            'min_amount': 1500,
            'expire_date': '2026-08-31',
            'type': 'coupon',
            'description': '夏季专属优惠'
        },
        'WELCOME50': {
            'name': '欢迎礼券',
            'discount': 200,
            'min_amount': 1000,
            'expire_date': '2026-12-31',
            'type': 'coupon',
            'description': '新用户专享'
        },
        'VIP1000': {
            'name': 'VIP专属券',
            'discount': 500,
            'min_amount': 2000,
            'expire_date': '2026-12-31',
            'type': 'coupon',
            'description': '会员专属福利'
        },
        'HOLIDAY666': {
            'name': '假日狂欢券',
            'discount': 666,
            'min_amount': 3000,
            'expire_date': '2026-10-07',
            'type': 'coupon',
            'description': '国庆假日特惠'
        },
        'POINTS50': {
            'name': '积分奖励',
            'discount': 0,
            'min_amount': 0,
            'expire_date': '2026-12-31',
            'type': 'points',
            'points': 500,
            'description': '奖励500积分'
        }
    }
    
    # 标准化输入
    code = code.strip().upper()
    
    if code not in promo_codes:
        return {'valid': False, 'reason': 'invalid_code'}
    
    promo = promo_codes[code]
    
    # 检查是否过期
    try:
        expire_date = datetime.strptime(promo['expire_date'], '%Y-%m-%d')
        if expire_date < datetime.now():
            return {'valid': False, 'reason': 'expired'}
    except:
        pass
    
    return {
        'valid': True,
        'coupon': promo
    }


def register_redeem_handlers(application):
    """注册促销码兑换相关处理器"""
    from telegram.ext import CommandHandler, ConversationHandler, MessageHandler
    
    redeem_conv = ConversationHandler(
        entry_points=[CommandHandler("redeem", redeem_cmd)],
        states={
            ENTER_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, redeem_cmd)
            ]
        },
        fallbacks=[],
        allow_reentry=True
    )
    
    application.add_handler(redeem_conv)
