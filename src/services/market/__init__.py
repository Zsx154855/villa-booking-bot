"""
Market Analysis Module for Villa Rental Business
别墅租赁市场分析模块

包含功能：
- 竞品价格监控
- 市场趋势分析
- 淡旺季价格策略
- 报告生成
"""

from .competitor_analyzer import CompetitorAnalyzer, MarketData, PriceRecommendation

__all__ = [
    "CompetitorAnalyzer",
    "MarketData", 
    "PriceRecommendation",
]
