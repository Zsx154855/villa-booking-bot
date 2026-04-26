"""
Taimili Villa Booking - Google Calendar Module
Google Calendar集成
"""

import os
from datetime import datetime, timedelta
from typing import Optional, List

from .base import CalendarService, CalendarEvent, TimeSlot, EventStatus

# Google Calendar API
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    GOOGLE_CALENDAR_AVAILABLE = True
except ImportError:
    GOOGLE_CALENDAR_AVAILABLE = False


class GoogleCalendarService(CalendarService):
    """Google Calendar服务实现"""
    
    def __init__(self, credentials_path: str, calendar_id: str = 'primary'):
        """
        初始化Google Calendar服务
        
        Args:
            credentials_path: 服务账号凭据JSON文件路径
            calendar_id: 日历ID（默认使用主日历）
        """
        if not GOOGLE_CALENDAR_AVAILABLE:
            raise ImportError("google-api-python-client未安装，请运行: pip install google-api-python-client google-auth")
        
        self.calendar_id = calendar_id
        self.credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        self.service = build('calendar', 'v3', credentials=self.credentials)
    
    async def create_event(self, event: CalendarEvent) -> str:
        """创建Google Calendar事件"""
        event_body = {
            'summary': event.title,
            'description': event.description or '',
            'start': {
                'dateTime': event.start.isoformat(),
                'timeZone': 'Asia/Bangkok'
            },
            'end': {
                'dateTime': event.end.isoformat(),
                'timeZone': 'Asia/Bangkok'
            },
            'status': event.status.value
        }
        
        if event.location:
            event_body['location'] = event.location
        
        result = self.service.events().insert(
            calendarId=self.calendar_id,
            body=event_body
        ).execute()
        
        return result['id']
    
    async def update_event(self, event_id: str, event: CalendarEvent) -> bool:
        """更新Google Calendar事件"""
        event_body = {
            'summary': event.title,
            'description': event.description or '',
            'start': {
                'dateTime': event.start.isoformat(),
                'timeZone': 'Asia/Bangkok'
            },
            'end': {
                'dateTime': event.end.isoformat(),
                'timeZone': 'Asia/Bangkok'
            },
            'status': event.status.value
        }
        
        try:
            self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=event_body
            ).execute()
            return True
        except Exception:
            return False
    
    async def delete_event(self, event_id: str) -> bool:
        """删除Google Calendar事件"""
        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            return True
        except Exception:
            return False
    
    async def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        """获取Google Calendar事件"""
        try:
            result = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            
            return CalendarEvent(
                id=result['id'],
                title=result.get('summary', ''),
                start=datetime.fromisoformat(result['start']['dateTime'].replace('Z', '+00:00')),
                end=datetime.fromisoformat(result['end']['dateTime'].replace('Z', '+00:00')),
                description=result.get('description'),
                location=result.get('location'),
                status=EventStatus(result.get('status', 'confirmed'))
            )
        except Exception:
            return None
    
    async def list_events(self, start: datetime, end: datetime) -> List[CalendarEvent]:
        """获取时间范围内的事件列表"""
        events_result = self.service.events().list(
            calendarId=self.calendar_id,
            timeMin=start.isoformat() + 'Z',
            timeMax=end.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = []
        for item in events_result.get('items', []):
            events.append(CalendarEvent(
                id=item['id'],
                title=item.get('summary', ''),
                start=datetime.fromisoformat(item['start']['dateTime'].replace('Z', '+00:00')),
                end=datetime.fromisoformat(item['end']['dateTime'].replace('Z', '+00:00')),
                description=item.get('description'),
                location=item.get('location'),
                status=EventStatus(item.get('status', 'confirmed'))
            ))
        
        return events
    
    async def check_availability(self, start: datetime, end: datetime) -> List[TimeSlot]:
        """检查时间段可用性"""
        events = await self.list_events(start, end)
        
        slots = []
        current = start
        
        for event in sorted(events, key=lambda e: e.start):
            if event.start > current:
                slots.append(TimeSlot(
                    start=current,
                    end=event.start,
                    available=True
                ))
            slots.append(TimeSlot(
                start=event.start,
                end=event.end,
                available=False,
                event_id=event.id
            ))
            current = max(current, event.end)
        
        if current < end:
            slots.append(TimeSlot(
                start=current,
                end=end,
                available=True
            ))
        
        return slots
