"""
Taimili Villa Bot 监控模块
包含: 健康检查、告警管理、通知发送

使用方法:
    from monitoring import get_notifier, get_alert_manager
    
    # 发送通知
    notifier = get_notifier()
    notifier.send_alert('WARNING', '服务异常', '响应时间过长')
    
    # 管理告警
    alert_mgr = get_alert_manager()
    alert_mgr.check_service_health()
"""

from .health_check_enhanced import EnhancedHealthHandler, run_enhanced_health_server
from .telegram_notifier import TelegramNotifier, get_notifier
from .email_notifier import EmailNotifier
from .alert_manager import AlertManager, get_alert_manager

__all__ = [
    'EnhancedHealthHandler',
    'run_enhanced_health_server',
    'TelegramNotifier',
    'get_notifier',
    'EmailNotifier',
    'AlertManager',
    'get_alert_manager'
]
