#!/usr/bin/env python3
"""
GBrain持久化模块 - Villa Booking Bot
基于GBrain三层架构 + Render免费版SQLite限制

Layer 1: Brain Repo - GitHub仓库知识存储
Layer 2: SQLite Persistence - 数据持久化
Layer 3: Agent MCP - 标准化知识接口
"""

__version__ = "1.0.0"

from .persistence import GBrainPersistence, gbrain_persistence
from .brain_repo import BrainRepo, brain_repo
from .mcp_interface import GBrainMCP, gbrain_mcp

__all__ = [
    "BrainRepo",
    "GBrainPersistence",
    "GBrainMCP",
    "gbrain_persistence",
    "gbrain_mcp",
    "brain_repo",
]
