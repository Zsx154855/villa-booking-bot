#!/usr/bin/env python3
"""
RAG Retriever - 检索器模块
支持关键词检索、语义重排序、置信度阈值
"""

import os
import logging
from typing import List, Dict, Optional, Tuple

from .indexer import get_indexer, rebuild_index
from .knowledge_base import get_knowledge_base, reload_knowledge_base

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 置信度阈值（TF-IDF分数通常较低，设为0.1更合理）
DEFAULT_CONFIDENCE_THRESHOLD = 0.1


class Retriever:
    """检索器"""
    
    def __init__(self, confidence_threshold: float = 0.1):
        self.confidence_threshold = confidence_threshold
        self.indexer = get_indexer()
        self.knowledge_base = get_knowledge_base()
        self._is_indexed = False
    
    def ensure_indexed(self):
        """确保索引已构建"""
        if not self._is_indexed:
            self.rebuild()
    
    def rebuild(self):
        """重建索引"""
        # 热更新知识库
        reload_knowledge_base()
        # 重建索引
        count = rebuild_index(self.knowledge_base)
        self._is_indexed = count > 0
        logger.info(f"🔍 检索器就绪: 索引 {count} 条文档")
    
    def retrieve(self, query: str, top_k: int = 5, doc_type: Optional[str] = None) -> List[Dict]:
        """
        检索相关文档
        
        Args:
            query: 用户查询
            top_k: 返回前k条
            doc_type: 可选，限定文档类型 (villa/faq/guide/nearby)
        
        Returns:
            检索结果列表
        """
        self.ensure_indexed()
        
        if not query or not query.strip():
            return []
        
        try:
            # 执行搜索
            if doc_type:
                results = self.indexer.search_by_type(query, doc_type, top_k)
            else:
                results = self.indexer.search(query, top_k)
            
            # 过滤置信度阈值
            filtered = [r for r in results if r['relevance_score'] >= self.confidence_threshold]
            
            logger.debug(f"检索 '{query}': 找到 {len(results)} 条, 通过阈值 {len(filtered)} 条")
            return filtered
            
        except Exception as e:
            logger.error(f"检索失败: {e}")
            return []
    
    def retrieve_villas(self, query: str, top_k: int = 3) -> List[Dict]:
        """检索别墅"""
        return self.retrieve(query, top_k, doc_type='villa')
    
    def retrieve_faq(self, query: str, top_k: int = 3) -> List[Dict]:
        """检索FAQ"""
        return self.retrieve(query, top_k, doc_type='faq')
    
    def retrieve_guides(self, query: str, top_k: int = 2) -> List[Dict]:
        """检索入住指南"""
        return self.retrieve(query, top_k, doc_type='guide')
    
    def retrieve_nearby(self, query: str, region: Optional[str] = None, top_k: int = 3) -> List[Dict]:
        """检索周边攻略"""
        results = self.retrieve(query, top_k, doc_type='nearby')
        
        if region:
            # 按地区过滤
            results = [r for r in results if r['metadata'].get('region') == region]
        
        return results
    
    def rerank_with_llm(self, query: str, candidates: List[Dict], 
                        llm_client=None, top_k: int = 3) -> List[Dict]:
        """
        使用LLM对候选结果进行重排序
        
        Args:
            query: 用户查询
            candidates: 候选文档列表
            llm_client: LLM客户端
            top_k: 返回前k条
        
        Returns:
            重排序后的结果
        """
        if not candidates or not llm_client:
            return candidates[:top_k]
        
        try:
            # 构建重排序prompt
            rerank_prompt = self._build_rerank_prompt(query, candidates)
            
            # 调用LLM
            response = llm_client.chat(messages=[
                {"role": "system", "content": "你是一个专业的别墅预订助手，负责评估文档与查询的相关性。"},
                {"role": "user", "content": rerank_prompt}
            ])
            
            # 解析LLM返回的排序
            # 假设LLM返回 JSON 格式: [{"index": 0, "reason": "..."}, ...]
            import json
            import re
            
            # 尝试提取JSON
            match = re.search(r'\[.*\]', response, re.DOTALL)
            if match:
                rankings = json.loads(match.group())
                reranked = []
                for rank in rankings:
                    idx = rank.get('index', 0)
                    if idx < len(candidates):
                        candidates[idx]['rerank_reason'] = rank.get('reason', '')
                        reranked.append(candidates[idx])
                return reranked[:top_k]
            
        except Exception as e:
            logger.warning(f"LLM重排序失败: {e}")
        
        # 回退到原始排序
        return candidates[:top_k]
    
    def _build_rerank_prompt(self, query: str, candidates: List[Dict]) -> str:
        """构建重排序prompt"""
        prompt_parts = [
            f"用户查询: {query}",
            "",
            "以下是候选文档，请评估每个文档与查询的相关性（1-5分）并说明理由：",
            ""
        ]
        
        for i, doc in enumerate(candidates):
            prompt_parts.append(f"文档{i}:")
            prompt_parts.append(f"  类型: {doc.get('doc_type', 'unknown')}")
            prompt_parts.append(f"  来源: {doc.get('source', '')}")
            prompt_parts.append(f"  内容: {doc.get('content', '')[:200]}...")
            prompt_parts.append("")
        
        prompt_parts.extend([
            "请按JSON数组格式返回排序结果：",
            '[{"index": 0, "score": 5, "reason": "..."}, ...]'
        ])
        
        return '\n'.join(prompt_parts)
    
    def format_retrieval_context(self, results: List[Dict], max_chars: int = 2000) -> str:
        """
        格式化检索结果为上下文
        
        Args:
            results: 检索结果
            max_chars: 最大字符数
        
        Returns:
            格式化的上下文字符串
        """
        if not results:
            return ""
        
        context_parts = ["【参考信息】"]
        total_chars = len("【参考信息】")
        
        for i, result in enumerate(results, 1):
            doc_type = result.get('doc_type', 'unknown')
            source = result.get('source', '')
            content = result.get('content', '')
            
            # 截断过长内容
            if total_chars + len(content) > max_chars:
                content = content[:max_chars - total_chars] + "..."
            
            part = f"\n{i}. [{doc_type}] {source}\n{content}"
            context_parts.append(part)
            total_chars += len(part)
        
        return '\n'.join(context_parts)


# 全局检索器
_retriever: Optional[Retriever] = None


def get_retriever(confidence_threshold: float = 0.1) -> Retriever:
    """获取检索器单例"""
    global _retriever
    if _retriever is None:
        _retriever = Retriever(confidence_threshold)
        _retriever.ensure_indexed()
    return _retriever


def retrieve(query: str, top_k: int = 5, doc_type: Optional[str] = None) -> List[Dict]:
    """便捷检索函数"""
    return get_retriever().retrieve(query, top_k, doc_type)


def format_context(results: List[Dict], max_chars: int = 2000) -> str:
    """便捷格式化函数"""
    return get_retriever().format_retrieval_context(results, max_chars)
