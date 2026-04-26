#!/usr/bin/env python3
"""Taimili Villa Booking Telegram Bot v4.0 - SQLite Database Version"""

import os
import json
import logging
import asyncio
import threading
import uuid
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

# 导入数据库模块
import database

# 导入handlers模块
from handlers import (
    profile_cmd, register_profile_handlers,
    mybookings_cmd, mybookings_detail_cmd, register_mybookings_handlers,
    coupons_cmd, register_coupons_handlers,
    points_cmd, register_points_handlers,
    redeem_cmd, register_redeem_handlers,
    review_cmd, review_submit, register_review_handlers,
    help_cmd, faq_cmd, register_help_handlers
)

# 导入支付处理模块
from src.services.payment.handlers import (
    pay_command, check_payment_status, handle_stripe_webhook,
    get_payment_button, format_payment_message
)

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============ 配置 ============
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Missing required environment variable: TELEGRAM_BOT_TOKEN")

PORT = int(os.environ.get('PORT', 8080))
DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# ============ 预订状态 ============
(
    SELECT_REGION, SELECT_CHECKIN, SELECT_CHECKOUT, 
    SELECT_VILLA, ENTER_GUESTS, ENTER_CONTACT,
    CONFIRM_BOOKING
) = range(7)

# ============ 地区配置 ============
REGIONS = ["芭提雅", "曼谷", "普吉岛"]
REGION_EMOJI = {"芭提雅": "🏖️", "曼谷": "🏙️", "普吉岛": "🏝️"}

# ============ 数据库初始化 ============
def init_database():
    """初始化数据库"""
    try:
        database.init_db()
        logger.info("✅ 数据库初始化成功")
        
        # 检查是否有数据
        villas = database.get_all_villas()
        if not villas:
            logger.warning("⚠️ 数据库中没有别墅数据，请运行 migrate.py 迁移数据")
        else:
            logger.info(f"📊 数据库中有 {len(villas)} 套别墅")
            
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")

# ============ 辅助函数 ============
def load_villas():
    """加载别墅数据（兼容旧接口）"""
    try:
        return database.get_all_villas()
    except Exception as e:
        logger.error(f"加载别墅数据失败: {e}")
        return []

def save_booking(booking):
    """保存预订记录"""
    # 转换格式以匹配新数据库结构
    booking_data = {
        'id': booking.get('id'),
        'user_id': str(booking.get('user_id')),
        'villa_id': booking.get('villa_id'),
        'villa_name': booking.get('villa_name'),
        'villa_region': booking.get('villa_region'),
        'checkin': booking.get('checkin'),
        'checkout': booking.get('checkout'),
        'guests': booking.get('guests', 1),
        'contact_name': booking.get('contact_name'),
        'contact_phone': booking.get('contact_phone'),
        'contact_note': booking.get('contact_note', ''),
        'price_per_night': booking.get('price_per_night', 0),
        'total_price': booking.get('total_price', 0),
        'status': booking.get('status', 'pending')
    }
    return database.create_booking(booking_data)

def load_bookings():
    """加载预订记录（兼容旧接口）"""
    try:
        # 返回所有预订记录（用于全局查询）
        # 注意：这个函数在原代码中是全局加载，新版本需要优化
        return []
    except Exception as e:
        logger.error(f"加载预订记录失败: {e}")
        return []

def get_user_bookings(user_id):
    """获取用户的预订记录"""
    try:
        return database.get_user_bookings(str(user_id))
    except Exception as e:
        logger.error(f"获取用户预订失败: {e}")
        return []

def format_price(price):
    """格式化价格"""
    return f"฿{price:,}"

def calculate_nights(checkin, checkout):
    """计算住宿天数"""
    try:
        d1 = datetime.strptime(checkin, "%Y-%m-%d")
        d2 = datetime.strptime(checkout, "%Y-%m-%d")
        return (d2 - d1).days
    except:
        return 0

def is_date_available(villa_id, checkin, checkout, exclude_booking_id=None):
    """检查别墅在指定日期是否可用"""
    return database.check_availability(villa_id, checkin, checkout, exclude_booking_id)

# ============ HTTP健康检查 ============
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        # 获取数据库健康状态
        db_health = database.health_check()
        response = {
            "status": "ok",
            "bot": "Taimili Villa Booking Bot v4.0 (SQLite)",
            "database": db_health['status'],
            "villas_count": db_health['record_counts'].get('villas', 0),
            "bookings_count": db_health['record_counts'].get('bookings', 0),
            "new_features": ["用户画像", "优惠券", "积分系统", "促销码兑换", "评价系统"]
        }
        self.wfile.write(json.dumps(response, ensure_ascii=False).encode())
    
    def log_message(self, format, *args):
        pass

def run_http_server():
    server = HTTPServer(('0.0.0.0', PORT), HealthHandler)
    logger.info(f"HTTP健康检查服务器启动: 端口 {PORT}")
    server.serve_forever()

# ============ 通用键盘 ============
def get_main_menu_keyboard():
    """主菜单键盘"""
    keyboard = [
        [InlineKeyboardButton("🏠 浏览别墅", callback_data="cmd_villas")],
        [InlineKeyboardButton("📅 查询可用", callback_data="cmd_check")],
        [InlineKeyboardButton("📝 开始预订", callback_data="cmd_book")],
        [InlineKeyboardButton("📋 我的预订", callback_data="cmd_mybookings")],
        [InlineKeyboardButton("📞 联系客服", callback_data="cmd_contact")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_region_keyboard():
    """地区选择键盘"""
    keyboard = []
    for region in REGIONS:
        emoji = REGION_EMOJI.get(region, "📍")
        keyboard.append([InlineKeyboardButton(
            f"{emoji} {region}", 
            callback_data=f"region_{region}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 返回主菜单", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard():
    """返回键盘"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 返回主菜单", callback_data="main_menu")]
    ])

def get_cancel_keyboard():
    """取消键盘"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ 取消预订", callback_data="cancel_booking")]
    ])

def get_confirm_keyboard():
    """确认键盘"""
    keyboard = [
        [
            InlineKeyboardButton("✅ 确认预订", callback_data="confirm_yes"),
            InlineKeyboardButton("❌ 取消", callback_data="confirm_no")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ 命令处理器 ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """开始命令"""
    welcome_text = (
        "🏠 *欢迎来到Taimili别墅预订助手！*\n\n"
        "我们提供泰国三大热门旅游地区的精品别墅预订服务：\n"
        "• 🏖️ 芭提雅 - 海滨度假\n"
        "• 🏙️ 曼谷 - 都市风情\n"
        "• 🏝️ 普吉岛 - 海岛风光\n\n"
        "请选择您需要的服务："
    )
    
    if update.message:
        await update.message.reply_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=get_main_menu_keyboard()
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=get_main_menu_keyboard()
        )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """帮助命令"""
    help_text = (
        "📋 *使用帮助*\n\n"
        "🛠️ *常用命令：*\n"
        "/start - 开始使用\n"
        "/help - 查看帮助\n"
        "/villas - 浏览所有别墅\n"
        "/villas 芭提雅 - 查看特定地区别墅\n"
        "/villa 编号 - 查看别墅详情（如 /villa PAT001）\n"
        "/check 日期 - 查询可用别墅（如 /check 2026-06-15）\n"
        "/book - 开始预订流程\n"
        "/mybookings - 查看我的预订\n"
        "/contact - 联系客服\n\n"
        "💡 *预订提示：*\n"
        "• 日期格式：YYYY-MM-DD\n"
        "• 别墅编号：如 PAT001、BKK002 等"
    )
    
    if update.message:
        await update.message.reply_text(help_text, parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.edit_message_text(help_text, parse_mode='Markdown')

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """别墅信息（简化版）"""
    villas = load_villas()
    if not villas:
        await update.message.reply_text("❌ 暂无可用别墅数据")
        return
    
    regions_count = {}
    for v in villas:
        r = v.get('region', '未知')
        regions_count[r] = regions_count.get(r, 0) + 1
    
    info_text = (
        "🏠 *Taimili度假别墅*\n\n"
        "📍 *覆盖地区：*\n"
    )
    for region in REGIONS:
        count = regions_count.get(region, 0)
        emoji = REGION_EMOJI.get(region, "📍")
        info_text += f"{emoji} {region}：{count}套别墅\n"
    
    info_text += (
        "\n🛏️ *房型选择：*\n"
        "• 独栋别墅 · 家庭套房 · 顶层套房\n"
        "• 精品公寓 · 泰式庭院\n\n"
        "✨ *特色服务：*\n"
        "• 私人泳池 · 海景/河景\n"
        "• 管家服务 · 机场接送\n"
        "• 中文服务 · 24小时客服\n\n"
        "使用 /villas 查看所有别墅详情"
    )
    
    if update.message:
        await update.message.reply_text(info_text, parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.edit_message_text(info_text, parse_mode='Markdown')

async def villas_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """浏览别墅命令"""
    villas = load_villas()
    if not villas:
        await update.message.reply_text("❌ 暂无可用别墅数据")
        return
    
    # 检查是否有地区参数
    region_filter = None
    if update.message and context.args:
        region_input = context.args[0]
        for region in REGIONS:
            if region in region_input:
                region_filter = region
                break
    
    if region_filter:
        filtered = [v for v in villas if v.get('region') == region_filter]
        if not filtered:
            await update.message.reply_text(f"❌ {region_filter}暂无别墅数据")
            return
        await show_villa_list(update, filtered, region_filter)
    else:
        # 显示地区选择菜单
        await show_region_selection(update)

async def show_region_selection(update: Update):
    """显示地区选择"""
    text = (
        "🌍 *选择您想浏览的地区*\n\n"
        "请选择一个地区，查看该地区的所有别墅："
    )
    
    keyboard = get_region_keyboard()
    
    if update.message:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=keyboard)
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)

async def show_villa_list(update: Update, villas: list, region: str = None):
    """显示别墅列表"""
    emoji = REGION_EMOJI.get(region, "🏠") if region else "🏠"
    
    header = f"{emoji} *别墅列表*\n" if region else "🏠 *全部别墅*\n"
    header += f"共 {len(villas)} 套别墅\n\n"
    
    for i, villa in enumerate(villas, 1):
        name = villa.get('name', '未命名')
        villa_id = villa.get('id', '')
        price = format_price(villa.get('price_per_night', 0))
        bedrooms = villa.get('bedrooms', 0)
        guests = villa.get('max_guests', 0)
        
        header += f"{i}. *{name}*\n"
        header += f"   🏷️ 编号：{villa_id} | 🛏️ {bedrooms}卧 | 👤 可住{guests}人\n"
        header += f"   💰 {price}/晚\n\n"
    
    header += "📝 输入 /villa <编号> 查看详情\n"
    header += "例如：/villa PAT001"
    
    keyboard = get_region_keyboard()
    
    if update.message:
        await update.message.reply_text(header, parse_mode='Markdown', reply_markup=keyboard)
    elif update.callback_query:
        await update.callback_query.edit_message_text(header, parse_mode='Markdown', reply_markup=keyboard)

async def villa_detail_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """别墅详情命令"""
    if not update.message or not context.args:
        await update.message.reply_text(
            "📝 请输入别墅编号查看详情\n"
            "例如：/villa PAT001"
        )
        return
    
    villa_id = context.args[0].upper()
    villa = database.get_villa(villa_id)
    
    if not villa:
        await update.message.reply_text(
            f"❌ 未找到编号为 {villa_id} 的别墅\n"
            "请输入正确的别墅编号"
        )
        return
    
    await show_villa_detail(update, villa)

async def show_villa_detail(update: Update, villa: dict, reply_to_message_id: int = None):
    """显示别墅详情"""
    name = villa.get('name', '未命名')
    villa_id = villa.get('id', '')
    region = villa.get('region', '')
    room_type = villa.get('room_type') or villa.get('type', '')
    price = format_price(villa.get('price_per_night', 0))
    bedrooms = villa.get('bedrooms', 0)
    bathrooms = villa.get('bathrooms', 0)
    max_guests = villa.get('max_guests', 0)
    amenities = villa.get('amenities', [])
    description = villa.get('description', '')
    emoji = REGION_EMOJI.get(region, "📍")
    
    detail_text = (
        f"{emoji} *{name}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏷️ 编号：{villa_id}\n"
        f"📍 地区：{region} | {room_type}\n"
        f"💰 价格：{price}/晚\n\n"
        f"🛏️ 卧室：{bedrooms}间 | 🚿 卫生间：{bathrooms}间\n"
        f"👤 最大入住：{max_guests}人\n\n"
        f"📝 *简介：*\n{description}\n\n"
    )
    
    if amenities:
        detail_text += "✨ *设施：*\n"
        if isinstance(amenities, list):
            detail_text += " • " + "\n • ".join(amenities[:8])
            if len(amenities) > 8:
                detail_text += f"\n • ...等{len(amenities)}项设施"
        else:
            detail_text += str(amenities)
    
    # 添加预订按钮
    keyboard = [
        [InlineKeyboardButton("📝 立即预订", callback_data=f"book_villa_{villa_id}")],
        [InlineKeyboardButton("🔙 返回别墅列表", callback_data=f"region_{region}")]
    ]
    
    if update.message:
        await update.message.reply_text(
            detail_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            detail_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True
        )

async def check_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查询可用别墅命令"""
    if not update.message or not context.args:
        await update.message.reply_text(
            "📅 请输入要查询的日期\n"
            "格式：/check 2026-06-15\n\n"
            "可同时查询日期范围：\n"
            "/check 2026-06-15 2026-06-18"
        )
        return
    
    try:
        checkin = context.args[0]
        checkout = context.args[1] if len(context.args) > 1 else None
        
        # 验证日期格式
        datetime.strptime(checkin, "%Y-%m-%d")
        if checkout:
            datetime.strptime(checkout, "%Y-%m-%d")
    except ValueError:
        await update.message.reply_text(
            "❌ 日期格式错误\n"
            "请使用格式：YYYY-MM-DD\n"
            "例如：/check 2026-06-15"
        )
        return
    
    if checkout is None:
        # 单日查询，假设住一晚
        checkout_date = datetime.strptime(checkin, "%Y-%m-%d") + timedelta(days=1)
        checkout = checkout_date.strftime("%Y-%m-%d")
    
    # 检查日期合理性
    checkin_date = datetime.strptime(checkin, "%Y-%m-%d")
    checkout_date = datetime.strptime(checkout, "%Y-%m-%d")
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if checkin_date < today:
        await update.message.reply_text("❌ 入住日期不能是过去的时间")
        return
    
    if checkout_date <= checkin_date:
        await update.message.reply_text("❌ 退房日期必须晚于入住日期")
        return
    
    # 查找可用别墅（使用数据库）
    available = database.find_available_villas(checkin, checkout)
    
    if not available:
        await update.message.reply_text(
            f"😔 很抱歉，{checkin} 至 {checkout} 期间\n"
            "暂无空房，请选择其他日期或地区"
        )
        return
    
    # 按地区分组显示
    nights = calculate_nights(checkin, checkout)
    
    response = (
        f"📅 *入住：*{checkin}\n"
        f"📅 *退房：*{checkout} （共{nights}晚）\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎉 找到 {len(available)} 套可用别墅：\n\n"
    )
    
    for villa in available:
        name = villa.get('name', '未命名')
        villa_id = villa.get('id', '')
        region = villa.get('region', '')
        emoji = REGION_EMOJI.get(region, "📍")
        price = format_price(villa.get('price_per_night', 0))
        total = format_price(villa.get('price_per_night', 0) * nights)
        
        response += (
            f"{emoji} *{name}*\n"
            f"   🏷️ {villa_id} | {price}/晚 | 合计 {total}\n\n"
        )
    
    response += "📝 输入 /villa <编号> 查看详情\n"
    response += "例如：/villa PAT001"
    
    keyboard = [
        [InlineKeyboardButton("📝 开始预订", callback_data="cmd_book")],
        [InlineKeyboardButton("🔙 重新查询日期", callback_data="cmd_check")]
    ]
    
    await update.message.reply_text(
        response,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True
    )

async def mybookings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """我的预订命令"""
    user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id
    bookings = get_user_bookings(user_id)
    
    if not bookings:
        keyboard = [
            [InlineKeyboardButton("📝 去预订", callback_data="cmd_book")]
        ]
        await update.message.reply_text(
            "📋 您还没有任何预订记录",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # 显示预订列表
    response = f"📋 *您的预订记录*\n共 {len(bookings)} 条\n━━━━━━━━━━━━━━━━━━━━\n\n"
    
    keyboard = []
    
    for i, booking in enumerate(bookings, 1):
        villa_id = booking.get('villa_id', '')
        villa_name = booking.get('villa_name', villa_id)
        checkin = booking.get('checkin', '')
        checkout = booking.get('checkout', '')
        status = booking.get('status', 'pending')
        nights = calculate_nights(checkin, checkout)
        
        status_emoji = {
            'pending': '⏳',
            'confirmed': '✅',
            'cancelled': '❌',
            'completed': '🏁'
        }.get(status, '❓')
        
        status_text = {
            'pending': '待确认',
            'confirmed': '已确认',
            'cancelled': '已取消',
            'completed': '已完成'
        }.get(status, '未知')
        
        response += (
            f"{i}. {status_emoji} *{villa_name}*\n"
            f"   📅 {checkin} → {checkout} ({nights}晚)\n"
            f"   📌 状态：{status_text}\n\n"
        )
    
    keyboard.append([InlineKeyboardButton("🔙 返回主菜单", callback_data="main_menu")])
    
    if update.message:
        await update.message.reply_text(response, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    elif update.callback_query:
        await update.callback_query.edit_message_text(response, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def contact_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """联系客服命令"""
    contact_text = (
        "📞 *联系我们*\n\n"
        "🏢 *Taimili度假别墅*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "💬 *在线客服：*\n"
        "@TaimiliSupport（优先回复）\n\n"
        "📱 *电话：*\n"
        "+66 2 XXX XXXX（泰国）\n"
        "+86 400 XXX XXXX（中国）\n\n"
        "📧 *邮箱：*\n"
        "booking@taimili.com\n\n"
        "🕐 *服务时间：*\n"
        "24小时中文客服\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "✨ 我们随时为您服务！"
    )
    
    keyboard = get_back_keyboard()
    
    if update.message:
        await update.message.reply_text(contact_text, parse_mode='Markdown', reply_markup=keyboard)
    elif update.callback_query:
        await update.callback_query.edit_message_text(contact_text, parse_mode='Markdown', reply_markup=keyboard)

# ============ 预订流程 ============
async def book_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """开始预订命令"""
    context.user_data.clear()
    
    keyboard = get_region_keyboard()
    
    text = (
        "📝 *开始预订流程*\n\n"
        "请选择您想预订别墅的地区："
    )
    
    await update.callback_query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=keyboard
    ) if update.callback_query else await update.message.reply_text(
        text,
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    
    return SELECT_REGION

async def book_select_region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """预订 - 选择地区"""
    query = update.callback_query
    await query.answer()
    
    region = query.data.replace("region_", "")
    context.user_data['region'] = region
    
    villas = database.get_villas_by_region(region)
    
    if not villas:
        await query.edit_message_text(
            f"❌ {region}暂无别墅数据，请选择其他地区",
            reply_markup=get_region_keyboard()
        )
        return SELECT_REGION
    
    emoji = REGION_EMOJI.get(region, "📍")
    text = f"{emoji} *{region}别墅列表*\n\n请选择您想要的别墅："
    
    keyboard = []
    for villa in villas:
        name = villa.get('name', '')
        villa_id = villa.get('id', '')
        price = format_price(villa.get('price_per_night', 0))
        bedrooms = villa.get('bedrooms', 0)
        max_guests = villa.get('max_guests', 0)
        
        keyboard.append([InlineKeyboardButton(
            f"🏠 {name} | {price}/晚 | {bedrooms}卧",
            callback_data=f"select_villa_{villa_id}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 重选地区", callback_data="cmd_book")])
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_VILLA

async def book_select_villa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """预订 - 选择别墅"""
    query = update.callback_query
    await query.answer()
    
    villa_id = query.data.replace("select_villa_", "")
    villa = database.get_villa(villa_id)
    
    if not villa:
        await query.edit_message_text("❌ 未找到该别墅", reply_markup=get_back_keyboard())
        return ConversationHandler.END
    
    context.user_data['villa_id'] = villa_id
    context.user_data['villa'] = villa
    
    # 显示别墅详情并要求输入日期
    emoji = REGION_EMOJI.get(villa.get('region', ''), "📍")
    text = (
        f"{emoji} *{villa.get('name')}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏷️ 编号：{villa_id}\n"
        f"💰 {format_price(villa.get('price_per_night', 0))}/晚\n"
        f"🛏️ {villa.get('bedrooms', 0)}卧 | 👤 可住{villa.get('max_guests', 0)}人\n\n"
        f"📅 *请输入入住日期*\n"
        f"格式：YYYY-MM-DD\n\n"
        f"例如：2026-06-15"
    )
    
    keyboard = [
        [InlineKeyboardButton("❌ 取消预订", callback_data="cancel_booking")]
    ]
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECT_CHECKIN

async def book_enter_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """预订 - 输入入住日期"""
    checkin_str = update.message.text.strip()
    
    try:
        checkin_date = datetime.strptime(checkin_str, "%Y-%m-%d")
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if checkin_date < today:
            await update.message.reply_text("❌ 入住日期不能是过去的时间，请重新输入：")
            return SELECT_CHECKIN
        
        context.user_data['checkin'] = checkin_str
        
        text = (
            f"✅ 入住日期：{checkin_str}\n\n"
            f"📅 *请输入退房日期*\n"
            f"格式：YYYY-MM-DD\n\n"
            f"例如：2026-06-18"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=get_cancel_keyboard())
        return SELECT_CHECKOUT
        
    except ValueError:
        await update.message.reply_text(
            "❌ 日期格式错误\n"
            "请使用格式：YYYY-MM-DD\n"
            "例如：2026-06-15"
        )
        return SELECT_CHECKIN

async def book_enter_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """预订 - 输入退房日期"""
    checkout_str = update.message.text.strip()
    checkin_str = context.user_data.get('checkin', '')
    villa_id = context.user_data.get('villa_id', '')
    
    try:
        checkout_date = datetime.strptime(checkout_str, "%Y-%m-%d")
        checkin_date = datetime.strptime(checkin_str, "%Y-%m-%d")
        
        if checkout_date <= checkin_date:
            await update.message.reply_text("❌ 退房日期必须晚于入住日期，请重新输入：")
            return SELECT_CHECKOUT
        
        # 检查是否可用（使用数据库）
        if not is_date_available(villa_id, checkin_str, checkout_str):
            await update.message.reply_text(
                "❌ 很抱歉，该别墅在您选择的日期已被预订\n"
                "请选择其他日期或其他别墅",
                reply_markup=get_cancel_keyboard()
            )
            return SELECT_CHECKOUT
        
        context.user_data['checkout'] = checkout_str
        
        # 计算总价
        villa = context.user_data.get('villa', {})
        price_per_night = villa.get('price_per_night', 0)
        nights = calculate_nights(checkin_str, checkout_str)
        total_price = price_per_night * nights
        
        emoji = REGION_EMOJI.get(villa.get('region', ''), "📍")
        
        text = (
            f"✅ 日期确认：\n"
            f"📅 入住：{checkin_str}\n"
            f"📅 退房：{checkout_str}（共{nights}晚）\n\n"
            f"{emoji} *请输入入住人数*\n"
            f"最多可住 {villa.get('max_guests', 0)} 人\n\n"
            f"直接输入数字，例如：2"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=get_cancel_keyboard())
        return ENTER_GUESTS
        
    except ValueError:
        await update.message.reply_text(
            "❌ 日期格式错误\n"
            "请使用格式：YYYY-MM-DD\n"
            "例如：2026-06-18"
        )
        return SELECT_CHECKOUT

async def book_enter_guests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """预订 - 输入入住人数"""
    try:
        guests = int(update.message.text.strip())
        villa = context.user_data.get('villa', {})
        max_guests = villa.get('max_guests', 0)
        
        if guests < 1:
            await update.message.reply_text("❌ 入住人数必须至少1人，请重新输入：")
            return ENTER_GUESTS
        
        if guests > max_guests:
            await update.message.reply_text(
                f"❌ 该别墅最多可住 {max_guests} 人\n"
                f"请重新输入（1-{max_guests}）："
            )
            return ENTER_GUESTS
        
        context.user_data['guests'] = guests
        
        text = (
            f"✅ 入住人数：{guests}人\n\n"
            f"📝 *请输入联系人信息*\n\n"
            f"格式：\n"
            f"姓名：XXX\n"
            f"电话：XXX-XXXX-XXXX\n"
            f"备注：（可选）\n\n"
            f"例如：\n"
            f"姓名：张三\n"
            f"电话：138-1234-5678\n"
            f"备注：需要加床"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=get_cancel_keyboard())
        return ENTER_CONTACT
        
    except ValueError:
        await update.message.reply_text("❌ 请输入有效的数字：")
        return ENTER_GUESTS

async def book_enter_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """预订 - 输入联系人信息"""
    contact_text = update.message.text.strip()
    
    # 简单验证
    if len(contact_text) < 5:
        await update.message.reply_text("❌ 信息不完整，请重新输入：")
        return ENTER_CONTACT
    
    # 解析联系人信息
    contact_info = {
        'raw': contact_text,
        'name': '',
        'phone': '',
        'note': ''
    }
    
    lines = contact_text.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('姓名'):
            contact_info['name'] = line.split('：')[-1].strip()
        elif line.startswith('电话'):
            contact_info['phone'] = line.split('：')[-1].strip()
        elif line.startswith('备注'):
            contact_info['note'] = line.split('：')[-1].strip()
    
    if not contact_info['name']:
        # 尝试从第一行获取
        for line in lines:
            line = line.strip()
            if line and ':' not in line and '：' not in line and len(line) >= 2:
                contact_info['name'] = line
                break
    
    context.user_data['contact'] = contact_info
    
    # 显示确认信息
    villa = context.user_data.get('villa', {})
    region = villa.get('region', '')
    emoji = REGION_EMOJI.get(region, "📍")
    price_per_night = villa.get('price_per_night', 0)
    checkin = context.user_data.get('checkin', '')
    checkout = context.user_data.get('checkout', '')
    guests = context.user_data.get('guests', 0)
    nights = calculate_nights(checkin, checkout)
    total_price = price_per_night * nights
    
    confirm_text = (
        f"📋 *请确认预订信息*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{emoji} *别墅：*{villa.get('name', '')}\n"
        f"🏷️ 编号：{villa.get('id', '')}\n\n"
        f"📅 入住：{checkin}\n"
        f"📅 退房：{checkout}（共{nights}晚）\n"
        f"👤 入住人数：{guests}人\n\n"
        f"💰 房价：{format_price(price_per_night)}/晚\n"
        f"💰 *总价：{format_price(total_price)}*\n\n"
        f"👤 联系人：{contact_info['name']}\n"
        f"📞 电话：{contact_info['phone']}\n"
        f"📝 备注：{contact_info['note'] or '无'}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"请确认以上信息无误后点击「确认预订」"
    )
    
    await update.message.reply_text(
        confirm_text,
        parse_mode='Markdown',
        reply_markup=get_confirm_keyboard()
    )
    return CONFIRM_BOOKING

async def book_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """预订 - 确认"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm_no":
        await query.edit_message_text(
            "❌ 预订已取消\n\n"
            "如需重新预订，请输入 /book",
            reply_markup=get_back_keyboard()
        )
        return ConversationHandler.END
    
    # 创建预订记录
    booking_id = str(uuid.uuidint())[:8].upper()
    user_id = query.from_user.id
    villa = context.user_data.get('villa', {})
    contact = context.user_data.get('contact', {})
    checkin = context.user_data.get('checkin', '')
    checkout = context.user_data.get('checkout', '')
    guests = context.user_data.get('guests', 0)
    
    booking = {
        'id': booking_id,
        'user_id': str(user_id),
        'villa_id': villa.get('id', ''),
        'villa_name': villa.get('name', ''),
        'villa_region': villa.get('region', ''),
        'checkin': checkin,
        'checkout': checkout,
        'guests': guests,
        'contact_name': contact.get('name', ''),
        'contact_phone': contact.get('phone', ''),
        'contact_note': contact.get('note', ''),
        'price_per_night': villa.get('price_per_night', 0),
        'total_price': villa.get('price_per_night', 0) * calculate_nights(checkin, checkout),
        'status': 'pending'
    }
    
    if save_booking(booking):
        emoji = REGION_EMOJI.get(villa.get('region', ''), "📍")
        nights = calculate_nights(checkin, checkout)
        
        # ===== 生成并发送PDF确认单 =====
        try:
            import io
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from src.services.document import generate_confirmation_pdf_bytes
            
            # 获取别墅完整信息
            villa_full = database.get_villa(villa.get('id', ''))
            
            # 添加booking_id字段用于PDF
            booking['booking_id'] = booking_id
            
            # 生成PDF
            pdf_bytes = generate_confirmation_pdf_bytes(booking, villa_full or villa)
            
            # 发送PDF给用户
            await context.bot.send_document(
                chat_id=user_id,
                document=io.BytesIO(pdf_bytes),
                filename=f"booking_confirmation_{booking_id}.pdf",
                caption=f"📄 预订确认单 | Booking #{booking_id}\n\n请保存此确认单作为入住凭证"
            )
            logger.info(f"✅ PDF确认单已发送给用户 {user_id}")
        except ImportError:
            logger.warning("PDF模块未安装，跳过PDF生成")
        except Exception as e:
            logger.warning(f"PDF生成失败: {e}")
        
        success_text = (
            f"✅ *预订提交成功！*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📋 预订编号：*{booking_id}*\n\n"
            f"{emoji} 别墅：{villa.get('name', '')}\n"
            f"📅 {checkin} → {checkout}（{nights}晚）\n"
            f"👤 入住人：{contact.get('name', '')}\n\n"
            f"💰 总价：{format_price(booking['total_price'])}\n\n"
            f"📄 确认单已发送至本对话\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"⏳ 您的预订已提交，客服将在24小时内\n"
            f"与您联系确认订单详情。\n\n"
            f"如有疑问，请联系：@TaimiliSupport"
        )
        
        keyboard = [
            [InlineKeyboardButton("📋 查看我的预订", callback_data="cmd_mybookings")],
            [InlineKeyboardButton("🏠 返回主菜单", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            success_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await query.edit_message_text(
            "❌ 预订保存失败，请联系客服处理",
            reply_markup=get_back_keyboard()
        )
    
    # 清理用户数据
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """取消预订"""
    context.user_data.clear()
    
    text = (
        "❌ 已取消预订流程\n\n"
        "如需重新预订，请输入 /book"
    )
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text,
            reply_markup=get_back_keyboard()
        )
    else:
        await update.message.reply_text(text, reply_markup=get_back_keyboard())
    
    return ConversationHandler.END

# ============ 回调处理器 ============
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理按钮回调"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # 主菜单
    if data == "main_menu":
        await start(update, context)
    
    # 别墅列表
    elif data == "cmd_villas":
        await show_region_selection(update)
    
    # 查询可用
    elif data == "cmd_check":
        await query.edit_message_text(
            "📅 *查询可用别墅*\n\n"
            "请输入日期查询\n"
            "格式：/check 2026-06-15\n\n"
            "或查询范围：\n"
            "/check 2026-06-15 2026-06-18",
            parse_mode='Markdown',
            reply_markup=get_back_keyboard()
        )
    
    # 预订
    elif data == "cmd_book":
        await book_cmd(update, context)
    
    # 我的预订
    elif data == "cmd_mybookings":
        await mybookings_cmd(update, context)
    
    # 联系客服
    elif data == "cmd_contact":
        await contact_cmd(update, context)
    
    # 地区选择
    elif data.startswith("region_"):
        region = data.replace("region_", "")
        region_villas = database.get_villas_by_region(region)
        if region_villas:
            await show_villa_list(update, region_villas, region)
        else:
            await query.edit_message_text(
                f"❌ {region}暂无别墅数据",
                reply_markup=get_region_keyboard()
            )
    
    # 直接预订别墅
    elif data.startswith("book_villa_"):
        villa_id = data.replace("book_villa_", "")
        context.user_data.clear()
        context.user_data['villa_id'] = villa_id
        
        villa = database.get_villa(villa_id)
        
        if villa:
            context.user_data['villa'] = villa
            context.user_data['region'] = villa.get('region', '')
            
            emoji = REGION_EMOJI.get(villa.get('region', ''), "📍")
            text = (
                f"{emoji} *{villa.get('name')}*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🏷️ 编号：{villa_id}\n"
                f"💰 {format_price(villa.get('price_per_night', 0))}/晚\n\n"
                f"📅 *请输入入住日期*\n"
                f"格式：YYYY-MM-DD\n\n"
                f"例如：2026-06-15"
            )
            
            keyboard = [
                [InlineKeyboardButton("❌ 取消预订", callback_data="cancel_booking")]
            ]
            
            await query.edit_message_text(
                text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return SELECT_CHECKIN

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理未知消息"""
    await update.message.reply_text(
        "🤔 我不太明白您的意思\n\n"
        "请使用菜单按钮或输入命令：\n"
        "/help - 查看帮助\n"
        "/villas - 浏览别墅\n"
        "/book - 开始预订"
    )

# ============ 主函数 ============
def main():
    # 初始化数据库
    init_database()
    
    # 启动HTTP健康检查服务器
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # 构建应用
    application = Application.builder().token(TOKEN).build()
    
    # 命令处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("villas", villas_cmd))
    application.add_handler(CommandHandler("villa", villa_detail_cmd))
    application.add_handler(CommandHandler("check", check_cmd))
    application.add_handler(CommandHandler("mybookings", mybookings_cmd))
    application.add_handler(CommandHandler("contact", contact_cmd))
    
    # 预订流程 ConversationHandler
    book_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(book_cmd, pattern="^cmd_book$"),
            CommandHandler("book", book_cmd)
        ],
        states={
            SELECT_REGION: [
                CallbackQueryHandler(book_select_region, pattern="^region_")
            ],
            SELECT_VILLA: [
                CallbackQueryHandler(book_select_villa, pattern="^select_villa_")
            ],
            SELECT_CHECKIN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, book_enter_checkin),
                CallbackQueryHandler(cancel_booking, pattern="^cancel_booking$")
            ],
            SELECT_CHECKOUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, book_enter_checkout),
                CallbackQueryHandler(cancel_booking, pattern="^cancel_booking$")
            ],
            ENTER_GUESTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, book_enter_guests),
                CallbackQueryHandler(cancel_booking, pattern="^cancel_booking$")
            ],
            ENTER_CONTACT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, book_enter_contact),
                CallbackQueryHandler(cancel_booking, pattern="^cancel_booking$")
            ],
            CONFIRM_BOOKING: [
                CallbackQueryHandler(book_confirm, pattern="^confirm_")
            ]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_booking, pattern="^cancel_booking$"),
            CallbackQueryHandler(start, pattern="^main_menu$")
        ],
        allow_reentry=True
    )
    application.add_handler(book_conv)
    
    # 按钮回调处理器
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # 直接预订别墅回调
    async def handle_booking_callback(update, context):
        """处理预订相关的回调"""
        query = update.callback_query
        await query.answer()
        data = query.data
        if data.startswith("select_villa_"):
            await book_select_villa(update, context)
        elif data.startswith("confirm_"):
            await book_confirm(update, context)
    
    application.add_handler(CallbackQueryHandler(handle_booking_callback, pattern="^(select_villa_|confirm_)"))
    
    # ============ 命令型Callback路由器 ============
    async def handle_cmd_callback(update, context):
        """处理cmd_xxx格式的callback，模拟命令执行"""
        query = update.callback_query
        await query.answer()
        data = query.data
        
        # 路由到对应的命令处理函数
        if data == "cmd_mybookings":
            await mybookings_cmd(update, context)
        elif data == "cmd_coupons":
            await coupons_cmd(update, context)
        elif data == "cmd_book":
            await start(update, context)  # 跳转到主菜单选择预订
        elif data == "cmd_claim_coupon":
            # TODO: 实现领取优惠券逻辑
            await query.edit_message_text("🎁 优惠券领取功能开发中，敬请期待！")
        elif data == "cmd_contact":
            await query.edit_message_text(
                "📞 *联系客服*\n\n"
                "📧 邮箱：support@taimili.com\n"
                "📱 微信：TaimiliVilla\n"
                "⏰ 工作时间：9:00-21:00 (GMT+7)\n\n"
                "我们会在24小时内回复您！",
                parse_mode='Markdown'
            )
        elif data == "cmd_faq":
            await faq_cmd(update, context)
        elif data == "cmd_help":
            await help_cmd(update, context)
        elif data == "cmd_points_history":
            await query.edit_message_text("📜 积分记录功能开发中，敬请期待！")
    
    application.add_handler(CallbackQueryHandler(handle_cmd_callback, pattern="^cmd_"))
    
    # ============ 取消预订处理器 ============
    async def handle_cancel_booking(update, context):
        """处理取消预订"""
        query = update.callback_query
        await query.answer()
        data = query.data  # cancel_booking_XXX
        
        booking_id = data.replace("cancel_booking_", "")
        
        # 调用数据库取消
        success = database.cancel_booking(booking_id)
        
        if success:
            await query.edit_message_text(
                f"✅ 预订 {booking_id} 已取消\n\n"
                "如需重新预订，请发送 /start",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 返回主菜单", callback_data="main_menu")
                ]])
            )
        else:
            await query.edit_message_text(
                f"❌ 取消失败，预订可能已被处理\n\n"
                "请联系客服处理",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📞 联系客服", callback_data="cmd_contact")
                ]])
            )
    
    application.add_handler(CallbackQueryHandler(handle_cancel_booking, pattern="^cancel_booking_"))
    
    # ============ 新功能处理器 (v4.0) ============
    # 用户画像 - /profile
    application.add_handler(CommandHandler("profile", profile_cmd))
    
    # 预订历史 - /mybookings (增强版)
    register_mybookings_handlers(application)
    
    # 优惠券 - /coupons
    register_coupons_handlers(application)
    
    # 积分查询 - /points
    application.add_handler(CommandHandler("points", points_cmd))
    
    # 促销码兑换 - /redeem
    register_redeem_handlers(application)
    
    # 评价 - /review
    register_review_handlers(application)
    
    # 帮助中心 - /help, /faq (增强版)
    register_help_handlers(application)
    
    # 消息处理器
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 Taimili Villa Booking Bot v4.0 (SQLite) 启动中...")
    
    # Python 3.10+ 兼容性修复：确保事件循环存在
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
