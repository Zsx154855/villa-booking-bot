"""
帮助中心处理器 - /help
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# ============ 帮助命令 ============
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """帮助命令"""
    help_text = (
        "📋 *Taimili别墅预订 - 帮助中心*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🛠️ *常用命令：*\n"
        "/start - 开始使用\n"
        "/help - 查看帮助（当前）\n"
        "/villas - 浏览所有别墅\n"
        "/villas 芭提雅 - 查看特定地区别墅\n"
        "/villa 编号 - 查看别墅详情（如 /villa PAT001）\n"
        "/check 日期 - 查询可用别墅\n"
        "/book - 开始预订流程\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "👤 *会员命令：*\n"
        "/profile - 我的用户画像\n"
        "/mybookings - 查看我的预订\n"
        "/coupons - 我的优惠券\n"
        "/points - 积分查询\n"
        "/redeem 促销码 - 兑换优惠券\n"
        "/review - 发表评价\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 *预订提示：*\n"
        "• 日期格式：YYYY-MM-DD\n"
        "• 别墅编号：如 PAT001、BKK002 等\n"
        "• 使用 /help faq 查看常见问题"
    )
    
    keyboard = [
        [InlineKeyboardButton("📖 常见问题 FAQ", callback_data="cmd_faq")],
        [InlineKeyboardButton("📞 联系客服", callback_data="cmd_contact")],
        [InlineKeyboardButton("🏠 返回主菜单", callback_data="main_menu")]
    ]
    
    if update.message:
        await update.message.reply_text(
            help_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            help_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def faq_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """常见问题"""
    faq_text = (
        "📖 *常见问题 FAQ*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🏷️ *关于预订*\n\n"
        "Q: 如何预订别墅？\n"
        "A: 使用 /book 命令，按照提示选择地区、别墅和日期即可完成预订。\n\n"
        "Q: 预订后多久确认？\n"
        "A: 客服将在24小时内与您联系确认订单。\n\n"
        "Q: 如何取消预订？\n"
        "A: 在订单确认前可自助取消，已确认订单请联系客服处理。\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "💰 *关于支付*\n\n"
        "Q: 支持哪些支付方式？\n"
        "A: 支持支付宝、微信支付、银行卡转账等多种方式。\n\n"
        "Q: 预订需要支付定金吗？\n"
        "A: 是的，确认预订需支付总价的30%作为定金。\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🏠 *关于别墅*\n\n"
        "Q: 入住和退房时间？\n"
        "A: 标准入住时间为15:00，退房时间为11:00。\n\n"
        "Q: 包含早餐吗？\n"
        "A: 部分别墅含早餐，详情请查看别墅介绍或咨询客服。\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🚗 *关于交通*\n\n"
        "Q: 提供接机服务吗？\n"
        "A: 是的，金卡及以上会员可享受免费接机服务，其他用户可付费预约。\n\n"
        "Q: 别墅距离机场多远？\n"
        "A: 各别墅位置不同，具体请查看别墅详情或咨询客服。\n\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("📋 所有命令", callback_data="cmd_help")],
        [InlineKeyboardButton("📞 联系客服", callback_data="cmd_contact")],
        [InlineKeyboardButton("🔙 返回主菜单", callback_data="main_menu")]
    ]
    
    if update.message:
        await update.message.reply_text(
            faq_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            faq_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


def register_help_handlers(application):
    """注册帮助相关处理器"""
    from telegram.ext import CommandHandler, CallbackQueryHandler
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("faq", faq_cmd))
    application.add_handler(CallbackQueryHandler(help_cmd, pattern="^cmd_help$"))
    application.add_handler(CallbackQueryHandler(faq_cmd, pattern="^cmd_faq$"))
