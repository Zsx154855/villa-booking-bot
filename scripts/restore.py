#!/usr/bin/env python3
"""
Taimili Villa Booking System - 数据库恢复脚本
用于从备份文件恢复数据库

使用方法:
    python scripts/restore.py backups/villas_daily_20260427_020000.db
    python scripts/restore.py backups/villas_daily_latest.db --verify-only
"""

import os
import sys
import sqlite3
import shutil
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

# ============ 日志配置 ============
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ============ 恢复类 ============
class DatabaseRestore:
    """数据库恢复类"""
    
    def __init__(self, target_path: str = 'data/villas.db'):
        self.target_path = Path(target_path)
        
    def verify_backup(self, backup_path: Path) -> Dict:
        """验证备份文件"""
        result = {
            'valid': False,
            'tables': {},
            'errors': []
        }
        
        if not backup_path.exists():
            result['errors'].append(f"备份文件不存在: {backup_path}")
            return result
            
        try:
            conn = sqlite3.connect(str(backup_path))
            cursor = conn.cursor()
            
            # 运行完整性检查
            cursor.execute("PRAGMA integrity_check;")
            integrity = cursor.fetchone()[0]
            
            if integrity != 'ok':
                result['errors'].append(f"完整性检查失败: {integrity}")
                return result
            
            # 获取表信息
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            for (table_name,) in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                result['tables'][table_name] = count
            
            # 获取数据库大小
            result['size_bytes'] = os.path.getsize(backup_path)
            result['size_kb'] = round(result['size_bytes'] / 1024, 2)
            result['valid'] = True
            
            conn.close()
            logger.info(f"✅ 备份文件验证通过")
            
        except sqlite3.Error as e:
            result['errors'].append(f"SQLite 错误: {e}")
        except Exception as e:
            result['errors'].append(f"验证异常: {e}")
            
        return result
    
    def restore(self, backup_path: Path, create_emergency_backup: bool = True) -> bool:
        """恢复数据库"""
        
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            logger.error(f"❌ 备份文件不存在: {backup_path}")
            return False
        
        # 验证备份文件
        logger.info("🔍 验证备份文件...")
        verification = self.verify_backup(backup_file)
        
        if not verification['valid']:
            logger.error("❌ 备份文件验证失败:")
            for error in verification['errors']:
                logger.error(f"   - {error}")
            return False
        
        # 显示备份内容
        logger.info("📊 备份文件内容:")
        for table, count in verification['tables'].items():
            logger.info(f"   - {table}: {count} 条记录")
        
        # 创建紧急备份（恢复前）
        if create_emergency_backup and self.target_path.exists():
            emergency_backup = self.target_path.with_suffix(
                f".emergency_backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            )
            logger.info(f"📦 创建紧急备份: {emergency_backup}")
            shutil.copy2(self.target_path, emergency_backup)
        
        # 执行恢复
        logger.info(f"📥 正在恢复: {backup_path} -> {self.target_path}")
        
        try:
            # 确保目标目录存在
            self.target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 复制备份文件
            shutil.copy2(backup_file, self.target_path)
            
            # 验证恢复结果
            logger.info("✅ 验证恢复结果...")
            conn = sqlite3.connect(str(self.target_path))
            cursor = conn.cursor()
            
            cursor.execute("PRAGMA integrity_check;")
            integrity = cursor.fetchone()[0]
            
            if integrity != 'ok':
                logger.error(f"❌ 恢复后完整性检查失败: {integrity}")
                conn.close()
                return False
            
            logger.info("✅ 恢复验证通过!")
            
            # 显示恢复后的数据
            logger.info("📊 恢复后数据库内容:")
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            for (table_name,) in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                logger.info(f"   - {table_name}: {count} 条记录")
            
            conn.close()
            
            logger.info("🎉 恢复完成!")
            return True
            
        except Exception as e:
            logger.error(f"❌ 恢复失败: {e}")
            return False
    
    def list_backups(self, backup_dir: Path) -> list:
        """列出可用的备份"""
        backups = []
        
        if not backup_dir.exists():
            return backups
            
        for backup_file in sorted(backup_dir.glob("villas_*.db"), reverse=True):
            if backup_file.is_symlink():
                continue
                
            try:
                parts = backup_file.stem.split('_')
                if len(parts) < 4:
                    continue
                    
                backup_type = parts[1]
                date_str = parts[2]
                time_str = parts[3]
                backup_time = datetime.strptime(f"{date_str}_{time_str}", '%Y%m%d_%H%M%S')
                
                backups.append({
                    'path': backup_file,
                    'type': backup_type,
                    'time': backup_time,
                    'size': os.path.getsize(backup_file),
                    'size_kb': round(os.path.getsize(backup_file) / 1024, 2)
                })
            except (IndexError, ValueError):
                continue
                
        return backups

# ============ 主程序 ============
def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(
        description='Taimili 别墅预订系统 - 数据库恢复工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/restore.py backups/villas_daily_latest.db
  python scripts/restore.py backups/villas_daily_20260427_020000.db
  python scripts/restore.py --list-backups
  python scripts/restore.py backups/villas_daily_latest.db --verify-only
        """
    )
    
    parser.add_argument(
        'backup_file',
        nargs='?',
        help='备份文件路径'
    )
    parser.add_argument(
        '--target',
        default='data/villas.db',
        help='恢复目标路径 (默认: data/villas.db)'
    )
    parser.add_argument(
        '--list-backups',
        action='store_true',
        help='列出可用备份'
    )
    parser.add_argument(
        '--verify-only',
        action='store_true',
        help='仅验证备份文件，不执行恢复'
    )
    parser.add_argument(
        '--no-emergency-backup',
        action='store_true',
        help='跳过创建紧急备份'
    )
    
    args = parser.parse_args()
    
    restore = DatabaseRestore(target_path=args.target)
    
    print("=" * 60)
    print("🏠 Taimili 别墅预订系统 - 数据库恢复")
    print("=" * 60)
    
    # 列出备份
    if args.list_backups:
        logger.info("📋 可用的备份文件:")
        backups = restore.list_backups(Path('data/backups'))
        
        if not backups:
            logger.info("   没有找到备份文件")
        else:
            for i, backup in enumerate(backups[:20], 1):  # 最多显示20个
                logger.info(
                    f"   {i}. [{backup['type']}] "
                    f"{backup['time'].strftime('%Y-%m-%d %H:%M:%S')} "
                    f"({backup['size_kb']} KB)"
                )
            if len(backups) > 20:
                logger.info(f"   ... 还有 {len(backups) - 20} 个备份")
        
        print("=" * 60)
        return
    
    # 验证模式
    if args.verify_only:
        if not args.backup_file:
            logger.error("❌ 请指定要验证的备份文件")
            sys.exit(1)
            
        backup_path = Path(args.backup_file)
        logger.info(f"🔍 验证备份文件: {backup_path}")
        
        result = restore.verify_backup(backup_path)
        
        if result['valid']:
            logger.info("✅ 备份文件有效")
            logger.info(f"   大小: {result['size_kb']} KB")
            for table, count in result['tables'].items():
                logger.info(f"   - {table}: {count} 条记录")
        else:
            logger.error("❌ 备份文件无效:")
            for error in result['errors']:
                logger.error(f"   - {error}")
            sys.exit(1)
        
        print("=" * 60)
        return
    
    # 恢复模式
    if not args.backup_file:
        logger.error("❌ 请指定要恢复的备份文件")
        logger.info("使用 --list-backups 查看可用备份")
        sys.exit(1)
    
    backup_path = Path(args.backup_file)
    
    # 处理符号链接
    if backup_path.is_symlink():
        backup_path = backup_path.resolve()
        logger.info(f"📍 解析符号链接: {backup_path}")
    
    logger.info(f"🔄 恢复目标: {args.target}")
    
    success = restore.restore(
        backup_path,
        create_emergency_backup=not args.no_emergency_backup
    )
    
    if success:
        logger.info("✅ 恢复成功!")
        logger.info("")
        logger.info("⚠️  请重启服务以加载恢复的数据:")
        logger.info("   python bot.py")
    else:
        logger.error("❌ 恢复失败!")
        sys.exit(1)
    
    print("=" * 60)

if __name__ == '__main__':
    main()
