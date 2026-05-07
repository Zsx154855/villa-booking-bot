#!/usr/bin/env python3
"""
GBrain Integration - 集成到现有Villa Bot记忆系统
将GBrain持久化能力与现有Hermes三层记忆架构整合
"""

import os
import sys
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

# 确保gbrain模块可导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gbrain import GBrainPersistence, GBrainMCP, BrainRepo
from gbrain.persistence import gbrain_persistence
from gbrain.mcp_interface import gbrain_mcp
from gbrain.brain_repo import brain_repo

logger = logging.getLogger(__name__)


class GBrainIntegration:
    """
    GBrain集成器
    
    功能：
    - 桥接现有memory/模块与GBrain持久化
    - 提供向后兼容的API
    - 自动初始化数据
    """
    
    def __init__(self):
        self.persistence = gbrain_persistence
        self.mcp = gbrain_mcp
        self.brain_repo = brain_repo
        self._initialized = False
        
        logger.info("🔄 GBrain集成器初始化中...")
    
    def initialize(self, villas: List[Dict] = None) -> bool:
        """
        初始化GBrain
        
        Args:
            villas: 别墅数据列表
            
        Returns:
            是否成功
        """
        if self._initialized:
            logger.info("GBrain已初始化，跳过")
            return True
        
        try:
            # 1. 如果提供了别墅数据，初始化
            if villas:
                self.mcp.initialize_villas(villas)
            
            # 2. 清理过期记忆
            self.persistence.cleanup_expired()
            
            # 3. 设置默认运营规则
            self._initialize_default_rules()
            
            self._initialized = True
            logger.info("✅ GBrain初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"GBrain初始化失败: {e}")
            return False
    
    def _initialize_default_rules(self):
        """初始化默认运营规则"""
        default_rules = {
            "cancellation_policy": {
                "free_days": 7,
                "description": "入住日期前7天可免费取消",
                "partial_days": 3,
                "partial_description": "入住日期前3天取消收取50%费用"
            },
            "checkin_checkout": {
                "checkin_time": "15:00",
                "checkout_time": "11:00"
            },
            "payment_methods": ["银行转账", "支付宝", "微信支付"],
            "deposit": {
                "amount": "50%",
                "description": "预订时需支付50%订金"
            }
        }
        
        self.persistence.set(
            user_id=None,
            memory_type="semantic",
            key="rules",
            value=default_rules
        )
        logger.info("✅ 默认运营规则已设置")
    
    def get_or_create_user_context(self, user_id: str) -> Dict:
        """
        获取或创建用户上下文
        
        整合Working + Episodic记忆
        """
        # 获取工作记忆
        working = self.mcp.get_working_memory(user_id, "context")
        working_data = working.data if working.success else {}
        
        # 获取用户画像
        profile = self.mcp.get_user_profile(user_id)
        profile_data = profile.data if profile.success and profile.data else {}
        
        # 合并
        return {
            "working_memory": working_data,
            "user_profile": profile_data,
            "preferences": profile_data.get('preferences', {})
        }
    
    def update_context(self, user_id: str, context: Dict) -> bool:
        """更新用户上下文"""
        # 保存工作记忆
        self.mcp.set_working_memory(
            user_id=user_id,
            key="context",
            value=context,
            ttl_seconds=1800
        )
        return True
    
    def record_interaction(
        self,
        user_id: str,
        interaction_type: str,
        data: Dict
    ) -> bool:
        """
        记录用户交互
        
        用于更新用户画像和分析
        """
        # 更新工作记忆中的交互历史
        current = self.mcp.get_working_memory(user_id, "interactions")
        interactions = current.data if current.success and current.data else []
        interactions.append({
            "type": interaction_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
        
        # 只保留最近20条
        interactions = interactions[-20:]
        
        self.mcp.set_working_memory(
            user_id=user_id,
            key="interactions",
            value=interactions,
            ttl_seconds=86400  # 24小时
        )
        
        # 如果是预订完成，更新画像
        if interaction_type == "booking_completed":
            self.mcp.record_booking(user_id, data)
        
        return True
    
    def search_villas(self, **criteria) -> List[Dict]:
        """搜索别墅（兼容现有API）"""
        result = self.mcp.search_villas(**criteria)
        return result.data if result.success else []
    
    def get_villa(self, villa_id: str) -> Optional[Dict]:
        """获取别墅（兼容现有API）"""
        result = self.mcp.get_villa(villa_id)
        return result.data if result.success else None
    
    def sync_from_database(self, database) -> bool:
        """
        从数据库同步数据到GBrain
        
        Args:
            database: database模块
        """
        try:
            # 同步别墅数据
            villas = database.get_all_villas()
            if villas:
                self.mcp.initialize_villas(villas)
                logger.info(f"已同步 {len(villas)} 套别墅到GBrain")
            
            return True
        except Exception as e:
            logger.error(f"同步数据失败: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """获取GBrain统计"""
        result = self.mcp.get_stats()
        return result.data if result.success else {}


# 全局单例
gbrain_integration = GBrainIntegration()


def init_gbrain_with_villas(villas: List[Dict] = None) -> bool:
    """
    便捷初始化函数
    
    Args:
        villas: 别墅数据列表
        
    Returns:
        是否成功
    """
    return gbrain_integration.initialize(villas)


def get_user_context(user_id: str) -> Dict:
    """获取用户上下文"""
    return gbrain_integration.get_or_create_user_context(user_id)


def record_interaction(user_id: str, interaction_type: str, data: Dict) -> bool:
    """记录用户交互"""
    return gbrain_integration.record_interaction(user_id, interaction_type, data)


# 导出便捷函数
__all__ = [
    "GBrainIntegration",
    "gbrain_integration",
    "init_gbrain_with_villas",
    "get_user_context",
    "record_interaction",
    "gbrain_persistence",
    "gbrain_mcp",
    "brain_repo"
]
