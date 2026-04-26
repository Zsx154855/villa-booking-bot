#!/usr/bin/env python3
"""
竞品分析使用示例
Usage examples for CompetitorAnalyzer
"""

from src.services.market import CompetitorAnalyzer, MarketData, PriceRecommendation


def example_basic_usage():
    """基本用法示例"""
    analyzer = CompetitorAnalyzer()
    
    # 获取市场数据
    data = analyzer.get_market_data("普吉岛", 4)
    print(f"地点: {data.location}")
    print(f"房型: {data.bedroom_count}卧")
    print(f"月均价格: {data.avg_monthly_price:,} THB")
    print(f"日均价格: {data.avg_daily_price:,} THB")
    print()


def example_seasonal_price():
    """季节性价格计算"""
    analyzer = CompetitorAnalyzer()
    
    for season in ["淡季", "平季", "旺季", "高峰"]:
        price = analyzer.get_seasonal_price("芭提雅", 4, season)
        print(f"[{season}] 日价: {price['daily_price']:,} THB, "
              f"月租: {price['monthly_price']:,} THB (系数: x{price['coefficient']:.2f})")


def example_price_recommendation():
    """价格建议生成"""
    analyzer = CompetitorAnalyzer()
    
    # 获取当前季节推荐
    rec = analyzer.recommend_price(
        location="普吉岛",
        bedroom_count=4,
        amenity_level="premium",
        target_occupancy=0.75
    )
    
    print(f"=== 价格建议 ===")
    print(f"地点: {rec.location}")
    print(f"房型: {rec.bedroom_count}卧")
    print(f"季节: {rec.season}")
    print(f"建议日价: {rec.recommended_daily:,} THB")
    print(f"建议月租: {rec.recommended_monthly:,} THB")
    print(f"置信度: {rec.confidence}")
    print(f"理由: {rec.reasoning}")
    print()


def example_competitor_comparison():
    """竞品对比"""
    analyzer = CompetitorAnalyzer()
    
    comparison = analyzer.compare_competitors("普吉岛", 4)
    
    print(f"=== 竞品对比: {comparison['location']} {comparison['bedroom_count']}卧 ===")
    print(f"市场均价: {comparison['market_avg']['daily']:,} THB/天, "
          f"{comparison['market_avg']['monthly']:,} THB/月")
    print(f"价格区间: {comparison['market_range']['min']:,} - "
          f"{comparison['market_range']['max']:,} THB/月")
    print("\n季节性价格:")
    for season, prices in comparison["seasonal_prices"].items():
        print(f"  {season}: {prices['daily_price']:,} THB/天 | "
              f"{prices['monthly_price']:,} THB/月 (x{prices['coef']:.2f})")
    print()


def example_generate_report():
    """生成完整报告"""
    analyzer = CompetitorAnalyzer()
    
    # 生成报告
    report = analyzer.generate_report(
        locations=["芭提雅", "普吉岛", "曼谷"],
        bedroom_counts=[3, 4, 5]
    )
    
    # 导出Markdown
    md_report = analyzer.export_to_markdown(report)
    
    # 保存
    with open("竞品分析报告.md", "w", encoding="utf-8") as f:
        f.write(md_report)
    
    print("✅ 报告已生成: 竞品分析报告.md")
    print(f"📊 分析了 {len(report['detailed_analysis'])} 个房型组合")
    print(f"🌡️ 当前季节: {report['current_season']}")


def example_multi_location_comparison():
    """多地点对比"""
    analyzer = CompetitorAnalyzer()
    bedrooms = [3, 4, 5]
    
    print("\n" + "="*80)
    print("多地点价格对比表 (月租, THB)")
    print("="*80)
    print(f"{'房型':<6}", end="")
    
    for loc in ["芭提雅", "普吉岛", "曼谷"]:
        print(f"{loc:<10}", end="")
    print()
    print("-"*50)
    
    for beds in bedrooms:
        print(f"{beds}卧", end="")
        for loc in ["芭提雅", "普吉岛", "曼谷"]:
            data = analyzer.get_market_data(loc, beds)
            print(f"{data.avg_monthly_price:>10,}", end="")
        print()


if __name__ == "__main__":
    print("=" * 60)
    print("竞品分析器使用示例")
    print("=" * 60)
    
    example_basic_usage()
    example_seasonal_price()
    print()
    example_price_recommendation()
    example_competitor_comparison()
    example_multi_location_comparison()
    print()
    example_generate_report()
