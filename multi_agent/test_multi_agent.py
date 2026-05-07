#!/usr/bin/env python3
"""
Multi-Agent System 测试脚本
验证Hub&Spoke架构的路由准确性
"""

import asyncio
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multi_agent import (
    router, 
    process_message, 
    get_router_status,
    MULTI_AGENT_ENABLED,
    AgentResponse,
    AgentType,
    IntentType
)


async def test_intent_routing():
    """测试意图路由"""
    print("=" * 60)
    print("🧪 Multi-Agent System 测试")
    print("=" * 60)
    print(f"\n📊 状态: {'✅ 已启用' if MULTI_AGENT_ENABLED else '❌ 已禁用'}")
    print(f"📋 模式: {get_router_status()}")
    print()
    
    test_cases = [
        # (用户消息, 预期意图)
        ("我想预订普吉岛的别墅", "booking"),
        ("有什么推荐的海景房吗", "booking"),
        ("计算一下5月1日到5月5日的房价", "booking"),
        
        ("入住当天怎么拿钥匙", "service"),
        ("房间空调不制冷怎么办", "service"),
        ("需要打扫服务怎么预约", "service"),
        ("我要投诉，服务太差了", "service"),
        ("帮我叫个去机场的车", "service"),
        
        ("普吉岛有什么好玩的地方", "info"),
        ("去曼谷怎么坐地铁", "info"),
        ("附近有什么好吃的餐厅", "info"),
        ("明天天气怎么样", "info"),
        
        ("支付方式有哪些", "payment"),
        ("取消预订能退款吗", "payment"),
        ("怎么开发票", "payment"),
        ("我的优惠券码怎么用", "payment"),
        ("查看我的积分", "payment"),
        
        ("你好啊", "unknown"),
        ("帮助", "unknown"),
    ]
    
    print("📝 意图路由测试")
    print("-" * 60)
    
    passed = 0
    failed = 0
    
    for message, expected_intent in test_cases:
        try:
            response = await process_message(
                user_id="test_user",
                username="test_user",
                message=message
            )
            
            actual_intent = response.intent.value
            status = "✅" if actual_intent == expected_intent else "⚠️"
            
            if actual_intent == expected_intent:
                passed += 1
            else:
                failed += 1
            
            print(f"{status} \"{message[:25]}...\"")
            print(f"   预期: {expected_intent} | 实际: {actual_intent}")
            
            # 显示部分回复
            if response.message:
                preview = response.message[:60].replace('\n', ' ')
                print(f"   回复: {preview}...")
            print()
            
        except Exception as e:
            print(f"❌ \"{message}\" - 错误: {e}")
            failed += 1
            print()
    
    print("-" * 60)
    print(f"📊 测试结果: {passed} 通过, {failed} 失败")
    print()


async def test_agent_responses():
    """测试各Agent的响应质量"""
    print("\n" + "=" * 60)
    print("📝 Agent响应质量测试")
    print("=" * 60)
    
    test_messages = [
        ("帮我推荐一个别墅", "booking"),
        ("WiFi连不上怎么办", "service"),
        ("芭提雅景点推荐", "info"),
        ("优惠券怎么用", "payment"),
    ]
    
    for message, _ in test_messages:
        print(f"\n📨 用户: \"{message}\"")
        print("-" * 40)
        
        response = await process_message(
            user_id="test_user",
            username="test_user",
            message=message
        )
        
        print(f"🎯 意图: {response.intent.value}")
        print(f"📤 来源: {response.source.value}")
        print(f"✅ 成功: {response.success}")
        print(f"\n💬 回复:\n{response.message[:200]}...")
        print()


async def test_context_passing():
    """测试上下文传递"""
    print("\n" + "=" * 60)
    print("🔄 上下文传递测试")
    print("=" * 60)
    
    # 第一轮对话
    response1 = await process_message(
        user_id="test_user",
        username="test_user",
        message="我想去普吉岛玩",
        active_region="普吉岛"
    )
    
    print(f"📨 第一轮: \"我想去普吉岛玩\"")
    print(f"   意图: {response1.intent.value}")
    print(f"   回复: {response1.message[:80]}...")
    
    # 第二轮对话 - 应该记住上下文
    response2 = await process_message(
        user_id="test_user",
        username="test_user",
        message="有什么好玩的",
        active_region="普吉岛"
    )
    
    print(f"\n📨 第二轮: \"有什么好玩的\"")
    print(f"   意图: {response2.intent.value}")
    print(f"   回复: {response2.message[:80]}...")


async def test_fallback():
    """测试降级机制"""
    print("\n" + "=" * 60)
    print("🛡️ 降级机制测试")
    print("=" * 60)
    
    if MULTI_AGENT_ENABLED:
        print("⚠️ Multi-Agent已启用，禁用后测试降级...")
        from multi_agent import disable_multi_agent, enable_multi_agent
        
        disable_multi_agent()
        response = await process_message(
            user_id="test_user",
            username="test_user",
            message="你好"
        )
        print(f"降级模式回复: {response.message[:100]}")
        
        enable_multi_agent()
        print("✅ 已恢复Multi-Agent模式")
    else:
        print("Multi-Agent未启用，跳过测试")


async def main():
    """运行所有测试"""
    print("\n🚀 启动Multi-Agent系统测试...\n")
    
    # 测试1: 意图路由
    await test_intent_routing()
    
    # 测试2: Agent响应质量
    await test_agent_responses()
    
    # 测试3: 上下文传递
    await test_context_passing()
    
    # 测试4: 降级机制
    await test_fallback()
    
    print("\n" + "=" * 60)
    print("✅ 测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    import os
    # 设置环境变量启用Multi-Agent进行测试
    os.environ["MULTI_AGENT_ENABLED"] = "true"
    
    # 重新导入以获取更新后的值
    from multi_agent import (
        router, 
        process_message, 
        get_router_status,
        MULTI_AGENT_ENABLED,
        AgentResponse,
        AgentType,
        IntentType,
        Coordinator
    )
    # 强制启用
    router.multi_agent_enabled = True
    router.coordinator = Coordinator()
    
    asyncio.run(main())
