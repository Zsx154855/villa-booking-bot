#!/usr/bin/env python3
"""
GBrain Layer 2: SQLite Persistence
SQLite持久化层 - 替换内存字典，数据重启不丢失
"""

import os
import json
import sqlite3
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class PersistentMemory:
    """持久化记忆单元"""
    id: str
    user_id: Optional[str]
    memory_type: str  # working/episodic/semantic
    key: str
    value: str  # JSON字符串
    created_at: str
    updated_at: str
    expires_at: Optional[str] = None  # TTL过期时间
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['value_obj'] = json.loads(self.value) if self.value else None
        return data


class GBrainPersistence:
    """
    GBrain SQLite持久化层
    
    特性：
    - SQLite WAL模式，高并发读写
    - 自动过期清理
    - 批量操作支持
    - 与现有memory/目录兼容
    """
    
    DB_NAME = "gbrain.db"
    
    def __init__(self, db_path: str = None):
        """
        初始化持久化层
        
        Args:
            db_path: 数据库路径，默认在应用目录
        """
        if db_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base_dir, self.DB_NAME)
        
        self._db_path = db_path
        self._lock = Lock()
        self._init_database()
        
        logger.info(f"✅ GBrain Persistence初始化完成 (DB: {db_path})")
    
    def _init_database(self):
        """初始化数据库表"""
        with self._get_connection() as conn:
            # 持久化记忆表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    memory_type TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT,
                    UNIQUE(user_id, memory_type, key)
                )
            """)
            
            # 别墅数据缓存表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS villas_cache (
                    villa_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # 用户画像表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    profile_data TEXT NOT NULL,
                    interaction_count INTEGER DEFAULT 0,
                    last_interaction TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # 预订历史表（用于分析）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS booking_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    villa_id TEXT,
                    checkin TEXT,
                    checkout TEXT,
                    total_price REAL,
                    status TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            # 创建索引
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_user_type 
                ON memories(user_id, memory_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_expires 
                ON memories(expires_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_booking_history_user 
                ON booking_history(user_id)
            """)
            
            # 启用WAL模式
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = sqlite3.connect(self._db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _generate_id(self, user_id: str, memory_type: str, key: str) -> str:
        """生成唯一ID"""
        raw = f"{user_id}:{memory_type}:{key}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
    
    # ============ 通用记忆操作 ============
    
    def set(
        self,
        user_id: Optional[str],
        memory_type: str,
        key: str,
        value: Any,
        ttl_seconds: int = None
    ) -> bool:
        """
        保存记忆
        
        Args:
            user_id: 用户ID（可选）
            memory_type: 记忆类型
            key: 键
            value: 值（会自动JSON序列化）
            ttl_seconds: 过期秒数（可选）
            
        Returns:
            是否成功
        """
        with self._lock:
            try:
                memory_id = self._generate_id(user_id or "", memory_type, key)
                now = datetime.now().isoformat()
                expires_at = None
                if ttl_seconds:
                    expires_at = (datetime.now() + timedelta(seconds=ttl_seconds)).isoformat()
                
                value_json = json.dumps(value, ensure_ascii=False)
                
                with self._get_connection() as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO memories 
                        (id, user_id, memory_type, key, value, created_at, updated_at, expires_at)
                        VALUES (?, ?, ?, ?, ?, 
                            COALESCE((SELECT created_at FROM memories WHERE id = ?), ?),
                            ?, ?)
                    """, (memory_id, user_id, memory_type, key, value_json,
                          memory_id, now, now, expires_at))
                
                return True
            except Exception as e:
                logger.error(f"保存记忆失败: {e}")
                return False
    
    def get(
        self,
        user_id: Optional[str],
        memory_type: str,
        key: str,
        include_expired: bool = False
    ) -> Optional[Any]:
        """
        获取记忆
        
        Args:
            user_id: 用户ID
            memory_type: 记忆类型
            key: 键
            include_expired: 是否包含过期数据
            
        Returns:
            记忆值或None
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    if include_expired:
                        rows = conn.execute("""
                            SELECT value, expires_at FROM memories 
                            WHERE user_id IS ? AND memory_type = ? AND key = ?
                        """, (user_id, memory_type, key)).fetchall()
                    else:
                        rows = conn.execute("""
                            SELECT value, expires_at FROM memories 
                            WHERE user_id IS ? AND memory_type = ? AND key = ?
                            AND (expires_at IS NULL OR expires_at > ?)
                        """, (user_id, memory_type, key, datetime.now().isoformat())).fetchall()
                    
                    if rows:
                        return json.loads(rows[0]['value'])
            except Exception as e:
                logger.error(f"获取记忆失败: {e}")
            return None
    
    def delete(self, user_id: Optional[str], memory_type: str, key: str) -> bool:
        """删除记忆"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    conn.execute("""
                        DELETE FROM memories 
                        WHERE user_id IS ? AND memory_type = ? AND key = ?
                    """, (user_id, memory_type, key))
                return True
            except Exception as e:
                logger.error(f"删除记忆失败: {e}")
                return False
    
    def get_all(
        self,
        user_id: Optional[str] = None,
        memory_type: str = None,
        limit: int = 100
    ) -> List[PersistentMemory]:
        """获取所有匹配的记忆"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    query = "SELECT * FROM memories WHERE 1=1"
                    params = []
                    
                    if user_id is not None:
                        query += " AND user_id = ?"
                        params.append(user_id)
                    
                    if memory_type:
                        query += " AND memory_type = ?"
                        params.append(memory_type)
                    
                    query += " ORDER BY updated_at DESC LIMIT ?"
                    params.append(limit)
                    
                    rows = conn.execute(query, params).fetchall()
                    return [PersistentMemory(**dict(row)) for row in rows]
            except Exception as e:
                logger.error(f"获取所有记忆失败: {e}")
                return []
    
    def cleanup_expired(self) -> int:
        """清理过期记忆"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute("""
                        DELETE FROM memories 
                        WHERE expires_at IS NOT NULL AND expires_at < ?
                    """, (datetime.now().isoformat(),))
                    count = cursor.rowcount
                    if count > 0:
                        logger.info(f"清理了 {count} 条过期记忆")
                    return count
            except Exception as e:
                logger.error(f"清理过期记忆失败: {e}")
                return 0
    
    # ============ 别墅缓存 ============
    
    def cache_villas(self, villas: List[Dict]) -> bool:
        """缓存别墅数据"""
        with self._lock:
            try:
                now = datetime.now().isoformat()
                with self._get_connection() as conn:
                    for villa in villas:
                        conn.execute("""
                            INSERT OR REPLACE INTO villas_cache (villa_id, data, updated_at)
                            VALUES (?, ?, ?)
                        """, (villa['id'], json.dumps(villa, ensure_ascii=False), now))
                logger.info(f"已缓存 {len(villas)} 套别墅")
                return True
            except Exception as e:
                logger.error(f"缓存别墅失败: {e}")
                return False
    
    def get_cached_villas(self) -> List[Dict]:
        """获取缓存的别墅数据"""
        try:
            with self._get_connection() as conn:
                rows = conn.execute("""
                    SELECT data FROM villas_cache ORDER BY updated_at DESC
                """).fetchall()
                return [json.loads(row['data']) for row in rows]
        except Exception as e:
            logger.error(f"获取缓存别墅失败: {e}")
            return []
    
    def get_cached_villa(self, villa_id: str) -> Optional[Dict]:
        """获取单套别墅缓存"""
        try:
            with self._get_connection() as conn:
                row = conn.execute("""
                    SELECT data FROM villas_cache WHERE villa_id = ?
                """, (villa_id,)).fetchone()
                if row:
                    return json.loads(row['data'])
        except Exception as e:
            logger.error(f"获取别墅缓存失败: {e}")
        return None
    
    # ============ 用户画像 ============
    
    def save_user_profile(self, user_id: str, profile_data: Dict) -> bool:
        """保存用户画像"""
        with self._lock:
            try:
                now = datetime.now().isoformat()
                with self._get_connection() as conn:
                    # 更新交互次数
                    conn.execute("""
                        UPDATE user_profiles 
                        SET profile_data = ?, 
                            interaction_count = interaction_count + 1,
                            last_interaction = ?,
                            updated_at = ?
                        WHERE user_id = ?
                    """, (json.dumps(profile_data, ensure_ascii=False), 
                          now, now, user_id))
                    
                    if conn.total_changes == 0:
                        conn.execute("""
                            INSERT INTO user_profiles 
                            (user_id, profile_data, interaction_count, last_interaction, created_at, updated_at)
                            VALUES (?, ?, 1, ?, ?, ?)
                        """, (user_id, json.dumps(profile_data, ensure_ascii=False),
                              now, now, now))
                return True
            except Exception as e:
                logger.error(f"保存用户画像失败: {e}")
                return False
    
    def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """获取用户画像"""
        try:
            with self._get_connection() as conn:
                row = conn.execute("""
                    SELECT profile_data FROM user_profiles WHERE user_id = ?
                """, (user_id,)).fetchone()
                if row:
                    return json.loads(row['profile_data'])
        except Exception as e:
            logger.error(f"获取用户画像失败: {e}")
        return None
    
    # ============ 预订历史 ============
    
    def record_booking(self, user_id: str, booking_data: Dict) -> bool:
        """记录预订"""
        with self._lock:
            try:
                now = datetime.now().isoformat()
                with self._get_connection() as conn:
                    conn.execute("""
                        INSERT INTO booking_history 
                        (user_id, villa_id, checkin, checkout, total_price, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        user_id,
                        booking_data.get('villa_id'),
                        booking_data.get('checkin'),
                        booking_data.get('checkout'),
                        booking_data.get('total_price', 0),
                        booking_data.get('status', 'completed'),
                        now
                    ))
                return True
            except Exception as e:
                logger.error(f"记录预订失败: {e}")
                return False
    
    def get_user_booking_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """获取用户预订历史"""
        try:
            with self._get_connection() as conn:
                rows = conn.execute("""
                    SELECT * FROM booking_history 
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (user_id, limit)).fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取预订历史失败: {e}")
            return []
    
    # ============ 统计方法 ============
    
    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计"""
        try:
            with self._get_connection() as conn:
                memory_count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
                villa_count = conn.execute("SELECT COUNT(*) FROM villas_cache").fetchone()[0]
                user_count = conn.execute("SELECT COUNT(*) FROM user_profiles").fetchone()[0]
                booking_count = conn.execute("SELECT COUNT(*) FROM booking_history").fetchone()[0]
                
                return {
                    "memory_count": memory_count,
                    "villa_count": villa_count,
                    "user_count": user_count,
                    "booking_count": booking_count
                }
        except Exception as e:
            logger.error(f"获取统计失败: {e}")
            return {}
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            with self._get_connection() as conn:
                conn.execute("SELECT 1")
                return {"status": "ok", "db_path": self._db_path}
        except Exception as e:
            return {"status": "error", "error": str(e)}


# 全局单例
gbrain_persistence = GBrainPersistence()
