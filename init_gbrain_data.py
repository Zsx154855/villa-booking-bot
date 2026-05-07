#!/usr/bin/env python3
"""
GBrain初始化脚本
初始化14套别墅数据到持久化存储
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gbrain_integration import gbrain_integration, brain_repo
import database


# 14套别墅完整数据
VILLAS_DATA = [
    {
        "id": "Pattaya-001",
        "name": "珊瑚海景别墅",
        "region": "芭提雅",
        "type": "海景别墅",
        "price_per_night": 3500,
        "max_guests": 6,
        "bedrooms": 3,
        "bathrooms": 3,
        "amenities": ["私人泳池", "海景", "厨房", "WiFi", "停车场", "管家服务", "早餐"],
        "description": "位于芭提雅中天海滩，180度海景，三层现代风格，每间卧室均可看海。",
        "images": [],
        "rating": 4.8
    },
    {
        "id": "Pattaya-002",
        "name": "热带风情别墅",
        "region": "芭提雅",
        "type": "花园别墅",
        "price_per_night": 2800,
        "max_guests": 8,
        "bedrooms": 4,
        "bathrooms": 4,
        "amenities": ["私人泳池", "热带花园", "厨房", "WiFi", "停车场", "BBQ设施"],
        "description": "坐落于热带花园中，远离喧嚣，适合家庭聚会和朋友派对。",
        "images": [],
        "rating": 4.7
    },
    {
        "id": "Pattaya-003",
        "name": "铂金尊享别墅",
        "region": "芭提雅",
        "type": "豪华别墅",
        "price_per_night": 5500,
        "max_guests": 10,
        "bedrooms": 5,
        "bathrooms": 5,
        "amenities": ["私人泳池", "海景", "KTV", "厨房", "WiFi", "停车场", "管家服务", "按摩池", "健身房"],
        "description": "顶级豪华配置，私人影院、KTV包房，适合高端商务接待和奢华度假。",
        "images": [],
        "rating": 4.9
    },
    {
        "id": "Pattaya-004",
        "name": "珍珠海岸别墅",
        "region": "芭提雅",
        "type": "海滨别墅",
        "price_per_night": 4200,
        "max_guests": 8,
        "bedrooms": 4,
        "bathrooms": 4,
        "amenities": ["私人海滩", "泳池", "海景", "厨房", "WiFi", "停车场", "皮划艇"],
        "description": "拥有私人海滩入口，出门即沙滩，是海滨度假的绝佳选择。",
        "images": [],
        "rating": 4.8
    },
    {
        "id": "Bangkok-001",
        "name": "曼谷天际公寓",
        "region": "曼谷",
        "type": "高层公寓",
        "price_per_night": 2200,
        "max_guests": 4,
        "bedrooms": 2,
        "bathrooms": 2,
        "amenities": ["城市景观", "健身房", "游泳池", "WiFi", "停车场", "便利店"],
        "description": "位于曼谷素坤逸路核心区，俯瞰城市天际线，交通便利。",
        "images": [],
        "rating": 4.6
    },
    {
        "id": "Bangkok-002",
        "name": "湄南河畔别墅",
        "region": "曼谷",
        "type": "河景别墅",
        "price_per_night": 4800,
        "max_guests": 8,
        "bedrooms": 4,
        "bathrooms": 4,
        "amenities": ["河景", "私人码头", "厨房", "WiFi", "停车场", "管家服务", "早餐"],
        "description": "坐落于湄南河畔，拥有私人码头，可乘船直达大皇宫和唐人街。",
        "images": [],
        "rating": 4.9
    },
    {
        "id": "Bangkok-003",
        "name": "暹罗广场名邸",
        "region": "曼谷",
        "type": "市中心公寓",
        "price_per_night": 2600,
        "max_guests": 4,
        "bedrooms": 2,
        "bathrooms": 2,
        "amenities": ["购物中心", "地铁站", "WiFi", "健身房", "天台泳池"],
        "description": "步行5分钟可达暹罗广场，购物、餐饮、娱乐一应俱全。",
        "images": [],
        "rating": 4.5
    },
    {
        "id": "Bangkok-004",
        "name": "考山路风情屋",
        "region": "曼谷",
        "type": "特色民宿",
        "price_per_night": 1500,
        "max_guests": 4,
        "bedrooms": 2,
        "bathrooms": 1,
        "amenities": ["WiFi", "空调", "厨房", "阳台", "旅游咨询"],
        "description": "位于考山路附近，体验地道曼谷背包客文化。",
        "images": [],
        "rating": 4.4
    },
    {
        "id": "Phuket-001",
        "name": "安达曼海景别墅",
        "region": "普吉岛",
        "type": "海景别墅",
        "price_per_night": 5800,
        "max_guests": 10,
        "bedrooms": 5,
        "bathrooms": 5,
        "amenities": ["私人泳池", "海景", "厨房", "WiFi", "停车场", "管家服务", "机场接送", "按摩池"],
        "description": "位于普吉岛西海岸，日落绝佳观景点，私人管家全程服务。",
        "images": [],
        "rating": 4.9
    },
    {
        "id": "Phuket-002",
        "name": "苏林海滩别墅",
        "region": "普吉岛",
        "type": "海滨别墅",
        "price_per_night": 4500,
        "max_guests": 8,
        "bedrooms": 4,
        "bathrooms": 4,
        "amenities": ["私人海滩", "泳池", "海景", "厨房", "WiFi", "停车场", "浮潜装备"],
        "description": "苏林海滩的私密别墅，沙滩细腻，海水清澈，适合潜水爱好者。",
        "images": [],
        "rating": 4.8
    },
    {
        "id": "Phuket-003",
        "name": "卡塔岩石别墅",
        "region": "普吉岛",
        "type": "悬崖别墅",
        "price_per_night": 6500,
        "max_guests": 8,
        "bedrooms": 4,
        "bathrooms": 4,
        "amenities": ["悬崖海景", "无边泳池", "厨房", "WiFi", "停车场", "管家服务", "SPA"],
        "description": "建在悬崖之上，无边泳池与大海融为一体，极致私密体验。",
        "images": [],
        "rating": 5.0
    },
    {
        "id": "Phuket-004",
        "name": "普吉镇花园洋房",
        "region": "普吉岛",
        "type": "花园洋房",
        "price_per_night": 2200,
        "max_guests": 6,
        "bedrooms": 3,
        "bathrooms": 2,
        "amenities": ["热带花园", "厨房", "WiFi", "停车场", "自行车"],
        "description": "位于普吉镇老街附近，体验当地文化与传统美食的理想之选。",
        "images": [],
        "rating": 4.6
    },
    {
        "id": "Phuket-005",
        "name": "拉扬私人庄园",
        "region": "普吉岛",
        "type": "庄园别墅",
        "price_per_night": 12000,
        "max_guests": 16,
        "bedrooms": 8,
        "bathrooms": 8,
        "amenities": ["私人泳池", "海景", "网球场", "KTV", "厨房", "WiFi", "停车场", "管家团队", "健身房", "酒窖"],
        "description": "普吉岛顶级私人庄园，适合大型家庭聚会、公司团建和婚礼派对。",
        "images": [],
        "rating": 4.9
    },
    {
        "id": "Phuket-006",
        "name": "奈函日落别墅",
        "region": "普吉岛",
        "type": "海景别墅",
        "price_per_night": 3800,
        "max_guests": 6,
        "bedrooms": 3,
        "bathrooms": 3,
        "amenities": ["日落海景", "私人泳池", "厨房", "WiFi", "停车场", "露台"],
        "description": "奈函海滩的精品别墅，以日落美景著称，氛围浪漫温馨。",
        "images": [],
        "rating": 4.7
    }
]


def main():
    """主函数"""
    print("=" * 50)
    print("GBrain别墅数据初始化")
    print("=" * 50)
    
    # 初始化数据库
    print("\n📦 初始化数据库...")
    try:
        database.init_db()
        print("✅ 数据库初始化完成")
    except Exception as e:
        print(f"⚠️ 数据库初始化: {e}")
    
    # 从数据库获取别墅数据
    print("\n📊 获取别墅数据...")
    try:
        db_villas = database.get_all_villas()
        if db_villas and len(db_villas) >= 14:
            print(f"✅ 从数据库获取到 {len(db_villas)} 套别墅")
            villas = db_villas
        else:
            print(f"⚠️ 数据库仅有 {len(db_villas) if db_villas else 0} 套，使用内置数据")
            villas = VILLAS_DATA
    except Exception as e:
        print(f"⚠️ 数据库查询失败: {e}，使用内置数据")
        villas = VILLAS_DATA
    
    # 初始化GBrain
    print("\n🧠 初始化GBrain持久化...")
    success = gbrain_integration.initialize(villas)
    
    if success:
        print("✅ GBrain初始化成功")
        
        # 统计
        stats = gbrain_integration.get_stats()
        print("\n📈 存储统计:")
        print(f"   - 记忆数量: {stats.get('memory_count', 'N/A')}")
        print(f"   - 别墅数量: {stats.get('villa_count', 'N/A')}")
        print(f"   - 用户数量: {stats.get('user_count', 'N/A')}")
        print(f"   - 预订数量: {stats.get('booking_count', 'N/A')}")
        print(f"   - Brain Repo条目: {stats.get('brain_repo_entries', 'N/A')}")
    else:
        print("❌ GBrain初始化失败")
        return 1
    
    # 同步到GitHub（如果可用）
    print("\n📤 同步到GitHub...")
    try:
        sync_stats = gbrain_integration.brain_repo.sync_all_to_github()
        if sync_stats.get('success', 0) > 0:
            print(f"✅ 已同步 {sync_stats['success']} 个条目到GitHub")
        else:
            print("⚠️ GitHub同步未执行（Token未配置或不可用）")
    except Exception as e:
        print(f"⚠️ GitHub同步失败: {e}")
    
    print("\n" + "=" * 50)
    print("初始化完成！")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    sys.exit(main())
