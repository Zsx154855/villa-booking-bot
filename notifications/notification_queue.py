#!/usr/bin/env python3
"""
Taimili Villa Booking Bot - 通知队列模块
用于在HTTP上下文中记录通知任务，由后台JobQueue执行发送
"""

import logging
from datetime import datetime
from typing import Dict, Any

import database

logger = logging.getLogger(__name__)

# ============ 通知任务类型 ============
class NotificationTask:
    """通知任务"""
    
    TYPE_BOOKING_CONFIRMATION = "booking_confirmation"
    TYPE_PAYMENT_SUCCESS = "payment_success"
    TYPE_CHECKIN_REMINDER = "checkin_reminder"
    TYPE_CHECKOUT_REMINDER = "checkout_reminder"

def queue_notification(booking_id: str, notification_type: str, user_id: str = None) -> bool:
    """
    将通知任务加入队列
    
    Args:
        booking_id: 预订ID
        notification_type: 通知类型
        user_id: 用户ID（可选，从booking中获取）
    
    Returns:
        是否成功加入队列
    """
    try:
        # 如果没有提供user_id，从预订中获取
        if not user_id:
            booking = database.get_booking(booking_id)
            if booking:
                user_id = booking.get('user_id')
        
        if not user_id:
            logger.error(f"❌ 无法获取用户ID，预订: {booking_id}")
            return False
        
        # 在预订记录中标记需要发送的通知
        pending_notifications = database.get_booking_field(booking_id, 'pending_notifications') or []
        
        if isinstance(pending_notifications, str):
            import json
            try:
                pending_notifications = json.loads(pending_notifications)
            except:
                pending_notifications = []
        
        if notification_type not in pending_notifications:
            pending_notifications.append(notification_type)
            
            # 使用JSON存储列表
            import json
            database.update_booking_field(booking_id, 'pending_notifications', json.dumps(pending_notifications))
            
            logger.info(f"📬 已加入通知队列: 预订{booking_id}, 类型{notification_type}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 加入通知队列失败: {e}")
        return False

def get_and_clear_pending_notifications(booking_id: str) -> list:
    """
    获取并清除预订的待处理通知
    
    Args:
        booking_id: 预订ID
    
    Returns:
        待处理的通知类型列表
    """
    try:
        import json
        pending_notifications = database.get_booking_field(booking_id, 'pending_notifications')
        
        if pending_notifications:
            try:
                notifications = json.loads(pending_notifications) if isinstance(pending_notifications, str) else pending_notifications
            except:
                notifications = []
        else:
            notifications = []
        
        # 清除待处理通知
        database.update_booking_field(booking_id, 'pending_notifications', json.dumps([]))
        
        return notifications
        
    except Exception as e:
        logger.error(f"❌ 获取待处理通知失败: {e}")
        return []

async def process_pending_notifications(bot, booking: Dict[str, Any]) -> bool:
    """
    处理预订的待处理通知
    
    Args:
        bot: Telegram Bot实例
        booking: 预订信息
    
    Returns:
        是否处理成功
    """
    from .notifier import (
        send_booking_confirmation,
        send_payment_success
    )
    
    try:
        user_id = booking.get('user_id')
        if not user_id:
            return False
        
        notifications = get_and_clear_pending_notifications(booking['id'])
        
        if not notifications:
            return True
        
        logger.info(f"📬 开始处理 {len(notifications)} 个待处理通知...")
        
        for notification_type in notifications:
            if notification_type == NotificationTask.TYPE_BOOKING_CONFIRMATION:
                # 预订确认通知已由bot.py直接发送，这里主要处理支付成功等场景
                pass
            elif notification_type == NotificationTask.TYPE_PAYMENT_SUCCESS:
                await send_payment_success(bot, user_id, booking)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 处理待处理通知失败: {e}")
        return False
