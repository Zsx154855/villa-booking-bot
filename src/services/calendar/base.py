"""
Taimili Villa Booking - Calendar Base Module
日历服务基类，定义统一接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class EventStatus(Enum):
    """事件状态"""
    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"


@dataclass
class CalendarEvent:
    """日历事件"""
    id: str
    title: str
    start: datetime
    end: datetime
    description: Optional[str] = None
    location: Optional[str] = None
    status: EventStatus = EventStatus.CONFIRMED
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'title': self.title,
            'start': self.start.isoformat(),
            'end': self.end.isoformat(),
            'description': self.description,
            'location': self.location,
            'status': self.status.value,
            'metadata': self.metadata
        }


@dataclass
class TimeSlot:
    """时间段"""
    start: datetime
    end: datetime
    available: bool = True
    event_id: Optional[str] = None


class CalendarService(ABC):
    """日历服务抽象基类"""
    
    @abstractmethod
    async def create_event(self, event: CalendarEvent) -> str:
        """
        创建日历事件
        
        Args:
            event: 日历事件对象
            
        Returns:
            str: 事件ID
        """
        pass
    
    @abstractmethod
    async def update_event(self, event_id: str, event: CalendarEvent) -> bool:
        """
        更新日历事件
        
        Args:
            event_id: 事件ID
            event: 更新后的事件数据
            
        Returns:
            bool: 是否成功
        """
        pass
    
    @abstractmethod
    async def delete_event(self, event_id: str) -> bool:
        """
        删除日历事件
        
        Args:
            event_id: 事件ID
            
        Returns:
            bool: 是否成功
        """
        pass
    
    @abstractmethod
    async def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        """
        获取日历事件
        
        Args:
            event_id: 事件ID
            
        Returns:
            CalendarEvent: 事件对象
        """
        pass
    
    @abstractmethod
    async def list_events(self, start: datetime, end: datetime) -> List[CalendarEvent]:
        """
        获取时间范围内的事件列表
        
        Args:
            start: 开始时间
            end: 结束时间
            
        Returns:
            List[CalendarEvent]: 事件列表
        """
        pass
    
    @abstractmethod
    async def check_availability(self, start: datetime, end: datetime) -> List[TimeSlot]:
        """
        检查时间段可用性
        
        Args:
            start: 开始时间
            end: 结束时间
            
        Returns:
            List[TimeSlot]: 可用时间段列表
        """
        pass
