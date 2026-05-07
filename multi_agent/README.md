# Multi-Agent System - Hub&Spoke架构

基于Hub&Spoke架构的多Agent协作框架，为别墅Bot提供智能意图识别和路由能力。

## 架构概览

```
                    ┌─────────────┐
                    │  User      │
                    │  Message   │
                    └─────┬───────┘
                          │
                          ▼
                    ┌─────────────┐
                    │ Coordinator │ ◄─── 中央调度 (Hub)
                    │  (意图识别) │
                    └─────┬───────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌───────────┐     ┌───────────┐     ┌───────────┐
│ Booking   │     │ Service   │     │ Info      │
│ Agent     │     │ Agent     │     │ Agent     │
│ (Spoke)   │     │ (Spoke)   │     │ (Spoke)   │
└───────────┘     └───────────┘     └───────────┘
                                              │
                                              ▼
                                    ┌─────────────┐
                                    │ Payment     │
                                    │ Agent       │
                                    │ (Spoke)     │
                                    └─────────────┘
```

## Agent职责

| Agent | 职责 | 关键词 |
|-------|------|--------|
| **Coordinator** | 意图识别、路由调度 | 全局 |
| **BookingAgent** | 预订查询、房源推荐、价格计算 | 预订、订房、房价 |
| **ServiceAgent** | 入住退房、清洁、维修 | 入住、退房、清洁 |
| **InfoAgent** | 景点攻略、交通指南 | 景点、美食、交通 |
| **PaymentAgent** | 支付退款、发票积分 | 支付、退款、优惠 |

## 快速开始

### 1. 环境配置

```bash
# 启用Multi-Agent模式
export MULTI_AGENT_ENABLED=true

# DeepSeek API配置
export DEEPSEEK_API_KEY=your_api_key
export DEEPSEEK_MODEL=deepseek-chat
```

### 2. 基本使用

```python
from multi_agent import process_message, router

# 处理用户消息
response = await process_message(
    user_id="123456",
    username="user_name",
    message="我想预订普吉岛的别墅"
)

print(response.message)  # Agent生成的回复
print(response.intent)   # 识别的意图
print(response.source)   # 处理的Agent
```

### 3. 与Telegram Bot集成

```python
from multi_agent_integration import handle_nlp_message

async def message_handler(update, context):
    # 尝试使用Multi-Agent处理
    response = await handle_nlp_message(update, context)
    if response:
        await update.message.reply_text(response)
        return
    
    # 回退到传统Handler
    # ... 原有逻辑
```

## 目录结构

```
multi_agent/
├── __init__.py          # 包入口
├── context.py           # Context协议 - Agent间通信标准
├── base.py              # BaseAgent基类
├── coordinator.py       # Coordinator - 中央调度
├── booking_agent.py     # BookingAgent - 预订专家
├── service_agent.py     # ServiceAgent - 服务专家
├── info_agent.py        # InfoAgent - 信息专家
├── payment_agent.py     # PaymentAgent - 支付专家
├── router.py            # 统一入口和路由
└── test_multi_agent.py  # 测试脚本
```

## Context传递机制

### AgentRequest
```python
@dataclass
class AgentRequest:
    request_id: str           # 请求唯一ID
    source: AgentType         # 来源Agent
    target: AgentType         # 目标Agent
    intent: IntentType        # 意图类型
    user_context: UserContext # 用户上下文
    conversation_context: ConversationContext  # 对话上下文
    raw_message: str          # 原始消息
    parameters: Dict         # 提取的参数
```

### AgentResponse
```python
@dataclass
class AgentResponse:
    request_id: str           # 请求ID
    source: AgentType         # 来源Agent
    success: bool            # 是否成功
    intent: IntentType        # 意图类型
    result: Dict              # 结构化结果
    message: str              # 回复消息
    suggested_actions: List  # 建议操作
```

### 防止信息衰减
- 每个Specialist收到完整必要上下文
- Coordinator传递完整的UserContext和ConversationContext
- 不依赖中间Agent转发

## Feature Flag控制

```python
# 环境变量控制
export MULTI_AGENT_ENABLED=false  # 禁用多Agent，使用传统单Agent

# 运行时切换
from multi_agent import enable_multi_agent, disable_multi_agent

enable_multi_agent()   # 启用
disable_multi_agent()  # 禁用
```

## 测试

```bash
cd villa-booking-bot
python multi_agent/test_multi_agent.py
```

测试包括：
- ✅ 意图路由准确性
- ✅ Agent响应质量
- ✅ 上下文传递
- ✅ 降级机制

## 扩展新Agent

1. 创建新的Agent类，继承`BaseAgent`
2. 实现`get_system_prompt()`
3. 实现`get_supported_intents()`
4. 实现`process()`方法
5. 在`Coordinator._register_specialists()`中注册

```python
from multi_agent import BaseAgent, AgentType, IntentType

class MyCustomAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType("custom"))
    
    def get_system_prompt(self) -> str:
        return "你的系统提示..."
    
    def get_supported_intents(self) -> List[IntentType]:
        return [IntentType.INFO]
    
    async def process(self, request: AgentRequest) -> AgentResponse:
        # 处理逻辑
        ...
```

## 注意事项

1. **向后兼容**: 原有Handler保持不变，Multi-Agent作为增强
2. **降级机制**: Multi-Agent失败时自动回退到单Agent模式
3. **性能考虑**: 意图识别使用快速匹配+LLM双重策略
4. **日志追踪**: 所有路由记录日志便于调试

## License

MIT
