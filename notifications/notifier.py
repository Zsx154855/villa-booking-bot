#!/usr/bin/env python3
"""
Taimili Villa Booking Bot - 通知系统核心模块
支持预订确认、入住提醒、退房提醒、支付通知等自动化消息
"""

import os
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any, List
from pathlib import Path

import database

logger = logging.getLogger(__name__)

# ============ 通知类型枚举 ============
class NotificationType(Enum):
    BOOKING_CONFIRMATION = "booking_confirmation"  # 预订确认
    PAYMENT_SUCCESS = "payment_success"             # 支付成功
    CHECKIN_REMINDER = "checkin_reminder"          # 入住前1天提醒
    CHECKIN_DAY = "checkin_day"                   # 入住当天提醒
    CHECKOUT_REMINDER = "checkout_reminder"        # 退房前1天提醒

# ============ 配置 ============
# 模板目录
TEMPLATE_DIR = Path(__file__).parent / "templates"
FALLBACK_TEMPLATE_DIR = Path(__file__).parent.parent.parent / "别墅运营系统" / "notifications" / "templates"

# 通知发送时间配置
CHECKIN_REMINDER_HOUR = 9   # 入住前1天提醒发送时间（小时）
CHECKIN_DAY_HOUR = 9        # 入住当天提醒发送时间（小时）
CHECKOUT_REMINDER_HOUR = 9  # 退房前1天提醒发送时间（小时）

# ============ 辅助函数 ============
def format_price(price: float) -> str:
    """格式化价格"""
    return f"฿{price:,.0f}"

def get_villa_emoji(region: str) -> str:
    """获取地区emoji"""
    emoji_map = {"芭提雅": "🏖️", "曼谷": "🏙️", "普吉岛": "🏝️"}
    return emoji_map.get(region, "📍")

def load_template(notification_type: NotificationType, lang: str = "zh") -> str:
    """
    加载通知模板
    
    Args:
        notification_type: 通知类型
        lang: 语言代码 (zh/en/th)
    
    Returns:
        模板内容字符串
    """
    filename = f"{notification_type.value}_{lang}.txt"
    
    # 优先从Bot目录加载
    template_path = TEMPLATE_DIR / filename
    if template_path.exists():
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    # 降级到运营系统目录
    fallback_path = FALLBACK_TEMPLATE_DIR / filename
    if fallback_path.exists():
        with open(fallback_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    logger.warning(f"⚠️ 模板文件不存在: {filename}")
    return None

def format_template(template: str, context: Dict[str, Any]) -> str:
    """
    格式化模板内容
    
    Args:
        template: 模板字符串
        context: 上下文数据字典
    
    Returns:
        格式化后的消息文本
    """
    if not template:
        return None
    
    try:
        return template.format(**context)
    except KeyError as e:
        logger.error(f"❌ 模板格式化失败，缺少变量: {e}")
        return None

def get_user_language(user_id: str) -> str:
    """
    获取用户语言偏好
    暂时默认中文，后续可扩展用户画像中的语言设置
    """
    # TODO: 从用户画像/数据库中读取语言偏好
    return "zh"

# ============ 核心通知函数 ============
async def send_booking_confirmation(bot, user_id: str, booking: Dict[str, Any]) -> bool:
    """
    发送预订确认通知
    
    Args:
        bot: Telegram Bot实例
        user_id: 用户ID
        booking: 预订信息字典
    
    Returns:
        是否发送成功
    """
    try:
        lang = get_user_language(user_id)
        template = load_template(NotificationType.BOOKING_CONFIRMATION, lang)
        
        if not template:
            # 降级为内联消息
            emoji = get_villa_emoji(booking.get('villa_region', ''))
            nights = (datetime.strptime(booking['checkout'], "%Y-%m-%d") - 
                      datetime.strptime(booking['checkin'], "%Y-%m-%d")).days
            
            message = (
                f"✅ *预订确认通知*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📋 预订编号：*{booking['id']}*\n\n"
                f"{emoji} 别墅：{booking.get('villa_name', '')}\n"
                f"📅 入住：{booking['checkin']}\n"
                f"📅 退房：{booking['checkout']}（{nights}晚）\n"
                f"👤 入住人：{booking.get('contact_name', '')}\n\n"
                f"💰 总价：{format_price(booking.get('total_price', 0))}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📄 您的预订已确认！\n"
                f"请保存好确认信息，入住时需出示。\n\n"
                f"如有疑问请联系：@TaimiliSupport"
            )
        else:
            context = {
                'booking_id': booking['id'],
                'villa_name': booking.get('villa_name', ''),
                'villa_region': booking.get('villa_region', ''),
                'checkin': booking['checkin'],
                'checkout': booking['checkout'],
                'nights': (datetime.strptime(booking['checkout'], "%Y-%m-%d") - 
                          datetime.strptime(booking['checkin'], "%Y-%m-%d")).days,
                'contact_name': booking.get('contact_name', ''),
                'total_price': format_price(booking.get('total_price', 0)),
                'emoji': get_villa_emoji(booking.get('villa_region', ''))
            }
            message = format_template(template, context)
        
        await bot.send_message(
            chat_id=int(user_id),
            text=message,
            parse_mode='Markdown'
        )
        
        logger.info(f"✅ 预订确认通知已发送给用户 {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ 发送预订确认通知失败: {e}")
        return False

async def send_payment_success(bot, user_id: str, booking: Dict[str, Any]) -> bool:
    """
    发送支付成功通知
    
    Args:
        bot: Telegram Bot实例
        user_id: 用户ID
        booking: 预订信息字典
    
    Returns:
        是否发送成功
    """
    try:
        emoji = get_villa_emoji(booking.get('villa_region', ''))
        
        message = (
            f"💳 *支付成功！*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✅ 您的预订已自动确认！\n\n"
            f"📋 预订编号：*{booking['id']}*\n\n"
            f"{emoji} 别墅：{booking.get('villa_name', '')}\n"
            f"📅 入住：{booking['checkin']}\n"
            f"📅 退房：{booking['checkout']}\n"
            f"💰 已支付：{format_price(booking.get('total_price', 0))}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📄 确认单已发送至本对话\n"
            f"请保存好确认单作为入住凭证\n\n"
            f"期待与您相见！🌴"
        )
        
        await bot.send_message(
            chat_id=int(user_id),
            text=message,
            parse_mode='Markdown'
        )
        
        logger.info(f"✅ 支付成功通知已发送给用户 {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ 发送支付成功通知失败: {e}")
        return False

async def send_checkin_reminder(bot, user_id: str, booking: Dict[str, Any]) -> bool:
    """
    发送入住前1天提醒
    
    Args:
        bot: Telegram Bot实例
        user_id: 用户ID
        booking: 预订信息字典
    
    Returns:
        是否发送成功
    """
    try:
        lang = get_user_language(user_id)
        template = load_template(NotificationType.CHECKIN_REMINDER, lang)
        
        if not template:
            # 降级为内联消息
            emoji = get_villa_emoji(booking.get('villa_region', ''))
            nights = (datetime.strptime(booking['checkout'], "%Y-%m-%d") - 
                      datetime.strptime(booking['checkin'], "%Y-%m-%d")).days
            
            message = (
                f"🔔 *入住提醒*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"明天就是您的入住日啦！🌴\n\n"
                f"📋 预订编号：*{booking['id']}*\n\n"
                f"{emoji} 别墅：{booking.get('villa_name', '')}\n"
                f"📅 入住：明天 {booking['checkin']}\n"
                f"📅 退房：{booking['checkout']}（{nights}晚）\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📍 *入住指南*\n"
                f"• 别墅地址将于入住当天发送\n"
                f"• 入住时间：14:00后\n"
                f"• 退房时间：次日12:00前\n"
                f"• 入住人需出示护照\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💡 如有任何问题，请联系：@TaimiliSupport\n\n"
                f"期待您的到来！✨"
            )
        else:
            context = {
                'booking_id': booking['id'],
                'villa_name': booking.get('villa_name', ''),
                'checkin': booking['checkin'],
                'checkout': booking['checkout'],
                'emoji': get_villa_emoji(booking.get('villa_region', ''))
            }
            message = format_template(template, context)
        
        await bot.send_message(
            chat_id=int(user_id),
            text=message,
            parse_mode='Markdown'
        )
        
        logger.info(f"✅ 入住前1天提醒已发送给用户 {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ 发送入住前1天提醒失败: {e}")
        return False

async def send_checkin_day_reminder(bot, user_id: str, booking: Dict[str, Any], 
                                    address: str = None) -> bool:
    """
    发送入住当天提醒
    
    Args:
        bot: Telegram Bot实例
        user_id: 用户ID
        booking: 预订信息字典
        address: 别墅地址（可选）
    
    Returns:
        是否发送成功
    """
    try:
        emoji = get_villa_emoji(booking.get('villa_region', ''))
        
        address_text = f"\n📍 *别墅地址：*\n{address}\n" if address else "\n📍 *别墅地址：*\n将于稍后发送\n"
        
        message = (
            f"🌴 *入住当天提醒*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"欢迎入住！祝您旅途愉快！✨\n\n"
            f"📋 预订编号：*{booking['id']}*\n\n"
            f"{emoji} 别墅：{booking.get('villa_name', '')}\n"
            f"📅 入住日期：今天 {booking['checkin']}\n"
            f"📅 退房日期：{booking['checkout']}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"⏰ *时间提示*\n"
            f"• 入住时间：14:00后\n"
            f"• 退房时间：次日12:00前\n\n"
            f"{address_text}"
            f"\n💡 *温馨提示*\n"
            f"• 入住人需出示护照\n"
            f"• 如需延迟退房请联系管家\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"祝您住宿愉快！🏠\n"
            f"如有疑问请联系：@TaimiliSupport"
        )
        
        await bot.send_message(
            chat_id=int(user_id),
            text=message,
            parse_mode='Markdown'
        )
        
        logger.info(f"✅ 入住当天提醒已发送给用户 {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ 发送入住当天提醒失败: {e}")
        return False

async def send_checkout_reminder(bot, user_id: str, booking: Dict[str, Any]) -> bool:
    """
    发送退房前1天提醒
    
    Args:
        bot: Telegram Bot实例
        user_id: 用户ID
        booking: 预订信息字典
    
    Returns:
        是否发送成功
    """
    try:
        lang = get_user_language(user_id)
        template = load_template(NotificationType.CHECKOUT_REMINDER, lang)
        
        if not template:
            # 降级为内联消息
            emoji = get_villa_emoji(booking.get('villa_region', ''))
            
            message = (
                f"🔔 *退房提醒*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"明天就是您的退房日啦～\n\n"
                f"📋 预订编号：*{booking['id']}*\n\n"
                f"{emoji} 别墅：{booking.get('villa_name', '')}\n"
                f"📅 退房日期：明天 {booking['checkout']}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"⏰ *退房须知*\n"
                f"• 请在 *12:00前* 完成退房\n"
                f"• 请将钥匙交还给管家\n"
                f"• 请检查个人物品不要遗漏\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"感谢您的入住！🌴\n"
                f"期待下次再见～\n\n"
                f"如有疑问请联系：@TaimiliSupport"
            )
        else:
            context = {
                'booking_id': booking['id'],
                'villa_name': booking.get('villa_name', ''),
                'checkout': booking['checkout'],
                'emoji': get_villa_emoji(booking.get('villa_region', ''))
            }
            message = format_template(template, context)
        
        await bot.send_message(
            chat_id=int(user_id),
            text=message,
            parse_mode='Markdown'
        )
        
        logger.info(f"✅ 退房前1天提醒已发送给用户 {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ 发送退房前1天提醒失败: {e}")
        return False

# ============ 定时任务 ============
async def job_checkin_reminder(context):
    """
    入住前1天提醒定时任务
    每天早上执行，查询明天入住的预订并发送提醒
    """
    try:
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # 查询明天入住的预订
        bookings = database.get_bookings_by_date(tomorrow)
        
        if not bookings:
            logger.info("📅 明天没有需要入住的预订")
            return
        
        logger.info(f"📬 开始发送 {len(bookings)} 条入住前1天提醒...")
        
        for booking in bookings:
            user_id = booking.get('user_id')
            if user_id:
                await send_checkin_reminder(context.bot, user_id, booking)
        
        logger.info(f"✅ 入住前1天提醒发送完成")
        
    except Exception as e:
        logger.error(f"❌ 入住前1天提醒任务执行失败: {e}")

async def job_checkin_day_reminder(context):
    """
    入住当天提醒定时任务
    每天早上执行，查询今天入住的预订并发送提醒
    """
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 查询今天入住的预订
        bookings = database.get_bookings_by_date(today)
        
        if not bookings:
            logger.info("📅 今天没有需要入住的预订")
            return
        
        logger.info(f"📬 开始发送 {len(bookings)} 条入住当天提醒...")
        
        for booking in bookings:
            user_id = booking.get('user_id')
            # TODO: 从别墅信息中获取地址
            address = None
            if user_id:
                await send_checkin_day_reminder(context.bot, user_id, booking, address)
        
        logger.info(f"✅ 入住当天提醒发送完成")
        
    except Exception as e:
        logger.error(f"❌ 入住当天提醒任务执行失败: {e}")

async def job_checkout_reminder(context):
    """
    退房前1天提醒定时任务
    每天早上执行，查询明天退房的预订并发送提醒
    """
    try:
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # 查询明天退房的预订
        bookings = database.get_bookings_by_checkout(tomorrow)
        
        if not bookings:
            logger.info("📅 明天没有需要退房的预订")
            return
        
        logger.info(f"📬 开始发送 {len(bookings)} 条退房前1天提醒...")
        
        for booking in bookings:
            user_id = booking.get('user_id')
            if user_id:
                await send_checkout_reminder(context.bot, user_id, booking)
        
        logger.info(f"✅ 退房前1天提醒发送完成")
        
    except Exception as e:
        logger.error(f"❌ 退房前1天提醒任务执行失败: {e}")

async def job_process_pending_notifications(context):
    """
    处理待处理通知队列
    检查并发送所有pending_notifications中的通知
    每15分钟执行一次
    """
    import json
    
    try:
        # 查询有待处理通知的预订
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM bookings 
            WHERE pending_notifications IS NOT NULL 
            AND pending_notifications != '[]' 
            AND pending_notifications != 'null'
        """)
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return
        
        logger.info(f"📬 发现 {len(rows)} 条待处理通知...")
        
        for row in rows:
            booking = dict(row)
            booking_id = booking.get('id') or booking.get('booking_id')
            user_id = booking.get('user_id')
            
            if not user_id or not booking_id:
                continue
            
            # 解析待处理通知
            try:
                pending = booking.get('pending_notifications', '[]')
                if isinstance(pending, str):
                    notifications = json.loads(pending)
                else:
                    notifications = pending
            except:
                continue
            
            if not notifications:
                continue
            
            # 发送各类型通知
            for notification_type in notifications:
                try:
                    if notification_type == 'payment_success':
                        await send_payment_success(context.bot, user_id, booking)
                        logger.info(f"✅ 已发送支付成功通知: {booking_id}")
                    elif notification_type == 'booking_confirmation':
                        await send_booking_confirmation(context.bot, user_id, booking)
                        logger.info(f"✅ 已发送预订确认通知: {booking_id}")
                except Exception as e:
                    logger.error(f"❌ 发送通知失败 {booking_id}.{notification_type}: {e}")
            
            # 清除已处理的待处理通知
            try:
                database.update_booking_field(booking_id, 'pending_notifications', '[]')
            except:
                pass
        
        logger.info(f"✅ 待处理通知处理完成")
        
    except Exception as e:
        logger.error(f"❌ 处理待处理通知任务失败: {e}")

def setup_notification_jobs(application):
    """
    配置通知定时任务
    
    Args:
        application: Telegram Application实例
    """
    from datetime import time
    
    # 创建JobQueue（如果不存在）
    job_queue = application.job_queue
    
    if job_queue is None:
        logger.warning("⚠️ JobQueue未初始化，跳过通知任务配置")
        return
    
    # 入住前1天提醒 - 每天早上9点
    job_queue.run_daily(
        job_checkin_reminder,
        time=time(hour=CHECKIN_REMINDER_HOUR, minute=0),
        name="checkin_reminder"
    )
    logger.info(f"✅ 已配置入住前1天提醒任务 (每天 {CHECKIN_REMINDER_HOUR}:00)")
    
    # 入住当天提醒 - 每天早上9点
    job_queue.run_daily(
        job_checkin_day_reminder,
        time=time(hour=CHECKIN_DAY_HOUR, minute=0),
        name="checkin_day_reminder"
    )
    logger.info(f"✅ 已配置入住当天提醒任务 (每天 {CHECKIN_DAY_HOUR}:00)")
    
    # 退房前1天提醒 - 每天早上9点
    job_queue.run_daily(
        job_checkout_reminder,
        time=time(hour=CHECKOUT_REMINDER_HOUR, minute=0),
        name="checkout_reminder"
    )
    logger.info(f"✅ 已配置退房前1天提醒任务 (每天 {CHECKOUT_REMINDER_HOUR}:00)")
    
    # 待处理通知处理 - 每15分钟执行一次
    job_queue.run_repeating(
        job_process_pending_notifications,
        interval=15 * 60,  # 15分钟
        first=30,  # 启动30秒后首次执行
        name="process_pending_notifications"
    )
    logger.info("✅ 已配置待处理通知处理任务 (每15分钟)")
    
    logger.info("🎉 通知定时任务配置完成!")

# ============ 数据库接口补充 ============
# 这些函数需要在database.py中实现
# 这里提供兼容性存根

def ensure_database_functions():
    """
    确保数据库模块有所需的函数
    如果缺失，添加兼容实现
    """
    if not hasattr(database, 'get_bookings_by_date'):
        def get_bookings_by_date(checkin: str) -> List[Dict]:
            """获取指定入住日期的预订"""
            try:
                conn = database.get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT * FROM bookings 
                       WHERE checkin = ? AND status IN ('pending', 'confirmed', 'paid')""",
                    (checkin,)
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
            except Exception as e:
                logger.error(f"查询入住预订失败: {e}")
                return []
            finally:
                if 'conn' in locals():
                    conn.close()
        
        database.get_bookings_by_date = get_bookings_by_date
        logger.info("✅ 已添加 get_bookings_by_date 兼容性实现")
    
    if not hasattr(database, 'get_bookings_by_checkout'):
        def get_bookings_by_checkout(checkout: str) -> List[Dict]:
            """获取指定退房日期的预订"""
            try:
                conn = database.get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT * FROM bookings 
                       WHERE checkout = ? AND status IN ('pending', 'confirmed', 'paid')""",
                    (checkout,)
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
            except Exception as e:
                logger.error(f"查询退房预订失败: {e}")
                return []
            finally:
                if 'conn' in locals():
                    conn.close()
        
        database.get_bookings_by_checkout = get_bookings_by_checkout
        logger.info("✅ 已添加 get_bookings_by_checkout 兼容性实现")
