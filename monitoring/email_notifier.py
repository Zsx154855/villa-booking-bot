#!/usr/bin/env python3
"""
邮件通知模块
支持 SendGrid API 和 SMTP 两种发送方式
"""

import os
import logging
from typing import List, Dict
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 尝试导入 SendGrid
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False

# SMTP 支持
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class EmailNotifier:
    """邮件通知器"""
    
    def __init__(self):
        # SMTP 配置
        self.smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', 587))
        self.smtp_user = os.environ.get('SMTP_USER')
        self.smtp_password = os.environ.get('SMTP_PASSWORD')
        self.from_email = os.environ.get('FROM_EMAIL', self.smtp_user)
        
        # 告警邮件接收者
        alert_emails = os.environ.get('ALERT_EMAILS', '')
        self.to_emails = [e.strip() for e in alert_emails.split(',') if e.strip()]
        
        # SendGrid 配置
        self.sendgrid_key = os.environ.get('SENDGRID_API_KEY')
        
        if not self.to_emails:
            logger.warning("⚠️ 邮件通知配置不完整: 未设置 ALERT_EMAILS")
            self.enabled = False
        elif not (self.smtp_user and self.smtp_password or self.sendgrid_key):
            logger.warning("⚠️ 邮件通知配置不完整: 缺少认证信息")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("✅ 邮件通知器已初始化")
    
    def send_email(self, subject: str, html_content: str, text_content: str = '') -> bool:
        """
        发送邮件
        
        Args:
            subject: 邮件主题
            html_content: HTML 格式内容
            text_content: 纯文本内容 (可选)
            
        Returns:
            bool: 发送是否成功
        """
        if not self.enabled:
            logger.info(f"📧 [模拟发送邮件] {subject}")
            return True
        
        # 优先使用 SendGrid
        if SENDGRID_AVAILABLE and self.sendgrid_key:
            return self._send_via_sendgrid(subject, html_content)
        
        # 降级到 SMTP
        return self._send_via_smtp(subject, html_content, text_content)
    
    def _send_via_sendgrid(self, subject: str, html_content: str) -> bool:
        """通过 SendGrid 发送"""
        try:
            sg = SendGridAPIClient(self.sendgrid_key)
            
            message = Mail(
                from_email=self.from_email,
                to_emails=self.to_emails,
                subject=f"[Taimili Bot] {subject}",
                html_content=html_content
            )
            
            response = sg.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"✅ SendGrid 邮件发送成功: {subject}")
                return True
            else:
                logger.error(f"❌ SendGrid 发送失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ SendGrid 异常: {e}")
            return False
    
    def _send_via_smtp(self, subject: str, html_content: str, text_content: str) -> bool:
        """通过 SMTP 发送"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[Taimili Bot] {subject}"
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            
            # 添加纯文本版本
            if text_content:
                msg.attach(MIMEText(text_content, 'plain'))
            
            # 添加 HTML 版本
            msg.attach(MIMEText(html_content, 'html'))
            
            # 发送
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, self.to_emails, msg.as_string())
            
            logger.info(f"✅ SMTP 邮件发送成功: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"❌ SMTP 发送失败: {e}")
            return False
    
    def send_alert_email(self, severity: str, title: str, message: str, details: Dict = None) -> bool:
        """
        发送告警邮件
        
        Args:
            severity: 告警级别 (CRITICAL/WARNING/INFO)
            title: 告警标题
            message: 告警消息
            details: 详细信息字典
        """
        severity_colors = {
            'CRITICAL': '#dc3545',  # 红色
            'WARNING': '#ffc107',   # 黄色
            'INFO': '#17a2b8'       # 蓝色
        }
        color = severity_colors.get(severity, '#6c757d')
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .header {{ background-color: {color}; color: white; padding: 20px; }}
        .header h2 {{ margin: 0; font-size: 24px; }}
        .content {{ padding: 20px; }}
        .detail {{ background-color: #f8f9fa; padding: 15px; margin: 10px 0; border-left: 4px solid {color}; border-radius: 4px; }}
        .detail ul {{ margin: 5px 0; padding-left: 20px; }}
        .detail li {{ margin: 5px 0; }}
        .footer {{ color: #6c757d; font-size: 12px; padding: 15px; text-align: center; border-top: 1px solid #eee; }}
        .button {{ display: inline-block; padding: 10px 20px; background-color: {color}; color: white; text-decoration: none; border-radius: 4px; margin-top: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🚨 {severity}: {title}</h2>
        </div>
        <div class="content">
            <p>{message}</p>
            
            <div class="detail">
                <strong>📊 告警信息</strong>
                <ul>
                    <li><strong>服务:</strong> Taimili Villa Bot v4.0</li>
                    <li><strong>级别:</strong> {severity}</li>
                    <li><strong>时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
                </ul>
            </div>
            
            {self._format_details_html(details) if details else ''}
            
            <p style="margin-top: 20px;">
                <a href="https://taimili-villa-bot.onrender.com/health" class="button">
                    查看健康状态
                </a>
            </p>
        </div>
        <div class="footer">
            此邮件由 Taimili Bot 监控系统自动发送<br>
            如需退订，请联系管理员
        </div>
    </div>
</body>
</html>
"""
        
        text_content = f"""
{severity}: {title}

{message}

服务: Taimili Villa Bot v4.0
级别: {severity}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{details if details else ''}

链接: https://taimili-villa-bot.onrender.com/health
"""
        
        return self.send_email(
            subject=f"{severity} - {title}",
            html_content=html,
            text_content=text_content
        )
    
    def _format_details_html(self, details: Dict) -> str:
        """格式化详情为 HTML"""
        items = []
        for key, value in details.items():
            if isinstance(value, dict):
                items.append(f"<li><strong>{key}:</strong></li>")
                items.append("<ul>")
                for k, v in value.items():
                    items.append(f"<li>{k}: {v}</li>")
                items.append("</ul>")
            else:
                items.append(f"<li><strong>{key}:</strong> {value}</li>")
        
        return f'''
        <div class="detail">
            <strong>📋 详细信息</strong>
            <ul>
                {"".join(items)}
            </ul>
        </div>
        '''
    
    def send_test_email(self) -> bool:
        """发送测试邮件"""
        return self.send_alert_email(
            severity='INFO',
            title='测试邮件',
            message='这是一封测试邮件，用于验证邮件通知配置是否正确。',
            details={
                '配置状态': '正常',
                '收件人': ', '.join(self.to_emails)
            }
        )


# 全局实例
_email_notifier = None


def get_email_notifier() -> EmailNotifier:
    """获取邮件通知器单例"""
    global _email_notifier
    if _email_notifier is None:
        _email_notifier = EmailNotifier()
    return _email_notifier
