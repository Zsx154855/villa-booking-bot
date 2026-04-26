#!/usr/bin/env python3
"""
Database Configuration Module
数据库配置模块 - 支持 PostgreSQL (Koyeb) 和 SQLite (本地开发)
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DatabaseConfig:
    """数据库配置类"""
    # 数据库类型: 'postgresql' 或 'sqlite'
    db_type: str = 'sqlite'
    
    # SQLite 配置
    sqlite_path: str = "data/villas.db"
    
    # PostgreSQL 配置
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_database: str = "villas"
    pg_user: str = "postgres"
    pg_password: str = ""
    
    # 连接池配置 (适配 Koyeb 免费版限制)
    pool_min_connections: int = 1
    pool_max_connections: int = 5
    pool_timeout: int = 30
    
    # 超时配置
    command_timeout: int = 30
    
    @property
    def database_url(self) -> str:
        """从环境变量获取数据库连接URL"""
        return os.environ.get('DATABASE_URL')
    
    @property
    def is_postgresql(self) -> bool:
        """是否使用 PostgreSQL"""
        return self.db_type == 'postgresql' or bool(self.database_url)
    
    @property
    def is_sqlite(self) -> bool:
        """是否使用 SQLite"""
        return not self.is_postgresql
    
    def get_postgres_dsn(self) -> str:
        """获取 PostgreSQL DSN 连接字符串"""
        if self.database_url:
            return self.database_url
        
        return (
            f"host={self.pg_host} "
            f"port={self.pg_port} "
            f"dbname={self.pg_database} "
            f"user={self.pg_user} "
            f"password={self.pg_password}"
        )
    
    def get_sqlite_path(self) -> str:
        """获取 SQLite 数据库路径"""
        return self.sqlite_path


def load_config() -> DatabaseConfig:
    """
    从环境变量加载数据库配置
    
    环境变量:
        DATABASE_URL: PostgreSQL 连接字符串 (优先)
        DB_TYPE: 数据库类型 ('postgresql' 或 'sqlite')
        SQLITE_PATH: SQLite 数据库路径 (默认: data/villas.db)
        PG_HOST: PostgreSQL 主机
        PG_PORT: PostgreSQL 端口
        PG_DATABASE: PostgreSQL 数据库名
        PG_USER: PostgreSQL 用户
        PG_PASSWORD: PostgreSQL 密码
    """
    config = DatabaseConfig()
    
    # 优先使用 DATABASE_URL
    if os.environ.get('DATABASE_URL'):
        config.db_type = 'postgresql'
        return config
    
    # 从环境变量加载配置
    db_type = os.environ.get('DB_TYPE', 'sqlite')
    config.db_type = db_type if db_type in ('postgresql', 'sqlite') else 'sqlite'
    
    # SQLite 配置
    config.sqlite_path = os.environ.get('SQLITE_PATH', 'data/villas.db')
    
    # PostgreSQL 配置
    config.pg_host = os.environ.get('PG_HOST', 'localhost')
    config.pg_port = int(os.environ.get('PG_PORT', 5432))
    config.pg_database = os.environ.get('PG_DATABASE', 'villas')
    config.pg_user = os.environ.get('PG_USER', 'postgres')
    config.pg_password = os.environ.get('PG_PASSWORD', '')
    
    # 连接池配置 (适配 Koyeb 免费版)
    config.pool_min_connections = int(os.environ.get('DB_POOL_MIN', 1))
    config.pool_max_connections = int(os.environ.get('DB_POOL_MAX', 5))
    
    return config


# 全局配置实例
db_config = load_config()


def is_production() -> bool:
    """判断是否为生产环境 (Koyeb)"""
    return db_config.is_postgresql


def is_development() -> bool:
    """判断是否为开发环境 (本地 SQLite)"""
    return not db_config.is_postgresql
