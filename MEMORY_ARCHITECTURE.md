# Hermes 三层记忆架构

本项目实现了基于Hermes Agent的三层记忆架构，用于别墅预订Bot的智能对话系统。

## 架构概述

```
┌─────────────────────────────────────────────────────────┐
│                     用户对话输入                          │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│              Layer 1: Working Memory                    │
│              工作记忆 - 当前对话上下文                    │
│              生命周期：单次对话 (30分钟TTL)              │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│              Layer 2: Episodic Memory                   │
│              情景记忆 - 用户历史交互记录                  │
│              生命周期：跨对话持久化                      │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│              Layer 3: Semantic Memory                    │
│              语义记忆 - 知识库和规则                      │
│              生命周期：永久，可更新                       │
└─────────────────────────────────────────────────────────┘
```

## 目录结构

```
memory/
├── __init__.py          # 包入口，统一接口
├── base.py              # 基类和接口定义
├── working_memory.py     # Layer 1: 工作记忆
├── episodic_memory.py    # Layer 2: 情景记忆
├── semantic_memory.py    # Layer 3: 语义记忆
└── episodic_store.json   # 情景记忆持久化存储
```

## 三层记忆详解

### Layer 1: Working Memory (工作记忆)

**职责**: 存储当前对话的上下文状态

**存储内容**:
- 用户当前意图
- 预订进度 (0-6)
- 已选地区/别墅
- 日期信息
- 近期消息摘要
- 用户提到的偏好

**特点**:
- JSON格式，轻量
- 线程安全
- 30分钟自动过期
- Token消耗低

**使用示例**:
```python
from memory import working_memory

# 创建或获取会话
context = working_memory.get_or_create_session(user_id, chat_id)

# 更新意图
working_memory.update_intent(context.session_id, "booking")

# 添加消息
working_memory.add_message(context.session_id, "user", "我想预订普吉岛的别墅")

# 获取上下文摘要
summary = working_memory.get_context_summary(context.session_id)
```

### Layer 2: Episodic Memory (情景记忆)

**职责**: 存储用户历史交互和偏好

**存储内容**:
- 用户画像摘要
- 历史预订记录
- 偏好地区/别墅
- 价格偏好
- 互动特征标签
- 交互历史摘要

**特点**:
- 持久化到文件
- 只存摘要，不存原始对话
- 自动聚合用户行为
- 支持个性化推荐

**使用示例**:
```python
from memory import episodic_memory

# 获取用户画像
profile = episodic_memory.load(user_id)

# 获取个性化上下文
context = episodic_memory.get_personalization_context(user_id)

# 获取推荐
recommendations = episodic_memory.suggest_villas_for_user(user_id, all_villas)
```

### Layer 3: Semantic Memory (语义记忆)

**职责**: 存储知识库和运营规则

**存储内容**:
- 别墅知识库 (14套别墅数据)
  - 房型/价格/位置/设施
  - 周边信息
- 运营规则
  - 退改政策
  - 入住流程
  - 常见问题 (FAQ)
- AGENTS.md 指令

**特点**:
- 永久存储
- 可动态更新
- 结构化JSON
- 支持全文检索

**使用示例**:
```python
from memory import semantic_memory

# 获取所有别墅
villas = semantic_memory.get_all_villas()

# 按地区搜索
villas = semantic_memory.get_villas_by_region("普吉岛")

# 高级搜索
villas = semantic_memory.search_villas(
    region="芭提雅",
    min_price=1000,
    max_price=3000,
    min_guests=4
)

# 获取运营规则
rules = semantic_memory.get_rules()
cancellation_policy = semantic_memory.get_rule("cancellation_policy.description")

# 搜索FAQ
faqs = semantic_memory.search_faq("取消政策")
```

## 统一接口

使用 `memory_integration` 可以方便地访问三层记忆：

```python
from memory_integration import memory_integration

# 消息入口处理
context = memory_integration.on_message_received(user_id, chat_id, message)

# 意图检测
memory_integration.on_intent_detected(session_id, "booking")

# 预订完成
memory_integration.on_booking_completed(user_id, session_id, booking_data)

# 获取LLM上下文
llm_context = memory_integration.build_llm_context(user_id, chat_id, intent)

# 个性化推荐
recommendations = memory_integration.get_villa_recommendations(user_id, region)
```

## 与Bot集成

在 `bot.py` 中的集成点：

1. **启动时**: 初始化记忆系统日志
2. **用户进入**: 创建/恢复工作记忆会话
3. **意图检测**: 更新工作记忆中的意图
4. **地区选择**: 记录用户偏好地区
5. **别墅选择**: 记录用户关注的别墅
6. **预订完成**: 聚合到情景记忆
7. **对话结束**: 清理工作记忆

## Token优化

Working Memory 设计为轻量级，典型Token消耗：

- 空会话: ~200 tokens
- 1个意图+1个别墅: ~350 tokens
- 完整预订流程: ~600 tokens

建议在调用LLM时，将Working Memory摘要与Semantic Memory知识库分离，以获得最佳效果。

## 数据持久化

- **Working Memory**: 内存存储，程序重启后丢失
- **Episodic Memory**: `memory/episodic_store.json` 文件存储
- **Semantic Memory**: 从 `villas.json` 加载，运行时内存存储

## 扩展建议

1. **增强偏好提取**: 使用LLM从对话中提取用户偏好
2. **跨用户学习**: 分析用户群体行为模式
3. **实时知识更新**: 支持从API更新别墅数据
4. **记忆压缩**: 对长期用户的记忆进行摘要压缩
