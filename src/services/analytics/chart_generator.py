#!/usr/bin/env python3
"""
Taimili Villa Booking System - Chart Generator
图表生成器

使用matplotlib生成各类数据可视化图表
"""

import os
import sys
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple
import io

# 尝试导入matplotlib
try:
    import matplotlib
    matplotlib.use('Agg')  # 无头模式，不显示窗口
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib import font_manager
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 中文字体配置
def _get_chinese_font() -> str:
    """获取可用的中文字体"""
    font_paths = [
        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
        '/System/Library/Fonts/PingFang.ttc',  # macOS
        'C:/Windows/Fonts/msyh.ttc',  # Windows
    ]
    
    for path in font_paths:
        if os.path.exists(path):
            return path
    
    # 返回默认
    return 'DejaVu Sans'


def _setup_chinese_font():
    """设置中文字体"""
    if not MATPLOTLIB_AVAILABLE:
        return
    
    try:
        font_path = _get_chinese_font()
        if os.path.exists(font_path):
            font_prop = font_manager.FontProperties(fname=font_path)
            plt.rcParams['font.family'] = font_prop.get_name()
            plt.rcParams['axes.unicode_minus'] = False
        else:
            # 尝试查找系统字体
            font_manager._load_fontmanager(try_read_cache=False)
    except Exception as e:
        logger.warning(f"设置中文字体失败: {e}")


# 初始化字体
_setup_chinese_font()


# ============ 图表配色方案 ============
COLORS = {
    'primary': '#2E86AB',      # 蓝色
    'secondary': '#A23B72',    # 紫色
    'success': '#27AE60',      # 绿色
    'warning': '#F39C12',      # 橙色
    'danger': '#E74C3C',       # 红色
    'info': '#3498DB',         # 浅蓝
    'light': '#ECF0F1',        # 浅灰
    'dark': '#2C3E50',         # 深灰
    'regions': ['#2E86AB', '#A23B72', '#27AE60', '#F39C12', '#E74C3C', '#9B59B6'],
}


class ChartGenerator:
    """图表生成器"""
    
    def __init__(self, figsize: Tuple[int, int] = (10, 6), dpi: int = 100):
        """
        初始化图表生成器
        
        Args:
            figsize: 图表大小 (宽, 高)
            dpi: 分辨率
        """
        self.figsize = figsize
        self.dpi = dpi
        self.font_size = 10
        self.title_size = 14
    
    def _save_to_bytes(self, fig) -> bytes:
        """将图表保存为字节流"""
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=self.dpi, 
                    bbox_inches='tight', facecolor='white')
        buf.seek(0)
        return buf.getvalue()
    
    def _save_to_file(self, fig, filepath: str) -> str:
        """保存图表到文件"""
        fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        return filepath
    
    # ============ 趋势图 ============
    
    def generate_trend_chart(
        self, 
        data: List[Dict], 
        x_key: str = 'date',
        y_keys: List[str] = None,
        title: str = '趋势图',
        ylabel: str = '数值',
        labels: Dict[str, str] = None
    ) -> bytes:
        """
        生成趋势折线图
        
        Args:
            data: 数据列表
            x_key: x轴字段名
            y_keys: y轴字段名列表
            title: 图表标题
            ylabel: y轴标签
            labels: 字段名到显示名的映射
        
        Returns:
            PNG图片的字节数据
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.error("matplotlib未安装，无法生成图表")
            return b''
        
        if not data or not y_keys:
            return b''
        
        labels = labels or {}
        
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)
        
        # 解析日期
        dates = [datetime.strptime(d[x_key], '%Y-%m-%d').date() for d in data]
        
        for key in y_keys:
            values = [d.get(key, 0) or 0 for d in data]
            label = labels.get(key, key)
            ax.plot(dates, values, marker='o', linewidth=2, label=label)
        
        # 设置日期格式
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.xticks(rotation=45)
        
        ax.set_xlabel('日期', fontsize=self.font_size)
        ax.set_ylabel(ylabel, fontsize=self.font_size)
        ax.set_title(title, fontsize=self.title_size, fontweight='bold')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return self._save_to_bytes(fig)
    
    def generate_booking_trend(self, daily_trends: List[Dict], title: str = None) -> bytes:
        """生成预订趋势图"""
        if not title:
            title = '📈 每日预订趋势'
        
        labels = {'bookings': '预订数', 'revenue': '收入'}
        return self.generate_trend_chart(
            daily_trends, 
            y_keys=['bookings', 'revenue'],
            title=title,
            ylabel='数值',
            labels=labels
        )
    
    def generate_revenue_trend(self, daily_trends: List[Dict], title: str = None) -> bytes:
        """生成收入趋势图"""
        if not title:
            title = '💰 每日收入趋势'
        
        return self.generate_trend_chart(
            daily_trends,
            y_keys=['revenue'],
            title=title,
            ylabel='收入 (¥)',
            labels={'revenue': '收入'}
        )
    
    # ============ 分布图 ============
    
    def generate_pie_chart(
        self,
        data: List[Dict],
        value_key: str,
        label_key: str,
        title: str = '分布图',
        colors: List[str] = None
    ) -> bytes:
        """
        生成饼图
        
        Args:
            data: 数据列表
            value_key: 数值字段名
            label_key: 标签字段名
            title: 图表标题
            colors: 颜色列表
        
        Returns:
            PNG图片的字节数据
        """
        if not MATPLOTLIB_AVAILABLE:
            return b''
        
        if not data:
            return b''
        
        colors = colors or COLORS['regions']
        
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)
        
        labels = [d.get(label_key, '未知') for d in data]
        values = [d.get(value_key, 0) or 0 for d in data]
        
        # 计算百分比
        total = sum(values)
        if total > 0:
            percentages = [v / total * 100 for v in values]
            pct_labels = [f'{l}\n({v:,})\n{p:.1f}%' for l, v, p in zip(labels, values, percentages)]
        else:
            pct_labels = labels
        
        wedges, texts = ax.pie(
            values, 
            labels=pct_labels,
            colors=colors[:len(values)],
            startangle=90,
            textprops={'fontsize': self.font_size - 2}
        )
        
        ax.set_title(title, fontsize=self.title_size, fontweight='bold')
        
        plt.tight_layout()
        return self._save_to_bytes(fig)
    
    def generate_region_pie(self, region_data: List[Dict], title: str = None) -> bytes:
        """生成地区分布饼图"""
        if not title:
            title = '📍 地区预订分布'
        return self.generate_pie_chart(
            region_data,
            value_key='bookings',
            label_key='region',
            title=title
        )
    
    def generate_villa_pie(self, villa_data: List[Dict], title: str = None) -> bytes:
        """生成别墅预订分布饼图"""
        if not title:
            title = '🏠 别墅预订分布'
        return self.generate_pie_chart(
            villa_data[:8],  # 最多8个
            value_key='bookings',
            label_key='name',
            title=title
        )
    
    # ============ 柱状图 ============
    
    def generate_bar_chart(
        self,
        data: List[Dict],
        x_key: str,
        y_keys: List[str],
        title: str = '柱状图',
        ylabel: str = '数值',
        labels: Dict[str, str] = None,
        stacked: bool = False
    ) -> bytes:
        """
        生成柱状图
        
        Args:
            data: 数据列表
            x_key: x轴字段名
            y_keys: y轴字段名列表
            title: 图表标题
            ylabel: y轴标签
            labels: 字段名到显示名的映射
            stacked: 是否堆叠
        
        Returns:
            PNG图片的字节数据
        """
        if not MATPLOTLIB_AVAILABLE:
            return b''
        
        if not data:
            return b''
        
        labels = labels or {}
        x_labels = [d.get(x_key, '')[:10] for d in data]  # 截断长标签
        
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)
        
        x = range(len(data))
        bar_width = 0.35
        
        for i, key in enumerate(y_keys):
            values = [d.get(key, 0) or 0 for d in data]
            label = labels.get(key, key)
            
            if stacked:
                ax.bar(x, values, bar_width, label=label, color=COLORS['regions'][i])
            else:
                offset = (i - len(y_keys) / 2 + 0.5) * bar_width
                ax.bar([xi + offset for xi in x], values, bar_width, label=label)
        
        ax.set_xlabel('', fontsize=self.font_size)
        ax.set_ylabel(ylabel, fontsize=self.font_size)
        ax.set_title(title, fontsize=self.title_size, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(x_labels, rotation=45, ha='right')
        
        if len(y_keys) > 1:
            ax.legend()
        
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        return self._save_to_bytes(fig)
    
    def generate_region_bar(self, region_data: List[Dict], title: str = None) -> bytes:
        """生成地区预订柱状图"""
        if not title:
            title = '📊 地区预订对比'
        return self.generate_bar_chart(
            region_data,
            x_key='region',
            y_keys=['bookings'],
            title=title,
            ylabel='预订数',
            labels={'bookings': '预订数'}
        )
    
    def generate_top_villas_bar(self, villa_data: List[Dict], title: str = None) -> bytes:
        """生成热门别墅柱状图"""
        if not title:
            title = '🏆 热门别墅 TOP 10'
        return self.generate_bar_chart(
            villa_data[:10],
            x_key='name',
            y_keys=['bookings'],
            title=title,
            ylabel='预订数',
            labels={'bookings': '预订数'}
        )
    
    def generate_revenue_bar(self, data: List[Dict], title: str = None) -> bytes:
        """生成收入柱状图"""
        if not title:
            title = '💰 各地区收入对比'
        return self.generate_bar_chart(
            data,
            x_key='region',
            y_keys=['revenue'],
            title=title,
            ylabel='收入 (¥)',
            labels={'revenue': '收入'}
        )
    
    # ============ 组合图表 ============
    
    def generate_daily_report_charts(self, report: Dict) -> Dict[str, bytes]:
        """生成日报表的图表组合"""
        charts = {}
        
        # 地区分布饼图
        if report.get('region_distribution'):
            charts['region_pie'] = self.generate_region_pie(report['region_distribution'])
        
        # 热门别墅柱状图
        if report.get('top_villas'):
            villa_data = [
                {'name': v['name'], 'bookings': v['bookings']}
                for v in report['top_villas']
            ]
            charts['top_villas'] = self.generate_top_villas_bar(villa_data)
        
        return charts
    
    def generate_weekly_report_charts(self, report: Dict) -> Dict[str, bytes]:
        """生成周报表的图表组合"""
        charts = {}
        
        # 每日趋势
        if report.get('daily_trends'):
            charts['trend'] = self.generate_booking_trend(report['daily_trends'])
        
        # 地区分布
        if report.get('region_distribution'):
            charts['region_pie'] = self.generate_region_pie(report['region_distribution'])
            charts['region_bar'] = self.generate_region_bar(report['region_distribution'])
        
        return charts
    
    def generate_monthly_report_charts(self, report: Dict) -> Dict[str, bytes]:
        """生成月报表的图表组合"""
        charts = {}
        
        # 每日趋势
        if report.get('daily_trends'):
            charts['trend'] = self.generate_booking_trend(report['daily_trends'])
            charts['revenue_trend'] = self.generate_revenue_trend(report['daily_trends'])
        
        # 地区分布
        if report.get('region_distribution'):
            charts['region_pie'] = self.generate_region_pie(report['region_distribution'])
            charts['region_bar'] = self.generate_region_bar(report['region_distribution'])
            charts['revenue_bar'] = self.generate_revenue_bar(report['region_distribution'])
        
        return charts
    
    # ============ 保存图表到文件 ============
    
    def save_chart(self, chart_bytes: bytes, filename: str, output_dir: str = None) -> str:
        """保存图表到文件"""
        if not output_dir:
            output_dir = os.path.join(PROJECT_ROOT, 'charts')
        
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'wb') as f:
            f.write(chart_bytes)
        
        logger.info(f"📊 图表已保存: {filepath}")
        return filepath
    
    def save_report_charts(self, report_type: str, report: Dict, prefix: str = None) -> Dict[str, str]:
        """保存报表的所有图表"""
        if report_type == 'daily':
            charts = self.generate_daily_report_charts(report)
        elif report_type == 'weekly':
            charts = self.generate_weekly_report_charts(report)
        elif report_type == 'monthly':
            charts = self.generate_monthly_report_charts(report)
        else:
            charts = {}
        
        prefix = prefix or f"{report_type}_{report.get('date', report.get('date_range_display', '').replace('/', '-'))}"
        
        saved = {}
        for name, data in charts.items():
            filename = f"{prefix}_{name}.png"
            saved[name] = self.save_chart(data, filename)
        
        return saved


# ============ 命令行入口 ============
if __name__ == '__main__':
    import argparse
    import json
    
    # 导入report_generator
    from report_generator import ReportGenerator
    
    parser = argparse.ArgumentParser(description='生成别墅预订图表')
    parser.add_argument('--type', '-t', choices=['daily', 'weekly', 'monthly', 'all'],
                        default='daily', help='报表类型')
    parser.add_argument('--date', '-d', help='日期 (YYYY-MM-DD)')
    parser.add_argument('--output', '-o', help='输出目录')
    args = parser.parse_args()
    
    if not MATPLOTLIB_AVAILABLE:
        print("❌ 错误: matplotlib未安装，请运行: pip install matplotlib")
        sys.exit(1)
    
    generator = ReportGenerator()
    chart_gen = ChartGenerator()
    
    if args.date:
        report_date = datetime.strptime(args.date, '%Y-%m-%d').date()
    else:
        report_date = None
    
    # 生成指定类型的图表
    report_types = ['all'] if args.type == 'all' else [args.type]
    
    for rtype in report_types:
        if rtype == 'daily':
            report = generator.get_daily_report(report_date)
        elif rtype == 'weekly':
            report = generator.get_weekly_report(report_date)
        elif rtype == 'monthly':
            year = report_date.year if report_date else None
            month = report_date.month if report_date else None
            report = generator.get_monthly_report(year, month)
        else:
            continue
        
        print(f"\n📊 生成 {rtype} 报表图表...")
        saved = chart_gen.save_report_charts(rtype, report)
        for name, path in saved.items():
            print(f"  ✅ {name}: {path}")
    
    print("\n✨ 完成!")
