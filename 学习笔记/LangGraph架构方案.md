# LangGraph架构方案 - Villa Booking Bot

## 任务概述
为Villa Booking Bot引入LangGraph复杂对话逻辑，实现多轮对话状态机管理。

---

## 一、LangGraph核心概念

### 1.1 什么是LangGraph？
LangGraph是LangChain团队开发的低层次Agent框架，被LinkedIn、Uber、Klarna等公司用于生产环境。
- 基于有向图建模Agent行为
- 支持循环（Cycles）和分支
- 内置checkpointing持久化

### 1.2 核心组件
```
StateGraph
├── State (状态) - TypedDict定义
├── Nodes (节点) - 执行函数
├── Edges (边)
│   ├── Normal Edge - 固定路由
│   └── Conditional Edge - 条件路由
└── Checkpointer - 状态持久化
```

### 1.3 状态设计
```python
class VillaState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    flow_type: Literal["booking", "complaint"]
    booking_status: BookingStatus
    booking_data: Dict[str, Any]
```

---

## 二、实现的对话流程

### 2.1 预订流程 (Booking Flow)
```
入口 → 地区选择 → 日期选择 → 别墅选择 → 人数确认 
    → 联系信息 → 确认预订 → 等待支付 → 完成
```
状态: `IDLE → SELECTING_REGION → SELECTING_DATES → SELECTING_VILLA 
    → ENTERING_GUESTS → ENTERING_CONTACT → CONFIRMING 
    → AWAITING_PAYMENT → COMPLETED`

### 2.2 客诉流程 (Complaint Flow)
```
入口 → 问题接收 → 问题分类 → 自动处理/转人工 → 跟进 → 解决
```
状态: `IDLE → RECEIVING → CLASSIFYING → AUTO_HANDLING/ESCALATING 
    → FOLLOWING_UP → RESOLVED`

---

## 三、代码结构

### 3.1 文件列表
- `langgraph_flows.py` - 对话流程定义
- `langgraph_integration.py` - 集成层

### 3.2 核心类
- `LangGraphManager` - 对话状态管理器
- `FlowType` - 流程类型枚举
- `VillaState` - 统一状态定义

---

## 四、集成方式

```python
from langgraph_integration import get_langgraph_manager

manager = get_langgraph_manager()
result = manager.handle_message(user_id, message)
```

---

*适用版本: Villa Bot v4.1+*
