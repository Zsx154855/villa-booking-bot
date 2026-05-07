#!/usr/bin/env python3
"""
Hermes三层记忆架构 - 基类模块
定义统一的记忆接口和数据结构
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from enum import Enum

logger = logging.getLogger(__name__)


class MemoryLayer(Enum):
    """记忆层级枚举"""
    WORKING = "working"      # 工作记忆 - 当前对话上下文
    EPISODIC = "episodic"   # 情景记忆 - 历史交互记录
    SEMANTIC = "semantic"   # 语义记忆 - 知识库和规则


class IntentType(Enum):
    """用户意图类型"""
    BOOKING = "booking"           # 预订
    INQUIRY = "inquiry"           # 咨询
    MODIFICATION = "modification" # 修改
    CANCELLATION = "cancellation" # 取消
    COMPLAINT = "complaint"       # 投诉
    PRAISE = "praise"             # 表扬
    UNKNOWN = "unknown"           # 未知


@dataclass
class ConversationContext:
    """对话上下文 - 用于Working Memory"""
    session_id: str
    user_id: str
    language: str = "zh"          # 用户语言偏好
    current_intent: str = IntentType.UNKNOWN.value
    booking_progress: int = -1    # 预订进度 (-1=未开始, 0-6=各步骤)
    
    # 当前预订状态
    selected_region: Optional[str] = None
    selected_villa: Optional[str] = None
    checkin_date: Optional[str] = None
    checkout_date: Optional[str] = None
    guest_count: int = 0
    
    # 对话历史摘要（轻量）
    recent_messages: List[Dict] = field(default_factory=list)
    mentioned_villas: List[str] = field(default_factory=list)
    preferences_mentioned: List[str] = field(default_factory=list)
    
    # 时间戳
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationContext':
        """从字典创建"""
        return cls(**data)
    
    def update_timestamp(self):
        """更新修改时间"""
        self.updated_at = datetime.now().isoformat()
    
    def add_message(self, role: str, content: str):
        """添加消息到历史（保持轻量，最多10条）"""
        self.recent_messages.append({
            "role": role,
            "content": content[:200],  # 截断过长内容
            "time": datetime.now().isoformat()
        })
        if len(self.recent_messages) > 10:
            self.recent_messages = self.recent_messages[-10:]
        self.update_timestamp()


@dataclass
class UserProfileSummary:
    """用户画像摘要 - 用于Episodic Memory"""
    user_id: str
    
    # 基本信息
    username: Optional[str] = None
    preferred_language: str = "zh"
    
    # 偏好分析
    preferred_regions: List[str] = field(default_factory=list)  # 常去地区
    preferred_villas: List[str] = field(default_factory=list) # 喜欢的别墅ID
    preferred_price_range: tuple = field(default_factory=lambda: (0, 5000))  # 价格偏好
    preferred_room_type: Optional[str] = None                   # 房型偏好
    
    # 行为统计
    total_bookings: int = 0
    total_spent: float = 0.0
    cancellation_count: int = 0
    average_stay_days: float = 0.0
    
    # 互动特征
    avg_response_length: str = "normal"  # short/normal/long
    is_repeat_customer: bool = False
    last_interaction: Optional[str] = None
    
    # 标签
    tags: List[str] = field(default_factory=list)  # 高价值/价格敏感/家庭游/情侣等
    
    # 交互历史摘要
    interaction_count: int = 0
    last_interaction_types: List[str] = field(default_factory=list)
    common_questions: List[str] = field(default_factory=list)
    
    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        # 处理元组序列化
        if isinstance(data['preferred_price_range'], tuple):
            data['preferred_price_range'] = list(data['preferred_price_range'])
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfileSummary':
        """从字典创建"""
        if isinstance(data.get('preferred_price_range'), list):
            data['preferred_price_range'] = tuple(data['preferred_price_range'])
        return cls(**data)


class BaseMemoryManager(ABC):
    """记忆管理器基类"""
    
    @abstractmethod
    def load(self, key: str) -> Optional[Any]:
        """加载记忆"""
        pass
    
    @abstractmethod
    def save(self, key: str, data: Any) -> bool:
        """保存记忆"""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """删除记忆"""
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """清空所有记忆"""
        pass
