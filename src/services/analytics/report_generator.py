#!/usr/bin/env python3
"""
Taimili Villa Booking System - Report Generator
数据报表生成器

功能：
- 日报表：当日预订数、总收入、地区分布、热门别墅
- 周报表：预订趋势、收入趋势、客户来源分析
- 月报表：综合运营数据、同比/环比分析
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any
from collections import defaultdict

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from database import get_connection, get_all_villas

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class ReportGenerator:
    """报表生成器"""
    
    def __init__(self, db_path: str = None):
        """
        初始化报表生成器
        
        Args:
            db_path: 数据库路径（可选，默认使用项目数据库）
        """
        self.db_path = db_path
    
    def _execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """执行SQL查询并返回结果"""
        with get_connection() as conn:
            if params:
                cursor = conn.execute(query, params)
            else:
                cursor = conn.execute(query)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
    
    def _get_date_range(self, report_type: str, reference_date: date = None) -> tuple:
        """获取日期范围"""
        if reference_date is None:
            reference_date = date.today()
        
        if report_type == 'daily':
            start_date = reference_date
            end_date = reference_date
        elif report_type == 'weekly':
            # 获取本周一
            start_date = reference_date - timedelta(days=reference_date.weekday())
            end_date = reference_date
        elif report_type == 'monthly':
            start_date = reference_date.replace(day=1)
            end_date = reference_date
        else:
            start_date = reference_date
            end_date = reference_date
        
        return start_date, end_date
    
    # ============ 日报表功能 ============
    
    def get_daily_report(self, report_date: date = None) -> Dict[str, Any]:
        """
        生成日报表数据
        
        Args:
            report_date: 报表日期，默认今天
        
        Returns:
            包含以下键的字典:
            - date: 报表日期
            - total_bookings: 当日预订数
            - total_revenue: 总收入
            - region_distribution: 地区预订分布
            - top_villas: 热门别墅排行
        """
        if report_date is None:
            report_date = date.today()
        
        date_str = report_date.isoformat()
        
        # 当日预订数统计
        query_bookings = """
            SELECT COUNT(*) as count, 
                   SUM(total_price) as revenue
            FROM bookings 
            WHERE DATE(created_at) = ?
            AND status IN ('pending', 'confirmed', 'completed')
        """
        booking_stats = self._execute_query(query_bookings, (date_str,))
        
        # 地区预订分布
        query_region = """
            SELECT villa_region as region, 
                   COUNT(*) as bookings,
                   SUM(total_price) as revenue
            FROM bookings 
            WHERE DATE(created_at) = ?
            AND status IN ('pending', 'confirmed', 'completed')
            GROUP BY villa_region
            ORDER BY bookings DESC
        """
        region_stats = self._execute_query(query_region, (date_str,))
        
        # 热门别墅排行
        query_villas = """
            SELECT b.villa_name, 
                   b.villa_region as region,
                   COUNT(*) as bookings,
                   SUM(b.total_price) as revenue
            FROM bookings b
            WHERE DATE(b.created_at) = ?
            AND b.status IN ('pending', 'confirmed', 'completed')
            GROUP BY b.villa_id
            ORDER BY bookings DESC, revenue DESC
            LIMIT 10
        """
        top_villas = self._execute_query(query_villas, (date_str,))
        
        # 组装报表数据
        report = {
            'date': date_str,
            'date_display': report_date.strftime('%Y年%m月%d日'),
            'total_bookings': booking_stats[0]['count'] if booking_stats else 0,
            'total_revenue': booking_stats[0]['revenue'] or 0,
            'region_distribution': [
                {
                    'region': r['region'] or '未知',
                    'bookings': r['bookings'],
                    'revenue': r['revenue'] or 0
                }
                for r in region_stats
            ],
            'top_villas': [
                {
                    'rank': i + 1,
                    'name': v['villa_name'] or '未知',
                    'region': v['region'] or '未知',
                    'bookings': v['bookings'],
                    'revenue': v['revenue'] or 0
                }
                for i, v in enumerate(top_villas)
            ]
        }
        
        logger.info(f"📊 生成日报表: {date_str}")
        return report
    
    def format_daily_report_text(self, report: Dict) -> str:
        """格式化日报表为文本"""
        lines = [
            f"📅 *日报表 - {report['date_display']}*",
            "",
            f"📈 *当日概况*",
            f"• 预订数量: `{report['total_bookings']}` 单",
            f"• 总收入: `¥{report['total_revenue']:,.2f}`",
            ""
        ]
        
        if report['region_distribution']:
            lines.append("📍 *地区分布*")
            for r in report['region_distribution']:
                lines.append(
                    f"  {r['region']}: {r['bookings']} 单 "
                    f"(¥{r['revenue']:,.2f})"
                )
            lines.append("")
        
        if report['top_villas']:
            lines.append("🏆 *热门别墅 TOP 5*")
            for v in report['top_villas'][:5]:
                lines.append(
                    f"  {v['rank']}. {v['name']} ({v['region']}) "
                    f"- {v['bookings']} 单"
                )
        
        return "\n".join(lines)
    
    # ============ 周报表功能 ============
    
    def get_weekly_report(self, reference_date: date = None) -> Dict[str, Any]:
        """
        生成周报表数据
        
        Args:
            reference_date: 参考日期，默认今天
        
        Returns:
            包含以下键的字典:
            - start_date, end_date: 本周日期范围
            - total_bookings: 本周总预订数
            - total_revenue: 本周总收入
            - daily_trends: 每日趋势
            - region_distribution: 地区分布
            - customer_sources: 客户来源分析
        """
        if reference_date is None:
            reference_date = date.today()
        
        start_date, end_date = self._get_date_range('weekly', reference_date)
        start_str = start_date.isoformat()
        end_str = end_date.isoformat()
        
        # 本周统计
        query_summary = """
            SELECT COUNT(*) as count,
                   SUM(total_price) as revenue
            FROM bookings
            WHERE DATE(created_at) BETWEEN ? AND ?
            AND status IN ('pending', 'confirmed', 'completed')
        """
        summary = self._execute_query(query_summary, (start_str, end_str))
        
        # 每日趋势
        query_daily = """
            SELECT DATE(created_at) as date,
                   COUNT(*) as bookings,
                   SUM(total_price) as revenue
            FROM bookings
            WHERE DATE(created_at) BETWEEN ? AND ?
            AND status IN ('pending', 'confirmed', 'completed')
            GROUP BY DATE(created_at)
            ORDER BY date
        """
        daily_trends = self._execute_query(query_daily, (start_str, end_str))
        
        # 地区分布
        query_region = """
            SELECT villa_region as region,
                   COUNT(*) as bookings,
                   SUM(total_price) as revenue
            FROM bookings
            WHERE DATE(created_at) BETWEEN ? AND ?
            AND status IN ('pending', 'confirmed', 'completed')
            GROUP BY villa_region
            ORDER BY bookings DESC
        """
        region_dist = self._execute_query(query_region, (start_str, end_str))
        
        # 客户来源分析（基于user_id分布）
        query_sources = """
            SELECT 
                CASE 
                    WHEN user_id LIKE 'telegram:%' THEN 'Telegram'
                    WHEN user_id LIKE 'wechat:%' THEN 'WeChat'
                    ELSE '其他'
                END as source,
                COUNT(*) as count,
                SUM(total_price) as revenue
            FROM bookings
            WHERE DATE(created_at) BETWEEN ? AND ?
            AND status IN ('pending', 'confirmed', 'completed')
            GROUP BY source
            ORDER BY count DESC
        """
        sources = self._execute_query(query_sources, (start_str, end_str))
        
        report = {
            'start_date': start_str,
            'end_date': end_str,
            'date_range_display': f"{start_date.strftime('%m/%d')} - {end_date.strftime('%m/%d')}",
            'total_bookings': summary[0]['count'] if summary else 0,
            'total_revenue': summary[0]['revenue'] or 0,
            'daily_trends': [
                {
                    'date': d['date'],
                    'bookings': d['bookings'],
                    'revenue': d['revenue'] or 0
                }
                for d in daily_trends
            ],
            'region_distribution': [
                {
                    'region': r['region'] or '未知',
                    'bookings': r['bookings'],
                    'revenue': r['revenue'] or 0
                }
                for r in region_dist
            ],
            'customer_sources': [
                {
                    'source': s['source'],
                    'count': s['count'],
                    'revenue': s['revenue'] or 0
                }
                for s in sources
            ]
        }
        
        logger.info(f"📊 生成周报表: {start_str} ~ {end_str}")
        return report
    
    def format_weekly_report_text(self, report: Dict) -> str:
        """格式化周报表为文本"""
        lines = [
            f"📅 *周报表 - {report['date_range_display']}*",
            "",
            f"📈 *本周概况*",
            f"• 总预订数: `{report['total_bookings']}` 单",
            f"• 总收入: `¥{report['total_revenue']:,.2f}`",
            ""
        ]
        
        if report['region_distribution']:
            lines.append("📍 *地区分布*")
            for r in report['region_distribution']:
                lines.append(
                    f"  {r['region']}: {r['bookings']} 单 "
                    f"(¥{r['revenue']:,.2f})"
                )
            lines.append("")
        
        if report['customer_sources']:
            lines.append("👥 *客户来源*")
            for s in report['customer_sources']:
                lines.append(f"  {s['source']}: {s['count']} 单")
            lines.append("")
        
        return "\n".join(lines)
    
    # ============ 月报表功能 ============
    
    def get_monthly_report(self, year: int = None, month: int = None) -> Dict[str, Any]:
        """
        生成月报表数据
        
        Args:
            year: 年份，默认今年
            month: 月份，默认本月
        
        Returns:
            包含以下键的字典:
            - year, month: 年月
            - total_bookings: 月总预订数
            - total_revenue: 月总收入
            - daily_trends: 每日趋势
            - region_distribution: 地区分布
            - comparison: 同比/环比分析
        """
        if year is None:
            year = date.today().year
        if month is None:
            month = date.today().month
        
        # 月份日期范围
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        start_str = start_date.isoformat()
        end_str = end_date.isoformat()
        
        # 本月统计
        query_summary = """
            SELECT COUNT(*) as count,
                   SUM(total_price) as revenue,
                   AVG(total_price) as avg_price
            FROM bookings
            WHERE DATE(created_at) BETWEEN ? AND ?
            AND status IN ('pending', 'confirmed', 'completed')
        """
        summary = self._execute_query(query_summary, (start_str, end_str))
        
        # 每日趋势
        query_daily = """
            SELECT DATE(created_at) as date,
                   COUNT(*) as bookings,
                   SUM(total_price) as revenue
            FROM bookings
            WHERE DATE(created_at) BETWEEN ? AND ?
            AND status IN ('pending', 'confirmed', 'completed')
            GROUP BY DATE(created_at)
            ORDER BY date
        """
        daily_trends = self._execute_query(query_daily, (start_str, end_str))
        
        # 地区分布
        query_region = """
            SELECT villa_region as region,
                   COUNT(*) as bookings,
                   SUM(total_price) as revenue
            FROM bookings
            WHERE DATE(created_at) BETWEEN ? AND ?
            AND status IN ('pending', 'confirmed', 'completed')
            GROUP BY villa_region
            ORDER BY bookings DESC
        """
        region_dist = self._execute_query(query_region, (start_str, end_str))
        
        # 环比数据（上月）
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        prev_start = date(prev_year, prev_month, 1)
        if prev_month == 12:
            prev_end = date(prev_year + 1, 1, 1) - timedelta(days=1)
        else:
            prev_end = date(prev_year, prev_month + 1, 1) - timedelta(days=1)
        
        query_prev = """
            SELECT COUNT(*) as count,
                   SUM(total_price) as revenue
            FROM bookings
            WHERE DATE(created_at) BETWEEN ? AND ?
            AND status IN ('pending', 'confirmed', 'completed')
        """
        prev_data = self._execute_query(query_prev, (prev_start.isoformat(), prev_end.isoformat()))
        
        # 同比数据（去年同月）
        query_yoy = """
            SELECT COUNT(*) as count,
                   SUM(total_price) as revenue
            FROM bookings
            WHERE DATE(created_at) BETWEEN ? AND ?
            AND status IN ('pending', 'confirmed', 'completed')
        """
        yoy_data = self._execute_query(query_yoy, (
            date(year - 1, month, 1).isoformat(),
            date(year - 1, month, 1 if month > 1 else 12 else 12, 
                 (date(year - 1, month + 1 if month < 12 else 1, 1) - timedelta(days=1)).day if month < 12 else 31).isoformat()
        ))
        
        current_bookings = summary[0]['count'] if summary else 0
        current_revenue = summary[0]['revenue'] or 0
        prev_bookings = prev_data[0]['count'] if prev_data else 0
        prev_revenue = prev_data[0]['revenue'] or 0
        yoy_bookings = yoy_data[0]['count'] if yoy_data else 0
        yoy_revenue = yoy_data[0]['revenue'] or 0
        
        # 计算环比/同比变化
        mom_change_bookings = self._calc_change(current_bookings, prev_bookings)
        mom_change_revenue = self._calc_change(current_revenue, prev_revenue)
        yoy_change_bookings = self._calc_change(current_bookings, yoy_bookings)
        yoy_change_revenue = self._calc_change(current_revenue, yoy_revenue)
        
        report = {
            'year': year,
            'month': month,
            'month_display': f"{year}年{month}月",
            'start_date': start_str,
            'end_date': end_str,
            'total_bookings': current_bookings,
            'total_revenue': current_revenue,
            'avg_price': summary[0]['avg_price'] or 0,
            'daily_trends': [
                {
                    'date': d['date'],
                    'bookings': d['bookings'],
                    'revenue': d['revenue'] or 0
                }
                for d in daily_trends
            ],
            'region_distribution': [
                {
                    'region': r['region'] or '未知',
                    'bookings': r['bookings'],
                    'revenue': r['revenue'] or 0
                }
                for r in region_dist
            ],
            'comparison': {
                'month_over_month': {
                    'prev_bookings': prev_bookings,
                    'prev_revenue': prev_revenue,
                    'bookings_change': mom_change_bookings,
                    'revenue_change': mom_change_revenue
                },
                'year_over_year': {
                    'yoy_bookings': yoy_bookings,
                    'yoy_revenue': yoy_revenue,
                    'bookings_change': yoy_change_bookings,
                    'revenue_change': yoy_change_revenue
                }
            }
        }
        
        logger.info(f"📊 生成月报表: {year}/{month}")
        return report
    
    def _calc_change(self, current: float, prev: float) -> float:
        """计算变化百分比"""
        if prev == 0:
            return 100.0 if current > 0 else 0.0
        return round((current - prev) / prev * 100, 2)
    
    def format_monthly_report_text(self, report: Dict) -> str:
        """格式化月报表为文本"""
        comp = report['comparison']
        mom = comp['month_over_month']
        yoy = comp['year_over_year']
        
        def change_str(change: float) -> str:
            if change > 0:
                return f"+{change}%"
            elif change < 0:
                return f"{change}%"
            return "0%"
        
        lines = [
            f"📅 *月报表 - {report['month_display']}*",
            "",
            f"📈 *本月概况*",
            f"• 总预订数: `{report['total_bookings']}` 单",
            f"• 总收入: `¥{report['total_revenue']:,.2f}`",
            f"• 平均客单价: `¥{report['avg_price']:,.2f}`",
            "",
            f"📊 *环比变化* (vs 上月)",
            f"• 预订数: {mom['prev_bookings']} → `{report['total_bookings']}` "
            f"({change_str(mom['bookings_change'])})",
            f"• 收入: ¥{mom['prev_revenue']:,.2f} → `¥{report['total_revenue']:,.2f}` "
            f"({change_str(mom['revenue_change'])})",
            "",
            f"📊 *同比变化* (vs 去年同月)",
            f"• 预订数: {yoy['yoy_bookings']} → `{report['total_bookings']}` "
            f"({change_str(yoy['bookings_change'])})",
            f"• 收入: ¥{yoy['yoy_revenue']:,.2f} → `¥{report['total_revenue']:,.2f}` "
            f"({change_str(yoy['revenue_change'])})",
            ""
        ]
        
        if report['region_distribution']:
            lines.append("📍 *地区分布*")
            for r in report['region_distribution']:
                lines.append(
                    f"  {r['region']}: {r['bookings']} 单 "
                    f"(¥{r['revenue']:,.2f})"
                )
        
        return "\n".join(lines)
    
    # ============ 通用功能 ============
    
    def get_all_villas_stats(self) -> Dict[str, Any]:
        """获取所有别墅的统计数据"""
        query = """
            SELECT 
                v.id, v.name, v.region, v.price_per_night,
                COUNT(b.id) as total_bookings,
                SUM(CASE WHEN b.status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN b.status = 'cancelled' THEN 1 ELSE 0 END) as cancelled,
                SUM(b.total_price) as total_revenue
            FROM villas v
            LEFT JOIN bookings b ON v.id = b.villa_id
            WHERE v.is_active = 1
            GROUP BY v.id
            ORDER BY total_bookings DESC
        """
        
        stats = self._execute_query(query)
        return {
            'villas': [
                {
                    'id': v['id'],
                    'name': v['name'],
                    'region': v['region'],
                    'price': v['price_per_night'],
                    'total_bookings': v['total_bookings'] or 0,
                    'completed': v['completed'] or 0,
                    'cancelled': v['cancelled'] or 0,
                    'total_revenue': v['total_revenue'] or 0,
                    'completion_rate': round(
                        (v['completed'] or 0) / v['total_bookings'] * 100, 2
                    ) if v['total_bookings'] else 0
                }
                for v in stats
            ],
            'summary': {
                'total_villas': len(stats),
                'total_bookings': sum(v['total_bookings'] or 0 for v in stats),
                'total_revenue': sum(v['total_revenue'] or 0 for v in stats)
            }
        }


# ============ 命令行入口 ============
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='生成别墅预订报表')
    parser.add_argument('--type', '-t', choices=['daily', 'weekly', 'monthly'],
                        default='daily', help='报表类型')
    parser.add_argument('--date', '-d', help='日期 (YYYY-MM-DD)')
    parser.add_argument('--format', '-f', choices=['text', 'json'],
                        default='text', help='输出格式')
    args = parser.parse_args()
    
    generator = ReportGenerator()
    
    if args.date:
        report_date = datetime.strptime(args.date, '%Y-%m-%d').date()
    else:
        report_date = None
    
    if args.type == 'daily':
        report = generator.get_daily_report(report_date)
        output = generator.format_daily_report_text(report)
    elif args.type == 'weekly':
        report = generator.get_weekly_report(report_date)
        output = generator.format_weekly_report_text(report)
    else:
        year = report_date.year if report_date else None
        month = report_date.month if report_date else None
        report = generator.get_monthly_report(year, month)
        output = generator.format_monthly_report_text(report)
    
    if args.format == 'json':
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(output)
