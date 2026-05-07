#!/usr/bin/env python3
"""
Taimili Villa Booking System - Calendar Synchronization Module
支持 Google Calendar 和飞书日历同步
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 尝试导入各平台日历模块
try:
    from .google_calendar import GoogleCalendarSync
    GOOGLE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Google Calendar 模块未安装: {e}")
    GOOGLE_AVAILABLE = False

try:
    from .feishu_calendar import FeishuCalendarSync
    FEISHU_AVAILABLE = True
except ImportError as e:
    logger.warning(f"飞书日历模块未安装: {e}")
    FEISHU_AVAILABLE = False


class CalendarSync:
    """
    日历同步管理器
    统一接口，支持多平台日历同步
    """
    
    def __init__(self):
        self.google = None
        self.feishu = None
        
        # 初始化 Google Calendar
        if GOOGLE_AVAILABLE:
            creds_path = os.environ.get('GOOGLE_CREDENTIALS_PATH', './credentials/google_credentials.json')
            if os.path.exists(creds_path):
                self.google = GoogleCalendarSync(creds_path)
                logger.info("✅ Google Calendar 已初始化")
            else:
                logger.warning(f"⚠️ Google 凭证文件不存在: {creds_path}")
        
        # 初始化飞书日历
        if FEISHU_AVAILABLE:
            app_id = os.environ.get('FEISHU_APP_ID')
            app_secret = os.environ.get('FEISHU_APP_SECRET')
            if app_id and app_secret:
                self.feishu = FeishuCalendarSync(app_id, app_secret)
                logger.info("✅ 飞书日历已初始化")
            else:
                logger.warning("⚠️ 飞书凭证未配置 (FEISHU_APP_ID, FEISHU_APP_SECRET)")
    
    def create_booking_event(self, booking_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        为预订创建日历事件
        
        Args:
            booking_info: 预订信息字典，包含:
                - booking_id: 预订ID
                - villa_name: 别墅名称
                - villa_location: 别墅位置
                - guest_name: 客人姓名
                - guest_phone: 客人电话
                - check_in_date: 入住日期 (YYYY-MM-DD)
                - check_out_date: 退房日期 (YYYY-MM-DD)
                - total_price: 总价
                - status: 预订状态
        
        Returns:
            同步结果字典
        """
        results = {
            'success': True,
            'google': None,
            'feishu': None,
            'errors': []
        }
        
        # 构造日历事件详情
        event_details = {
            'summary': f"🏠 {booking_info.get('villa_name', '别墅预订')} - {booking_info.get('guest_name', '客人')}",
            'description': self._build_description(booking_info),
            'location': booking_info.get('villa_location', ''),
            'start_date': booking_info.get('check_in_date'),
            'end_date': booking_info.get('check_out_date'),
            'booking_id': booking_info.get('booking_id')
        }
        
        # 同步到 Google Calendar
        if self.google:
            try:
                result = self.google.create_booking_event(event_details)
                results['google'] = result
                if not result.get('success'):
                    results['errors'].append(f"Google: {result.get('error')}")
            except Exception as e:
                logger.error(f"Google Calendar 同步失败: {e}")
                results['errors'].append(f"Google: {str(e)}")
        
        # 同步到飞书日历
        if self.feishu:
            try:
                result = self.feishu.create_booking_event(event_details)
                results['feishu'] = result
                if not result.get('success'):
                    results['errors'].append(f"飞书: {result.get('error')}")
            except Exception as e:
                logger.error(f"飞书日历同步失败: {e}")
                results['errors'].append(f"飞书: {str(e)}")
        
        # 如果两个都失败
        if not results['google'] and not results['feishu']:
            results['success'] = False
            results['errors'].append("所有日历平台均不可用")
        
        return results
    
    def cancel_booking_event(self, booking_id: str, calendar_event_ids: Dict[str, str]) -> Dict[str, Any]:
        """
        取消预订日历事件
        
        Args:
            booking_id: 预订ID
            calendar_event_ids: 各平台的事件ID，格式:
                {'google': 'event_id', 'feishu': 'event_id'}
        
        Returns:
            取消结果字典
        """
        results = {
            'success': True,
            'google': None,
            'feishu': None,
            'errors': []
        }
        
        # 从 Google Calendar 删除
        if self.google and calendar_event_ids.get('google'):
            try:
                result = self.google.delete_event(calendar_event_ids['google'])
                results['google'] = result
            except Exception as e:
                logger.error(f"Google Calendar 删除事件失败: {e}")
                results['errors'].append(f"Google: {str(e)}")
        
        # 从飞书日历删除
        if self.feishu and calendar_event_ids.get('feishu'):
            try:
                result = self.feishu.delete_event(calendar_event_ids['feishu'])
                results['feishu'] = result
            except Exception as e:
                logger.error(f"飞书日历删除事件失败: {e}")
                results['errors'].append(f"飞书: {str(e)}")
        
        return results
    
    def check_availability(self, check_in: str, check_out: str, villa_id: str) -> Dict[str, Any]:
        """
        检查日期是否可用（用于防止超订）
        
        Args:
            check_in: 入住日期 (YYYY-MM-DD)
            check_out: 退房日期 (YYYY-MM-DD)
            villa_id: 别墅ID
        
        Returns:
            可用性检查结果
        """
        conflicts = []
        
        # TODO: 从数据库查询该别墅在日期范围内的现有预订
        # 目前仅做占位，后续集成数据库查询
        
        return {
            'available': len(conflicts) == 0,
            'conflicts': conflicts
        }
    
    def _build_description(self, booking_info: Dict[str, Any]) -> str:
        """构建日历事件描述"""
        lines = [
            f"📋 预订编号: {booking_info.get('booking_id', 'N/A')}",
            f"👤 客人姓名: {booking_info.get('guest_name', 'N/A')}",
            f"📞 联系电话: {booking_info.get('guest_phone', 'N/A')}",
            f"📅 入住日期: {booking_info.get('check_in_date', 'N/A')}",
            f"📅 退房日期: {booking_info.get('check_out_date', 'N/A')}",
            f"💰 总价: {booking_info.get('total_price', 'N/A')}",
            f"📊 预订状态: {booking_info.get('status', 'N/A')}",
        ]
        
        if booking_info.get('special_requests'):
            lines.append(f"📝 特殊要求: {booking_info.get('special_requests')}")
        
        return '\n'.join(lines)


# 全局实例（延迟初始化）
_calendar_sync = None

def get_calendar_sync() -> CalendarSync:
    """获取日历同步实例"""
    global _calendar_sync
    if _calendar_sync is None:
        _calendar_sync = CalendarSync()
    return _calendar_sync
