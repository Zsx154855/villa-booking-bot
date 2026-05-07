#!/usr/bin/env python3
"""
Hermes三层记忆架构 - 记忆系统包

包含：
- base.py: 基类和接口定义
- working_memory.py: Layer 1 工作记忆
- episodic_memory.py: Layer 2 情景记忆
- semantic_memory.py: Layer 3 语义记忆
"""

from typing import Dict, Any

from .base import (
    MemoryLayer,
    IntentType,
    ConversationContext,
    UserProfileSummary,
    BaseMemoryManager
)

from .working_memory import WorkingMemoryManager, working_memory
from .episodic_memory import EpisodicMemoryManager, episodic_memory
from .semantic_memory import SemanticMemoryManager, semantic_memory


class MemorySystem:
    """
    三层记忆系统统一接口
    
    提供统一的API访问三层记忆
    """
    
    def __init__(self):
        self.working = working_memory
        self.episodic = episodic_memory
        self.semantic = semantic_memory
    
    def get_context_for_user(self, user_id: str, chat_id: int) -> Dict:
        """
        获取用户的完整上下文
        
        整合三层记忆，返回给LLM使用
        """
        # 1. 获取工作记忆
        wm_context = self.working.get_or_create_session(user_id, chat_id)
        
        # 2. 获取情景记忆（用户画像）
        profile = self.episodic.load(user_id)
        
        # 3. 构建语义记忆上下文
        region = wm_context.selected_region if wm_context else None
        villa_ids = wm_context.mentioned_villas if wm_context else []
        intent = wm_context.current_intent if wm_context else "unknown"
        
        semantic_contexts = self.semantic.get_context_for_intent(
            intent,
            region=region,
            villa_ids=villa_ids
        )
        
        # 4. 整合所有上下文
        return {
            "working": wm_context.to_dict() if wm_context else {},
            "episodic": profile.to_dict() if profile else {},
            "semantic": semantic_contexts,
            "summary": {
                "user_preferences": self.episodic.get_personalization_context(user_id),
                "conversation_state": self.working.get_context_summary(wm_context.session_id) if wm_context else "新对话",
                "working_memory_tokens": self.working.get_token_estimate(wm_context.session_id) if wm_context else 0
            }
        }
    
    def update_after_interaction(self, user_id: str, session_id: str, interaction_data: Dict):
        """
        交互后更新记忆
        
        将工作记忆中的信息聚合到情景记忆
        """
        # 更新情景记忆
        self.episodic.update_from_working_memory(user_id, interaction_data)
        
        # 记录交互摘要
        self.episodic.add_interaction_record(
            user_id,
            interaction_type=interaction_data.get('current_intent', 'unknown'),
            summary=interaction_data.get('summary', ''),
            metadata=interaction_data.get('metadata', {})
        )
    
    def cleanup(self):
        """清理过期数据"""
        return self.working.cleanup_expired()


# 全局单例
memory_system = MemorySystem()

__all__ = [
    'MemoryLayer',
    'IntentType',
    'ConversationContext',
    'UserProfileSummary',
    'BaseMemoryManager',
    'WorkingMemoryManager',
    'EpisodicMemoryManager',
    'SemanticMemoryManager',
    'working_memory',
    'episodic_memory',
    'semantic_memory',
    'memory_system'
]
