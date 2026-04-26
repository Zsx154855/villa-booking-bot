"""
优惠券处理器 - /coupons
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

# ============ 优惠券命令 ============
async def coupons_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """我的优惠券命令"""
    try:
        user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id
        
        # 模拟优惠券数据（实际应从数据库获取）
        coupons = _get_user_coupons(str(user_id))
        
        if not coupons:
            keyboard = [
                [InlineKeyboardButton("🎁 领取优惠券", callback_data="cmd_claim_coupon")],
                [InlineKeyboardButton("🔙 返回主菜单", callback_data="main_menu")]
            ]
            text = (
                "🎟️ *我的优惠券*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "😔 您还没有优惠券\n\n"
                "快去领取优惠吧！"
            )
        else:
            # 按状态分组
            available = [c for c in coupons if c['status'] == 'available']
            used = [c for c in coupons if c['status'] == 'used']
            expired = [c for c in coupons if c['status'] == 'expired']
            
            text = (
                "🎟️ *我的优惠券*\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📊 优惠券概览\n"
                f"• 可用：{len(available)} 张\n"
                f"• 已使用：{len(used)} 张\n"
                f"• 已过期：{len(expired)} 张\n\n"
            )
            
            keyboard = []
            
            # 显示可用优惠券
            if available:
                text += "✨ *可用优惠券*\n\n"
                for i, coupon in enumerate(available, 1):
                    discount = coupon.get('discount', 0)
                    min_amount = coupon.get('min_amount', 0)
                    expire_date = coupon.get('expire_date', '')
                    
                    text += (
                        f"{i}. 🎫 {coupon['name']}\n"
                        f"   优惠：减免 ฿{discount:,.0f}\n"
                        f"   条件：满 ฿{min_amount:,.0f} 使用\n"
                        f"   有效期：{expire_date}\n\n"
                    )
            
            # 显示已使用优惠券
            if used:
                text += "✅ *已使用*\n\n"
                for coupon in used[:3]:
                    text += f"• {coupon['name']}\n"
                if len(used) > 3:
                    text += f"• ...等{len(used)}张\n"
                text += "\n"
            
            keyboard.append([InlineKeyboardButton("🎁 领取更多优惠券", callback_data="cmd_claim_coupon")])
        
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
        logger.error(f"加载优惠券失败: {e}")
        error_text = "❌ 加载优惠券失败，请稍后重试"
        if update.message:
            await update.message.reply_text(error_text)
        elif update.callback_query:
            await update.callback_query.edit_message_text(error_text)


def _get_user_coupons(user_id: str) -> list:
    """获取用户优惠券（模拟数据）"""
    # 实际应从数据库获取
    today = datetime.now().strftime('%Y-%m-%d')
    
    coupons = [
        {
            'id': 'CP001',
            'name': '新用户专享券',
            'discount': 200,
            'min_amount': 1000,
            'expire_date': '2026-12-31',
            'status': 'available',
            'description': '首次预订满1000铢立减200铢'
        },
        {
            'id': 'CP002',
            'name': '夏季清凉券',
            'discount': 150,
            'min_amount': 800,
            'expire_date': '2026-06-30',
            'status': 'available',
            'description': '夏季特惠，满800铢减150铢'
        },
        {
            'id': 'CP003',
            'name': '会员专属券',
            'discount': 300,
            'min_amount': 1500,
            'expire_date': '2026-05-15',
            'status': 'available',
            'description': '金卡会员专享，满1500铢减300铢'
        },
        {
            'id': 'CP004',
            'name': '早鸟优惠券',
            'discount': 100,
            'min_amount': 500,
            'expire_date': '2026-03-01',
            'status': 'used',
            'description': '提前30天预订可使用'
        },
        {
            'id': 'CP005',
            'name': '春节特惠券',
            'discount': 500,
            'min_amount': 3000,
            'expire_date': '2026-02-15',
            'status': 'expired',
            'description': '春节期间的特别优惠'
        }
    ]
    
    return coupons


def register_coupons_handlers(application):
    """注册优惠券相关处理器"""
    from telegram.ext import CommandHandler, CallbackQueryHandler
    application.add_handler(CommandHandler("coupons", coupons_cmd))
    application.add_handler(CallbackQueryHandler(coupons_cmd, pattern="^cmd_coupons$"))
