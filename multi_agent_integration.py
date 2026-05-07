#!/usr/bin/env python3
"""
Multi-Agent Integration - 与Telegram Bot集成
提供NLP消息处理和Agent路由
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 尝试导入Multi-Agent模块
try:
    from multi_agent import (
        router, 
        process_message, 
        get_router_status,
        MULTI_AGENT_ENABLED,
        AgentResponse,
        AgentType,
        IntentType
    )
    MULTI_AGENT_AVAILABLE = True
    logger.info(f"✅ Multi-Agent module loaded (enabled: {MULTI_AGENT_ENABLED})")
except ImportError as e:
    MULTI_AGENT_AVAILABLE = False
    MULTI_AGENT_ENABLED = False
    logger.warning(f"⚠️ Multi-Agent module not available: {e}")


async def handle_nlp_message(
    update, 
    context,
    message: str = None
) -> Optional[str]:
    """
    使用Multi-Agent处理自然语言消息
    
    Args:
        update: Telegram Update对象
        context: Telegram Context对象
        message: 要处理的消息（可选，默认从update获取）
    
    Returns:
        str: 响应消息，如果不需要处理返回None
    """
    if not MULTI_AGENT_AVAILABLE or not MULTI_AGENT_ENABLED:
        return None
    
    try:
        # 获取消息内容
        if message is None:
            if update.message:
                message = update.message.text
            elif update.callback_query:
                # callback query 不需要NLP处理
                return None
            else:
                return None
        
        # 获取用户信息
        user_id = update.effective_user.id if update.effective_user else "unknown"
        username = update.effective_user.username if update.effective_user else ""
        
        # 获取对话上下文
        conversation_id = str(context._chat_id) if hasattr(context, '_chat_id') else str(user_id)
        
        # 从user_data获取上下文
        booking_step = context.user_data.get('booking_step', 'none') if hasattr(context, 'user_data') else 'none'
        active_region = context.user_data.get('region', '') if hasattr(context, 'user_data') else ''
        active_villa_id = context.user_data.get('villa_id', '') if hasattr(context, 'user_data') else ''
        
        # 处理消息
        response = await process_message(
            user_id=str(user_id),
            username=username,
            message=message,
            conversation_id=conversation_id,
            booking_step=booking_step,
            active_region=active_region,
            active_villa_id=active_villa_id
        )
        
        # 记录路由信息
        if os.environ.get("DEBUG_MODE"):
            logger.info(f"🎯 Routed to {response.source.value}: intent={response.intent.value}")
        
        return response.message if response else None
        
    except Exception as e:
        logger.error(f"❌ NLP processing error: {e}")
        return None


def should_use_nlp(text: str) -> bool:
    """
    判断是否应该使用NLP处理
    
    Args:
        text: 用户输入文本
    
    Returns:
        bool: 是否使用NLP
    """
    if not MULTI_AGENT_ENABLED:
        return False
    
    # 检查是否是命令
    if text.startswith('/'):
        return False
    
    # 检查是否是简单响应（短且明确）
    short_patterns = ['是', '否', '好', '可以', '确定', '取消', '1', '2', '3']
    if text in short_patterns or len(text) <= 2:
        return False
    
    # 检查是否是日期输入
    import re
    if re.match(r'^\d{4}-\d{2}-\d{2}$', text):
        return False
    
    # 检查是否是数字输入
    if text.isdigit():
        return False
    
    return True


def get_multi_agent_status() -> dict:
    """获取Multi-Agent状态"""
    if not MULTI_AGENT_AVAILABLE:
        return {
            "available": False,
            "message": "Multi-Agent模块未安装"
        }
    
    return {
        "available": True,
        "enabled": MULTI_AGENT_ENABLED,
        **get_router_status()
    }


class MultiAgentMiddleware:
    """
    Multi-Agent中间件
    用于包装Telegram Handler
    """
    
    def __init__(self):
        self.enabled = MULTI_AGENT_ENABLED and MULTI_AGENT_AVAILABLE
    
    async def process(self, update, context) -> Optional[str]:
        """处理消息，返回响应或None"""
        if not self.enabled:
            return None
        
        # 只处理消息类型
        if not update.message:
            return None
        
        text = update.message.text
        if not text:
            return None
        
        # 决定是否使用NLP
        if not should_use_nlp(text):
            return None
        
        # 尝试使用NLP处理
        response = await handle_nlp_message(update, context, text)
        return response
    
    def wrap_handler(self, handler_func):
        """
        包装handler函数
        在原handler之前先尝试Multi-Agent处理
        """
        async def wrapped(update, context):
            # 尝试NLP处理
            response = await self.process(update, context)
            if response:
                await update.message.reply_text(response)
                return
            
            # 交给原handler处理
            return await handler_func(update, context)
        
        return wrapped


# 全局中间件实例
middleware = MultiAgentMiddleware()
