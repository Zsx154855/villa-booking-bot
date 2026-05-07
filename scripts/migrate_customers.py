#!/usr/bin/env python3
"""
客户数据迁移脚本
将旧的 users 表数据迁移到新的 customers 表

用法: python scripts/migrate_customers.py [--dry-run]
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database
from modules.customer import CustomerService

def migrate_users_to_customers(dry_run: bool = True):
    """迁移用户数据到客户表"""
    print("=" * 60)
    print("🔄 开始迁移用户数据到客户表")
    print("=" * 60)
    
    if dry_run:
        print("⚠️ 模拟运行模式（不会实际写入数据）")
    
    try:
        # 初始化数据库
        database.init_db()
        
        # 获取所有用户
        with database.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM users")
            columns = [desc[0] for desc in cursor.description]
            users = cursor.fetchall()
        
        print(f"\n📊 发现 {len(users)} 个用户记录")
        
        if len(users) == 0:
            print("✅ 没有需要迁移的数据")
            return
        
        migrated = 0
        skipped = 0
        
        for user in users:
            user_data = dict(zip(columns, user))
            telegram_id = user_data.get('telegram_id')
            username = user_data.get('username')
            
            # 检查是否已存在
            existing = CustomerService.get(telegram_id)
            if existing:
                print(f"⏭️ 跳过已存在的客户: {telegram_id} ({username})")
                skipped += 1
                continue
            
            if dry_run:
                print(f"🔍 [模拟] 将迁移: {telegram_id} ({username})")
            else:
                # 执行迁移
                customer = CustomerService.get_or_create(
                    telegram_id=telegram_id,
                    username=username,
                    source='migration'
                )
                if customer:
                    print(f"✅ 已迁移: {telegram_id} ({username})")
                    migrated += 1
                else:
                    print(f"❌ 迁移失败: {telegram_id}")
        
        print("\n" + "=" * 60)
        print(f"📋 迁移完成:")
        print(f"   ✅ 已迁移: {migrated}")
        print(f"   ⏭️ 已跳过: {skipped}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()

def sync_bookings_to_customers(dry_run: bool = True):
    """根据预订记录同步客户消费统计"""
    print("=" * 60)
    print("🔄 同步预订数据到客户统计")
    print("=" * 60)
    
    if dry_run:
        print("⚠️ 模拟运行模式（不会实际写入数据）")
    
    try:
        # 初始化数据库
        database.init_db()
        
        # 获取所有完成的预订
        with database.get_connection() as conn:
            cursor = conn.execute("""
                SELECT user_id, 
                       COUNT(*) as completed_count,
                       SUM(total_price) as total_spent,
                       SUM(
                           CAST(julianday(checkout) - julianday(checkin) AS INTEGER)
                       ) as total_nights
                FROM bookings 
                WHERE status = 'completed'
                GROUP BY user_id
            """)
            bookings = cursor.fetchall()
        
        print(f"\n📊 发现 {len(bookings)} 个有完成预订的客户")
        
        synced = 0
        for row in bookings:
            user_id = row[0]
            completed_count = row[1]
            total_spent = row[2] or 0
            total_nights = row[3] or 0
            
            # 获取或创建客户
            customer = CustomerService.get_or_create(
                telegram_id=user_id,
                source='booking_sync'
            )
            
            if not customer:
                continue
            
            if dry_run:
                print(f"🔍 [模拟] 将更新 {user_id}: "
                      f"消费{total_spent:.0f}铢, {completed_count}次预订, {total_nights}晚")
            else:
                # 直接更新客户统计（不追加，而是设置绝对值）
                from database import update_customer, calculate_vip_level, calculate_points
                
                vip_info = calculate_vip_level(total_spent)
                updates = {
                    'total_spent': total_spent,
                    'completed_bookings': completed_count,
                    'total_nights': total_nights,
                    'total_bookings': completed_count,  # 假设完成的都是全部预订
                    'vip_level': vip_info['current']['name'],
                    'points': calculate_points(total_spent)
                }
                
                if update_customer(user_id, updates):
                    print(f"✅ 已同步 {user_id}: "
                          f"消费{total_spent:.0f}铢, VIP {vip_info['current']['name']}")
                    synced += 1
                else:
                    print(f"❌ 同步失败: {user_id}")
        
        print("\n" + "=" * 60)
        print(f"📋 同步完成: {synced} 个客户已更新")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 同步失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="客户数据迁移工具")
    parser.add_argument('--no-dry-run', action='store_true',
                      help='实际执行迁移（默认是模拟运行）')
    parser.add_argument('--sync', action='store_true',
                      help='同步预订数据到客户统计')
    parser.add_argument('--migrate', action='store_true',
                      help='迁移用户数据')
    parser.add_argument('--all', action='store_true',
                      help='执行所有迁移')
    
    args = parser.parse_args()
    
    dry_run = not args.no_dry_run
    
    if args.all or args.migrate:
        migrate_users_to_customers(dry_run)
    
    if args.all or args.sync:
        sync_bookings_to_customers(dry_run)
    
    if not any([args.all, args.migrate, args.sync]):
        # 默认执行全部
        print("🔄 执行完整迁移流程...")
        print()
        migrate_users_to_customers(dry_run)
        print()
        sync_bookings_to_customers(dry_run)

if __name__ == '__main__':
    main()
