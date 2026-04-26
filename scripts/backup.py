#!/usr/bin/env python3
"""
Taimili Villa Booking System - 数据库备份脚本
支持：本地备份、云端同步、版本管理

使用方法:
    python scripts/backup.py --type daily
    python scripts/backup.py --type weekly --no-upload
    python scripts/backup.py --type monthly

环境变量:
    DB_PATH: 数据库路径 (默认: data/villas.db)
    BACKUP_DIR: 备份目录 (默认: data/backups)
    GITHUB_TOKEN: GitHub Personal Access Token
    GITHUB_REPO: 目标仓库 (格式: owner/repo)
"""

import os
import sys
import sqlite3
import shutil
import json
import hashlib
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
import base64

# ============ 配置区域 ============
class BackupConfig:
    """备份配置"""
    
    # 数据库路径
    DB_PATH = os.environ.get('DB_PATH', 'data/villas.db')
    
    # 备份目录
    BACKUP_DIR = os.environ.get('BACKUP_DIR', 'data/backups')
    
    # GitHub 配置
    GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
    GITHUB_REPO = os.environ.get('GITHUB_REPO', '')
    GITHUB_BRANCH = os.environ.get('GITHUB_BRANCH', 'main')
    
    # 保留策略
    RETAIN_DAILY = 7    # 每日备份保留天数
    RETAIN_WEEKLY = 4   # 每周备份保留份数
    RETAIN_MONTHLY = 12 # 月度备份保留月数
    
    # 日志配置
    LOG_LEVEL = logging.INFO

# ============ 日志配置 ============
def setup_logging(log_file: str = 'backup.log') -> logging.Logger:
    """配置日志"""
    # 确保日志目录存在
    log_path = Path(BackupConfig.BACKUP_DIR) / log_file
    
    logging.basicConfig(
        level=BackupConfig.LOG_LEVEL,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path, encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ============ 数据库工具类 ============
class DatabaseBackup:
    """数据库备份类"""
    
    def __init__(self, db_path: str, backup_dir: str):
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def get_backup_filename(self, backup_type: str = 'daily') -> str:
        """生成备份文件名"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        return f"villas_{backup_type}_{timestamp}.db"
    
    def calculate_checksum(self, filepath: Path) -> str:
        """计算文件 MD5 校验和"""
        md5 = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                md5.update(chunk)
        return md5.hexdigest()
    
    def get_db_stats(self) -> Dict:
        """获取数据库统计信息"""
        if not self.db_path.exists():
            return {'exists': False}
            
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        stats = {
            'exists': True,
            'size_bytes': os.path.getsize(self.db_path),
            'size_kb': round(os.path.getsize(self.db_path) / 1024, 2),
            'tables': {}
        }
        
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            for (table_name,) in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                stats['tables'][table_name] = count
                
        except sqlite3.Error as e:
            logger.error(f"获取统计信息失败: {e}")
        finally:
            conn.close()
            
        return stats
    
    def create_backup(self, backup_type: str = 'daily') -> Optional[Path]:
        """创建数据库备份"""
        if not self.db_path.exists():
            logger.error(f"源数据库不存在: {self.db_path}")
            return None
        
        backup_name = self.get_backup_filename(backup_type)
        backup_path = self.backup_dir / backup_name
        
        try:
            # 使用 SQLite 的 backup API 创建备份
            source_conn = sqlite3.connect(str(self.db_path))
            backup_conn = sqlite3.connect(str(backup_path))
            
            source_conn.backup(backup_conn)
            
            source_conn.close()
            backup_conn.close()
            
            # 计算校验和
            checksum = self.calculate_checksum(backup_path)
            
            # 获取数据库统计
            db_stats = self.get_db_stats()
            
            # 写入元数据
            meta = {
                'backup_type': backup_type,
                'created_at': datetime.utcnow().isoformat(),
                'original_size': os.path.getsize(self.db_path),
                'backup_size': os.path.getsize(backup_path),
                'checksum': checksum,
                'db_stats': db_stats
            }
            
            meta_path = backup_path.with_suffix('.json')
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ 备份成功: {backup_name}")
            logger.info(f"   大小: {os.path.getsize(backup_path) / 1024:.2f} KB")
            logger.info(f"   校验和: {checksum}")
            
            # 创建符号链接指向最新备份
            latest_link = self.backup_dir / f"villas_{backup_type}_latest.db"
            if latest_link.exists():
                latest_link.unlink()
            latest_link.symlink_to(backup_path.name)
            
            return backup_path
            
        except Exception as e:
            logger.error(f"❌ 备份失败: {e}")
            if backup_path.exists():
                backup_path.unlink()
            return None
    
    def cleanup_old_backups(self):
        """清理过期备份"""
        if not self.backup_dir.exists():
            return
            
        now = datetime.utcnow()
        deleted = []
        
        for backup_file in self.backup_dir.glob("villas_*.db"):
            # 跳过符号链接
            if backup_file.is_symlink():
                continue
                
            # 跳过 latest 链接
            if 'latest' in backup_file.name:
                continue
                
            try:
                # 解析备份文件名
                # 格式: villas_{type}_{date}_{time}.db
                parts = backup_file.stem.split('_')
                if len(parts) < 4:
                    continue
                    
                backup_type = parts[1]
                date_str = parts[2]
                time_str = parts[3]
                backup_time = datetime.strptime(f"{date_str}_{time_str}", '%Y%m%d_%H%M%S')
                age_days = (now - backup_time).days
                
                should_delete = False
                
                if backup_type == 'daily' and age_days > BackupConfig.RETAIN_DAILY:
                    should_delete = True
                elif backup_type == 'weekly' and age_days > BackupConfig.RETAIN_WEEKLY * 7:
                    should_delete = True
                elif backup_type == 'monthly' and age_days > BackupConfig.RETAIN_MONTHLY * 30:
                    should_delete = True
                
                if should_delete:
                    backup_file.unlink()
                    # 删除元数据
                    meta_file = backup_file.with_suffix('.json')
                    if meta_file.exists():
                        meta_file.unlink()
                    deleted.append(backup_file.name)
                    logger.info(f"🗑️ 删除过期备份: {backup_file.name}")
                    
            except (IndexError, ValueError) as e:
                # 无法解析的文件，跳过
                continue
        
        if deleted:
            logger.info(f"清理完成: 删除 {len(deleted)} 个过期备份")

# ============ GitHub 同步类 ============
class GitHubSync:
    """GitHub 同步类"""
    
    API_BASE = "https://api.github.com"
    
    def __init__(self, token: str, repo: str):
        self.token = token
        self.repo = repo
        self.headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }
        
    def _request(self, method: str, url: str, **kwargs):
        """发送 HTTP 请求"""
        import requests
        return requests.request(method, url, headers=self.headers, **kwargs)
    
    def upload_file(self, file_path: Path, remote_path: str, message: str = None) -> bool:
        """上传文件到 GitHub"""
        if not file_path.exists():
            logger.error(f"文件不存在: {file_path}")
            return False
            
        try:
            import requests
            
            with open(file_path, 'rb') as f:
                content = f.read()
            
            encoded_content = base64.b64encode(content).decode('utf-8')
            
            url = f"{self.API_BASE}/repos/{self.repo}/contents/{remote_path}"
            
            # 检查文件是否存在
            response = requests.get(url, headers=self.headers)
            sha = None
            if response.status_code == 200:
                sha = response.json().get('sha')
                logger.info(f"文件已存在，将更新: {remote_path}")
            
            # 构建请求数据
            data = {
                'message': message or f'Backup: {file_path.name}',
                'content': encoded_content,
                'branch': BackupConfig.GITHUB_BRANCH
            }
            if sha:
                data['sha'] = sha
                
            # 上传文件
            response = requests.put(url, headers=self.headers, json=data)
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ 上传成功: {remote_path}")
                return True
            else:
                logger.error(f"❌ 上传失败: {response.status_code} - {response.text}")
                return False
                
        except ImportError:
            logger.warning("requests 库未安装，跳过 GitHub 上传")
            return False
        except Exception as e:
            logger.error(f"❌ 上传异常: {e}")
            return False

# ============ 主程序 ============
def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(
        description='Taimili 别墅预订系统 - 数据库备份工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/backup.py --type daily           # 每日备份
  python scripts/backup.py --type weekly          # 每周备份
  python scripts/backup.py --type monthly         # 月度备份
  python scripts/backup.py --no-upload           # 跳过云端上传
  python scripts/backup.py --no-cleanup          # 跳过清理旧备份
        """
    )
    
    parser.add_argument(
        '--type', '-t',
        choices=['daily', 'weekly', 'monthly', 'full'],
        default='daily',
        help='备份类型 (默认: daily)'
    )
    parser.add_argument(
        '--no-upload',
        action='store_true',
        help='跳过云端上传'
    )
    parser.add_argument(
        '--no-cleanup',
        action='store_true',
        help='跳过清理旧备份'
    )
    parser.add_argument(
        '--db-path',
        default=BackupConfig.DB_PATH,
        help=f'数据库路径 (默认: {BackupConfig.DB_PATH})'
    )
    parser.add_argument(
        '--backup-dir',
        default=BackupConfig.BACKUP_DIR,
        help=f'备份目录 (默认: {BackupConfig.BACKUP_DIR})'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🏠 Taimili 别墅预订系统 - 数据库备份")
    print("=" * 60)
    
    logger.info(f"数据库路径: {args.db_path}")
    logger.info(f"备份目录: {args.backup_dir}")
    logger.info(f"备份类型: {args.type}")
    
    # 创建备份实例
    backup = DatabaseBackup(
        db_path=args.db_path,
        backup_dir=args.backup_dir
    )
    
    # 显示数据库统计
    stats = backup.get_db_stats()
    if stats['exists']:
        logger.info(f"📊 数据库统计:")
        for table, count in stats.get('tables', {}).items():
            logger.info(f"   - {table}: {count} 条记录")
        logger.info(f"   - 总大小: {stats.get('size_kb', 0)} KB")
    else:
        logger.warning("⚠️ 数据库文件不存在或无法访问")
    
    # 创建备份
    backup_path = backup.create_backup(args.type)
    
    if backup_path:
        logger.info("✅ 备份创建成功!")
        
        # 上传到 GitHub
        if not args.no_upload and BackupConfig.GITHUB_TOKEN and BackupConfig.GITHUB_REPO:
            logger.info("📤 正在上传到 GitHub...")
            sync = GitHubSync(
                token=BackupConfig.GITHUB_TOKEN,
                repo=BackupConfig.GITHUB_REPO
            )
            
            # 上传备份文件
            remote_path = f"backups/{backup_path.name}"
            sync.upload_file(backup_path, remote_path)
            
            # 上传元数据
            meta_path = backup_path.with_suffix('.json')
            if meta_path.exists():
                sync.upload_file(meta_path, f"backups/{meta_path.name}")
        elif not BackupConfig.GITHUB_TOKEN:
            logger.info("ℹ️ 未配置 GITHUB_TOKEN，跳过云端上传")
        elif not BackupConfig.GITHUB_REPO:
            logger.info("ℹ️ 未配置 GITHUB_REPO，跳过云端上传")
    else:
        logger.error("❌ 备份失败!")
        sys.exit(1)
    
    # 清理旧备份
    if not args.no_cleanup:
        logger.info("🧹 清理过期备份...")
        backup.cleanup_old_backups()
    
    print("=" * 60)
    print("✅ 备份任务完成")
    print("=" * 60)

if __name__ == '__main__':
    main()
