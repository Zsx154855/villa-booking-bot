#!/usr/bin/env python3
"""
通知模块 - 预订确认、支付成功、定时任务等
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


async def send_booking_confirmation(bot, user_id: str, booking: Dict[str, Any]) -> bool:
    """发送预订确认通知"""
    try:
        villa_name = booking.get('villa_name', '别墅')
        checkin = booking.get('checkin_date', 'N/A')
        checkout = booking.get('checkout_date', 'N/A')
        total = booking.get('total_price', 'N/A')
        
        message = (
            f"✅ 预订确认\n\n"
            f"🏠 {villa_name}\n"
            f"📅 入住：{checkin}\n"
            f"📅 退房：{checkout}\n"
            f"💰 总价：¥{total}\n\n"
            f"感谢您的预订！如有问题请随时联系我们。"
        )
        
        await bot.send_message(chat_id=user_id, text=message)
        logger.info(f"预订确认已发送: user={user_id}, villa={villa_name}")
        return True
    except Exception as e:
        logger.error(f"发送预订确认失败: {e}")
        return False


async def send_payment_success(bot, user_id: str, payment_info: Dict[str, Any]) -> bool:
    """发送支付成功通知"""
    try:
        amount = payment_info.get('amount', 'N/A')
        villa_name = payment_info.get('villa_name', '别墅')
        
        message = (
            f"💰 支付成功\n\n"
            f"🏠 {villa_name}\n"
            f"💵 金额：¥{amount}\n\n"
            f"支付已完成，期待您的入住！"
        )
        
        await bot.send_message(chat_id=user_id, text=message)
        logger.info(f"支付通知已发送: user={user_id}, amount={amount}")
        return True
    except Exception as e:
        logger.error(f"发送支付通知失败: {e}")
        return False


def setup_notification_jobs(application):
    """设置定时通知任务"""
    try:
        # 预留：可在此添加定时任务
        # 例如：每日入住提醒、退房提醒等
        logger.info("✅ 通知定时任务已设置")
    except Exception as e:
        logger.error(f"设置通知任务失败: {e}")


def ensure_database_functions():
    """确保数据库函数可用"""
    try:
        import database
        # 验证数据库连接
        database.get_connection()
        logger.info("✅ 数据库函数验证通过")
    except Exception as e:
        logger.warning(f"数据库函数验证: {e}")
