#!/usr/bin/env python3
"""
Multi-Agent Router - 统一入口
提供与传统单Agent的切换机制
"""

import os
import uuid
import logging
from typing import Optional, Dict, Any

from .context import (
    AgentRequest, AgentResponse, AgentType, IntentType,
    UserContext, ConversationContext, ContextBuilder
)
from .coordinator import Coordinator

logger = logging.getLogger(__name__)

# Feature Flag
MULTI_AGENT_ENABLED = os.environ.get("MULTI_AGENT_ENABLED", "false").lower() in ("true", "1", "yes")

# 全局Coordinator实例
_coordinator: Optional[Coordinator] = None


def get_coordinator() -> Coordinator:
    """获取或创建Coordinator实例"""
    global _coordinator
    if _coordinator is None:
        _coordinator = Coordinator()
        logger.info("✅ Coordinator initialized")
    return _coordinator


class MultiAgentRouter:
    """
    Multi-Agent路由器
    
    提供统一的消息处理入口，支持：
    1. 多Agent协作模式（Multi-Agent）
    2. 单Agent回退模式（Single-Agent）
    """
    
    def __init__(self):
        self.multi_agent_enabled = MULTI_AGENT_ENABLED
        self.coordinator = get_coordinator() if self.multi_agent_enabled else None
        
        if self.multi_agent_enabled:
            logger.info("🔄 Multi-Agent mode ENABLED")
        else:
            logger.info("🔒 Single-Agent mode (fallback)")
    
    async def process_message(
        self,
        user_id: str,
        username: str,
        message: str,
        conversation_id: str = None,
        history_summary: str = "",
        recent_messages: list = None,
        **kwargs
    ) -> AgentResponse:
        """
        处理用户消息
        
        Args:
            user_id: 用户ID
            username: 用户名
            message: 用户消息
            conversation_id: 对话ID
            history_summary: 历史摘要
            recent_messages: 最近消息列表
            **kwargs: 其他参数
        
        Returns:
            AgentResponse: Agent响应
        """
        if not self.multi_agent_enabled:
            return self._fallback_response(message)
        
        # 生成请求ID
        request_id = str(uuid.uuid4())[:8]
        
        # 构建请求
        request = AgentRequest(
            request_id=request_id,
            source=AgentType.COORDINATOR,
            target=AgentType.COORDINATOR,
            intent=IntentType.UNKNOWN,
            user_context=UserContext(
                user_id=str(user_id),
                username=username,
                contact_name=kwargs.get("contact_name"),
                contact_phone=kwargs.get("contact_phone"),
                language=kwargs.get("language", "zh"),
                current_booking_step=kwargs.get("booking_step", "none")
            ),
            conversation_context=ConversationContext(
                conversation_id=conversation_id or request_id,
                history_summary=history_summary,
                recent_messages=recent_messages or [],
                active_villa_id=kwargs.get("active_villa_id"),
                active_region=kwargs.get("active_region")
            ),
            raw_message=message,
            parameters=kwargs.get("parameters", {})
        )
        
        # 添加消息到历史
        request.conversation_context.add_message("user", message)
        
        try:
            # 通过Coordinator处理
            response = await self.coordinator.process(request)
            
            # 添加assistant消息到历史
            request.conversation_context.add_message("assistant", response.message)
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Multi-Agent processing error: {e}")
            return self._fallback_response(message)
    
    def _fallback_response(self, message: str) -> AgentResponse:
        """降级响应 - 单Agent模式"""
        return ContextBuilder.create_success_response(
            request_id="fallback",
            source=AgentType.COORDINATOR,
            intent=IntentType.UNKNOWN,
            result={"mode": "single_agent"},
            message="⚠️ 当前Multi-Agent模式不可用，请使用传统命令进行操作。\n\n"
                    "可用命令：\n"
                    "/start - 开始使用\n"
                    "/book - 预订别墅\n"
                    "/villas - 查看别墅\n"
                    "/help - 获取帮助"
        )
    
    def get_status(self) -> Dict[str, Any]:
        """获取Router状态"""
        status = {
            "multi_agent_enabled": self.multi_agent_enabled,
            "mode": "multi_agent" if self.multi_agent_enabled else "single_agent",
            "coordinator_ready": self.coordinator is not None
        }
        
        if self.multi_agent_enabled and self.coordinator:
            status["registered_agents"] = {
                agent_type.value: True 
                for agent_type in self.coordinator.agents.keys()
            }
        
        return status


# 全局Router实例
router = MultiAgentRouter()


async def process_message(
    user_id: str,
    username: str,
    message: str,
    **kwargs
) -> AgentResponse:
    """
    快捷函数：处理用户消息
    """
    return await router.process_message(
        user_id=user_id,
        username=username,
        message=message,
        **kwargs
    )


def get_router_status() -> Dict[str, Any]:
    """获取Router状态"""
    return router.get_status()


def enable_multi_agent():
    """启用Multi-Agent模式（运行时）"""
    global MULTI_AGENT_ENABLED, router
    MULTI_AGENT_ENABLED = True
    router = MultiAgentRouter()
    logger.info("✅ Multi-Agent mode enabled at runtime")


def disable_multi_agent():
    """禁用Multi-Agent模式（运行时）"""
    global MULTI_AGENT_ENABLED, router
    MULTI_AGENT_ENABLED = False
    router = MultiAgentRouter()
    logger.info("🔒 Multi-Agent mode disabled at runtime")
