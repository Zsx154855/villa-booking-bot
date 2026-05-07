#!/usr/bin/env python3
"""
Context Protocol - Multi-Agent通信协议
定义Agent间传递的上下文结构，防止信息衰减
"""

import json
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class IntentType(Enum):
    """意图类型枚举"""
    BOOKING = "booking"           # 预订相关
    SERVICE = "service"           # 运营服务
    INFO = "info"                 # 信息查询
    PAYMENT = "payment"          # 支付相关
    UNKNOWN = "unknown"           # 未知


class AgentType(Enum):
    """Agent类型枚举"""
    COORDINATOR = "coordinator"
    BOOKING = "booking_agent"
    SERVICE = "service_agent"
    INFO = "info_agent"
    PAYMENT = "payment_agent"


@dataclass
class UserContext:
    """用户上下文"""
    user_id: str
    username: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    language: str = "zh"
    current_booking_step: str = "none"
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ConversationContext:
    """对话上下文 - 防止电话游戏衰减"""
    conversation_id: str
    history_summary: str = ""
    recent_messages: List[Dict] = field(default_factory=list)
    pending_confirmations: List[str] = field(default_factory=list)
    active_villa_id: Optional[str] = None
    active_region: Optional[str] = None
    
    def add_message(self, role: str, content: str):
        """添加消息到历史"""
        self.recent_messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        # 保持最近10条消息
        if len(self.recent_messages) > 10:
            self.recent_messages = self.recent_messages[-10:]
    
    def update_summary(self, summary: str):
        """更新对话摘要"""
        self.history_summary = summary
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class AgentRequest:
    """Agent请求结构"""
    request_id: str
    source: AgentType
    target: AgentType
    intent: IntentType
    user_context: UserContext
    conversation_context: ConversationContext
    raw_message: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "request_id": self.request_id,
            "source": self.source.value,
            "target": self.target.value,
            "intent": self.intent.value,
            "user_context": self.user_context.to_dict(),
            "conversation_context": self.conversation_context.to_dict(),
            "raw_message": self.raw_message,
            "parameters": self.parameters,
            "timestamp": self.timestamp
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class AgentResponse:
    """Agent响应结构"""
    request_id: str
    source: AgentType
    success: bool
    intent: IntentType
    result: Dict[str, Any]
    message: str
    should_forward_to_user: bool = True
    suggested_actions: List[str] = field(default_factory=list)
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "request_id": self.request_id,
            "source": self.source.value,
            "success": self.success,
            "intent": self.intent.value,
            "result": self.result,
            "message": self.message,
            "should_forward_to_user": self.should_forward_to_user,
            "suggested_actions": self.suggested_actions,
            "error": self.error,
            "timestamp": self.timestamp
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'AgentResponse':
        data = json.loads(json_str)
        data['source'] = AgentType(data['source'])
        data['intent'] = IntentType(data['intent'])
        return cls(**data)


class ContextBuilder:
    """Context构建器 - 简化创建过程"""
    
    @staticmethod
    def create_request(
        request_id: str,
        source: AgentType,
        target: AgentType,
        intent: IntentType,
        user_id: str,
        raw_message: str,
        username: str = None,
        **kwargs
    ) -> AgentRequest:
        """创建标准请求"""
        user_ctx = UserContext(
            user_id=user_id,
            username=username,
            contact_name=kwargs.get('contact_name'),
            contact_phone=kwargs.get('contact_phone'),
            language=kwargs.get('language', 'zh'),
            current_booking_step=kwargs.get('booking_step', 'none')
        )
        
        conv_ctx = ConversationContext(
            conversation_id=kwargs.get('conversation_id', request_id),
            history_summary=kwargs.get('history_summary', ''),
            recent_messages=kwargs.get('recent_messages', []),
            active_villa_id=kwargs.get('active_villa_id'),
            active_region=kwargs.get('active_region')
        )
        
        return AgentRequest(
            request_id=request_id,
            source=source,
            target=target,
            intent=intent,
            user_context=user_ctx,
            conversation_context=conv_ctx,
            raw_message=raw_message,
            parameters=kwargs.get('parameters', {})
        )
    
    @staticmethod
    def create_success_response(
        request_id: str,
        source: AgentType,
        intent: IntentType,
        result: Dict,
        message: str,
        **kwargs
    ) -> AgentResponse:
        """创建成功响应"""
        return AgentResponse(
            request_id=request_id,
            source=source,
            success=True,
            intent=intent,
            result=result,
            message=message,
            should_forward_to_user=kwargs.get('should_forward', True),
            suggested_actions=kwargs.get('suggested_actions', [])
        )
    
    @staticmethod
    def create_error_response(
        request_id: str,
        source: AgentType,
        intent: IntentType,
        error: str,
        message: str = ""
    ) -> AgentResponse:
        """创建错误响应"""
        return AgentResponse(
            request_id=request_id,
            source=source,
            success=False,
            intent=intent,
            result={},
            message=message or f"处理失败: {error}",
            error=error
        )
