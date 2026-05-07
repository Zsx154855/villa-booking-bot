#!/usr/bin/env python3
"""
Google Calendar 集成模块
使用 OAuth 2.0 进行身份验证和授权
"""

import os
import logging
import pickle
from datetime import datetime
from typing import Dict, Any, Optional

# Google API 客户端库
try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# OAuth 2.0 权限范围
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

# 日历ID（primary 表示主日历）
CALENDAR_ID = 'primary'

# Token 文件路径
TOKEN_FILE = './credentials/google_token.pickle'


class GoogleCalendarSync:
    """Google Calendar 同步类"""
    
    def __init__(self, credentials_path: str):
        """
        初始化 Google Calendar 客户端
        
        Args:
            credentials_path: Google Cloud 凭证 JSON 文件路径
        """
        if not GOOGLE_API_AVAILABLE:
            raise ImportError("Google API 库未安装，请运行: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2")
        
        self.credentials_path = credentials_path
        self.creds = self._get_credentials()
        self.service = build('calendar', 'v3', credentials=self.creds)
        logger.info("✅ Google Calendar 服务已初始化")
    
    def _get_credentials(self) -> Credentials:
        """
        获取 OAuth 2.0 凭证
        
        Returns:
            Google 认证凭证对象
        """
        creds = None
        
        # 检查是否存在 token 文件
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
        
        # 如果凭证无效或过期，则刷新或重新授权
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                logger.info("🔄 已刷新 Google 凭证")
            else:
                # 首次运行需要用户授权
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info("✅ 已获取 Google 授权")
            
            # 保存凭证
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)
        
        return creds
    
    def create_booking_event(self, booking_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        在 Google Calendar 中创建预订事件
        
        Args:
            booking_info: 预订信息字典，包含:
                - summary: 事件标题
                - description: 事件描述
                - location: 地点
                - start_date: 开始日期 (YYYY-MM-DD)
                - end_date: 结束日期 (YYYY-MM-DD)
                - booking_id: 预订ID
        
        Returns:
            创建结果字典
        """
        try:
            # 构造事件对象
            event = {
                'summary': booking_info.get('summary', '别墅预订'),
                'location': booking_info.get('location', ''),
                'description': booking_info.get('description', ''),
                'colorId': 5,  # 黄色，用于表示预订
                'start': {
                    'date': booking_info.get('start_date'),
                },
                'end': {
                    'date': booking_info.get('end_date'),
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 提前1天邮件提醒
                        {'method': 'popup', 'minutes': 60},  # 提前1小时弹窗提醒
                    ],
                },
                'extendedProperties': {
                    'private': {
                        'booking_id': booking_info.get('booking_id', ''),
                        'source': 'villa-booking-bot'
                    }
                }
            }
            
            # 创建事件
            created_event = self.service.events().insert(
                calendarId=CALENDAR_ID,
                body=event
            ).execute()
            
            logger.info(f"✅ Google Calendar 事件已创建: {created_event['id']}")
            
            return {
                'success': True,
                'event_id': created_event['id'],
                'html_link': created_event.get('htmlLink'),
                'calendar': 'google'
            }
        
        except Exception as e:
            logger.error(f"❌ 创建 Google Calendar 事件失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'calendar': 'google'
            }
    
    def update_booking_event(self, event_id: str, booking_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新预订事件
        
        Args:
            event_id: 事件ID
            booking_info: 更新的预订信息
        
        Returns:
            更新结果字典
        """
        try:
            # 先获取现有事件
            event = self.service.events().get(
                calendarId=CALENDAR_ID,
                eventId=event_id
            ).execute()
            
            # 更新事件信息
            if 'summary' in booking_info:
                event['summary'] = booking_info['summary']
            if 'location' in booking_info:
                event['location'] = booking_info['location']
            if 'description' in booking_info:
                event['description'] = booking_info['description']
            if 'start_date' in booking_info:
                event['start']['date'] = booking_info['start_date']
            if 'end_date' in booking_info:
                event['end']['date'] = booking_info['end_date']
            
            # 更新事件
            updated_event = self.service.events().update(
                calendarId=CALENDAR_ID,
                eventId=event_id,
                body=event
            ).execute()
            
            logger.info(f"✅ Google Calendar 事件已更新: {event_id}")
            
            return {
                'success': True,
                'event_id': updated_event['id'],
                'html_link': updated_event.get('htmlLink'),
                'calendar': 'google'
            }
        
        except Exception as e:
            logger.error(f"❌ 更新 Google Calendar 事件失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'calendar': 'google'
            }
    
    def delete_event(self, event_id: str) -> Dict[str, Any]:
        """
        删除事件
        
        Args:
            event_id: 事件ID
        
        Returns:
            删除结果字典
        """
        try:
            self.service.events().delete(
                calendarId=CALENDAR_ID,
                eventId=event_id
            ).execute()
            
            logger.info(f"✅ Google Calendar 事件已删除: {event_id}")
            
            return {
                'success': True,
                'event_id': event_id,
                'calendar': 'google'
            }
        
        except Exception as e:
            logger.error(f"❌ 删除 Google Calendar 事件失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'calendar': 'google'
            }
    
    def get_event_by_booking_id(self, booking_id: str) -> Optional[Dict[str, Any]]:
        """
        根据预订ID查找事件
        
        Args:
            booking_id: 预订ID
        
        Returns:
            事件字典，如果未找到则返回 None
        """
        try:
            # 获取所有事件
            now = datetime.utcnow().isoformat() + 'Z'
            events_result = self.service.events().list(
                calendarId=CALENDAR_ID,
                timeMin=now,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # 查找匹配的事件
            for event in events:
                extended_properties = event.get('extendedProperties', {}).get('private', {})
                if extended_properties.get('booking_id') == booking_id:
                    return event
            
            return None
        
        except Exception as e:
            logger.error(f"❌ 查找事件失败: {e}")
            return None
    
    def check_date_availability(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        检查日期范围内的预订情况
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
        
        Returns:
            可用性检查结果
        """
        try:
            # 查询日期范围内的事件
            time_min = f"{start_date}T00:00:00Z"
            time_max = f"{end_date}T23:59:59Z"
            
            events_result = self.service.events().list(
                calendarId=CALENDAR_ID,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            return {
                'available': True,
                'events': events,
                'calendar': 'google'
            }
        
        except Exception as e:
            logger.error(f"❌ 检查可用性失败: {e}")
            return {
                'available': False,
                'error': str(e),
                'calendar': 'google'
            }
