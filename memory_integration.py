#!/usr/bin/env python3
"""
Hermes三层记忆架构 - 与Bot的集成模块
在关键处理点集成三层记忆
"""

import logging
from typing import Dict, Any, Optional

from memory import memory_system, working_memory, episodic_memory, semantic_memory

logger = logging.getLogger(__name__)


class MemoryIntegration:
    """记忆系统集成类"""
    
    def __init__(self):
        self.memory = memory_system
    
    # ============ 消息入口处理 ============
    
    def on_message_received(self, user_id: str, chat_id: int, message: str) -> Dict[str, Any]:
        """
        消息接收时的记忆处理
        
        返回完整的上下文给Bot使用
        """
        # 1. 获取或创建工作记忆会话
        context = self.memory.working.get_or_create_session(user_id, chat_id)
        
        # 2. 添加用户消息到工作记忆
        self.memory.working.add_message(context.session_id, "user", message)
        
        # 3. 查询用户画像（情景记忆）
        profile = self.memory.episodic.load(user_id)
        
        # 4. 构建完整上下文
        full_context = {
            "session_id": context.session_id,
            "working_memory": context,
            "user_profile": profile,
            "user_preferences": self.memory.episodic.get_personalization_context(user_id),
            "conversation_summary": self.memory.working.get_context_summary(context.session_id)
        }
        
        return full_context
    
    def on_intent_detected(self, session_id: str, intent: str, entities: Dict = None):
        """检测到意图时更新工作记忆"""
        self.memory.working.update_intent(session_id, intent)
        
        if entities:
            self.memory.working.set_booking_data(session_id, **entities)
    
    def on_villa_mentioned(self, session_id: str, villa_id: str, villa_name: str):
        """记录用户提到的别墅"""
        ctx = self.memory.working.load(session_id)
        if ctx:
            if villa_id not in ctx.mentioned_villas:
                ctx.mentioned_villas.append(villa_id)
            self.memory.working.save(session_id, ctx)
    
    def on_preference_mentioned(self, session_id: str, preference: str):
        """记录用户提到的偏好"""
        ctx = self.memory.working.load(session_id)
        if ctx:
            if preference not in ctx.preferences_mentioned:
                ctx.preferences_mentioned.append(preference)
            self.memory.working.save(session_id, ctx)
    
    # ============ 预订流程处理 ============
    
    def on_region_selected(self, session_id: str, region: str):
        """地区选择时更新记忆"""
        self.memory.working.set_booking_data(session_id, selected_region=region)
    
    def on_villa_selected(self, session_id: str, villa_id: str):
        """别墅选择时更新记忆"""
        self.memory.working.set_booking_data(session_id, selected_villa=villa_id)
        self.on_villa_mentioned(session_id, villa_id, "")
    
    def on_booking_progress(self, session_id: str, progress: int):
        """预订进度更新"""
        self.memory.working.update_booking_progress(session_id, progress)
    
    def on_booking_completed(self, user_id: str, session_id: str, booking_data: Dict):
        """
        预订完成后的记忆处理
        
        将工作记忆聚合到情景记忆
        """
        ctx = self.memory.working.load(session_id)
        if not ctx:
            return
        
        # 更新情景记忆
        interaction_data = {
            'selected_region': ctx.selected_region,
            'selected_villa': ctx.selected_villa,
            'preferences_mentioned': ctx.preferences_mentioned,
            'booking_completed': True,
            'booking_amount': booking_data.get('total_price', 0),
            'current_intent': ctx.current_intent
        }
        
        self.memory.update_after_interaction(user_id, session_id, interaction_data)
        
        # 添加交互记录
        self.memory.episodic.add_interaction_record(
            user_id,
            interaction_type="booking_completed",
            summary=f"预订了{ctx.selected_villa}，{ctx.checkin_date}至{ctx.checkout_date}",
            metadata={
                "villa_id": ctx.selected_villa,
                "checkin": ctx.checkin_date,
                "checkout": ctx.checkout_date,
                "total_price": booking_data.get('total_price', 0)
            }
        )
        
        logger.info(f"✅ 记忆更新: 用户 {user_id} 完成预订 {ctx.selected_villa}")
    
    def on_conversation_end(self, user_id: str, session_id: str, summary: str = ""):
        """对话结束时的处理"""
        ctx = self.memory.working.load(session_id)
        if not ctx:
            return
        
        # 如果有有效交互，更新情景记忆
        if ctx.booking_progress > 0 or ctx.mentioned_villas:
            interaction_data = {
                'selected_region': ctx.selected_region,
                'selected_villa': ctx.selected_villa,
                'preferences_mentioned': ctx.preferences_mentioned,
                'booking_completed': ctx.booking_progress == 6,  # 6是预订完成状态
                'current_intent': ctx.current_intent,
                'summary': summary
            }
            self.memory.update_after_interaction(user_id, session_id, interaction_data)
        
        # 清理工作记忆
        self.memory.working.delete(session_id)
        
        logger.debug(f"对话结束，清理工作记忆: {session_id}")
    
    # ============ 知识库查询 ============
    
    def get_knowledge_for_intent(self, intent: str, **kwargs) -> str:
        """根据意图获取相关知识"""
        contexts = semantic_memory.get_context_for_intent(intent, **kwargs)
        return "\n\n".join(f"【{k.upper()}】\n{v}" for k, v in contexts.items())
    
    def get_villa_recommendations(self, user_id: str, region: str = None, limit: int = 5) -> list:
        """获取个性化别墅推荐"""
        # 获取用户偏好
        preferences = self.memory.episodic.get_user_preferences(user_id)
        
        # 搜索可用别墅
        search_params = {}
        if region:
            search_params['region'] = region
        if preferences.get('preferred_price_range'):
            price_range = preferences['preferred_price_range']
            search_params['min_price'] = price_range[0]
            search_params['max_price'] = price_range[1]
        
        villas = semantic_memory.search_villas(**search_params) if search_params else semantic_memory.get_all_villas()
        
        # 如果有用户历史偏好，进行推荐
        if preferences.get('preferred_villas') or preferences.get('preferred_regions'):
            return self.memory.episodic.suggest_villas_for_user(user_id, villas)[:limit]
        
        return villas[:limit]
    
    # ============ 上下文构建 ============
    
    def build_llm_context(self, user_id: str, chat_id: int, current_intent: str = "unknown") -> str:
        """
        为LLM构建完整的上下文提示
        
        整合三层记忆，生成简洁的上下文摘要
        """
        context_parts = []
        
        # 1. 用户画像（来自情景记忆）
        user_context = self.memory.episodic.get_personalization_context(user_id)
        if user_context:
            context_parts.append(f"【用户背景】{user_context}")
        
        # 2. 当前对话状态（来自工作记忆）
        ctx = self.memory.working.get_or_create_session(user_id, chat_id)
        conversation_state = self.memory.working.get_context_summary(ctx.session_id)
        if conversation_state and conversation_state != "新对话":
            context_parts.append(f"【当前状态】{conversation_state}")
        
        # 3. 相关知识（来自语义记忆）
        knowledge_context = self.get_knowledge_for_intent(current_intent)
        if knowledge_context:
            context_parts.append(f"\n【相关知识】\n{knowledge_context}")
        
        return "\n".join(context_parts) if context_parts else ""
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户统计信息"""
        profile = self.memory.episodic.load(user_id)
        if not profile:
            return {}
        
        return {
            "total_bookings": profile.total_bookings,
            "preferred_regions": profile.preferred_regions,
            "preferred_villas_count": len(profile.preferred_villas),
            "is_repeat_customer": profile.is_repeat_customer,
            "interaction_count": profile.interaction_count
        }


# 全局实例
memory_integration = MemoryIntegration()
