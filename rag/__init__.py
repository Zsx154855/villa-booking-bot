#!/usr/bin/env python3
"""
RAG System - 检索增强生成系统
轻量级RAG实现（不依赖向量数据库）
"""

import logging
from typing import Dict, List, Optional, Any

from .knowledge_base import KnowledgeBase, get_knowledge_base, reload_knowledge_base
from .indexer import TFIDFIndexer, get_indexer, rebuild_index
from .retriever import Retriever, get_retriever
from .generator import Generator, get_generator, generate_answer

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class RAGSystem:
    """
    RAG系统主类
    
    四阶段流程：
    1. 数据准备 - 从知识库加载
    2. 索引构建 - TF-IDF倒排索引
    3. 检索 - 关键词匹配+重排序
    4. 生成 - LLM生成答案
    """
    
    def __init__(self, llm_client=None, confidence_threshold: float = 0.1):
        """
        初始化RAG系统
        
        Args:
            llm_client: LLM客户端（可选，无LLM时使用模板生成）
            confidence_threshold: 置信度阈值
        """
        self.llm_client = llm_client
        self.confidence_threshold = confidence_threshold
        
        # 初始化组件
        self.knowledge_base = get_knowledge_base()
        self.retriever = get_retriever(confidence_threshold)
        self.generator = get_generator(llm_client)
        
        # 确保索引已构建
        self.retriever.ensure_indexed()
        
        logger.info("✅ RAG系统初始化完成")
    
    def query(self, question: str, language: str = 'zh',
              top_k: int = 5, include_sources: bool = True) -> str:
        """
        查询
        
        Args:
            question: 用户问题
            language: 输出语言 (zh/en/th)
            top_k: 检索返回条数
            include_sources: 是否包含信息来源
        
        Returns:
            生成的回答
        """
        if not question or not question.strip():
            return self.generator._no_answer_response(question, language)
        
        # 1. 检索
        retrieval_results = self.retriever.retrieve(question, top_k)
        
        # 2. 生成
        answer = self.generator.generate(
            question,
            retrieval_results,
            language=language,
            include_source=include_sources
        )
        
        return answer
    
    def query_villa(self, question: str, language: str = 'zh') -> str:
        """查询别墅相关问题"""
        results = self.retriever.retrieve_villas(question)
        return self.generator.generate(question, results, language)
    
    def query_faq(self, question: str, language: str = 'zh') -> str:
        """查询FAQ"""
        results = self.retriever.retrieve_faq(question)
        return self.generator.generate(question, results, language)
    
    def query_nearby(self, question: str, region: str = None, language: str = 'zh') -> str:
        """查询周边攻略"""
        results = self.retriever.retrieve_nearby(question, region)
        return self.generator.generate(question, results, language)
    
    def reload(self):
        """重新加载（热更新）"""
        reload_knowledge_base()
        self.retriever.rebuild()
        logger.info("🔄 RAG系统热更新完成")
    
    def set_llm_client(self, llm_client):
        """设置LLM客户端"""
        self.llm_client = llm_client
        self.generator.set_llm_client(llm_client)


# 全局RAG系统实例
_rag_system: Optional[RAGSystem] = None


def get_rag_system(llm_client=None, confidence_threshold: float = 0.1) -> RAGSystem:
    """获取RAG系统单例"""
    global _rag_system
    if _rag_system is None:
        _rag_system = RAGSystem(llm_client, confidence_threshold)
    return _rag_system


def rag_query(question: str, language: str = 'zh',
             top_k: int = 5, llm_client=None) -> str:
    """便捷查询函数"""
    rag = get_rag_system(llm_client)
    return rag.query(question, language, top_k)


# 导出
__all__ = [
    'RAGSystem',
    'get_rag_system',
    'rag_query',
    'get_knowledge_base',
    'get_indexer',
    'get_retriever',
    'get_generator',
    'reload_knowledge_base',
    'rebuild_index'
]
