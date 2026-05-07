#!/usr/bin/env python3
"""
Hermes三层记忆架构 - Layer 2: Episodic Memory
情景记忆管理 - 用户历史交互记录
生命周期：跨对话，持久化
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
import os

from .base import BaseMemoryManager, UserProfileSummary, MemoryLayer

logger = logging.getLogger(__name__)


class EpisodicMemoryManager(BaseMemoryManager):
    """
    情景记忆管理器
    
    特性：
    - 持久化到文件系统
    - 只存储摘要，不存储原始对话
    - 自动聚合用户行为
    - 支持增量更新
    """
    
    def __init__(self, storage_path: str = None):
        if storage_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            storage_path = os.path.join(base_dir, "episodic_store.json")
        
        self._storage_path = storage_path
        self._profiles: Dict[str, UserProfileSummary] = {}
        self._load_from_disk()
        logger.info(f"✅ Episodic Memory初始化完成 (存储路径: {storage_path})")
    
    def _load_from_disk(self):
        """从磁盘加载数据"""
        if os.path.exists(self._storage_path):
            try:
                with open(self._storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for user_id, profile_data in data.items():
                        self._profiles[user_id] = UserProfileSummary.from_dict(profile_data)
                logger.info(f"加载了 {len(self._profiles)} 个用户画像")
            except Exception as e:
                logger.error(f"加载情景记忆失败: {e}")
    
    def _save_to_disk(self):
        """保存数据到磁盘"""
        try:
            with open(self._storage_path, 'w', encoding='utf-8') as f:
                data = {uid: profile.to_dict() for uid, profile in self._profiles.items()}
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存情景记忆失败: {e}")
    
    def load(self, key: str) -> Optional[UserProfileSummary]:
        """加载用户画像"""
        return self._profiles.get(key)
    
    def save(self, key: str, data: UserProfileSummary) -> bool:
        """保存用户画像"""
        try:
            self._profiles[key] = data
            self._save_to_disk()
            return True
        except Exception as e:
            logger.error(f"保存用户画像失败: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除用户画像"""
        if key in self._profiles:
            del self._profiles[key]
            self._save_to_disk()
            return True
        return False
    
    def clear(self) -> bool:
        """清空所有情景记忆"""
        self._profiles.clear()
        self._save_to_disk()
        return True
    
    # ============ 用户画像操作 ============
    
    def get_or_create_profile(self, user_id: str) -> UserProfileSummary:
        """获取或创建用户画像"""
        if user_id not in self._profiles:
            self._profiles[user_id] = UserProfileSummary(user_id=user_id)
        return self._profiles[user_id]
    
    def update_from_working_memory(self, user_id: str, context: Dict[str, Any]):
        """
        从工作记忆更新情景记忆
        
        context 应包含：
        - selected_villa: 选中的别墅ID
        - selected_region: 选中的地区
        - preferences_mentioned: 提到的偏好
        - booking_completed: 是否完成预订
        - booking_amount: 预订金额
        """
        profile = self.get_or_create_profile(user_id)
        
        # 更新地区偏好
        if context.get('selected_region'):
            region = context['selected_region']
            if region not in profile.preferred_regions:
                profile.preferred_regions.append(region)
        
        # 更新别墅偏好
        if context.get('selected_villa'):
            villa_id = context['selected_villa']
            if villa_id not in profile.preferred_villas:
                profile.preferred_villas.append(villa_id)
        
        # 更新偏好标签
        if context.get('preferences_mentioned'):
            for pref in context['preferences_mentioned']:
                if pref not in profile.preferences_mentioned:
                    profile.preferences_mentioned.append(pref)
        
        # 预订完成统计
        if context.get('booking_completed'):
            profile.total_bookings += 1
            profile.is_repeat_customer = profile.total_bookings > 1
            
            if context.get('booking_amount'):
                profile.total_spent += context['booking_amount']
        
        # 交互计数
        profile.interaction_count += 1
        
        # 最后交互时间
        profile.last_interaction = datetime.now().isoformat()
        
        # 更新意图历史
        if context.get('current_intent'):
            intent = context['current_intent']
            profile.last_interaction_types.append(intent)
            if len(profile.last_interaction_types) > 10:
                profile.last_interaction_types = profile.last_interaction_types[-10:]
        
        profile.updated_at = datetime.now().isoformat()
        self.save(user_id, profile)
    
    def update_profile(self, user_id: str, **kwargs) -> bool:
        """直接更新用户画像字段"""
        profile = self.get_or_create_profile(user_id)
        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        profile.updated_at = datetime.now().isoformat()
        return self.save(user_id, profile)
    
    def add_interaction_record(self, user_id: str, interaction_type: str, summary: str, metadata: Dict = None):
        """
        添加交互记录摘要
        
        注意：只存储摘要，不存储原始对话内容
        """
        profile = self.get_or_create_profile(user_id)
        
        record = {
            "type": interaction_type,
            "summary": summary,
            "time": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        # 存储在profile的最后交互记录中（保留最近20条）
        if not hasattr(profile, '_interaction_records'):
            profile._interaction_records = []
        
        profile._interaction_records.append(record)
        if len(profile._interaction_records) > 20:
            profile._interaction_records = profile._interaction_records[-20:]
        
        profile.updated_at = datetime.now().isoformat()
        self.save(user_id, profile)
    
    # ============ 查询方法 ============
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """获取用户偏好摘要"""
        profile = self.load(user_id)
        if not profile:
            return {}
        
        return {
            "preferred_regions": profile.preferred_regions,
            "preferred_villas": profile.preferred_villas,
            "preferred_room_type": profile.preferred_room_type,
            "price_range": profile.preferred_price_range,
            "tags": profile.tags,
            "is_repeat_customer": profile.is_repeat_customer
        }
    
    def get_personalization_context(self, user_id: str) -> str:
        """
        生成个性化上下文（用于LLM）
        
        返回一个简洁的用户背景描述
        """
        profile = self.load(user_id)
        if not profile:
            return ""
        
        parts = []
        
        if profile.is_repeat_customer:
            parts.append(f"回头客(共{profile.total_bookings}次预订)")
        elif profile.interaction_count > 3:
            parts.append("活跃用户")
        
        if profile.preferred_regions:
            parts.append(f"偏好地区: {', '.join(profile.preferred_regions[:2])}")
        
        if profile.tags:
            parts.append(f"标签: {', '.join(profile.tags[:3])}")
        
        if profile.preferred_room_type:
            parts.append(f"偏好房型: {profile.preferred_room_type}")
        
        if profile.avg_response_length == "short":
            parts.append("(简洁回复)")
        elif profile.avg_response_length == "long":
            parts.append("(详细回复)")
        
        return " | ".join(parts) if parts else ""
    
    def suggest_villas_for_user(self, user_id: str, available_villas: List[Dict]) -> List[Dict]:
        """
        基于用户偏好推荐别墅
        
        简单的基于规则的推荐：
        1. 优先推荐用户之前喜欢的地区
        2. 考虑价格范围
        3. 考虑房型偏好
        """
        profile = self.load(user_id)
        if not profile:
            return available_villas[:5]  # 返回前5个
        
        # 评分
        scored = []
        for villa in available_villas:
            score = 0
            
            # 地区匹配
            if villa.get('region') in profile.preferred_regions:
                score += 10
            
            # 价格范围匹配
            price = villa.get('price_per_night', 0)
            min_p, max_p = profile.preferred_price_range
            if min_p <= price <= max_p:
                score += 5
            
            # 房型匹配
            if profile.preferred_room_type and villa.get('type') == profile.preferred_room_type:
                score += 3
            
            # 之前喜欢过的
            if villa.get('id') in profile.preferred_villas:
                score += 20
            
            scored.append((villa, score))
        
        # 按分数排序
        scored.sort(key=lambda x: x[1], reverse=True)
        return [v[0] for v in scored[:5]]
    
    def get_all_profiles(self) -> List[UserProfileSummary]:
        """获取所有用户画像"""
        return list(self._profiles.values())
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        profiles = self.get_all_profiles()
        return {
            "total_users": len(profiles),
            "repeat_customers": sum(1 for p in profiles if p.is_repeat_customer),
            "total_bookings": sum(p.total_bookings for p in profiles),
            "avg_interactions": sum(p.interaction_count for p in profiles) / max(len(profiles), 1)
        }


# 全局单例
episodic_memory = EpisodicMemoryManager()
