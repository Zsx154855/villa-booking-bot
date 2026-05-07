#!/usr/bin/env python3
"""
GBrain Layer 3: Agent MCP Interface
标准化知识访问接口 - 统一的知识操作接口
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from .persistence import GBrainPersistence, gbrain_persistence
from .brain_repo import BrainRepo, brain_repo

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """记忆类型枚举"""
    WORKING = "working"      # 工作记忆
    EPISODIC = "episodic"    # 情景记忆
    SEMANTIC = "semantic"    # 语义记忆


@dataclass
class KnowledgeQuery:
    """知识查询请求"""
    query_type: str          # villa/customer/rule/faq/booking
    filters: Dict = field(default_factory=dict)
    user_id: Optional[str] = None
    include_context: bool = True


@dataclass  
class KnowledgeResponse:
    """知识响应"""
    success: bool
    data: Any = None
    error: str = None
    source: str = ""  # persistence/brain_repo/cache
    metadata: Dict = field(default_factory=dict)


class GBrainMCP:
    """
    GBrain MCP (Model Context Protocol) 接口
    
    提供统一的知识访问接口，支持：
    - 别墅信息查询
    - 用户画像读写
    - 运营规则获取
    - FAQ检索
    - 预订历史分析
    """
    
    def __init__(
        self,
        persistence: GBrainPersistence = None,
        brain_repo: BrainRepo = None
    ):
        """
        初始化MCP接口
        
        Args:
            persistence: 持久化层实例
            brain_repo: 脑库仓库实例
        """
        self.persistence = persistence or gbrain_persistence
        self.brain_repo = brain_repo or brain_repo
        
        # 缓存配置
        self._villa_cache_ttl = 3600  # 1小时
        self._profile_cache_ttl = 1800  # 30分钟
        
        logger.info("✅ GBrain MCP初始化完成")
    
    # ============ 别墅查询 ============
    
    def get_villa(
        self,
        villa_id: str,
        use_cache: bool = True
    ) -> KnowledgeResponse:
        """
        获取别墅信息
        
        优先级：缓存 > 持久化 > Brain Repo
        """
        # 1. 尝试缓存
        if use_cache:
            cached = self.persistence.get_cached_villa(villa_id)
            if cached:
                return KnowledgeResponse(
                    success=True,
                    data=cached,
                    source="cache",
                    metadata={"villa_id": villa_id}
                )
        
        # 2. 尝试Brain Repo
        brain_entry = self.brain_repo.get_villa(villa_id)
        if brain_entry:
            return KnowledgeResponse(
                success=True,
                data=json.loads(brain_entry.content),
                source="brain_repo",
                metadata={"villa_id": villa_id}
            )
        
        # 3. 尝试持久化
        persisted = self.persistence.get_cached_villa(villa_id)
        if persisted:
            return KnowledgeResponse(
                success=True,
                data=persisted,
                source="persistence",
                metadata={"villa_id": villa_id}
            )
        
        return KnowledgeResponse(
            success=False,
            error=f"未找到别墅: {villa_id}",
            metadata={"villa_id": villa_id}
        )
    
    def search_villas(
        self,
        region: str = None,
        min_price: int = None,
        max_price: int = None,
        min_guests: int = None,
        amenities: List[str] = None,
        limit: int = 20
    ) -> KnowledgeResponse:
        """
        搜索别墅
        
        Args:
            region: 地区筛选
            min_price: 最低价格
            max_price: 最高价格
            min_guests: 最少入住人数
            amenities: 设施列表
            limit: 返回数量限制
        """
        try:
            # 获取所有缓存的别墅
            all_villas = self.persistence.get_cached_villas()
            
            if not all_villas:
                # 尝试从Brain Repo获取
                brain_villas = self.brain_repo.get_by_type("villa")
                all_villas = [
                    json.loads(v.content) for v in brain_villas 
                    if v.metadata.get('villa_id')
                ]
            
            # 应用筛选
            results = all_villas
            if region:
                results = [v for v in results if v.get('region') == region]
            if min_price:
                results = [v for v in results 
                          if v.get('price_per_night', 0) >= min_price]
            if max_price:
                results = [v for v in results 
                          if v.get('price_per_night', 0) <= max_price]
            if min_guests:
                results = [v for v in results 
                          if v.get('max_guests', 0) >= min_guests]
            if amenities:
                results = [v for v in results
                          if all(a in v.get('amenities', []) for a in amenities)]
            
            # 限制数量
            results = results[:limit]
            
            return KnowledgeResponse(
                success=True,
                data=results,
                source="persistence" if all_villas else "brain_repo",
                metadata={"total": len(results), "filters": {
                    "region": region,
                    "price_range": f"{min_price}-{max_price}" if min_price or max_price else None,
                    "min_guests": min_guests,
                    "amenities": amenities
                }}
            )
        except Exception as e:
            logger.error(f"搜索别墅失败: {e}")
            return KnowledgeResponse(
                success=False,
                error=str(e)
            )
    
    def initialize_villas(self, villas: List[Dict]) -> KnowledgeResponse:
        """
        初始化别墅数据到持久化存储
        
        Args:
            villas: 别墅数据列表
            
        Returns:
            初始化结果
        """
        try:
            # 1. 保存到SQLite缓存
            self.persistence.cache_villas(villas)
            
            # 2. 保存到Brain Repo
            if hasattr(self.brain_repo, 'initialize_villas'):
                count = self.brain_repo.initialize_villas(villas)
            else:
                count = 0
            
            # 3. 同步到GitHub（如果可用）
            if hasattr(self.brain_repo, 'sync_all_to_github'):
                sync_stats = self.brain_repo.sync_all_to_github()
            else:
                sync_stats = {"success": 0, "failed": 0}
            
            return KnowledgeResponse(
                success=True,
                data={
                    "cached": len(villas),
                    "brain_repo_initialized": count,
                    "github_sync": sync_stats
                },
                source="all",
                metadata={"total_villas": len(villas)}
            )
        except Exception as e:
            logger.error(f"初始化别墅失败: {e}")
            return KnowledgeResponse(
                success=False,
                error=str(e)
            )
    
    # ============ 用户画像 ============
    
    def get_user_profile(self, user_id: str) -> KnowledgeResponse:
        """获取用户画像"""
        try:
            profile = self.persistence.get_user_profile(user_id)
            
            if profile:
                return KnowledgeResponse(
                    success=True,
                    data=profile,
                    source="persistence"
                )
            
            # 尝试Brain Repo
            brain_entry = self.brain_repo.get_customer(user_id)
            if brain_entry:
                profile = json.loads(brain_entry.content)
                return KnowledgeResponse(
                    success=True,
                    data=profile,
                    source="brain_repo"
                )
            
            return KnowledgeResponse(
                success=True,
                data=None,
                metadata={"message": "用户画像不存在"}
            )
        except Exception as e:
            logger.error(f"获取用户画像失败: {e}")
            return KnowledgeResponse(
                success=False,
                error=str(e)
            )
    
    def save_user_profile(
        self,
        user_id: str,
        profile_data: Dict,
        sync_brain: bool = True
    ) -> KnowledgeResponse:
        """
        保存用户画像
        
        Args:
            user_id: 用户ID
            profile_data: 画像数据
            sync_brain: 是否同步到Brain Repo
        """
        try:
            # 1. 保存到持久化
            self.persistence.save_user_profile(user_id, profile_data)
            
            # 2. 可选：同步到Brain Repo
            if sync_brain and hasattr(self.brain_repo, 'save_customer'):
                self.brain_repo.save_customer(user_id, profile_data)
            
            return KnowledgeResponse(
                success=True,
                data=profile_data,
                source="persistence",
                metadata={"user_id": user_id}
            )
        except Exception as e:
            logger.error(f"保存用户画像失败: {e}")
            return KnowledgeResponse(
                success=False,
                error=str(e)
            )
    
    def update_user_preference(
        self,
        user_id: str,
        preference_type: str,
        preference_value: Any
    ) -> KnowledgeResponse:
        """
        更新用户偏好
        
        Args:
            user_id: 用户ID
            preference_type: 偏好类型 (region/price_range/villa/facility)
            preference_value: 偏好值
        """
        try:
            profile = self.persistence.get_user_profile(user_id) or {}
            
            # 初始化偏好结构
            if 'preferences' not in profile:
                profile['preferences'] = {}
            
            # 更新偏好
            if preference_type == 'region':
                regions = profile['preferences'].get('preferred_regions', [])
                if preference_value not in regions:
                    regions.append(preference_value)
                profile['preferences']['preferred_regions'] = regions
            
            elif preference_type == 'price_range':
                profile['preferences']['price_range'] = preference_value
            
            elif preference_type == 'villa':
                villas = profile['preferences'].get('liked_villas', [])
                if preference_value not in villas:
                    villas.append(preference_value)
                profile['preferences']['liked_villas'] = villas
            
            profile['updated_at'] = datetime.now().isoformat()
            
            return self.save_user_profile(user_id, profile)
        except Exception as e:
            logger.error(f"更新用户偏好失败: {e}")
            return KnowledgeResponse(success=False, error=str(e))
    
    # ============ 预订历史 ============
    
    def record_booking(self, user_id: str, booking_data: Dict) -> KnowledgeResponse:
        """记录预订"""
        try:
            self.persistence.record_booking(user_id, booking_data)
            
            # 更新用户画像统计
            profile = self.persistence.get_user_profile(user_id) or {}
            profile['total_bookings'] = profile.get('total_bookings', 0) + 1
            profile['total_spent'] = profile.get('total_spent', 0) + booking_data.get('total_price', 0)
            self.persistence.save_user_profile(user_id, profile)
            
            return KnowledgeResponse(
                success=True,
                data=booking_data,
                source="persistence",
                metadata={"user_id": user_id}
            )
        except Exception as e:
            logger.error(f"记录预订失败: {e}")
            return KnowledgeResponse(success=False, error=str(e))
    
    def get_booking_history(self, user_id: str, limit: int = 10) -> KnowledgeResponse:
        """获取预订历史"""
        try:
            history = self.persistence.get_user_booking_history(user_id, limit)
            return KnowledgeResponse(
                success=True,
                data=history,
                source="persistence"
            )
        except Exception as e:
            logger.error(f"获取预订历史失败: {e}")
            return KnowledgeResponse(success=False, error=str(e))
    
    # ============ 工作记忆 ============
    
    def set_working_memory(
        self,
        user_id: str,
        key: str,
        value: Any,
        ttl_seconds: int = 1800
    ) -> KnowledgeResponse:
        """
        设置工作记忆（TTL自动过期）
        
        Args:
            user_id: 用户ID
            key: 键
            value: 值
            ttl_seconds: 过期秒数（默认30分钟）
        """
        try:
            self.persistence.set(
                user_id=user_id,
                memory_type=MemoryType.WORKING.value,
                key=key,
                value=value,
                ttl_seconds=ttl_seconds
            )
            return KnowledgeResponse(
                success=True,
                metadata={"user_id": user_id, "key": key, "ttl": ttl_seconds}
            )
        except Exception as e:
            return KnowledgeResponse(success=False, error=str(e))
    
    def get_working_memory(
        self,
        user_id: str,
        key: str
    ) -> KnowledgeResponse:
        """获取工作记忆"""
        try:
            value = self.persistence.get(
                user_id=user_id,
                memory_type=MemoryType.WORKING.value,
                key=key
            )
            return KnowledgeResponse(
                success=True,
                data=value,
                source="persistence"
            )
        except Exception as e:
            return KnowledgeResponse(success=False, error=str(e))
    
    def get_all_working_memory(
        self,
        user_id: str
    ) -> KnowledgeResponse:
        """获取用户所有工作记忆"""
        try:
            memories = self.persistence.get_all(
                user_id=user_id,
                memory_type=MemoryType.WORKING.value
            )
            return KnowledgeResponse(
                success=True,
                data=[m.to_dict() for m in memories],
                source="persistence"
            )
        except Exception as e:
            return KnowledgeResponse(success=False, error=str(e))
    
    # ============ 语义记忆（知识库） ============
    
    def get_rules(self, rule_key: str = None) -> KnowledgeResponse:
        """获取运营规则"""
        try:
            rules = self.persistence.get(
                user_id=None,
                memory_type=MemoryType.SEMANTIC.value,
                key="rules"
            )
            
            if rules and rule_key:
                keys = rule_key.split('.')
                for k in keys:
                    rules = rules.get(k)
            
            return KnowledgeResponse(
                success=True,
                data=rules,
                source="persistence"
            )
        except Exception as e:
            return KnowledgeResponse(success=False, error=str(e))
    
    def set_rules(self, rules: Dict) -> KnowledgeResponse:
        """设置运营规则"""
        try:
            self.persistence.set(
                user_id=None,
                memory_type=MemoryType.SEMANTIC.value,
                key="rules",
                value=rules
            )
            return KnowledgeResponse(success=True)
        except Exception as e:
            return KnowledgeResponse(success=False, error=str(e))
    
    # ============ 系统方法 ============
    
    def cleanup(self) -> KnowledgeResponse:
        """清理过期数据"""
        try:
            expired_count = self.persistence.cleanup_expired()
            return KnowledgeResponse(
                success=True,
                metadata={"cleaned": expired_count}
            )
        except Exception as e:
            return KnowledgeResponse(success=False, error=str(e))
    
    def get_stats(self) -> KnowledgeResponse:
        """获取统计信息"""
        try:
            stats = self.persistence.get_stats()
            stats['brain_repo_available'] = self.brain_repo.is_available() if hasattr(self.brain_repo, 'is_available') else False
            stats['brain_repo_entries'] = len(self.brain_repo._cache) if hasattr(self.brain_repo, '_cache') else 0
            return KnowledgeResponse(success=True, data=stats)
        except Exception as e:
            return KnowledgeResponse(success=False, error=str(e))
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "persistence": self.persistence.health_check(),
            "brain_repo": {
                "available": self.brain_repo.is_available() if hasattr(self.brain_repo, 'is_available') else False,
                "entries": len(self.brain_repo._cache) if hasattr(self.brain_repo, '_cache') else 0
            }
        }


# 全局单例
gbrain_mcp = GBrainMCP()
