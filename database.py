#!/usr/bin/env python3
"""
Taimili Villa Booking System - Database Module
支持 PostgreSQL (Koyeb 生产环境) 和 SQLite (本地开发)
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

# 导入配置模块
from database_config import db_config, is_production

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============ 数据库路径配置 (SQLite) ============
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DATA_DIR, db_config.get_sqlite_path())

# ============ PostgreSQL 连接池 ============
_pg_pool = None

def _get_pg_pool():
    """获取 PostgreSQL 连接池 (延迟初始化)"""
    global _pg_pool
    if _pg_pool is None:
        try:
            import psycopg2
            from psycopg2 import pool
            
            # 适配 Koyeb 免费版限制，使用简单连接池
            _pg_pool = psycopg2.pool.SimpleConnectionPool(
                db_config.pool_min_connections,
                db_config.pool_max_connections,
                dbconfig=db_config.get_postgres_dsn(),
                connect_timeout=db_config.command_timeout
            )
            logger.info("✅ PostgreSQL 连接池初始化成功")
        except ImportError:
            logger.error("psycopg2 未安装，请运行: pip install psycopg2-binary")
            raise
        except Exception as e:
            logger.error(f"PostgreSQL 连接池初始化失败: {e}")
            raise
    return _pg_pool

@contextmanager
def get_pg_connection():
    """获取 PostgreSQL 连接的上下文管理器"""
    pool = _get_pg_pool()
    conn = None
    try:
        conn = pool.getconn()
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"PostgreSQL 错误: {e}")
        raise
    finally:
        if conn:
            pool.putconn(conn)

# ============ SQLite 连接管理 ============
def get_db_path():
    """获取 SQLite 数据库路径，确保 data 目录存在"""
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    return DB_PATH

@contextmanager
def get_sqlite_connection():
    """获取 SQLite 连接的上下文管理器"""
    import sqlite3
    conn = None
    try:
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"SQLite 错误: {e}")
        raise
    finally:
        if conn:
            conn.close()

# ============ 统一连接接口 ============
@contextmanager
def get_connection():
    """统一获取数据库连接 - 根据配置自动选择 PostgreSQL 或 SQLite"""
    if db_config.is_postgresql:
        with get_pg_connection() as conn:
            yield conn
    else:
        with get_sqlite_connection() as conn:
            yield conn

# ============ 参数占位符适配 ============
def _get_param_placeholder(idx: int, db_type: str = None) -> str:
    """获取参数占位符 - 适配不同数据库"""
    if db_type is None:
        db_type = 'postgresql' if db_config.is_postgresql else 'sqlite'
    return '?' if db_type == 'sqlite' else f'${idx}'

def _adapt_params(params: list, db_type: str = None) -> list:
    """适配参数列表 - SQLite 直接用列表，PostgreSQL 需要元组"""
    return tuple(params) if db_type == 'postgresql' else params

# ============ 数据库初始化 ============
def init_db():
    """初始化数据库，创建表结构"""
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    
    if db_config.is_postgresql:
        # PostgreSQL 初始化
        init_pg_schema(schema_path)
    else:
        # SQLite 初始化
        init_sqlite_schema(schema_path)
    
    logger.info("✅ 数据库初始化完成")
    
    # 自动导入初始数据（如果数据库为空）
    _auto_import_initial_data()
    
    return True

def _auto_import_initial_data():
    """自动导入初始数据（如果数据库为空）"""
    try:
        # 检查是否有别墅数据
        villas = get_all_villas(active_only=False)
        if villas:
            logger.info(f"📊 数据库已有 {len(villas)} 套别墅数据")
            return
        
        # 尝试从 villas.json 导入
        villas_json_path = os.path.join(os.path.dirname(__file__), "villas.json")
        if os.path.exists(villas_json_path):
            logger.info("🔄 检测到数据库为空，自动导入villas.json...")
            with open(villas_json_path, 'r', encoding='utf-8') as f:
                villas_data = json.load(f)
            
            imported = 0
            for villa in villas_data:
                # 转换字段名
                villa_record = {
                    "id": villa.get("id"),
                    "name": villa.get("name"),
                    "region": villa.get("region"),
                    "room_type": villa.get("type"),
                    "price_per_night": villa.get("price_per_night", 0),
                    "bedrooms": villa.get("bedrooms", 0),
                    "bathrooms": villa.get("bathrooms", 0),
                    "max_guests": villa.get("max_guests", 0),
                    "amenities": json.dumps(villa.get("amenities", []), ensure_ascii=False),
                    "images": json.dumps(villa.get("images", []), ensure_ascii=False),
                    "description": villa.get("description", ""),
                    "is_active": True
                }
                if create_villa(villa_record):
                    imported += 1
            
            logger.info(f"✅ 成功导入 {imported} 套别墅数据")
        else:
            logger.warning("⚠️ 未找到villas.json文件，请手动迁移数据")
    except Exception as e:
        logger.error(f"❌ 自动导入数据失败: {e}")

def init_sqlite_schema(schema_path: str):
    """初始化 SQLite schema"""
    import sqlite3
    
    with get_sqlite_connection() as conn:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = f.read()
        
        # SQLite 兼容处理
        schema = schema.replace('SERIAL PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT')
        schema = schema.replace('TIMESTAMP DEFAULT CURRENT_TIMESTAMP', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        
        conn.executescript(schema)

def init_pg_schema(schema_path: str):
    """初始化 PostgreSQL schema"""
    with get_pg_connection() as conn:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = f.read()
        
        cursor = conn.cursor()
        cursor.execute(schema)
        cursor.close()

# ============ 别墅数据操作 ============
def get_all_villas(region: Optional[str] = None, active_only: bool = True) -> List[Dict]:
    """获取所有别墅列表"""
    sql = "SELECT * FROM villas WHERE 1=1"
    params = []
    
    if region:
        sql += " AND region = ?"
        params.append(region)
    
    if active_only:
        sql += " AND is_active = 1"
    
    sql += " ORDER BY region, id"
    
    with get_connection() as conn:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
        return [_row_to_dict(row, cursor.description) for row in rows]

def get_villa(villa_id: str) -> Optional[Dict]:
    """根据ID获取别墅信息"""
    placeholders = _get_param_placeholder(1)
    with get_connection() as conn:
        cursor = conn.execute(
            f"SELECT * FROM villas WHERE id = {placeholders}",
            (villa_id,)
        )
        row = cursor.fetchone()
        return _row_to_dict(row, cursor.description) if row else None

def get_villas_by_region(region: str) -> List[Dict]:
    """按地区获取别墅列表"""
    return get_all_villas(region=region)

def create_villa(villa: Dict) -> bool:
    """创建新别墅记录"""
    try:
        with get_connection() as conn:
            columns = [
                "id", "name", "region", "room_type", "price_per_night",
                "bedrooms", "bathrooms", "max_guests", "amenities",
                "images", "description", "is_active"
            ]
            values_placeholders = ", ".join(["?" for _ in range(len(columns))])
            
            conn.execute(f"""
                INSERT INTO villas (
                    {", ".join(columns)}
                ) VALUES ({values_placeholders})
            """, (
                villa.get('id'),
                villa.get('name'),
                villa.get('region'),
                villa.get('type'),  # JSON用type，DB用room_type
                villa.get('price_per_night'),
                villa.get('bedrooms', 0),
                villa.get('bathrooms', 0),
                villa.get('max_guests', 0),
                json.dumps(villa.get('amenities', []), ensure_ascii=False),
                json.dumps(villa.get('images', []), ensure_ascii=False),
                villa.get('description', ''),
                villa.get('is_active', 1)
            ))
            logger.info(f"✅ 别墅创建成功: {villa.get('id')}")
            return True
    except Exception as e:
        logger.error(f"创建别墅失败: {e}")
        return False

def update_villa(villa_id: str, updates: Dict) -> bool:
    """更新别墅信息"""
    try:
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            if key in ['amenities', 'images']:
                value = json.dumps(value, ensure_ascii=False)
            set_clauses.append(f"{key} = ?")
            params.append(value)
        
        set_clauses.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        
        params.append(villa_id)
        
        sql = f"UPDATE villas SET {', '.join(set_clauses)} WHERE id = ?"
        
        with get_connection() as conn:
            conn.execute(sql, tuple(params))
            logger.info(f"✅ 别墅更新成功: {villa_id}")
            return True
    except Exception as e:
        logger.error(f"更新别墅失败: {e}")
        return False

# ============ 预订数据操作 ============
def create_booking(booking: Dict) -> bool:
    """创建新预订记录"""
    try:
        with get_connection() as conn:
            columns = [
                "booking_id", "user_id", "villa_id", "villa_name", "villa_region",
                "checkin", "checkout", "guests",
                "contact_name", "contact_phone", "contact_note",
                "price_per_night", "total_price", "status"
            ]
            values_placeholders = ", ".join(['?' for _ in range(len(columns))])
            
            conn.execute(f"""
                INSERT INTO bookings (
                    {", ".join(columns)}
                ) VALUES ({values_placeholders})
            """, (
                booking.get('id'),
                booking.get('user_id'),
                booking.get('villa_id'),
                booking.get('villa_name'),
                booking.get('villa_region'),
                booking.get('checkin'),
                booking.get('checkout'),
                booking.get('guests', 1),
                booking.get('contact_name'),
                booking.get('contact_phone'),
                booking.get('contact_note', ''),
                booking.get('price_per_night', 0),
                booking.get('total_price', 0),
                booking.get('status', 'pending')
            ))
            logger.info(f"✅ 预订创建成功: {booking.get('id')}")
            return True
    except Exception as e:
        logger.error(f"创建预订失败: {e}")
        return False

def get_booking(booking_id: str) -> Optional[Dict]:
    """根据预订ID获取预订信息"""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM bookings WHERE booking_id = ?",
            (booking_id,)
        )
        row = cursor.fetchone()
        return _row_to_dict(row, cursor.description) if row else None

def get_user_bookings(user_id: str) -> List[Dict]:
    """获取用户的所有预订记录"""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM bookings WHERE user_id = ? ORDER BY created_at DESC",
            (str(user_id),)
        )
        rows = cursor.fetchall()
        return [_row_to_dict(row, cursor.description) for row in rows]

def get_villa_bookings(villa_id: str, status: Optional[str] = None) -> List[Dict]:
    """获取别墅的所有预订记录"""
    sql = "SELECT * FROM bookings WHERE villa_id = ?"
    params = [villa_id]
    
    if status:
        sql += " AND status = ?"
        params.append(status)
    
    sql += " ORDER BY checkin"
    
    with get_connection() as conn:
        cursor = conn.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [_row_to_dict(row, cursor.description) for row in rows]

def update_booking_status(booking_id: str, status: str) -> bool:
    """更新预订状态"""
    try:
        with get_connection() as conn:
            conn.execute(
                "UPDATE bookings SET status = ?, updated_at = ? WHERE booking_id = ?",
                (status, datetime.now().isoformat(), booking_id)
            )
            logger.info(f"✅ 预订状态更新: {booking_id} -> {status}")
            return True
    except Exception as e:
        logger.error(f"更新预订状态失败: {e}")
        return False

def cancel_booking(booking_id: str) -> bool:
    """取消预订"""
    return update_booking_status(booking_id, 'cancelled')

def update_booking_field(booking_id: str, field: str, value: Any) -> bool:
    """更新预订的单个字段"""
    try:
        # 验证字段名安全性
        allowed_fields = {'payment_id', 'payment_status', 'stripe_customer_id'}
        if field not in allowed_fields:
            logger.warning(f"⚠️ 尝试更新不允许的字段: {field}")
            return False
        
        with get_connection() as conn:
            conn.execute(
                f"UPDATE bookings SET {field} = ?, updated_at = ? WHERE booking_id = ?",
                (value, datetime.now().isoformat(), booking_id)
            )
            logger.info(f"✅ 预订字段更新: {booking_id}.{field} = {value}")
            return True
    except Exception as e:
        logger.error(f"更新预订字段失败: {e}")
        return False

# ============ 可用性检查 ============
def check_availability(villa_id: str, checkin: str, checkout: str, 
                       exclude_booking_id: Optional[str] = None) -> bool:
    """
    检查别墅在指定日期范围内是否可用
    """
    sql = """
        SELECT COUNT(*) as count FROM bookings
        WHERE villa_id = ?
        AND status NOT IN ('cancelled', 'rejected')
        AND checkin < ?
        AND checkout > ?
    """
    params = [villa_id, checkout, checkin]
    
    if exclude_booking_id:
        sql += " AND booking_id != ?"
        params.append(exclude_booking_id)
    
    with get_connection() as conn:
        cursor = conn.execute(sql, tuple(params))
        row = cursor.fetchone()
        count = row[0] if row else 0
        
        return count == 0

def find_available_villas(checkin: str, checkout: str, 
                          region: Optional[str] = None) -> List[Dict]:
    """查找在指定日期范围内可用的别墅"""
    villas = get_all_villas(region=region)
    
    available = []
    for villa in villas:
        if check_availability(villa['id'], checkin, checkout):
            available.append(villa)
    
    return available

# ============ 用户数据操作 ============
def get_or_create_user(telegram_id: str, username: str = None) -> Dict:
    """获取或创建用户记录"""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?",
            (str(telegram_id),)
        )
        row = cursor.fetchone()
        
        if row:
            conn.execute(
                "UPDATE users SET last_seen = ? WHERE telegram_id = ?",
                (datetime.now().isoformat(), str(telegram_id))
            )
            return _row_to_dict(row, cursor.description)
        
        conn.execute("""
            INSERT INTO users (telegram_id, username)
            VALUES (?, ?)
        """, (str(telegram_id), username))
        
        cursor = conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?",
            (str(telegram_id),)
        )
        row = cursor.fetchone()
        return _row_to_dict(row, cursor.description) if row else {}

def update_user_language(telegram_id: str, language: str) -> bool:
    """更新用户语言偏好"""
    try:
        with get_connection() as conn:
            conn.execute(
                "UPDATE users SET preferred_language = ? WHERE telegram_id = ?",
                (language, str(telegram_id))
            )
            return True
    except Exception as e:
        logger.error(f"更新用户语言失败: {e}")
        return False

# ============ 统计与分析 ============
def get_booking_stats() -> Dict:
    """获取预订统计信息"""
    with get_connection() as conn:
        cursor = conn.execute("SELECT COUNT(*) as total FROM bookings")
        total = cursor.fetchone()[0]
        
        cursor = conn.execute("""
            SELECT status, COUNT(*) as count 
            FROM bookings 
            GROUP BY status
        """)
        status_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        today = datetime.now().strftime('%Y-%m-%d')
        cursor = conn.execute(
            "SELECT COUNT(*) as count FROM bookings WHERE DATE(created_at) = ?",
            (today,)
        )
        today_new = cursor.fetchone()[0]
        
        return {
            'total': total,
            'by_status': status_counts,
            'today_new': today_new
        }

def get_villa_occupancy(villa_id: str, year: int = None, month: int = None) -> Dict:
    """获取别墅入住率统计"""
    if not year:
        year = datetime.now().year
    if not month:
        month = datetime.now().month
    
    with get_connection() as conn:
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        days_in_month = (next_month - datetime(year, month, 1)).days
        
        start_date = f"{year}-{month:02d}-01"
        end_date = next_month.strftime('%Y-%m-%d')
        
        cursor = conn.execute("""
            SELECT SUM(
                LEAST(DATE(checkout), ?) - GREATEST(DATE(checkin), ?)
            ) as booked_days
            FROM bookings
            WHERE villa_id = ?
            AND status IN ('confirmed', 'completed')
            AND checkin < ?
            AND checkout > ?
        """, (end_date, start_date, villa_id, end_date, start_date))
        
        row = cursor.fetchone()
        booked_days = max(0, row[0] or 0)
        occupancy_rate = (booked_days / days_in_month) * 100 if days_in_month > 0 else 0
        
        return {
            'year': year,
            'month': month,
            'days_in_month': days_in_month,
            'booked_days': booked_days,
            'occupancy_rate': round(occupancy_rate, 1)
        }

# ============ 辅助函数 ============
def _row_to_dict(row, description=None) -> Dict:
    """将数据库 Row 转换为字典，并解析 JSON 字段"""
    if not row:
        return {}
    
    # 获取列名
    if description:
        columns = [d[0] for d in description]
        result = dict(zip(columns, row))
    else:
        result = dict(row)
    
    # 解析 JSON 字段
    for field in ['amenities', 'images']:
        if field in result and result[field]:
            try:
                if isinstance(result[field], str):
                    result[field] = json.loads(result[field])
            except json.JSONDecodeError:
                result[field] = []
        else:
            result[field] = result.get(field, [])
    
    return result

def backup_db(backup_path: str = None) -> str:
    """备份数据库"""
    if not backup_path:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = os.path.join(DATA_DIR, "backups")
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        backup_path = os.path.join(backup_dir, f"villas_backup_{timestamp}.db")
    
    import shutil
    
    if db_config.is_postgresql:
        # PostgreSQL 备份
        backup_pg_db(backup_path)
    else:
        # SQLite 备份
        shutil.copy2(get_db_path(), backup_path)
    
    logger.info(f"✅ 数据库已备份到: {backup_path}")
    return backup_path

def backup_pg_db(backup_path: str):
    """PostgreSQL 数据库备份 (使用 pg_dump)"""
    import subprocess
    
    try:
        result = subprocess.run([
            'pg_dump',
            '--dbname=' + db_config.get_postgres_dsn(),
            '-f', backup_path
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.warning(f"pg_dump 备份失败: {result.stderr}")
    except FileNotFoundError:
        logger.warning("pg_dump 未安装，无法备份 PostgreSQL")

def restore_db(backup_path: str) -> bool:
    """从备份恢复数据库"""
    try:
        import shutil
        
        if db_config.is_postgresql:
            restore_pg_db(backup_path)
        else:
            shutil.copy2(backup_path, get_db_path())
        
        logger.info(f"✅ 数据库已从备份恢复: {backup_path}")
        return True
    except Exception as e:
        logger.error(f"恢复数据库失败: {e}")
        return False

def restore_pg_db(backup_path: str):
    """PostgreSQL 数据库恢复 (使用 psql)"""
    import subprocess
    
    try:
        result = subprocess.run([
            'psql',
            '--dbname=' + db_config.get_postgres_dsn(),
            '-f', backup_path
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(result.stderr)
    except FileNotFoundError:
        raise Exception("psql 未安装，无法恢复 PostgreSQL")

# ============ 数据库健康检查 ============
def health_check() -> Dict:
    """数据库健康检查"""
    result = {
        'status': 'ok',
        'db_type': db_config.db_type,
        'is_production': is_production(),
        'tables': [],
        'record_counts': {}
    }
    
    if db_config.is_postgresql:
        result['db_path'] = db_config.get_postgres_dsn().split()[0].split('=')[1]  # host
    else:
        result['db_path'] = get_db_path()
        result['exists'] = os.path.exists(get_db_path())
    
    try:
        with get_connection() as conn:
            if db_config.is_postgresql:
                cursor = conn.execute("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
                result['tables'] = [row[0] for row in cursor.fetchall()]
                
                for table in ['villas', 'bookings', 'users']:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    result['record_counts'][table] = cursor.fetchone()[0]
            else:
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' 
                    ORDER BY name
                """)
                result['tables'] = [row[0] for row in cursor.fetchall()]
                
                for table in ['villas', 'bookings', 'users']:
                    cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table}")
                    result['record_counts'][table] = cursor.fetchone()[0]
        
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
    
    return result

# ============ 清理连接池 ============
def close_pool():
    """关闭 PostgreSQL 连接池"""
    global _pg_pool
    if _pg_pool:
        _pg_pool.closeall()
        _pg_pool = None
        logger.info("✅ PostgreSQL 连接池已关闭")

# ============ 主函数 - 测试 ============
if __name__ == '__main__':
    print("🏠 Taimili Villa Booking System - Database Module")
    print("=" * 50)
    print(f"数据库类型: {'PostgreSQL (Koyeb)' if is_production() else 'SQLite (本地开发)'}")
    print(f"配置: {db_config}")
    print("=" * 50)
    
    # 健康检查
    print("\n📊 健康检查:")
    health = health_check()
    for key, value in health.items():
        print(f"  {key}: {value}")
    
    # 关闭连接池
    close_pool()
