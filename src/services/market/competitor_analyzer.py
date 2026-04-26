"""
竞品分析器 - Competitor Analyzer
用于泰国别墅租赁市场的竞品分析和价格策略
"""

import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional


@dataclass
class MarketData:
    """市场数据"""
    location: str           # 地点：芭提雅/曼谷/普吉岛
    bedroom_count: int      # 卧室数量
    avg_monthly_price: float  # 月均价格 (THB)
    avg_daily_price: float    # 日均价格 (THB)
    price_range_min: float    # 价格区间最小值
    price_range_max: float    # 价格区间最大值
    data_source: str         # 数据来源
    last_updated: str         # 最后更新时间


@dataclass
class PriceRecommendation:
    """价格建议"""
    location: str
    bedroom_count: int
    season: str              # 淡季/平季/旺季/高峰
    recommended_daily: float   # 建议日价 (THB)
    recommended_monthly: float # 建议月租 (THB)
    confidence: str          # 置信度：高/中/低
    reasoning: str            # 建议理由


class CompetitorAnalyzer:
    """竞品分析器"""
    
    # 泰国别墅市场基础数据 (基于网络调研)
    MARKET_DATA = {
        "芭提雅": {
            "2_bed": {
                "monthly": {"avg": 55000, "min": 30000, "max": 80000},
                "daily": {"avg": 2200, "min": 1500, "max": 3500},
            },
            "3_bed": {
                "monthly": {"avg": 75000, "min": 45000, "max": 120000},
                "daily": {"avg": 3000, "min": 2000, "max": 5000},
            },
            "4_bed": {
                "monthly": {"avg": 110000, "min": 70000, "max": 200000},
                "daily": {"avg": 4500, "min": 3000, "max": 8000},
            },
            "5_bed": {
                "monthly": {"avg": 150000, "min": 100000, "max": 300000},
                "daily": {"avg": 6000, "min": 4000, "max": 12000},
            },
        },
        "普吉岛": {
            "2_bed": {
                "monthly": {"avg": 90000, "min": 60000, "max": 150000},
                "daily": {"avg": 3500, "min": 2500, "max": 6000},
            },
            "3_bed": {
                "monthly": {"avg": 130000, "min": 80000, "max": 250000},
                "daily": {"avg": 5000, "min": 3500, "max": 10000},
            },
            "4_bed": {
                "monthly": {"avg": 180000, "min": 120000, "max": 400000},
                "daily": {"avg": 7500, "min": 5000, "max": 15000},
            },
            "5_bed": {
                "monthly": {"avg": 280000, "min": 180000, "max": 600000},
                "daily": {"avg": 12000, "min": 8000, "max": 25000},
            },
        },
        "曼谷": {
            "2_bed": {
                "monthly": {"avg": 45000, "min": 25000, "max": 80000},
                "daily": {"avg": 1800, "min": 1200, "max": 3500},
            },
            "3_bed": {
                "monthly": {"avg": 70000, "min": 40000, "max": 150000},
                "daily": {"avg": 2800, "min": 1800, "max": 6000},
            },
            "4_bed": {
                "monthly": {"avg": 120000, "min": 80000, "max": 250000},
                "daily": {"avg": 5000, "min": 3500, "max": 10000},
            },
            "5_bed": {
                "monthly": {"avg": 200000, "min": 120000, "max": 500000},
                "daily": {"avg": 8500, "min": 6000, "max": 18000},
            },
        },
    }
    
    # 淡旺季价格系数
    SEASONAL_COEFFICIENTS = {
        "淡季": {      # 5月-10月
            "pattaya": 0.75,
            "phuket": 0.70,
            "bangkok": 0.85,
        },
        "平季": {      # 3月-4月, 11月
            "pattaya": 1.00,
            "phuket": 0.95,
            "bangkok": 1.00,
        },
        "旺季": {      # 12月-2月
            "pattaya": 1.30,
            "phuket": 1.25,
            "bangkok": 1.15,
        },
        "高峰": {      # 圣诞/新年/中国春节
            "pattaya": 1.60,
            "phuket": 1.55,
            "bangkok": 1.40,
        },
    }
    
    def __init__(self):
        self.last_analysis = None
        
    def get_market_data(self, location: str, bedroom_count: int) -> MarketData:
        """获取市场数据"""
        location_map = {
            "芭提雅": "芭提雅",
            "pattaya": "芭提雅",
            "phuket": "普吉岛",
            "普吉岛": "普吉岛",
            "bangkok": "曼谷",
            "曼谷": "曼谷",
        }
        
        loc = location_map.get(location.lower(), location)
        bed_key = f"{bedroom_count}_bed"
        
        if loc not in self.MARKET_DATA or bed_key not in self.MARKET_DATA[loc]:
            raise ValueError(f"Unsupported location/bedroom: {location}/{bedroom_count}")
            
        data = self.MARKET_DATA[loc][bed_key]
        
        return MarketData(
            location=loc,
            bedroom_count=bedroom_count,
            avg_monthly_price=data["monthly"]["avg"],
            avg_daily_price=data["daily"]["avg"],
            price_range_min=data["monthly"]["min"],
            price_range_max=data["monthly"]["max"],
            data_source="Market Research 2024-2025",
            last_updated=datetime.now().strftime("%Y-%m-%d"),
        )
    
    def get_current_season(self) -> str:
        """获取当前季节"""
        month = datetime.now().month
        
        if month in [12, 1, 2]:
            return "旺季"
        elif month in [3, 4, 11]:
            return "平季"
        elif month in [5, 6, 7, 8, 9, 10]:
            return "淡季"
        return "平季"
    
    def get_seasonal_price(
        self, 
        location: str, 
        bedroom_count: int, 
        season: Optional[str] = None
    ) -> dict:
        """计算季节性价格"""
        market = self.get_market_data(location, bedroom_count)
        if season is None:
            season = self.get_current_season()
            
        # 使用地点标识符（处理大小写）
        loc_key = location.lower()
        # 匹配关键词
        loc_map = {
            "芭提雅": "pattaya", "pattaya": "pattaya",
            "普吉岛": "phuket", "phuket": "phuket",
            "曼谷": "bangkok", "bangkok": "bangkok",
        }
        loc_id = loc_map.get(loc_key, loc_key)
        
        # 获取季节系数
        seasonal_coefs = self.SEASONAL_COEFFICIENTS.get(season, {})
        coef = seasonal_coefs.get(loc_id, 1.0)
        
        return {
            "season": season,
            "daily_price": round(market.avg_daily_price * coef),
            "monthly_price": round(market.avg_monthly_price * coef),
            "coefficient": coef,
            "base_daily": market.avg_daily_price,
            "base_monthly": market.avg_monthly_price,
        }
    
    def recommend_price(
        self,
        location: str,
        bedroom_count: int,
        amenity_level: str = "standard",  # standard, premium, luxury
        target_occupancy: float = 0.70,
    ) -> PriceRecommendation:
        """
        生成价格建议
        
        Args:
            location: 地点
            bedroom_count: 卧室数量
            amenity_level: 设施水平 (standard/premium/luxury)
            target_occupancy: 目标入住率
        """
        season = self.get_current_season()
        seasonal_price = self.get_seasonal_price(location, bedroom_count, season)
        
        # 设施水平调整系数
        amenity_coef = {
            "standard": 1.0,
            "premium": 1.25,
            "luxury": 1.60,
        }
        
        amenity_adj = amenity_coef.get(amenity_level, 1.0)
        
        # 基础价格（取市场均值）
        base_daily = seasonal_price["base_daily"]
        base_monthly = seasonal_price["base_monthly"]
        
        # 考虑设施水平
        recommended_daily = round(base_daily * seasonal_price["coefficient"] * amenity_adj)
        recommended_monthly = round(base_monthly * seasonal_price["coefficient"] * amenity_adj)
        
        # 置信度判断
        if target_occupancy >= 0.75:
            confidence = "高"
        elif target_occupancy >= 0.55:
            confidence = "中"
        else:
            confidence = "低"
        
        reasoning = (
            f"基于{location}{bedroom_count}卧别墅市场数据，"
            f"当前为{season}，市场均价约{base_monthly:,} THB/月。"
            f"结合{amenity_level}设施定位，建议定价为"
            f"{recommended_daily:,} THB/天 或 {recommended_monthly:,} THB/月，"
            f"预期入住率{target_occupancy*100:.0f}%。"
        )
        
        return PriceRecommendation(
            location=location,
            bedroom_count=bedroom_count,
            season=season,
            recommended_daily=recommended_daily,
            recommended_monthly=recommended_monthly,
            confidence=confidence,
            reasoning=reasoning,
        )
    
    def compare_competitors(self, location: str, bedroom_count: int) -> dict:
        """竞品对比分析"""
        market = self.get_market_data(location, bedroom_count)
        recommendations = {}
        
        for season in ["淡季", "平季", "旺季", "高峰"]:
            rec = self.recommend_price(location, bedroom_count, "premium", 0.70)
            price_data = self.get_seasonal_price(location, bedroom_count, season)
            recommendations[season] = {
                "daily_price": price_data["daily_price"],
                "monthly_price": price_data["monthly_price"],
                "coef": price_data["coefficient"],
            }
        
        return {
            "location": location,
            "bedroom_count": bedroom_count,
            "market_avg": {
                "daily": market.avg_daily_price,
                "monthly": market.avg_monthly_price,
            },
            "market_range": {
                "min": market.price_range_min,
                "max": market.price_range_max,
            },
            "seasonal_prices": recommendations,
            "last_updated": market.last_updated,
        }
    
    def generate_report(
        self,
        locations: list = None,
        bedroom_counts: list = None,
    ) -> dict:
        """生成完整分析报告"""
        if locations is None:
            locations = ["芭提雅", "普吉岛", "曼谷"]
        if bedroom_counts is None:
            bedroom_counts = [3, 4, 5]
            
        report = {
            "report_title": "泰国别墅租赁市场竞品分析报告",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "current_season": self.get_current_season(),
            "market_overview": {
                "芭提雅": {
                    "description": "成熟的海滨度假市场，夜生活丰富，价格相对亲民",
                    "avg_3bed_monthly": "75,000 THB",
                    "avg_4bed_monthly": "110,000 THB",
                    "avg_5bed_monthly": "150,000 THB",
                },
                "普吉岛": {
                    "description": "高端海岛度假市场，国际游客多，价格最高",
                    "avg_3bed_monthly": "130,000 THB",
                    "avg_4bed_monthly": "180,000 THB",
                    "avg_5bed_monthly": "280,000 THB",
                },
                "曼谷": {
                    "description": "城市商务休闲市场，短租需求大，季节波动小",
                    "avg_3bed_monthly": "70,000 THB",
                    "avg_4bed_monthly": "120,000 THB",
                    "avg_5bed_monthly": "200,000 THB",
                },
            },
            "seasonal_analysis": {
                "淡季": {
                    "months": "5月-10月",
                    "price_adjustment": "-20% to -30%",
                    "tips": "适合长租推广，家庭客群营销",
                },
                "平季": {
                    "months": "3月-4月, 11月",
                    "price_adjustment": "0% to +5%",
                    "tips": "提前布局节假日促销",
                },
                "旺季": {
                    "months": "12月-2月",
                    "price_adjustment": "+25% to +35%",
                    "tips": "适当提高价格，减少长租优惠",
                },
                "高峰": {
                    "months": "圣诞/新年/中国春节",
                    "price_adjustment": "+50% to +60%",
                    "tips": "最大化收益，设置最短入住天数",
                },
            },
            "detailed_analysis": [],
        }
        
        # 添加详细分析
        for loc in locations:
            for beds in bedroom_counts:
                try:
                    analysis = self.compare_competitors(loc, beds)
                    report["detailed_analysis"].append(analysis)
                except ValueError:
                    continue
                    
        self.last_analysis = report
        return report
    
    def export_to_markdown(self, report: dict = None) -> str:
        """导出为Markdown格式"""
        if report is None:
            report = self.last_analysis or self.generate_report()
            
        md = f"""# {report['report_title']}

> 生成时间: {report['generated_at']}
> 当前季节: {report['current_season']}

## 市场概览

| 地点 | 市场特点 | 3卧均价/月 | 4卧均价/月 | 5卧均价/月 |
|------|----------|-----------|-----------|-----------|
| **芭提雅** | 成熟海滨度假市场，价格亲民 | {report['market_overview']['芭提雅']['avg_3bed_monthly']} | {report['market_overview']['芭提雅']['avg_4bed_monthly']} | {report['market_overview']['芭提雅']['avg_5bed_monthly']} |
| **普吉岛** | 高端海岛度假，国际游客多 | {report['market_overview']['普吉岛']['avg_3bed_monthly']} | {report['market_overview']['普吉岛']['avg_4bed_monthly']} | {report['market_overview']['普吉岛']['avg_5bed_monthly']} |
| **曼谷** | 城市商务休闲，短租需求大 | {report['market_overview']['曼谷']['avg_3bed_monthly']} | {report['market_overview']['曼谷']['avg_4bed_monthly']} | {report['market_overview']['曼谷']['avg_5bed_monthly']} |

## 季节性分析

| 季节 | 月份 | 价格调整 | 运营建议 |
|------|------|---------|---------|
| **淡季** | 5月-10月 | {report['seasonal_analysis']['淡季']['price_adjustment']} | {report['seasonal_analysis']['淡季']['tips']} |
| **平季** | 3月-4月, 11月 | {report['seasonal_analysis']['平季']['price_adjustment']} | {report['seasonal_analysis']['平季']['tips']} |
| **旺季** | 12月-2月 | {report['seasonal_analysis']['旺季']['price_adjustment']} | {report['seasonal_analysis']['旺季']['tips']} |
| **高峰** | 圣诞/新年/春节 | {report['seasonal_analysis']['高峰']['price_adjustment']} | {report['seasonal_analysis']['高峰']['tips']} |

## 详细竞品分析

"""
        
        for analysis in report.get("detailed_analysis", []):
            md += f"""### {analysis['location']} - {analysis['bedroom_count']}卧别墅

**市场均价**
- 日均: {analysis['market_avg']['daily']:,} THB
- 月均: {analysis['market_avg']['monthly']:,} THB

**价格区间**: {analysis['market_range']['min']:,} - {analysis['market_range']['max']:,} THB/月

**季节性价格表**

| 季节 | 日价 (THB) | 月租 (THB) | 系数 |
|------|-----------|-----------|------|
"""
            for season, prices in analysis["seasonal_prices"].items():
                md += f"| {season} | {prices['daily_price']:,} | {prices['monthly_price']:,} | x{prices['coef']:.2f} |\n"
            
            md += "\n"
            
        return md


def main():
    """主函数 - 演示用法"""
    analyzer = CompetitorAnalyzer()
    
    # 生成完整报告
    report = analyzer.generate_report()
    
    # 导出为Markdown
    md_report = analyzer.export_to_markdown(report)
    
    # 保存报告
    with open("竞品分析报告.md", "w", encoding="utf-8") as f:
        f.write(md_report)
    
    print("报告已生成: 竞品分析报告.md")
    
    # 单项价格建议示例
    print("\n=== 价格建议示例 ===")
    rec = analyzer.recommend_price("普吉岛", 4, "premium", 0.75)
    print(f"地点: {rec.location}")
    print(f"房型: {rec.bedroom_count}卧")
    print(f"季节: {rec.season}")
    print(f"建议日价: {rec.recommended_daily:,} THB")
    print(f"建议月租: {rec.recommended_monthly:,} THB")
    print(f"置信度: {rec.confidence}")
    print(f"理由: {rec.reasoning}")


if __name__ == "__main__":
    main()
