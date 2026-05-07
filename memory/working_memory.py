#!/usr/bin/env python3
"""
Hermes三层记忆架构 - Layer 1: Working Memory
工作记忆管理 - 当前对话上下文
生命周期：单次对话
"""

import json
import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, List
from threading import Lock

from .base import BaseMemoryManager, ConversationContext, MemoryLayer

logger = logging.getLogger(__name__)


class WorkingMemoryManager(BaseMemoryManager):
    """
    工作记忆管理器
    
    特性：
    - 轻量级JSON格式，不占用太多Token
    - 线程安全
    - 单次对话生命周期
    - 自动过期清理
    """
    
    def __init__(self, ttl_seconds: int = 1800):  # 默认30分钟过期
        self._memory_store: Dict[str, ConversationContext] = {}
        self._lock = Lock()
        self._ttl_seconds = ttl_seconds
        logger.info(f"✅ Working Memory初始化完成 (TTL={ttl_seconds}s)")
    
    def _generate_session_id(self, user_id: str, chat_id: int) -> str:
        """生成会话ID"""
        key = f"{user_id}:{chat_id}:{datetime.now().strftime('%Y%m%d%H%M')}"
        return hashlib.md5(key.encode()).hexdigest()[:16]
    
    def create_session(self, user_id: str, chat_id: int) -> ConversationContext:
        """创建新的工作记忆会话"""
        session_id = self._generate_session_id(user_id, chat_id)
        
        context = ConversationContext(
            session_id=session_id,
            user_id=user_id
        )
        
        with self._lock:
            self._memory_store[session_id] = context
        
        logger.debug(f"创建工作记忆会话: {session_id}")
        return context
    
    def get_or_create_session(self, user_id: str, chat_id: int) -> ConversationContext:
        """获取或创建工作记忆会话"""
        # 尝试查找现有会话
        with self._lock:
            for session_id, ctx in self._memory_store.items():
                if ctx.user_id == user_id:
                    # 检查是否过期
                    updated = datetime.fromisoformat(ctx.updated_at)
                    if (datetime.now() - updated).total_seconds() < self._ttl_seconds:
                        return ctx
                    else:
                        # 已过期，删除
                        del self._memory_store[session_id]
                        break
        
        return self.create_session(user_id, chat_id)
    
    def load(self, key: str) -> Optional[ConversationContext]:
        """加载工作记忆"""
        with self._lock:
            return self._memory_store.get(key)
    
    def save(self, key: str, data: ConversationContext) -> bool:
        """保存工作记忆"""
        try:
            with self._lock:
                data.update_timestamp()
                self._memory_store[key] = data
            return True
        except Exception as e:
            logger.error(f"保存工作记忆失败: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除工作记忆"""
        with self._lock:
            if key in self._memory_store:
                del self._memory_store[key]
                return True
        return False
    
    def clear(self) -> bool:
        """清空所有工作记忆"""
        with self._lock:
            self._memory_store.clear()
        return True
    
    def cleanup_expired(self) -> int:
        """清理过期记忆"""
        count = 0
        with self._lock:
            expired_keys = []
            for session_id, ctx in self._memory_store.items():
                updated = datetime.fromisoformat(ctx.updated_at)
                if (datetime.now() - updated).total_seconds() > self._ttl_seconds:
                    expired_keys.append(session_id)
            
            for key in expired_keys:
                del self._memory_store[key]
                count += 1
        
        if count > 0:
            logger.info(f"清理了 {count} 个过期工作记忆")
        return count
    
    # ============ 便捷方法 ============
    
    def update_intent(self, session_id: str, intent: str) -> bool:
        """更新用户意图"""
        ctx = self.load(session_id)
        if ctx:
            ctx.current_intent = intent
            return self.save(session_id, ctx)
        return False
    
    def update_booking_progress(self, session_id: str, progress: int) -> bool:
        """更新预订进度"""
        ctx = self.load(session_id)
        if ctx:
            ctx.booking_progress = progress
            return self.save(session_id, ctx)
        return False
    
    def add_message(self, session_id: str, role: str, content: str) -> bool:
        """添加对话消息"""
        ctx = self.load(session_id)
        if ctx:
            ctx.add_message(role, content)
            return self.save(session_id, ctx)
        return False
    
    def set_booking_data(self, session_id: str, **kwargs) -> bool:
        """设置预订数据"""
        ctx = self.load(session_id)
        if ctx:
            for key, value in kwargs.items():
                if hasattr(ctx, key):
                    setattr(ctx, key, value)
            return self.save(session_id, ctx)
        return False
    
    def get_context_summary(self, session_id: str) -> str:
        """获取上下文摘要（用于LLM）"""
        ctx = self.load(session_id)
        if not ctx:
            return ""
        
        # 生成轻量摘要
        summary_parts = []
        
        if ctx.current_intent != "unknown":
            summary_parts.append(f"意图: {ctx.current_intent}")
        
        if ctx.booking_progress >= 0:
            summary_parts.append(f"预订进度: {ctx.booking_progress}/6")
        
        if ctx.selected_region:
            summary_parts.append(f"已选地区: {ctx.selected_region}")
        
        if ctx.selected_villa:
            summary_parts.append(f"已选别墅: {ctx.selected_villa}")
        
        if ctx.mentioned_villas:
            summary_parts.append(f"用户关注别墅: {', '.join(ctx.mentioned_villas[-3:])}")
        
        if ctx.preferences_mentioned:
            summary_parts.append(f"用户偏好: {', '.join(ctx.preferences_mentioned[-3:])}")
        
        return " | ".join(summary_parts) if summary_parts else "新对话"
    
    def get_token_estimate(self, session_id: str) -> int:
        """估算当前记忆的Token数"""
        ctx = self.load(session_id)
        if not ctx:
            return 0
        
        # 简单估算：JSON字符串长度 / 4
        json_str = json.dumps(ctx.to_dict(), ensure_ascii=False)
        return len(json_str) // 4


# 全局单例
working_memory = WorkingMemoryManager()
