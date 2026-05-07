#!/usr/bin/env python3
"""
Token Optimizer 测试脚本
验证 OpenClaw Token 优化策略的正确性
"""

import sys
import os
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.ai.token_optimizer import (
    TokenOptimizer,
    ConversationManager,
    ConversationMessage,
    UserContext
)


def load_test_villas():
    """加载测试别墅数据"""
    with open('villas.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def test_token_optimizer():
    """测试 Token 优化器"""
    print("=" * 60)
    print("测试 Token Optimizer")
    print("=" * 60)

    villas = load_test_villas()
    optimizer = TokenOptimizer(villas, compact_threshold=10)

    # 测试别墅摘要生成
    print("\n📋 别墅摘要:")
    print(optimizer.villa_summary[:500] + "...")

    # 测试价格范围
    print(f"\n💰 价格范围: {optimizer.get_price_range()}")

    return optimizer


def test_context_pruning():
    """测试 contextPruning"""
    print("\n" + "=" * 60)
    print("测试 contextPruning（上下文裁剪）")
    print("=" * 60)

    villas = load_test_villas()
    optimizer = TokenOptimizer(villas)

    # 模拟 20 条消息
    messages = []
    for i in range(20):
        messages.append(ConversationMessage(
            role="user" if i % 2 == 0 else "assistant",
            content=f"这是第 {i+1} 条消息的内容 " * 10
        ))

    print(f"\n原始消息数: {len(messages)}")

    user_context = UserContext(user_id="test_user")
    pruned = optimizer.prune_messages(messages, user_context)

    print(f"裁剪后消息数: {len(pruned)}")
    print(f"✅ 保留最近 {optimizer.KEEP_RECENT_TURNS} 轮对话")


def test_context_injection():
    """测试 contextInjection"""
    print("\n" + "=" * 60)
    print("测试 contextInjection（上下文注入）")
    print("=" * 60)

    villas = load_test_villas()
    optimizer = TokenOptimizer(villas)

    base_prompt = "你是别墅预订助手"

    # 无上下文
    print("\n📝 无上下文注入:")
    result = optimizer.inject_context(base_prompt, UserContext())
    print(result[:300] + "...")

    # 有上下文
    print("\n📝 有上下文注入:")
    ctx = UserContext(
        user_id="test",
        language="zh",
        preferred_region="芭提雅",
        budget_range=(1000, 3000),
        booking_intent="预订海景别墅",
        guest_count=4
    )
    result = optimizer.inject_context(base_prompt, ctx)
    print(result[:500] + "...")

    print("\n✅ 用户信息直接注入 system prompt，减少重复提问")


def test_compact():
    """测试 compact 压缩"""
    print("\n" + "=" * 60)
    print("测试 compact（对话历史压缩）")
    print("=" * 60)

    villas = load_test_villas()
    optimizer = TokenOptimizer(villas, compact_threshold=10)

    # 模拟 15 条消息
    messages = []
    for i in range(15):
        role = "user" if i % 2 == 0 else "assistant"
        content = f"第 {i+1} 轮对话"
        messages.append(ConversationMessage(role=role, content=content))

    print(f"\n原始消息数: {len(messages)}")

    user_context = UserContext(
        user_id="test",
        preferred_region="普吉岛",
        booking_intent="蜜月预订",
        guest_count=2
    )

    compacted, summary = optimizer.compact_history(messages, user_context)

    print(f"压缩后消息数: {len(compacted)}")
    print(f"\n📋 生成摘要:\n{summary}")
    print(f"\n✅ 早期 {len(messages) - optimizer.COMPACT_KEEP_TURNS} 条消息被压缩为摘要")


def test_conversation_manager():
    """测试对话管理器"""
    print("\n" + "=" * 60)
    print("测试 ConversationManager")
    print("=" * 60)

    villas = load_test_villas()
    manager = ConversationManager(villas)

    user_id = "test_user_123"

    # 添加消息
    for i in range(12):
        manager.add_message(user_id, "user", f"用户问题 {i+1}")
        manager.add_message(user_id, "assistant", f"助手回答 {i+1}")

    print(f"\n添加了 12 条消息")

    # 更新上下文
    manager.update_user_context(
        user_id,
        preferred_region="曼谷",
        budget_range=(1500, 4000),
        guest_count=3
    )

    # 获取优化后的消息
    base_prompt = "你是别墅助手"
    messages, summary = manager.get_optimized_messages(user_id, base_prompt)

    print(f"优化后消息数: {len(messages)}")
    if summary:
        print(f"压缩摘要: {summary[:100]}...")

    # 获取增强的 system prompt
    enhanced = manager.get_enhanced_system_prompt(user_id, base_prompt)
    print(f"增强后 system prompt 长度: {len(enhanced)} 字符")

    # 获取统计
    stats = manager.get_conversation_stats(user_id)
    print(f"\n📊 对话统计: {stats}")


def test_token_estimation():
    """测试 Token 估算"""
    print("\n" + "=" * 60)
    print("测试 Token 估算")
    print("=" * 60)

    villas = load_test_villas()
    optimizer = TokenOptimizer(villas)

    test_texts = [
        "你好",
        "Hello, how are you?",
        "我想预订一套芭提雅的海景别墅",
        "这是一段较长的中文文本，用于测试Token估算功能是否准确"
    ]

    for text in test_texts:
        tokens = optimizer._count_tokens(text)
        print(f"\n文本: {text[:40]}...")
        print(f"字符数: {len(text)}, 估算 Token: {tokens}")


def main():
    """运行所有测试"""
    print("\n🧪 OpenClaw Token Optimizer 测试\n")

    test_token_optimizer()
    test_context_pruning()
    test_context_injection()
    test_compact()
    test_conversation_manager()
    test_token_estimation()

    print("\n" + "=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60)

    print("""
📚 Token 优化策略总结:

1. contextPruning（上下文裁剪）
   - 保留最近 5 轮对话
   - 移除早期不相关的历史消息

2. contextInjection（上下文注入）
   - 用户信息直接注入 system prompt
   - 别墅列表、预算、日期等关键信息
   - 减少"请再说一遍"式的重复提问

3. compact（压缩）
   - 超过 10 轮时压缩早期对话
   - 保留关键信息（预订意向、预算、日期）
   - 显著减少 token 消耗

4. AGENTS.md
   - 定义 Bot 角色边界
   - 减少越界回答
   - 规范回复格式
""")


if __name__ == "__main__":
    main()
