#!/usr/bin/env python3
"""
告警管理器
管理告警状态、冷却、通知发送
"""

import os
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, Callable, Optional
from collections import defaultdict

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlertManager:
    """告警管理器 - 实现告警冷却机制，防止告警风暴"""
    
    # 告警冷却时间 (秒)
    COOLDOWN = {
        'CRITICAL': 300,   # 5 分钟
        'WARNING': 900,    # 15 分钟
        'INFO': 3600       # 1 小时
    }
    
    def __init__(self):
        self.last_alerts: Dict[str, float] = {}  # 告警名称 -> 上次发送时间
        self.alert_counts: Dict[str, int] = defaultdict(int)  # 告警计数
        self.failed_check_count: int = 0  # 连续失败次数
        self.lock = threading.Lock()
        
        # 延迟导入通知器
        self._notifiers_initialized = False
    
    def _init_notifiers(self):
        """延迟初始化通知器"""
        if self._notifiers_initialized:
            return
        
        try:
            from .telegram_notifier import TelegramNotifier
            from .email_notifier import EmailNotifier
            
            self.telegram = TelegramNotifier()
            self.email = EmailNotifier()
            self._notifiers_initialized = True
            
        except ImportError as e:
            logger.warning(f"⚠️ 无法导入通知器: {e}")
            self.telegram = None
            self.email = None
    
    def should_send(self, alert_name: str, severity: str) -> bool:
        """
        检查是否应该发送告警 (考虑冷却时间)
        
        Args:
            alert_name: 告警名称 (唯一标识)
            severity: 告警级别 (CRITICAL/WARNING/INFO)
            
        Returns:
            bool: 是否应该发送
        """
        cooldown = self.COOLDOWN.get(severity, 3600)
        current_time = time.time()
        
        with self.lock:
            last_time = self.last_alerts.get(alert_name, 0)
            
            if current_time - last_time < cooldown:
                remaining = int(cooldown - (current_time - last_time))
                logger.debug(f"⏳ 告警 {alert_name} 处于冷却期，剩余 {remaining} 秒")
                return False
            
            self.last_alerts[alert_name] = current_time
            self.alert_counts[alert_name] += 1
            return True
    
    def send_alert(self, severity: str, title: str, message: str, 
                   details: Optional[Dict] = None,
                   use_telegram: bool = True,
                   use_email: bool = True) -> bool:
        """
        发送告警
        
        Args:
            severity: 告警级别 (CRITICAL/WARNING/INFO)
            title: 告警标题
            message: 告警消息
            details: 详细信息字典
            use_telegram: 是否使用 Telegram
            use_email: 是否使用邮件
            
        Returns:
            bool: 是否发送成功 (包括模拟发送)
        """
        self._init_notifiers()
        
        # 检查冷却
        if not self.should_send(title, severity):
            logger.info(f"⏳ 告警已抑制: {title} (冷却中)")
            return False
        
        logger.warning(f"🚨 发送告警 [{severity}]: {title}")
        
        results = []
        details_str = str(details) if details else ''
        
        # 发送 Telegram
        if use_telegram and self.telegram and self.telegram.enabled:
            try:
                results.append(
                    self.telegram.send_alert(severity, title, message, details_str)
                )
            except Exception as e:
                logger.error(f"❌ Telegram 发送失败: {e}")
        
        # 发送邮件 (仅严重和警告告警)
        if use_email and self.email and self.email.enabled and severity in ['CRITICAL', 'WARNING']:
            try:
                results.append(
                    self.email.send_alert_email(severity, title, message, details)
                )
            except Exception as e:
                logger.error(f"❌ 邮件发送失败: {e}")
        
        return any(results) if results else True
    
    def on_health_check_failure(self, error: str = '') -> bool:
        """
        处理健康检查失败
        
        Args:
            error: 错误信息
            
        Returns:
            bool: 是否发送了告警
        """
        with self.lock:
            self.failed_check_count += 1
        
        # 连续 3 次失败才发送告警
        threshold = 3
        
        if self.failed_check_count >= threshold:
            return self.send_alert(
                severity='CRITICAL',
                title='服务健康检查连续失败',
                message=f'健康检查连续失败 {self.failed_check_count} 次',
                details={
                    '连续失败次数': self.failed_check_count,
                    '最后错误': error or 'Unknown',
                    '阈值': threshold
                }
            )
        
        logger.warning(f"⚠️ 健康检查失败 (第 {self.failed_check_count}/{threshold} 次)")
        return False
    
    def on_health_check_success(self):
        """健康检查成功后重置计数"""
        with self.lock:
            if self.failed_check_count > 0:
                logger.info(f"✅ 健康检查恢复 (之前连续失败 {self.failed_check_count} 次)")
            self.failed_check_count = 0
    
    def check_service_health(self) -> Dict:
        """
        执行完整健康检查并发送告警
        
        Returns:
            Dict: 健康检查结果
        """
        try:
            import requests
            
            # 调用健康检查端点
            response = requests.get(
                'http://localhost:8080/health',
                timeout=10
            )
            
            data = response.json()
            
            # 检查整体状态
            if data.get('status') == 'ok':
                self.on_health_check_success()
                return {'status': 'healthy', 'data': data}
            
            # 状态降级
            self.send_alert(
                severity='WARNING',
                title='服务状态降级',
                message=f"健康检查返回: {data.get('status')}",
                details=data
            )
            
            return {'status': 'degraded', 'data': data}
            
        except ImportError:
            # requests 未安装，使用 urllib
            return self._check_health_with_urllib()
            
        except Exception as e:
            return self._handle_health_check_error(str(e))
    
    def _check_health_with_urllib(self) -> Dict:
        """使用 urllib 检查健康状态"""
        try:
            import urllib.request
            
            req = urllib.request.Request(
                'http://localhost:8080/health',
                headers={'User-Agent': 'AlertManager/1.0'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                import json
                data = json.loads(response.read())
                
                if data.get('status') == 'ok':
                    self.on_health_check_success()
                    return {'status': 'healthy', 'data': data}
                
                return {'status': 'degraded', 'data': data}
                
        except Exception as e:
            return self._handle_health_check_error(str(e))
    
    def _handle_health_check_error(self, error: str) -> Dict:
        """处理健康检查错误"""
        self.on_health_check_failure(error)
        return {'status': 'error', 'error': error}
    
    def get_stats(self) -> Dict:
        """获取告警统计信息"""
        with self.lock:
            return {
                'total_alerts': sum(self.alert_counts.values()),
                'alert_counts': dict(self.alert_counts),
                'failed_check_count': self.failed_check_count,
                'active_cooldowns': {
                    name: int(time.time() - last_time)
                    for name, last_time in self.last_alerts.items()
                }
            }


# 全局实例
_alert_manager = None


def get_alert_manager() -> AlertManager:
    """获取告警管理器单例"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


# 便捷函数
def send_alert(severity: str, title: str, message: str, **kwargs) -> bool:
    """快捷发送告警"""
    return get_alert_manager().send_alert(severity, title, message, **kwargs)


def check_health() -> Dict:
    """快捷执行健康检查"""
    return get_alert_manager().check_service_health()
