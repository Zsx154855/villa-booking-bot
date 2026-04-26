#!/usr/bin/env python3
"""
监控脚本
可独立运行，用于定时健康检查和告警

用法:
    python monitoring/monitor_runner.py
    
    # 指定端点
    python monitoring/monitor_runner.py --url https://your-app.onrender.com/health
    
    # 发送测试通知
    python monitoring/monitor_runner.py --test-notify
"""

import os
import sys
import time
import json
import argparse
import logging
from datetime import datetime
from typing import Dict, Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='Taimili Bot 健康检查监控')
    
    parser.add_argument(
        '--url',
        default=os.environ.get('HEALTH_CHECK_URL', 'https://taimili-villa-bot.onrender.com/health'),
        help='健康检查端点 URL'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='请求超时时间 (秒)'
    )
    parser.add_argument(
        '--threshold',
        type=int,
        default=5000,
        help='响应时间阈值 (毫秒)'
    )
    parser.add_argument(
        '--test-notify',
        action='store_true',
        help='发送测试通知'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='静默模式 (只输出错误)'
    )
    
    return parser.parse_args()


def check_health(url: str, timeout: int = 30, threshold_ms: int = 5000) -> Dict:
    """
    检查服务健康状态
    
    Args:
        url: 健康检查端点
        timeout: 超时时间
        threshold_ms: 响应时间阈值 (毫秒)
        
    Returns:
        Dict: 检查结果
    """
    import urllib.request
    import urllib.error
    
    result = {
        'url': url,
        'timestamp': datetime.now().isoformat(),
        'status': 'unknown',
        'http_code': None,
        'response_time_ms': None,
        'data': None,
        'error': None
    }
    
    start_time = time.time()
    
    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'TaimiliMonitor/1.0',
                'Accept': 'application/json'
            }
        )
        
        with urllib.request.urlopen(req, timeout=timeout) as response:
            response_time = (time.time() - start_time) * 1000
            response_body = response.read().decode('utf-8')
            
            result['http_code'] = response.status
            result['response_time_ms'] = round(response_time, 2)
            
            # 解析响应
            try:
                result['data'] = json.loads(response_body)
                result['status'] = result['data'].get('status', 'unknown')
            except json.JSONDecodeError:
                result['status'] = 'invalid_json'
            
            # 检查响应时间
            if response_time > threshold_ms:
                result['warning'] = f'响应时间超过阈值: {response_time:.2f}ms > {threshold_ms}ms'
            
    except urllib.error.HTTPError as e:
        result['error'] = f'HTTP错误: {e.code} {e.reason}'
        result['http_code'] = e.code
        
    except urllib.error.URLError as e:
        result['error'] = f'连接错误: {e.reason}'
        
    except Exception as e:
        result['error'] = f'未知错误: {str(e)}'
    
    return result


def send_notifications(check_result: Dict):
    """发送告警通知"""
    # 延迟导入以避免不必要的依赖
    from monitoring import get_notifier, get_alert_manager
    
    notifier = get_notifier()
    alert_mgr = get_alert_manager()
    
    status = check_result['status']
    
    # 健康检查成功
    if status == 'ok':
        alert_mgr.on_health_check_success()
        if not args.quiet:
            logger.info("✅ 健康检查通过")
        return True
    
    # 服务离线或错误
    if check_result['error'] or status not in ['ok', 'healthy']:
        alert_mgr.on_health_check_failure(check_result.get('error', 'Unknown error'))
        return False
    
    # 状态降级
    if 'warning' in check_result:
        notifier.send_alert(
            severity='WARNING',
            title='响应时间过长',
            message=check_result['warning'],
            details=check_result
        )
    
    return False


def test_notifications():
    """发送测试通知"""
    from monitoring import get_notifier, get_email_notifier
    
    print("📤 发送测试通知...")
    
    # Telegram 测试
    telegram = get_notifier()
    if telegram.enabled:
        success = telegram.send_alert(
            severity='INFO',
            title='测试告警',
            message='这是一条测试消息，用于验证 Telegram 通知配置是否正确。'
        )
        print(f"   Telegram: {'✅ 发送成功' if success else '❌ 发送失败'}")
    else:
        print("   Telegram: ⏭️ 未配置 (将使用模拟模式)")
    
    # 邮件测试
    email = get_email_notifier()
    if email.enabled:
        success = email.send_test_email()
        print(f"   Email: {'✅ 发送成功' if success else '❌ 发送失败'}")
    else:
        print("   Email: ⏭️ 未配置")
    
    print("✅ 测试通知发送完成")


def main():
    """主函数"""
    global args
    args = parse_args()
    
    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
    
    # 测试通知模式
    if args.test_notify:
        test_notifications()
        return
    
    # 执行健康检查
    logger.info(f"🔍 开始健康检查: {args.url}")
    
    result = check_health(args.url, args.timeout, args.threshold)
    
    # 输出结果
    if args.quiet:
        if result['status'] != 'ok':
            print(json.dumps(result, indent=2))
    else:
        print("\n📊 健康检查结果:")
        print(f"   状态: {result['status']}")
        print(f"   HTTP: {result['http_code'] or 'N/A'}")
        print(f"   响应时间: {result['response_time_ms'] or 'N/A'} ms")
        
        if result['error']:
            print(f"   错误: {result['error']}")
        
        if 'warning' in result:
            print(f"   警告: {result['warning']}")
        
        if result['data']:
            print("\n📋 详细信息:")
            print(json.dumps(result['data'], indent=2, ensure_ascii=False))
    
    # 发送通知
    success = send_notifications(result)
    
    # 返回状态码
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
