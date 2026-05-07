#!/usr/bin/env python3
"""
客户管理命令行工具
用法: python scripts/customer_cli.py <command> [options]

Commands:
    list              - 列出所有客户
    stats             - 显示客户统计
    top               - 显示Top客户
    search <query>    - 搜索客户
    view <telegram_id> - 查看客户详情
    vip <telegram_id> - 查看客户VIP进度
    block <telegram_id> - 封禁客户
    unblock <telegram_id> - 解封客户
"""

import sys
import os
import argparse

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database
from modules.customer import (
    CustomerService, format_customer_info, format_customer_card,
    get_customer_summary, VIP_BENEFITS
)
from database import calculate_vip_level

def cmd_list(args):
    """列出所有客户"""
    customers = CustomerService.get_all(include_inactive=args.all)
    
    if not customers:
        print("📋 暂无客户数据")
        return
    
    print(f"\n📋 客户列表 (共 {len(customers)} 位)")
    print("━" * 60)
    
    for i, c in enumerate(customers, 1):
        blocked = "🚫" if c.get('is_blocked') else ""
        print(f"{i}. {format_customer_card(c)} {blocked}")
        
        if args.verbose:
            print(f"   创建时间: {c.get('created_at', 'N/A')[:10]}")
            print(f"   最后访问: {c.get('last_seen', 'N/A')[:10]}")
    
    print("━" * 60)

def cmd_stats(args):
    """显示客户统计"""
    stats = CustomerService.get_stats()
    
    if not stats:
        print("❌ 无法获取统计数据")
        return
    
    print("\n📊 客户统计概览")
    print("━" * 60)
    print(f"👥 总客户数: {stats.get('total_customers', 0)}")
    print(f"📅 本月新增: {stats.get('new_this_month', 0)}")
    print(f"🟢 7日活跃: {stats.get('active_recent_7d', 0)}")
    print()
    
    print("🏆 VIP分布:")
    total = stats.get('total_customers', 0)
    vip_dist = stats.get('vip_distribution', {})
    for level in ['钻石会员', '金卡会员', '银卡会员', '普通会员']:
        count = vip_dist.get(level, 0)
        pct = (count / total * 100) if total > 0 else 0
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"   {level:8}: {count:3} ({pct:5.1f}%) {bar}")
    
    print()
    print("💰 消费统计:")
    print(f"   总收入: ฿{stats.get('total_revenue', 0):,.2f}")
    print(f"   平均消费: ฿{stats.get('avg_spent', 0):,.2f}")
    print(f"   最高消费: ฿{stats.get('max_spent', 0):,.2f}")
    print("━" * 60)

def cmd_top(args):
    """显示Top客户"""
    by = args.sort_by or 'spent'
    customers = CustomerService.get_top(limit=args.limit, by=by)
    
    if not customers:
        print("📋 暂无客户数据")
        return
    
    sort_label = {
        'spent': '消费额',
        'bookings': '预订数',
        'nights': '入住天数'
    }.get(by, '消费额')
    
    print(f"\n🏆 Top {len(customers)} 客户 (按{sort_label})")
    print("━" * 70)
    
    for i, c in enumerate(customers, 1):
        spent = c.get('total_spent', 0)
        bookings = c.get('completed_bookings', 0)
        nights = c.get('total_nights', 0)
        points = c.get('points', 0)
        
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
        
        print(f"{medal} {c.get('username', 'User')}")
        print(f"   🏆 {c.get('vip_level', '普通会员')} | "
              f"💰 ฿{spent:,.0f} | "
              f"📅 {bookings}次/{nights}晚 | "
              f"🎫 {points}分")
    
    print("━" * 70)

def cmd_search(args):
    """搜索客户"""
    customers = CustomerService.search(args.query)
    
    if not customers:
        print(f"🔍 未找到匹配 '{args.query}' 的客户")
        return
    
    print(f"\n🔍 搜索结果 ({len(customers)} 位)")
    print("━" * 60)
    
    for c in customers:
        print(format_customer_card(c))
        print(f"   🆔 {c.get('telegram_id')}")
        print()

def cmd_view(args):
    """查看客户详情"""
    customer = CustomerService.get(args.telegram_id)
    
    if not customer:
        print(f"❌ 未找到客户: {args.telegram_id}")
        return
    
    print(format_customer_info(customer))
    
    # 显示权益
    vip_level = customer.get('vip_level', '普通会员')
    benefits = VIP_BENEFITS.get(vip_level, [])
    if benefits:
        print("\n🎁 会员权益:")
        for b in benefits:
            print(f"   ✅ {b}")

def cmd_vip(args):
    """查看VIP升级进度"""
    progress = CustomerService.get_vip_progress(args.telegram_id)
    
    if not progress:
        print(f"❌ 未找到客户: {args.telegram_id}")
        return
    
    customer = CustomerService.get(args.telegram_id)
    
    print(f"\n⬆️ VIP升级进度 - {customer.get('username', 'User')}")
    print("━" * 60)
    print(f"🏆 当前等级: {progress['current_level']}")
    print(f"💰 当前折扣: {progress['current_discount']}%")
    
    if progress['next_level']:
        print()
        print(f"⬆️ 下一等级: {progress['next_level']} ({progress['next_discount']}%折扣)")
        print(f"📊 升级进度: {progress['progress_percent']:.1f}%")
        
        # 进度条
        pct = progress['progress_percent']
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"   [{bar}]")
        
        print(f"💵 再消费: ฿{progress['points_to_next']:,.2f}")
    else:
        print()
        print("🎉 已达到最高等级！")
    
    print("━" * 60)

def cmd_block(args):
    """封禁客户"""
    success = CustomerService.block(args.telegram_id, blocked=True)
    if success:
        print(f"✅ 已封禁客户: {args.telegram_id}")
    else:
        print(f"❌ 封禁失败: {args.telegram_id}")

def cmd_unblock(args):
    """解封客户"""
    success = CustomerService.block(args.telegram_id, blocked=False)
    if success:
        print(f"✅ 已解封客户: {args.telegram_id}")
    else:
        print(f"❌ 解封失败: {args.telegram_id}")

def main():
    parser = argparse.ArgumentParser(
        description="客户管理命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python customer_cli.py list                    # 列出所有客户
  python customer_cli.py list --all              # 包含已禁用客户
  python customer_cli.py stats                    # 显示统计
  python customer_cli.py top --limit 5           # Top 5客户
  python customer_cli.py top --sort-by bookings  # 按预订数排序
  python customer_cli.py search 张三             # 搜索客户
  python customer_cli.py view 123456789          # 查看客户详情
  python customer_cli.py vip 123456789           # 查看VIP进度
  python customer_cli.py block 123456789         # 封禁客户
  python customer_cli.py unblock 123456789       # 解封客户
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # list
    p_list = subparsers.add_parser('list', help='列出所有客户')
    p_list.add_argument('--all', action='store_true', help='包含已禁用客户')
    p_list.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    
    # stats
    subparsers.add_parser('stats', help='显示客户统计')
    
    # top
    p_top = subparsers.add_parser('top', help='显示Top客户')
    p_top.add_argument('-n', '--limit', type=int, default=10, help='显示数量')
    p_top.add_argument('-s', '--sort-by', choices=['spent', 'bookings', 'nights'],
                      dest='sort_by', help='排序方式')
    
    # search
    p_search = subparsers.add_parser('search', help='搜索客户')
    p_search.add_argument('query', help='搜索关键词')
    
    # view
    p_view = subparsers.add_parser('view', help='查看客户详情')
    p_view.add_argument('telegram_id', help='Telegram用户ID')
    
    # vip
    p_vip = subparsers.add_parser('vip', help='查看VIP进度')
    p_vip.add_argument('telegram_id', help='Telegram用户ID')
    
    # block
    p_block = subparsers.add_parser('block', help='封禁客户')
    p_block.add_argument('telegram_id', help='Telegram用户ID')
    
    # unblock
    p_unblock = subparsers.add_parser('unblock', help='解封客户')
    p_unblock.add_argument('telegram_id', help='Telegram用户ID')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 初始化数据库
    try:
        database.init_db()
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        return
    
    # 执行命令
    commands = {
        'list': cmd_list,
        'stats': cmd_stats,
        'top': cmd_top,
        'search': cmd_search,
        'view': cmd_view,
        'vip': cmd_vip,
        'block': cmd_block,
        'unblock': cmd_unblock,
    }
    
    cmd = commands.get(args.command)
    if cmd:
        cmd(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
