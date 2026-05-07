# Villa Booking Bot - AGENTS.md

## Bot Identity

**Name**: Taimili Villa Booking Assistant  
**Type**: Telegram Chatbot  
**Language**: 中文为主，支持英文/泰文  
**Version**: 4.1+ with LangGraph Integration

---

## Core Purpose

专业的泰国度假别墅预订助手，帮助用户在芭提雅、曼谷、普吉岛预订心仪的别墅。

---

## Capabilities

### 1. Booking Services
- ✅ 查询可用别墅
- ✅ 展示别墅详情（价格、设施、图片）
- ✅ 引导预订流程
- ✅ 订单管理（查看、取消）
- ✅ 支付处理（Stripe/转账）

### 2. Customer Support
- ✅ 回答别墅相关问题
- ✅ 提供入住指南
- ✅ 处理投诉和反馈
- ✅ 推荐合适别墅

### 3. User Management
- ✅ 用户注册和画像
- ✅ 积分系统
- ✅ 优惠券发放
- ✅ 评价系统

---

## LangGraph Integration (复杂对话流程)

### 概述
Villa Bot v4.1 集成 LangGraph 实现复杂多轮对话流程，采用状态机架构管理对话状态。

### 核心文件
- `langgraph_flows.py` - LangGraph 对话流程定义
- `langgraph_integration.py` - 与 bot.py 的集成层

### 实现的对话流程

#### 1. 预订流程 (Booking Flow)
```
入口 → 地区选择 → 日期选择 → 别墅选择 → 人数确认 
    → 联系信息 → 确认预订 → 等待支付 → 完成
```
**状态机状态**: `IDLE → SELECTING_REGION → SELECTING_DATES → SELECTING_VILLA 
              → ENTERING_GUESTS → ENTERING_CONTACT → CONFIRMING 
              → AWAITING_PAYMENT → COMPLETED`

#### 2. 客诉流程 (Complaint Flow)
```
入口 → 问题接收 → 问题分类 → 自动处理/转人工 → 跟进 → 解决
```
**状态机状态**: `IDLE → RECEIVING → CLASSIFYING → AUTO_HANDLING/ESCALATING 
              → FOLLOWING_UP → RESOLVED`

### LangGraph 最佳实践
1. **状态设计**: 使用 TypedDict 定义状态，简洁明确
2. **节点纯函数**: 节点返回部分状态更新，便于测试
3. **边界验证**: 节点边界进行状态验证
4. **循环保护**: 设置 max_steps 防止无限循环
5. **Checkpoint**: 使用 MemorySaver 持久化状态

### 集成方式
```python
from langgraph_integration import get_langgraph_manager

manager = get_langgraph_manager()
result = manager.handle_message(user_id, message)
```

### 环境变量
| 变量 | 说明 | 默认值 |
|------|------|--------|
| LANGGRAPH_LLM_PROVIDER | LLM提供者 | deepseek |
| LANGGRAPH_CHECKPOINTER | 检查点存储 | memory |
| LANGGRAPH_MAX_STEPS | 最大对话步数 | 20 |

---

## Commands Reference

| Command | Description |
|---------|-------------|
| /start | 开始使用 |
| /help | 帮助信息 |
| /book | 开始预订 |
| /mybookings | 我的订单 |
| /profile | 个人中心 |
| /cancel | 取消当前流程 |

---

## Version History

- **v4.1**: LangGraph 复杂对话流程集成
- **v4.0**: AI 集成，Token 优化
- **v3.x**: 数据库重构，支付集成
- **v2.x**: 多功能扩展
- **v1.x**: 基础预订功能

---

*Last Updated: 2024*
