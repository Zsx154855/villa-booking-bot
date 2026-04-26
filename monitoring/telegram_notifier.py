#!/usr/bin/env python3
"""
Telegram 通知模块
用于发送监控告警和定时报告
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict
import urllib.request
import urllib.error

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Telegram 通知器"""
    
    def __init__(self, bot_token: str = None, chat_id: str = None):
        """
        初始化 Telegram 通知器
        
        Args:
            bot_token: Telegram Bot Token (可从环境变量 TELEGRAM_NOTIFY_TOKEN 获取)
            chat_id: 接收通知的 Chat ID (可从环境变量 TELEGRAM_NOTIFY_CHAT_ID 获取)
        """
        self.bot_token = bot_token or os.environ.get('TELEGRAM_NOTIFY_TOKEN')
        self.chat_id = chat_id or os.environ.get('TELEGRAM_NOTIFY_CHAT_ID')
        self.api_base = f'https://api.telegram.org/bot{self.bot_token}' if self.bot_token else None
        
        if not self.bot_token or not self.chat_id:
            logger.warning("⚠️ Telegram 通知配置不完整，将使用模拟模式")
            logger.warning(f"   需要设置环境变量: TELEGRAM_NOTIFY_TOKEN, TELEGRAM_NOTIFY_CHAT_ID")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("✅ Telegram 通知器已初始化")
    
    def send_message(self, text: str, parse_mode: str = 'Markdown') -> bool:
        """
        发送消息
        
        Args:
            text: 消息内容 (支持 Markdown)
            parse_mode: 解析模式 (Markdown / HTML)
            
        Returns:
            bool: 发送是否成功
        """
        if not self.enabled:
            logger.info(f"📱 [模拟发送] {text[:100]}...")
            return True
        
        try:
            url = f'{self.api_base}/sendMessage'
            data = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode
            }
            
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode(),
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read())
                if result.get('ok'):
                    logger.info("✅ Telegram 消息发送成功")
                    return True
                else:
                    logger.error(f"❌ Telegram 发送失败: {result}")
                    return False
                    
        except urllib.error.URLError as e:
            logger.error(f"❌ Telegram 网络错误: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Telegram 发送异常: {e}")
            return False
    
    def send_health_report(self, health_data: Dict) -> bool:
        """发送健康检查报告"""
        status_icon = {
            'ok': '🟢',
            'degraded': '🟡',
            'unhealthy': '🔴'
        }.get(health_data.get('status', 'unknown'), '❓')
        
        db_check = health_data.get('checks', {}).get('database', {})
        sys_check = health_data.get('checks', {}).get('system', {})
        perf = health_data.get('performance', {})
        
        # 安全获取嵌套数据
        db_details = db_check.get('details', {})
        sys_details = sys_check.get('details', {})
        
        message = f"""
{status_icon} *Taimili Villa Bot 健康报告*

📅 时间: {health_data.get('timestamp', 'N/A')}
🔧 版本: {health_data.get('version', 'N/A')}

📊 数据库状态:
• 别墅数量: {db_details.get('villas_count', 'N/A')}
• 预订数量: {db_details.get('bookings_count', 'N/A')}
• 查询时间: {db_details.get('query_time_ms', 'N/A')} ms
• 状态: {db_check.get('status', 'unknown')}

💻 系统资源:
• 磁盘使用: {sys_details.get('disk', {}).get('usage_percent', 'N/A')}%
• 内存使用: {sys_details.get('memory', {}).get('usage_percent', 'N/A')}%
• 进程内存: {sys_details.get('process', {}).get('memory_mb', 'N/A')} MB

⚡ 性能:
• 响应时间: {perf.get('response_time_ms', 'N/A')} ms
• 状态: {perf.get('status', 'unknown')}

🔗 链接: https://taimili-villa-bot.onrender.com
"""
        
        return self.send_message(message)
    
    def send_alert(self, severity: str, title: str, message: str, details: str = '') -> bool:
        """
        发送告警通知
        
        Args:
            severity: 告警级别 (CRITICAL/WARNING/INFO)
            title: 告警标题
            message: 告警消息
            details: 详细信息
        """
        icons = {
            'CRITICAL': '🚨',
            'WARNING': '⚠️',
            'INFO': 'ℹ️'
        }
        
        icon = icons.get(severity, '📢')
        
        alert_message = f"""
{icon} *{severity} - {title}*

{message}
"""
        
        if details:
            alert_message += f"""
📋 详情:
```
{details}
```
"""
        
        alert_message += f"""
🕐 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return self.send_message(alert_message)
    
    def send_simple_message(self, message: str) -> bool:
        """发送简单文本消息"""
        return self.send_message(message, parse_mode='')


# 全局实例 (延迟初始化)
_notifier = None


def get_notifier() -> TelegramNotifier:
    """获取通知器单例"""
    global _notifier
    if _notifier is None:
        _notifier = TelegramNotifier()
    return _notifier


# 便捷函数
def send_alert(severity: str, title: str, message: str, details: str = '') -> bool:
    """快捷发送告警"""
    return get_notifier().send_alert(severity, title, message, details)


def send_health_report(health_data: Dict) -> bool:
    """快捷发送健康报告"""
    return get_notifier().send_health_report(health_data)
