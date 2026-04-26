#!/usr/bin/env python3
"""
增强版健康检查端点
包含: 数据库、响应时间、系统资源等全面检查
"""

import os
import json
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# 尝试导入 psutil (可选)
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class EnhancedHealthHandler(BaseHTTPRequestHandler):
    """增强型健康检查处理器"""
    
    # 告警阈值配置
    THRESHOLDS = {
        'response_time_ms': 5000,      # 响应时间阈值 (ms)
        'disk_usage_percent': 85,       # 磁盘使用率阈值 (%)
        'memory_usage_percent': 80,     # 内存使用率阈值 (%)
        'db_query_time_ms': 1000,       # 数据库查询时间阈值 (ms)
    }
    
    def do_GET(self):
        start_time = time.time()
        
        # 收集各项检查结果
        checks = {
            'status': 'ok',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'service': 'taimili-villa-bot',
            'version': 'v4.0',
            'checks': {}
        }
        
        all_healthy = True
        
        # 1. 数据库健康检查
        db_check = self._check_database()
        checks['checks']['database'] = db_check
        if db_check['status'] != 'healthy':
            all_healthy = False
        
        # 2. 系统资源检查 (需要 psutil)
        if PSUTIL_AVAILABLE:
            sys_check = self._check_system_resources()
            checks['checks']['system'] = sys_check
            if sys_check['status'] != 'healthy':
                all_healthy = False
        else:
            checks['checks']['system'] = {
                'status': 'unknown',
                'note': 'psutil not installed'
            }
        
        # 3. 性能指标
        response_time = (time.time() - start_time) * 1000
        checks['performance'] = {
            'response_time_ms': round(response_time, 2),
            'status': 'healthy' if response_time < self.THRESHOLDS['response_time_ms'] else 'degraded'
        }
        
        # 整体状态
        checks['status'] = 'ok' if all_healthy else 'degraded'
        
        # 响应码设置
        status_code = 200 if checks['status'] == 'ok' else 503
        
        # 发送响应
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(json.dumps(checks, ensure_ascii=False).encode())
    
    def _check_database(self):
        """检查数据库健康状态"""
        result = {'status': 'healthy', 'details': {}}
        
        try:
            # 延迟导入以避免循环依赖
            import database
            start = time.time()
            db_health = database.health_check()
            query_time = (time.time() - start) * 1000
            
            result['details'] = {
                'type': 'sqlite',
                'villas_count': db_health['record_counts'].get('villas', 0),
                'bookings_count': db_health['record_counts'].get('bookings', 0),
                'query_time_ms': round(query_time, 2)
            }
            
            if query_time > self.THRESHOLDS['db_query_time_ms']:
                result['status'] = 'degraded'
                result['warning'] = f'查询时间过长: {query_time:.2f}ms'
                
        except Exception as e:
            result['status'] = 'unhealthy'
            result['error'] = str(e)
        
        return result
    
    def _check_system_resources(self):
        """检查系统资源"""
        result = {'status': 'healthy', 'details': {}}
        
        try:
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_info = {
                'total_gb': round(disk.total / (1024**3), 2),
                'used_gb': round(disk.used / (1024**3), 2),
                'free_gb': round(disk.free / (1024**3), 2),
                'usage_percent': disk.percent
            }
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_info = {
                'total_gb': round(memory.total / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2),
                'usage_percent': memory.percent
            }
            
            # 进程信息
            process = psutil.Process()
            process_info = {
                'pid': process.pid,
                'memory_mb': round(process.memory_info().rss / (1024**2), 2),
                'cpu_percent': process.cpu_percent(interval=0.1)
            }
            
            result['details'] = {
                'disk': disk_info,
                'memory': memory_info,
                'process': process_info
            }
            
            # 检查阈值
            warnings = []
            if disk.percent > self.THRESHOLDS['disk_usage_percent']:
                warnings.append(f"磁盘使用率过高: {disk.percent}%")
            if memory.percent > self.THRESHOLDS['memory_usage_percent']:
                warnings.append(f"内存使用率过高: {memory.percent}%")
            
            if warnings:
                result['status'] = 'degraded'
                result['warnings'] = warnings
                
        except Exception as e:
            result['status'] = 'unhealthy'
            result['error'] = str(e)
        
        return result
    
    def log_message(self, format, *args):
        """抑制日志输出"""
        pass


def run_enhanced_health_server(port=8081):
    """运行增强型健康检查服务器 (独立进程)"""
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    server = HTTPServer(('0.0.0.0', port), EnhancedHealthHandler)
    logger.info(f"🚀 增强型健康检查服务器启动: 端口 {port}")
    logger.info(f"📍 健康检查端点: http://0.0.0.0:{port}/health")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("⛔ 健康检查服务器已停止")
        server.shutdown()


if __name__ == '__main__':
    run_enhanced_health_server()
