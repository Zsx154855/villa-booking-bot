#!/usr/bin/env python3
"""
RAG Knowledge Base - 知识库管理模块
支持多语言(中文/英文/泰语)和热更新
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 知识库目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "rag", "data")

# 支持的语言
SUPPORTED_LANGUAGES = ['zh', 'en', 'th']


class KnowledgeBase:
    """知识库管理类"""
    
    def __init__(self):
        self._villas: List[Dict] = []
        self._faq: List[Dict] = []
        self._guides: List[Dict] = []
        self._nearby: List[Dict] = []
        self._last_modified: Dict[str, float] = {}
        self._load_all()
    
    def _load_all(self):
        """加载所有知识库文件"""
        self._load_villas()
        self._load_faq()
        self._load_guides()
        self._load_nearby()
        logger.info(f"✅ 知识库加载完成: {len(self._villas)}别墅, {len(self._faq)}FAQ, {len(self._guides)}指南, {len(self._nearby)}周边")
    
    def _load_json(self, filename: str) -> List[Dict]:
        """加载单个JSON文件，支持热更新检测"""
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            logger.warning(f"⚠️ 知识库文件不存在: {filepath}")
            # 返回空列表而不是缓存
            setattr(self, f"__{filename.replace('.json', '')}", [])
            return []
        
        # 始终读取文件（缓存只用于加速）
        cache_key = filename.replace('.json', '')
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 更新缓存
            setattr(self, f"__{cache_key}", data)
            # 移除缓存标记，表示已加载
            if cache_key in self._last_modified:
                del self._last_modified[cache_key]
            
            logger.info(f"📖 加载: {filename} ({len(data)} 条记录)")
            return data
        except Exception as e:
            logger.error(f"❌ 加载 {filename} 失败: {e}")
            # 返回已有缓存
            cached = getattr(self, f"__{cache_key}", [])
            return cached
    
    def _load_villas(self):
        """加载别墅数据"""
        self.__villas = self._load_json('villas.json')
        self._villas = self.__villas
    
    def _load_faq(self):
        """加载FAQ数据"""
        self.__faq = self._load_json('faq.json')
        self._faq = self.__faq
    
    def _load_guides(self):
        """加载入住指南"""
        self.__guides = self._load_json('guides.json')
        self._guides = self.__guides
    
    def _load_nearby(self):
        """加载周边攻略"""
        self.__nearby = self._load_json('nearby.json')
        self._nearby = self.__nearby
    
    def reload_if_modified(self) -> bool:
        """热更新：检查并重新加载修改过的文件"""
        reloaded = False
        for filename in ['villas.json', 'faq.json', 'guides.json', 'nearby.json']:
            filepath = os.path.join(DATA_DIR, filename)
            if os.path.exists(filepath):
                mtime = os.path.getmtime(filepath)
                if filename.replace('.json', '') not in self._last_modified or \
                   self._last_modified.get(filename.replace('.json', '')) != mtime:
                    self._load_json(filename)
                    reloaded = True
        
        if reloaded:
            self._load_all()
            logger.info("🔄 知识库热更新完成")
        return reloaded
    
    def get_all_documents(self) -> List[Dict[str, Any]]:
        """获取所有文档（用于索引构建）"""
        docs = []
        
        # 添加别墅文档
        for villa in self._villas:
            docs.append({
                'id': f"villa_{villa.get('id', '')}",
                'type': 'villa',
                'source': villa.get('name', ''),
                'content': self._villa_to_text(villa),
                'metadata': {
                    'id': villa.get('id'),
                    'name': villa.get('name'),
                    'region': villa.get('region'),
                    'price': villa.get('price_per_night'),
                    'bedrooms': villa.get('bedrooms'),
                    'max_guests': villa.get('max_guests'),
                    'amenities': villa.get('amenities', [])
                }
            })
        
        # 添加FAQ文档
        for faq in self._faq:
            docs.append({
                'id': f"faq_{faq.get('id', '')}",
                'type': 'faq',
                'source': '常见问题',
                'content': self._faq_to_text(faq),
                'metadata': {
                    'category': faq.get('category', ''),
                    'question': faq.get('question', '')
                }
            })
        
        # 添加入住指南文档
        for guide in self._guides:
            docs.append({
                'id': f"guide_{guide.get('id', '')}",
                'type': 'guide',
                'source': '入住指南',
                'content': self._guide_to_text(guide),
                'metadata': {
                    'title': guide.get('title', ''),
                    'category': guide.get('category', '')
                }
            })
        
        # 添加周边攻略文档
        for nearby in self._nearby:
            docs.append({
                'id': f"nearby_{nearby.get('id', '')}",
                'type': 'nearby',
                'source': nearby.get('region', ''),
                'content': self._nearby_to_text(nearby),
                'metadata': {
                    'region': nearby.get('region', ''),
                    'category': nearby.get('category', ''),
                    'name': nearby.get('name', '')
                }
            })
        
        return docs
    
    def _villa_to_text(self, villa: Dict) -> str:
        """将别墅数据转换为文本"""
        texts = []
        
        # 基础信息
        name = villa.get('name', '')
        region = villa.get('region', '')
        room_type = villa.get('room_type', '')
        price = villa.get('price_per_night', 0)
        bedrooms = villa.get('bedrooms', 0)
        bathrooms = villa.get('bathrooms', 0)
        max_guests = villa.get('max_guests', 0)
        
        texts.append(f"别墅名称: {name}")
        texts.append(f"地区: {region}")
        if room_type:
            texts.append(f"房型: {room_type}")
        texts.append(f"价格: {price}泰铢/晚")
        texts.append(f"卧室: {bedrooms}间 | 浴室: {bathrooms}间 | 可住: {max_guests}人")
        
        # 设施
        amenities = villa.get('amenities', [])
        if amenities:
            texts.append(f"设施: {', '.join(amenities)}")
        
        # 描述
        description = villa.get('description', '')
        if description:
            texts.append(f"描述: {description}")
        
        # 多语言描述
        for lang in SUPPORTED_LANGUAGES:
            desc_key = f'description_{lang}'
            if desc_key in villa:
                texts.append(f"[{lang}] {villa[desc_key]}")
        
        return '\n'.join(texts)
    
    def _faq_to_text(self, faq: Dict) -> str:
        """将FAQ转换为文本"""
        texts = []
        texts.append(f"问题: {faq.get('question', '')}")
        texts.append(f"答案: {faq.get('answer', '')}")
        
        if faq.get('category'):
            texts.append(f"分类: {faq.get('category')}")
        
        # 多语言
        for lang in SUPPORTED_LANGUAGES:
            q_key = f'question_{lang}'
            a_key = f'answer_{lang}'
            if q_key in faq:
                texts.append(f"[{lang}] 问题: {faq[q_key]}")
            if a_key in faq:
                texts.append(f"[{lang}] 答案: {faq[a_key]}")
        
        return '\n'.join(texts)
    
    def _guide_to_text(self, guide: Dict) -> str:
        """将入住指南转换为文本"""
        texts = []
        texts.append(f"标题: {guide.get('title', '')}")
        texts.append(f"内容: {guide.get('content', '')}")
        
        if guide.get('category'):
            texts.append(f"分类: {guide.get('category')}")
        
        return '\n'.join(texts)
    
    def _nearby_to_text(self, nearby: Dict) -> str:
        """将周边攻略转换为文本"""
        texts = []
        texts.append(f"名称: {nearby.get('name', '')}")
        texts.append(f"地区: {nearby.get('region', '')}")
        texts.append(f"类型: {nearby.get('category', '')}")
        
        desc = nearby.get('description', '')
        if desc:
            texts.append(f"描述: {desc}")
        
        distance = nearby.get('distance', '')
        if distance:
            texts.append(f"距离: {distance}")
        
        # 多语言
        for lang in SUPPORTED_LANGUAGES:
            desc_key = f'description_{lang}'
            if desc_key in nearby:
                texts.append(f"[{lang}] {nearby[desc_key]}")
        
        return '\n'.join(texts)
    
    def get_villa_by_id(self, villa_id: str) -> Optional[Dict]:
        """根据ID获取别墅"""
        for villa in self._villas:
            if villa.get('id') == villa_id:
                return villa
        return None
    
    def get_villas_by_region(self, region: str) -> List[Dict]:
        """根据地区获取别墅"""
        return [v for v in self._villas if v.get('region') == region]
    
    def search_by_keywords(self, keywords: List[str]) -> List[Dict]:
        """根据关键词搜索文档"""
        results = []
        all_docs = self.get_all_documents()
        
        for doc in all_docs:
            score = 0
            content_lower = doc['content'].lower()
            
            for kw in keywords:
                kw_lower = kw.lower()
                if kw_lower in content_lower:
                    score += 1
            
            if score > 0:
                doc['relevance_score'] = score
                results.append(doc)
        
        # 按相关性排序
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        return results


# 全局单例
_knowledge_base: Optional[KnowledgeBase] = None


def get_knowledge_base() -> KnowledgeBase:
    """获取知识库单例"""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase()
    return _knowledge_base


def reload_knowledge_base() -> bool:
    """重新加载知识库（支持热更新）"""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase()
        return True
    return _knowledge_base.reload_if_modified()
