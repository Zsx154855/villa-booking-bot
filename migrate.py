#!/usr/bin/env python3
"""
Taimili Villa Booking System - Data Migration Script
将数据从JSON文件迁移到SQLite数据库
"""

import os
import sys
import json
import logging
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============ 路径配置 ============
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
VILLAS_JSON = os.path.join(DATA_DIR, "villas.json")
BOOKINGS_JSON = os.path.join(DATA_DIR, "bookings.json")

# ============ 迁移统计 ============
class MigrationStats:
    def __init__(self):
        self.villas_total = 0
        self.villas_success = 0
        self.villas_failed = 0
        self.bookings_total = 0
        self.bookings_success = 0
        self.bookings_failed = 0
        self.errors = []

stats = MigrationStats()

# ============ 迁移函数 ============
def load_json(file_path: str) -> list:
    """加载JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"✅ 成功加载 {file_path}，共 {len(data)} 条记录")
            return data
    except FileNotFoundError:
        logger.warning(f"⚠️ 文件不存在: {file_path}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON解析错误: {e}")
        stats.errors.append(f"JSON解析错误 {file_path}: {e}")
        return []

def migrate_villas():
    """迁移别墅数据"""
    print("\n" + "=" * 50)
    print("🏠 迁移别墅数据")
    print("=" * 50)
    
    villas = load_json(VILLAS_JSON)
    stats.villas_total = len(villas)
    
    if not villas:
        print("⚠️ 没有别墅数据需要迁移")
        return
    
    for villa in villas:
        try:
            # 标准化字段名
            villa_data = {
                'id': villa.get('id', ''),
                'name': villa.get('name', ''),
                'region': villa.get('region', ''),
                'type': villa.get('type', villa.get('room_type', '')),
                'price_per_night': villa.get('price_per_night', 0),
                'bedrooms': villa.get('bedrooms', 0),
                'bathrooms': villa.get('bathrooms', 0),
                'max_guests': villa.get('max_guests', 0),
                'amenities': villa.get('amenities', []),
                'images': villa.get('images', []),
                'description': villa.get('description', ''),
                'is_active': villa.get('is_active', 1)
            }
            
            if database.create_villa(villa_data):
                stats.villas_success += 1
                print(f"   ✅ {villa_data['id']}: {villa_data['name']}")
            else:
                stats.villas_failed += 1
                print(f"   ❌ {villa.get('id', 'N/A')}: 插入失败")
                
        except Exception as e:
            stats.villas_failed += 1
            stats.errors.append(f"迁移别墅失败: {villa.get('id', 'N/A')} - {e}")
            print(f"   ❌ {villa.get('id', 'N/A')}: {e}")
    
    print(f"\n📊 别墅迁移结果: {stats.villas_success}/{stats.villas_total} 成功")

def migrate_bookings():
    """迁移预订数据"""
    print("\n" + "=" * 50)
    print("📋 迁移预订数据")
    print("=" * 50)
    
    bookings = load_json(BOOKINGS_JSON)
    stats.bookings_total = len(bookings)
    
    if not bookings:
        print("⚠️ 没有预订数据需要迁移")
        return
    
    for booking in bookings:
        try:
            booking_data = {
                'id': booking.get('id', ''),
                'user_id': booking.get('user_id', ''),
                'villa_id': booking.get('villa_id', ''),
                'villa_name': booking.get('villa_name', ''),
                'villa_region': booking.get('villa_region', ''),
                'checkin': booking.get('checkin', ''),
                'checkout': booking.get('checkout', ''),
                'guests': booking.get('guests', 1),
                'contact_name': booking.get('contact_name', ''),
                'contact_phone': booking.get('contact_phone', ''),
                'contact_note': booking.get('contact_note', ''),
                'price_per_night': booking.get('price_per_night', 0),
                'total_price': booking.get('total_price', 0),
                'status': booking.get('status', 'pending')
            }
            
            if database.create_booking(booking_data):
                stats.bookings_success += 1
                print(f"   ✅ {booking_data['id']}: {booking_data['villa_name']}")
            else:
                stats.bookings_failed += 1
                print(f"   ❌ {booking.get('id', 'N/A')}: 插入失败")
                
        except Exception as e:
            stats.bookings_failed += 1
            stats.errors.append(f"迁移预订失败: {booking.get('id', 'N/A')} - {e}")
            print(f"   ❌ {booking.get('id', 'N/A')}: {e}")
    
    print(f"\n📊 预订迁移结果: {stats.bookings_success}/{stats.bookings_total} 成功")

def verify_migration():
    """验证迁移结果"""
    print("\n" + "=" * 50)
    print("🔍 验证迁移结果")
    print("=" * 50)
    
    # 备份原始JSON文件
    backup_dir = os.path.join(DATA_DIR, "backups")
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 保存原始文件到备份目录
    if os.path.exists(VILLAS_JSON):
        import shutil
        backup_path = os.path.join(backup_dir, f"villas_original_{timestamp}.json")
        shutil.copy2(VILLAS_JSON, backup_path)
        logger.info(f"已备份原始别墅数据到: {backup_path}")
    
    if os.path.exists(BOOKINGS_JSON):
        import shutil
        backup_path = os.path.join(backup_dir, f"bookings_original_{timestamp}.json")
        shutil.copy2(BOOKINGS_JSON, backup_path)
        logger.info(f"已备份原始预订数据到: {backup_path}")
    
    # 检查数据库数据
    print("\n📊 数据库统计:")
    health = database.health_check()
    
    print(f"   数据库路径: {health['db_path']}")
    print(f"   别墅表: {health['record_counts'].get('villas', 0)} 条记录")
    print(f"   预订表: {health['record_counts'].get('bookings', 0)} 条记录")
    print(f"   用户表: {health['record_counts'].get('users', 0)} 条记录")
    
    # 抽样验证
    print("\n📋 抽样验证 - 别墅列表:")
    villas = database.get_all_villas()
    for villa in villas[:3]:
        print(f"   • {villa['id']}: {villa['name']} ({villa['region']}) - ฿{villa['price_per_night']}/晚")
    
    if len(villas) > 3:
        print(f"   ... 共 {len(villas)} 套别墅")
    
    # 数据完整性检查
    print("\n🔐 数据完整性检查:")
    errors_found = 0
    
    # 检查别墅数据的必要字段
    for villa in database.get_all_villas():
        if not villa.get('id') or not villa.get('name'):
            print(f"   ❌ 别墅数据不完整: {villa}")
            errors_found += 1
    
    if errors_found == 0:
        print("   ✅ 所有数据完整性检查通过")

def print_summary():
    """打印迁移总结"""
    print("\n" + "=" * 50)
    print("📊 迁移总结")
    print("=" * 50)
    
    print(f"""
🏠 别墅数据:
   总数: {stats.villas_total}
   成功: {stats.villas_success} ✅
   失败: {stats.villas_failed} ❌

📋 预订数据:
   总数: {stats.bookings_total}
   成功: {stats.bookings_success} ✅
   失败: {stats.bookings_failed} ❌

⚠️ 错误信息:
""")
    
    if stats.errors:
        for error in stats.errors:
            print(f"   • {error}")
    else:
        print("   无错误记录")
    
    total = stats.villas_total + stats.bookings_total
    success = stats.villas_success + stats.bookings_success
    
    print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{'✅ 迁移完成!' if stats.villas_failed == 0 and stats.bookings_failed == 0 else '⚠️ 迁移完成，存在失败记录'}
数据迁移率: {success}/{total} ({100*success/total:.1f}%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

def rollback():
    """回滚操作 - 恢复原始JSON文件"""
    print("\n⚠️ 执行回滚...")
    
    backup_dir = os.path.join(DATA_DIR, "backups")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 查找最新备份
    import glob
    villa_backups = sorted(glob.glob(os.path.join(backup_dir, "villas_original_*.json")))
    booking_backups = sorted(glob.glob(os.path.join(backup_dir, "bookings_original_*.json")))
    
    if villa_backups:
        import shutil
        latest = villa_backups[-1]
        shutil.copy2(latest, VILLAS_JSON)
        logger.info(f"已恢复别墅数据: {latest}")
    
    if booking_backups:
        import shutil
        latest = booking_backups[-1]
        shutil.copy2(latest, BOOKINGS_JSON)
        logger.info(f"已恢复预订数据: {latest}")
    
    print("✅ 回滚完成")

# ============ 主函数 ============
def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   🏠 Taimili Villa Booking System                        ║
║   📦 Database Migration: JSON → SQLite                   ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
""")
    
    # 检查源文件
    print("\n🔍 检查源文件...")
    
    if not os.path.exists(VILLAS_JSON):
        print(f"❌ 别墅数据文件不存在: {VILLAS_JSON}")
        return
    
    print(f"   ✅ {VILLAS_JSON}")
    
    if os.path.exists(BOOKINGS_JSON):
        print(f"   ✅ {BOOKINGS_JSON}")
    else:
        print(f"   ⚠️ {BOOKINGS_JSON} (将在迁移后创建)")
    
    # 初始化数据库
    print("\n📦 初始化数据库...")
    try:
        database.init_db()
        print("   ✅ 数据库初始化完成")
    except Exception as e:
        print(f"   ❌ 数据库初始化失败: {e}")
        return
    
    # 询问是否继续
    response = input("\n是否开始迁移数据? (y/n): ").strip().lower()
    if response != 'y':
        print("已取消迁移")
        return
    
    # 执行迁移
    migrate_villas()
    migrate_bookings()
    
    # 验证结果
    verify_migration()
    
    # 打印总结
    print_summary()
    
    # 询问是否成功
    if stats.villas_failed == 0 and stats.bookings_failed == 0:
        print("\n🎉 恭喜！数据迁移成功完成！")
        print("\n📝 后续步骤:")
        print("   1. 更新 bot.py 使用数据库模块")
        print("   2. 测试所有功能")
        print("   3. 推送到 GitHub")
        print("   4. Koyeb 将自动部署")
    else:
        print("\n⚠️ 迁移存在失败记录，请检查错误信息后重试或回滚")

if __name__ == '__main__':
    main()
