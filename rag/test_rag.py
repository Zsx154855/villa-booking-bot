#!/usr/bin/env python3
"""
RAG System Test Script
测试RAG系统
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag import get_rag_system, get_knowledge_base


def test_knowledge_base():
    """测试知识库加载"""
    print("=" * 60)
    print("测试1: 知识库加载")
    print("=" * 60)
    
    kb = get_knowledge_base()
    
    print(f"✅ 别墅数量: {len(kb._villas)}")
    print(f"✅ FAQ数量: {len(kb._faq)}")
    print(f"✅ 指南数量: {len(kb._guides)}")
    print(f"✅ 周边攻略: {len(kb._nearby)}")
    
    # 显示别墅列表
    print("\n别墅列表:")
    for v in kb._villas[:3]:
        print(f"  - {v['id']}: {v['name']} ({v['region']}) - ฿{v['price_per_night']}/晚")
    
    return True


def test_rag_system():
    """测试RAG系统"""
    print("\n" + "=" * 60)
    print("测试2: RAG系统初始化")
    print("=" * 60)
    
    rag = get_rag_system()
    
    print(f"✅ RAG系统阈值: {rag.confidence_threshold}")
    print(f"✅ Retriever阈值: {rag.retriever.confidence_threshold}")
    
    return True


def test_retrieval():
    """测试检索功能"""
    print("\n" + "=" * 60)
    print("测试3: 检索功能")
    print("=" * 60)
    
    rag = get_rag_system()
    
    # 测试不同类型的查询
    test_queries = [
        ("普吉岛", None),
        ("押金", "faq"),
        ("普吉岛", "nearby")
    ]
    
    for query, doc_type in test_queries:
        print(f"\n📝 查询: {query}")
        if doc_type:
            print(f"   类型: {doc_type}")
        
        if doc_type == "faq":
            results = rag.retriever.retrieve_faq(query)
        elif doc_type == "nearby":
            results = rag.retriever.retrieve_nearby(query)
        else:
            results = rag.retriever.retrieve(query)
        
        print(f"   找到 {len(results)} 条结果")
        
        for i, r in enumerate(results[:2], 1):
            print(f"   {i}. [{r['doc_type']}] {r['source']}")
            print(f"      相关度: {r['relevance_score']:.2f}")
    
    return True


def test_generation():
    """测试答案生成"""
    print("\n" + "=" * 60)
    print("测试4: 答案生成")
    print("=" * 60)
    
    rag = get_rag_system()
    
    # 测试查询
    test_queries = [
        "普吉岛有什么好玩的？",
        "预订需要押金吗？",
        "Cinq Royal别墅特色"
    ]
    
    for query in test_queries:
        print(f"\n📝 查询: {query}")
        answer = rag.query(query, language='zh')
        print(f"📤 回答:")
        print("-" * 40)
        print(answer[:300] + "..." if len(answer) > 300 else answer)
    
    return True


def test_multilingual():
    """测试多语言支持"""
    print("\n" + "=" * 60)
    print("测试5: 多语言支持")
    print("=" * 60)
    
    rag = get_rag_system()
    
    queries = [
        ("How much is the villa?", "en"),
        ("ราคาวิลล่า", "th"),
        ("别墅价格", "zh")
    ]
    
    for query, lang in queries:
        print(f"\n📝 [{lang}] {query}")
        answer = rag.query(query, language=lang)
        print(f"   回答: {answer[:100]}...")
    
    return True


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("🏠 Villa Booking Bot - RAG系统测试")
    print("=" * 60)
    
    tests = [
        ("知识库加载", test_knowledge_base),
        ("RAG系统初始化", test_rag_system),
        ("检索功能", test_retrieval),
        ("答案生成", test_generation),
        ("多语言支持", test_multilingual),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result, None))
        except Exception as e:
            import traceback
            results.append((name, False, str(e)))
            print(f"\n❌ 测试失败: {e}")
            traceback.print_exc()
    
    # 打印结果摘要
    print("\n" + "=" * 60)
    print("📊 测试结果摘要")
    print("=" * 60)
    
    passed = sum(1 for _, result, _ in results if result)
    total = len(results)
    
    for name, result, error in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
        if error:
            print(f"         错误: {error}")
    
    print(f"\n通过: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 所有测试通过!")
    else:
        print(f"\n⚠️ {total - passed} 个测试失败")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
