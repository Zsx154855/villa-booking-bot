"""
Taimili Villa Booking Bot - 通知系统模块
提供预订、入住、退房等自动化通知功能
"""

from .notifier import (
    # 核心通知函数
    send_booking_confirmation,
    send_checkin_reminder,
    send_checkout_reminder,
    send_payment_success,
    send_checkin_day_reminder,
    
    # 定时任务注册
    setup_notification_jobs,
    
    # 模板加载
    load_template,
    
    # 通知类型枚举
    NotificationType,
    
    # 数据库兼容性
    ensure_database_functions
)

from .notification_queue import (
    # 通知队列
    queue_notification,
    get_and_clear_pending_notifications,
    process_pending_notifications,
    NotificationTask
)

__all__ = [
    # 核心通知函数
    'send_booking_confirmation',
    'send_checkin_reminder',
    'send_checkout_reminder',
    'send_payment_success',
    'send_checkin_day_reminder',
    
    # 定时任务注册
    'setup_notification_jobs',
    
    # 模板加载
    'load_template',
    
    # 通知类型枚举
    'NotificationType',
    
    # 数据库兼容性
    'ensure_database_functions',
    
    # 通知队列
    'queue_notification',
    'get_and_clear_pending_notifications',
    'process_pending_notifications',
    'NotificationTask'
]
