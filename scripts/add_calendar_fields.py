#!/usr/bin/env python3
"""
数据库迁移脚本：为预订表添加日历事件ID字段
运行方式: python scripts/add_calendar_fields.py
"""

import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database

def add_calendar_fields():
    """添加日历事件ID字段"""
    
    # 检查当前数据库类型
    from database_config import is_production
    
    print(f"📊 数据库类型: {'PostgreSQL (生产)' if is_production else 'SQLite (开发)'}")
    
    # 定义需要添加的字段
    # Google Calendar 字段
    google_fields = [
        ('google_event_id', 'VARCHAR(255)'),  # Google Calendar 事件ID
    ]
    
    # 飞书日历字段
    feishu_fields = [
        ('feishu_event_id', 'VARCHAR(255)'),  # 飞书日历事件ID
    ]
    
    all_fields = google_fields + feishu_fields
    
    for field_name, field_type in all_fields:
        try:
            if is_production:
                # PostgreSQL
                query = f"""
                ALTER TABLE bookings 
                ADD COLUMN IF NOT EXISTS {field_name} {field_type};
                """
            else:
                # SQLite
                query = f"""
                ALTER TABLE bookings 
                ADD COLUMN {field_name} {field_type};
                """
            
            database.execute_query(query)
            print(f"✅ 字段 {field_name} 已添加")
            
        except Exception as e:
            if 'duplicate column' in str(e).lower() or 'already exists' in str(e).lower():
                print(f"⏭️ 字段 {field_name} 已存在，跳过")
            else:
                print(f"❌ 添加字段 {field_name} 失败: {e}")

def add_calendar_event_id_to_booking():
    """
    在预订记录中保存日历事件ID
    在 create_booking 函数中调用
    """
    pass  # 这是一个占位函数，实际逻辑在 calendar/__init__.py 中

if __name__ == '__main__':
    print("🔄 开始数据库迁移...\n")
    
    add_calendar_fields()
    
    print("\n✅ 迁移完成！")
    print("\n📝 下一步：")
    print("1. 配置日历凭证 (.env.calendar.example)")
    print("2. 重启 Bot 服务")
    print("3. 运行 /sync 命令同步现有预订")
