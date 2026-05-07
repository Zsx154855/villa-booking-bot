#!/usr/bin/env python3
"""
RAG Module for Villa Booking Bot
RAG系统集成模块
"""

import logging
from typing import Optional

from rag import get_rag_system, rag_query, get_retriever, format_context

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 全局RAG系统实例
_rag = None


def init_rag(llm_client=None, confidence_threshold: float = 0.1):
    """初始化RAG系统"""
    global _rag
    _rag = get_rag_system(llm_client, confidence_threshold)
    logger.info("✅ RAG模块初始化完成")
    return _rag


def get_rag():
    """获取RAG系统实例"""
    global _rag
    if _rag is None:
        _rag = init_rag()
    return _rag


def rag_answer(question: str, language: str = 'zh', 
              top_k: int = 5, llm_client=None) -> str:
    """
    RAG问答
    
    Args:
        question: 用户问题
        language: 输出语言
        top_k: 检索数量
        llm_client: LLM客户端
    
    Returns:
        生成的回答
    """
    rag = get_rag()
    return rag.query(question, language, top_k)


def rag_villa_recommend(requirements: str, language: str = 'zh') -> str:
    """
    别墅推荐
    
    Args:
        requirements: 用户需求描述
        language: 输出语言
    
    Returns:
        推荐结果
    """
    rag = get_rag()
    return rag.query_villa(requirements, language)


def rag_faq(query: str, language: str = 'zh') -> str:
    """
    FAQ查询
    
    Args:
        query: 用户问题
        language: 输出语言
    
    Returns:
        FAQ答案
    """
    rag = get_rag()
    return rag.query_faq(query, language)


def rag_nearby(query: str, region: str = None, language: str = 'zh') -> str:
    """
    周边攻略查询
    
    Args:
        query: 用户问题
        region: 地区筛选
        language: 输出语言
    
    Returns:
        攻略信息
    """
    rag = get_rag()
    return rag.query_nearby(query, region, language)


def reload_rag():
    """热更新RAG系统"""
    rag = get_rag()
    rag.reload()
    logger.info("🔄 RAG系统已热更新")


def should_use_rag(message: str) -> bool:
    """
    判断是否应该使用RAG
    
    基于关键词判断是否涉及知识库查询
    
    Args:
        message: 用户消息
    
    Returns:
        是否使用RAG
    """
    # RAG相关关键词
    rag_keywords = [
        # 别墅相关
        '别墅', ' villa', 'Villa',
        # 设施相关
        '设施', '设备', '有没有', '可以',
        # 预订相关
        '预订', '预定', '预约', 'booking',
        # 价格相关
        '价格', '多少钱', '房价', 'price',
        # 位置相关
        '位置', '在哪', '距离', 'near',
        # 服务相关
        '服务', '接送', '厨师', 'spa', 'service',
        # 入住相关
        '入住', '退房', 'check',
        # 问题咨询
        '怎么', '如何', '可以吗', 'question',
        # 周边
        '附近', '周边', '景点', '推荐', '附近', 'around'
    ]
    
    message_lower = message.lower()
    return any(kw in message_lower for kw in rag_keywords)


def format_rag_response(response: str, use_rag: bool) -> str:
    """
    格式化RAG响应
    
    Args:
        response: RAG生成的响应
        use_rag: 是否使用了RAG
    
    Returns:
        格式化后的响应
    """
    if not use_rag:
        return response
    
    # 添加RAG标识
    return f"🔍 *RAG知识库检索*\n\n{response}"


# 导出
__all__ = [
    'init_rag',
    'get_rag',
    'rag_answer',
    'rag_villa_recommend',
    'rag_faq',
    'rag_nearby',
    'reload_rag',
    'should_use_rag',
    'format_rag_response',
    'format_context'
]
