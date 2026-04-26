#!/usr/bin/env python3
"""
Taimili 别墅运营系统 - 健康检查脚本
检查系统各项功能是否正常
"""

import os
import sys

def check_dependencies():
    """检查依赖"""
    print("📦 检查依赖...")
    required = [
        'telegram',
        'reportlab',
        'matplotlib',
        'openpyxl',
        'stripe'
    ]
    
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
            print(f"  ✓ {pkg}")
        except ImportError:
            print(f"  ✗ {pkg} (缺失)")
            missing.append(pkg)
    
    return len(missing) == 0

def check_environment():
    """检查环境变量"""
    print("\n🔑 检查环境变量...")
    vars = {
        'TELEGRAM_BOT_TOKEN': True,
        'STRIPE_SECRET_KEY': False,
        'STRIPE_WEBHOOK_SECRET': False,
        'DATABASE_URL': False
    }
    
    for var, required in vars.items():
        value = os.environ.get(var)
        if value:
            print(f"  ✓ {var} = {value[:20]}...")
        elif required:
            print(f"  ✗ {var} (必需)")
        else:
            print(f"  ⚠ {var} (可选)")
    
    return os.environ.get('TELEGRAM_BOT_TOKEN') is not None

def check_database():
    """检查数据库"""
    print("\n🗄️ 检查数据库...")
    try:
        import database
        database.init_db()
        villas = database.get_all_villas()
        print(f"  ✓ 数据库连接正常")
        print(f"  ✓ 别墅数据: {len(villas)} 套")
        return True
    except Exception as e:
        print(f"  ✗ 数据库错误: {e}")
        return False

def check_files():
    """检查文件"""
    print("\n📁 检查文件...")
    files = [
        'bot.py',
        'database.py',
        'villas.json',
        'requirements.txt',
        'src/services/document/pdf_generator.py',
        'src/services/payment/stripe_payment.py',
        'src/services/analytics/report_generator.py'
    ]
    
    for f in files:
        if os.path.exists(f):
            print(f"  ✓ {f}")
        else:
            print(f"  ✗ {f} (缺失)")
    
    return True

def check_render():
    """检查Render服务"""
    print("\n🌐 检查Render服务...")
    try:
        import urllib.request
        with urllib.request.urlopen('https://taimili-villa-bot.onrender.com/health', timeout=30) as response:
            if response.status == 200:
                print("  ✓ 服务在线")
                return True
    except Exception as e:
        print(f"  ⚠ 服务离线或唤醒中: {e}")
    return False

def main():
    print("=" * 50)
    print("🏠 Taimili 别墅运营系统 - 健康检查")
    print("=" * 50)
    
    results = {
        '依赖': check_dependencies(),
        '环境': check_environment(),
        '数据库': check_database(),
        '文件': check_files(),
        '服务': check_render()
    }
    
    print("\n" + "=" * 50)
    print("检查结果汇总:")
    print("=" * 50)
    
    all_passed = True
    for name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("✅ 所有检查通过！")
    else:
        print("⚠️ 部分检查未通过，请检查上方详情")
    
    return all_passed

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
