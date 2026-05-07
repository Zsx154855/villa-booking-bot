#!/usr/bin/env python3
"""
GBrain Layer 1: Brain Repo
GitHub仓库知识存储 - 长期知识持久化
"""

import os
import json
import logging
import base64
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# 使用标准库urllib避免依赖冲突
import urllib.request
import urllib.parse
import urllib.error

logger = logging.getLogger(__name__)


@dataclass
class BrainEntry:
    """知识条目"""
    id: str
    type: str  # villa/customer/strategy/rule/faq
    title: str
    content: str
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str
    
    def to_markdown(self) -> str:
        """转换为Markdown格式"""
        lines = [
            "---",
            f"type: {self.type}",
            f"title: {self.title}",
            f"tags: {','.join(self.metadata.get('tags', []))}",
            f"created: {self.created_at}",
            f"updated: {self.updated_at}",
            "---",
            "",
            f"# {self.title}",
            "",
            self.content,
        ]
        if self.metadata.get('timeline'):
            lines.append("\n## Timeline")
            for event in self.metadata['timeline']:
                lines.append(f"- {event}")
        return "\n".join(lines)


class BrainRepo:
    """
    Brain Repo - GitHub仓库知识存储
    
    功能：
    - 读写GitHub仓库中的Markdown知识文件
    - 同步别墅信息、客户偏好、运营策略
    - 支持版本历史追踪
    """
    
    def __init__(
        self,
        github_token: str = None,
        repo_owner: str = None,
        repo_name: str = None
    ):
        """
        初始化Brain Repo
        
        Args:
            github_token: GitHub Personal Access Token
            repo_owner: 仓库所有者
            repo_name: 仓库名称
        """
        self.github_token = github_token or os.environ.get('GITHUB_TOKEN')
        self.repo_owner = repo_owner or os.environ.get('GITHUB_REPO_OWNER', 'villa-ai')
        self.repo_name = repo_name or os.environ.get('GITHUB_REPO_NAME', 'villa-knowledge')
        self.base_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}"
        self.headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # 本地缓存
        self._cache: Dict[str, BrainEntry] = {}
        self._initialized = False
        
        logger.info(f"✅ BrainRepo初始化完成 (仓库: {self.repo_owner}/{self.repo_name})")
    
    def is_available(self) -> bool:
        """检查GitHub连接是否可用"""
        if not self.github_token:
            logger.warning("⚠️ GitHub Token未配置")
            return False
        try:
            req = urllib.request.Request(
                self.base_url,
                headers=self.headers
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"GitHub连接失败: {e}")
            return False
    
    def _get_file_path(self, entry: BrainEntry) -> str:
        """获取文件路径"""
        type_paths = {
            "villa": "villas",
            "customer": "customers", 
            "strategy": "strategy",
            "rule": "rules",
            "faq": "faq"
        }
        folder = type_paths.get(entry.type, "misc")
        safe_id = entry.id.replace("/", "-").replace(" ", "-")
        return f"{folder}/{safe_id}.md"
    
    def _get_sha(self, path: str) -> Optional[str]:
        """获取文件SHA（用于更新）"""
        url = f"{self.base_url}/contents/{path}"
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                return data.get("sha")
        except Exception as e:
            logger.debug(f"获取SHA失败: {e}")
        return None
    
    def save(self, entry: BrainEntry, force_sync: bool = False) -> bool:
        """
        保存知识条目到GitHub
        
        Args:
            entry: 知识条目
            force_sync: 是否强制同步到GitHub
            
        Returns:
            是否成功
        """
        self._cache[entry.id] = entry
        
        if not force_sync or not self.is_available():
            # 仅保存到本地缓存
            return True
        
        path = self._get_file_path(entry)
        content = entry.to_markdown()
        
        # Base64编码
        content_bytes = content.encode('utf-8')
        content_base64 = base64.b64encode(content_bytes).decode('utf-8')
        
        # 获取SHA（如果文件存在）
        sha = self._get_sha(path)
        
        # 构建请求数据
        data = json.dumps({
            "message": f"Update {entry.type}: {entry.title}",
            "content": content_base64,
        }).encode()
        
        req = urllib.request.Request(url, data=data, headers={
            **self.headers,
            "Content-Type": "application/json"
        })
        req.get_method = lambda: "PUT"
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status in [200, 201]:
                    logger.info(f"✅ 已同步到GitHub: {path}")
                    return True
        except Exception as e:
            logger.error(f"GitHub同步异常: {e}")
        return False
    
    def load(self, entry_id: str) -> Optional[BrainEntry]:
        """从缓存加载知识条目"""
        return self._cache.get(entry_id)
    
    def search(self, query: str, type_filter: str = None) -> List[BrainEntry]:
        """搜索知识条目"""
        results = []
        query_lower = query.lower()
        
        for entry in self._cache.values():
            if type_filter and entry.type != type_filter:
                continue
            
            # 简单关键词匹配
            if (query_lower in entry.title.lower() or 
                query_lower in entry.content.lower()):
                results.append(entry)
        
        return results
    
    def get_by_type(self, entry_type: str) -> List[BrainEntry]:
        """按类型获取所有条目"""
        return [e for e in self._cache.values() if e.type == entry_type]
    
    def get_villa(self, villa_id: str) -> Optional[BrainEntry]:
        """获取别墅信息"""
        return self._cache.get(f"villa_{villa_id}")
    
    def get_customer(self, user_id: str) -> Optional[BrainEntry]:
        """获取客户信息"""
        return self._cache.get(f"customer_{user_id}")
    
    def save_customer(self, user_id: str, profile_data: Dict) -> BrainEntry:
        """保存客户信息"""
        entry = BrainEntry(
            id=f"customer_{user_id}",
            type="customer",
            title=f"User {user_id}",
            content=json.dumps(profile_data, ensure_ascii=False),
            metadata={
                "tags": ["customer"],
                "user_id": user_id
            },
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        self._cache[entry.id] = entry
        return entry
    
    def initialize_villas(self, villas: List[Dict]) -> int:
        """
        初始化别墅数据
        
        Args:
            villas: 别墅数据列表
            
        Returns:
            初始化数量
        """
        count = 0
        for villa in villas:
            entry = BrainEntry(
                id=f"villa_{villa['id']}",
                type="villa",
                title=villa.get('name', f"Villa {villa['id']}"),
                content=self._format_villa_content(villa),
                metadata={
                    "tags": [villa.get('region', ''), villa.get('type', '')],
                    "villa_id": villa['id'],
                    "region": villa.get('region'),
                    "price": villa.get('price_per_night'),
                    "timeline": []
                },
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            self._cache[entry.id] = entry
            count += 1
        
        logger.info(f"✅ 已初始化 {count} 套别墅到Brain Repo")
        return count
    
    def _format_villa_content(self, villa: Dict) -> str:
        """格式化别墅内容"""
        lines = [
            f"## 基本信息",
            f"- **编号**: {villa.get('id')}",
            f"- **地区**: {villa.get('region', '未知')}",
            f"- **房型**: {villa.get('type', '未知')}",
            f"- **价格**: ฿{villa.get('price_per_night', 0):,} / 晚",
            "",
            f"## 容量",
            f"- **最大入住**: {villa.get('max_guests', 0)} 人",
            f"- **卧室**: {villa.get('bedrooms', 0)} 间",
            f"- **卫生间**: {villa.get('bathrooms', 0)} 间",
            "",
            f"## 设施",
        ]
        
        amenities = villa.get('amenities', [])
        if isinstance(amenities, list):
            for a in amenities:
                lines.append(f"- {a}")
        else:
            lines.append(str(amenities))
        
        if villa.get('description'):
            lines.extend(["", f"## 描述", villa['description']])
        
        return "\n".join(lines)
    
    def sync_all_to_github(self) -> Dict[str, int]:
        """
        同步所有缓存到GitHub
        
        Returns:
            同步统计 {success: count, failed: count}
        """
        stats = {"success": 0, "failed": 0}
        
        if not self.is_available():
            logger.warning("⚠️ GitHub不可用，跳过同步")
            return stats
        
        for entry in self._cache.values():
            if self.save(entry, force_sync=True):
                stats["success"] += 1
            else:
                stats["failed"] += 1
        
        logger.info(f"GitHub同步完成: {stats}")
        return stats


# 全局单例
brain_repo = BrainRepo()
