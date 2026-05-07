#!/usr/bin/env python3
"""
RAG Indexer - 索引构建模块
基于关键词+TF-IDF的轻量级索引
支持热更新和增量索引
"""

import os
import json
import re
import sqlite3
import logging
from typing import Dict, List, Set, Tuple, Optional
from collections import Counter
import math

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 索引数据库路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_DB_PATH = os.path.join(BASE_DIR, "rag", "data", "rag_index.db")

# 确保目录存在
_index_db_dir = os.path.dirname(INDEX_DB_PATH)
if not os.path.exists(_index_db_dir):
    os.makedirs(_index_db_dir, exist_ok=True)

# 停用词列表
STOPWORDS = {
    'zh': {'的', '了', '和', '是', '在', '有', '我', '你', '他', '她', '它', '们', '这', '那', '就', '也', '都', '要', '会', '可以', '能', '可以', '一个', '没有', '什么', '怎么', '为什么', '吗', '呢', '吧', '啊', '哦', '嗯', '呢'},
    'en': {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'and', 'or', 'but', 'if', 'then', 'than', 'so', 'that', 'this', 'it', 'its'},
    'th': {'และ', 'กับ', 'ของ', 'ที่', 'เป็น', 'ได้', 'มี', 'ใน', 'ไม่', 'หรือ', 'ถ้า', 'แต่', 'ก็', 'เลย', 'นะ', 'ครับ', 'ค่ะ', 'คะ'}
}


class TFIDFIndexer:
    """TF-IDF 索引器"""
    
    def __init__(self):
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()
    
    def _init_db(self):
        """初始化索引数据库"""
        db_dir = os.path.dirname(INDEX_DB_PATH)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        self._conn = sqlite3.connect(INDEX_DB_PATH)
        self._conn.row_factory = sqlite3.Row
        
        # 创建索引表
        self._conn.executescript('''
            -- 文档表
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                doc_type TEXT,
                source TEXT,
                content TEXT,
                metadata TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            
            -- 词项表
            CREATE TABLE IF NOT EXISTS terms (
                term TEXT PRIMARY KEY,
                doc_count INTEGER DEFAULT 0
            );
            
            -- 倒排索引表
            CREATE TABLE IF NOT EXISTS inverted_index (
                term TEXT,
                doc_id TEXT,
                tf REAL DEFAULT 0,
                idf REAL DEFAULT 0,
                tfidf REAL DEFAULT 0,
                PRIMARY KEY (term, doc_id),
                FOREIGN KEY (term) REFERENCES terms(term),
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
            );
            
            -- 创建索引
            CREATE INDEX IF NOT EXISTS idx_inverted_term ON inverted_index(term);
            CREATE INDEX IF NOT EXISTS idx_inverted_doc ON inverted_index(doc_id);
            CREATE INDEX IF NOT EXISTS idx_inverted_tfidf ON inverted_index(tfidf);
        ''')
        self._conn.commit()
        logger.info(f"✅ 索引数据库初始化完成: {INDEX_DB_PATH}")
    
    def _tokenize(self, text: str) -> List[str]:
        """分词 - 支持中英泰混合"""
        if not text:
            return []
        
        tokens = []
        
        # 中文分词 - 字符级 + 双字词
        chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
        chinese_tokens = chinese_pattern.findall(text)
        
        # 英文分词
        english_pattern = re.compile(r'[a-zA-Z]+')
        english_tokens = english_pattern.findall(text)
        
        # 泰文分词
        thai_pattern = re.compile(r'[\u0e00-\u0e7f]+')
        thai_tokens = thai_pattern.findall(text)
        
        # 合并并清理
        all_tokens = chinese_tokens + english_tokens + thai_tokens
        
        for token in all_tokens:
            token_lower = token.lower()
            
            # 跳过停用词
            is_stopword = (
                token_lower in STOPWORDS.get('zh', set()) or 
                token_lower in STOPWORDS.get('en', set())
            )
            if is_stopword:
                continue
            
            # 中文词处理
            if re.search(r'[\u4e00-\u9fff]', token):
                # 单字跳过（太低效）
                if len(token) < 2:
                    continue
                
                # 双字词提取
                for i in range(len(token) - 1):
                    bigram = token_lower[i:i+2]
                    if len(bigram) >= 2 and bigram not in STOPWORDS.get('zh', set()):
                        tokens.append(bigram)
                
                # 整词也添加
                if len(token) >= 2:
                    tokens.append(token_lower)
            else:
                # 英文/泰文：长度>=2
                if len(token_lower) >= 2:
                    tokens.append(token_lower)
        
        return tokens
    
    def _calculate_tf(self, tokens: List[str]) -> Dict[str, float]:
        """计算词频(TF)"""
        counter = Counter(tokens)
        total = len(tokens) if tokens else 1
        return {term: count / total for term, count in counter.items()}
    
    def _calculate_idf(self, term: str, num_docs: int) -> float:
        """计算逆文档频率(IDF)"""
        cursor = self._conn.cursor()
        cursor.execute('SELECT doc_count FROM terms WHERE term = ?', (term,))
        row = cursor.fetchone()
        doc_count = row['doc_count'] if row else 0
        
        # 平滑处理
        return math.log((num_docs + 1) / (doc_count + 1)) + 1
    
    def build_index(self, documents: List[Dict]) -> int:
        """构建索引"""
        if not documents:
            return 0
        
        cursor = self._conn.cursor()
        num_docs = len(documents)
        
        # 清空旧索引
        cursor.execute('DELETE FROM inverted_index')
        cursor.execute('DELETE FROM documents')
        cursor.execute('DELETE FROM terms')
        
        for doc in documents:
            doc_id = doc['id']
            doc_type = doc.get('type', '')
            source = doc.get('source', '')
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            
            # 保存文档
            cursor.execute('''
                INSERT OR REPLACE INTO documents (doc_id, doc_type, source, content, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (doc_id, doc_type, source, content, json.dumps(metadata, ensure_ascii=False)))
            
            # 分词
            tokens = self._tokenize(content)
            tf = self._calculate_tf(tokens)
            
            # 更新词项表和倒排索引
            for term, tf_value in tf.items():
                # 更新词项文档计数
                cursor.execute('''
                    INSERT INTO terms (term, doc_count)
                    VALUES (?, 1)
                    ON CONFLICT(term) DO UPDATE SET doc_count = doc_count + 1
                ''', (term,))
                
                # 计算IDF和TF-IDF
                idf = self._calculate_idf(term, num_docs)
                tfidf = tf_value * idf
                
                # 保存倒排索引
                cursor.execute('''
                    INSERT OR REPLACE INTO inverted_index (term, doc_id, tf, idf, tfidf)
                    VALUES (?, ?, ?, ?, ?)
                ''', (term, doc_id, tf_value, idf, tfidf))
        
        self._conn.commit()
        logger.info(f"✅ 索引构建完成: {len(documents)} 文档")
        return len(documents)
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """搜索文档"""
        if not query:
            return []
        
        cursor = self._conn.cursor()
        query_tokens = self._tokenize(query)
        
        if not query_tokens:
            return []
        
        # 查询每个词项的文档
        doc_scores = {}
        for term in query_tokens:
            cursor.execute('''
                SELECT doc_id, tfidf FROM inverted_index
                WHERE term = ?
            ''', (term,))
            
            for row in cursor.fetchall():
                doc_id = row['doc_id']
                tfidf = row['tfidf']
                doc_scores[doc_id] = doc_scores.get(doc_id, 0) + tfidf
        
        # 按得分排序
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        
        # 获取文档详情
        results = []
        for doc_id, score in sorted_docs[:top_k]:
            cursor.execute('SELECT * FROM documents WHERE doc_id = ?', (doc_id,))
            row = cursor.fetchone()
            if row:
                results.append({
                    'doc_id': row['doc_id'],
                    'doc_type': row['doc_type'],
                    'source': row['source'],
                    'content': row['content'],
                    'metadata': json.loads(row['metadata']),
                    'relevance_score': round(score, 4)
                })
        
        return results
    
    def search_by_type(self, query: str, doc_type: str, top_k: int = 3) -> List[Dict]:
        """按类型搜索"""
        all_results = self.search(query, top_k * 2)
        return [r for r in all_results if r['doc_type'] == doc_type][:top_k]
    
    def close(self):
        """关闭连接"""
        if self._conn:
            self._conn.close()


# 全局索引器
_indexer: Optional[TFIDFIndexer] = None


def get_indexer() -> TFIDFIndexer:
    """获取索引器单例"""
    global _indexer
    if _indexer is None:
        _indexer = TFIDFIndexer()
    return _indexer


def rebuild_index(knowledge_base) -> int:
    """重建索引"""
    indexer = get_indexer()
    documents = knowledge_base.get_all_documents()
    return indexer.build_index(documents)
