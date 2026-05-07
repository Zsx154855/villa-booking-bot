#!/usr/bin/env python3
"""
Coordinator - 中央调度Agent
Hub&Spoke架构的核心，负责意图识别和路由
"""

import os
import json
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from .context import (
    AgentRequest, AgentResponse, AgentType, IntentType,
    UserContext, ConversationContext, ContextBuilder
)
from .base import BaseAgent, CoordinatorMixin

logger = logging.getLogger(__name__)


class IntentRecognizer:
    """意图识别器 - LLM驱动的智能路由"""
    
    SYSTEM_PROMPT = """你是一个别墅预订助手的意图识别专家。
分析用户消息，判断其意图类型并提取参数。

意图类型：
- booking: 预订相关（查询房源、推荐、计算价格、开始预订）
- service: 运营服务（入住退房、清洁、维修、投诉）
- info: 信息查询（周边攻略、交通、景点、天气）
- payment: 支付相关（支付、退款、发票、优惠码）

输出格式（JSON）：
{
    "intent": "booking|service|info|payment|unknown",
    "confidence": 0.0-1.0,
    "parameters": {
        "region": "芭提雅|曼谷|普吉岛|null",
        "checkin": "YYYY-MM-DD|null",
        "checkout": "YYYY-MM-DD|null",
        "guests": 数字|null,
        "villa_id": "string|null",
        "action_type": "string|null"
    },
    "reasoning": "简短推理过程"
}

注意：
- 只返回JSON，不要其他内容
- 如果无法确定意图，返回 intent: "unknown"
"""
    
    def __init__(self, llm_caller):
        self.llm_caller = llm_caller
    
    async def recognize(self, message: str, context: Dict = None) -> Dict:
        """识别意图"""
        # 快速关键词匹配（兜底）
        quick_intent = self._quick_match(message)
        if quick_intent:
            logger.info(f"Quick match intent: {quick_intent}")
            return {"intent": quick_intent, "confidence": 0.8, "parameters": {}, "reasoning": "关键词匹配"}
        
        # LLM识别
        context_hint = ""
        if context:
            context_hint = f"\n\n上下文提示：当前在{context.get('current_step', '未知环节')}"
        
        full_prompt = f"用户消息：{message}{context_hint}"
        
        try:
            response = await self.llm_caller(
                [{"role": "user", "content": full_prompt}],
                self.SYSTEM_PROMPT
            )
            
            # 解析JSON响应
            result = json.loads(response)
            return result
            
        except json.JSONDecodeError:
            logger.warning(f"Intent JSON parse failed: {response[:200]}")
            return {"intent": "unknown", "confidence": 0.0, "parameters": {}, "reasoning": "解析失败"}
        except Exception as e:
            logger.error(f"Intent recognition error: {e}")
            return {"intent": "unknown", "confidence": 0.0, "parameters": {}, "reasoning": str(e)}
    
    def _quick_match(self, message: str) -> Optional[str]:
        """快速关键词匹配"""
        message_lower = message.lower()
        
        patterns = {
            "booking": ["预订", "订房", "入住", "预定", "房间", "别墅", "价格", "推荐", "查看"],
            "service": ["入住", "退房", "清洁", "维修", "问题", "投诉", "服务"],
            "info": ["攻略", "交通", "景点", "附近", "周边", "怎么去", "天气"],
            "payment": ["支付", "付款", "退款", "发票", "优惠", "折扣", "优惠券"]
        }
        
        for intent, keywords in patterns.items():
            for kw in keywords:
                if kw in message_lower:
                    return intent
        return None


class Coordinator(BaseAgent, CoordinatorMixin):
    """
    Coordinator - 中央调度Agent
    
    职责：
    1. 接收所有用户消息
    2. 意图识别
    3. 路由到对应Specialist
    4. 汇总结果回复用户
    """
    
    def __init__(self):
        BaseAgent.__init__(self, AgentType.COORDINATOR)
        CoordinatorMixin.__init__(self)
        self.intent_recognizer = IntentRecognizer(self.call_llm)
        self._register_specialists()
    
    def _register_specialists(self):
        """注册所有Specialist Agents"""
        from .booking_agent import BookingAgent
        from .service_agent import ServiceAgent
        from .info_agent import InfoAgent
        from .payment_agent import PaymentAgent
        
        self.register_agent(AgentType.BOOKING, BookingAgent())
        self.register_agent(AgentType.SERVICE, ServiceAgent())
        self.register_agent(AgentType.INFO, InfoAgent())
        self.register_agent(AgentType.PAYMENT, PaymentAgent())
        
        logger.info("✅ All Specialist Agents registered")
    
    def get_system_prompt(self) -> str:
        return """你是一个别墅预订助手的中央调度Coordinator。
        
你的职责：
1. 理解用户需求
2. 识别用户意图
3. 将请求路由到专业Agent处理
4. 汇总专业Agent的结果，给用户清晰的回复

你已经连接了以下专业Agent：
- BookingAgent: 处理预订查询、房源推荐、价格计算
- ServiceAgent: 处理入住/退房、清洁、维修等运营服务
- InfoAgent: 处理周边攻略、交通、景点信息查询
- PaymentAgent: 处理支付、退款、发票

当用户提出问题时，你会将请求转发给对应的专业Agent，然后整合结果回复用户。"""
    
    def get_supported_intents(self) -> List[IntentType]:
        return [IntentType.BOOKING, IntentType.SERVICE, IntentType.INFO, IntentType.PAYMENT]
    
    async def process(self, request: AgentRequest) -> AgentResponse:
        """处理请求 - Coordinator主流程"""
        logger.info(f"📨 Coordinator received: {request.raw_message[:100]}")
        
        # 意图识别
        intent_result = await self.intent_recognizer.recognize(
            request.raw_message,
            {
                "current_step": request.user_context.current_booking_step,
                "active_region": request.conversation_context.active_region
            }
        )
        
        intent = IntentType(intent_result.get("intent", "unknown"))
        confidence = intent_result.get("confidence", 0.0)
        
        logger.info(f"🎯 Intent recognized: {intent.value} (confidence: {confidence})")
        
        # 如果置信度太低，使用unknown处理
        if confidence < 0.3 and intent == IntentType.UNKNOWN:
            return await self._handle_unknown(request)
        
        # 路由到Specialist
        target_type = self.route_to_agent(intent)
        if not target_type:
            return await self._handle_unknown(request)
        
        # 更新请求参数
        if intent_result.get("parameters"):
            request.parameters.update(intent_result["parameters"])
        
        # 转发请求
        response = await self.forward_to_agent(request, target_type)
        
        # 格式化最终回复
        return self._format_response(response, intent_result)
    
    async def _handle_unknown(self, request: AgentRequest) -> AgentResponse:
        """处理未知意图"""
        return ContextBuilder.create_success_response(
            request.request_id,
            self.agent_type,
            IntentType.UNKNOWN,
            result={},
            message="抱歉，我不太理解您的意思。请问您需要什么帮助？\n\n您可以尝试：\n• 查看别墅列表\n• 了解预订流程\n• 咨询周边信息"
        )
    
    def _format_response(self, response: AgentResponse, intent_result: Dict) -> AgentResponse:
        """格式化响应，添加额外信息"""
        response.result["intent_reasoning"] = intent_result.get("reasoning", "")
        return response
    
    def get_intent_keywords(self) -> Dict[IntentType, List[str]]:
        return {
            IntentType.BOOKING: ["预订", "订房", "预定", "房间", "别墅", "价格", "推荐", "入住日期", "退房"],
            IntentType.SERVICE: ["入住", "退房", "清洁", "维修", "问题", "投诉", "服务"],
            IntentType.INFO: ["攻略", "交通", "景点", "附近", "周边", "怎么去", "天气", "推荐"],
            IntentType.PAYMENT: ["支付", "付款", "退款", "发票", "优惠", "折扣", "优惠券", "积分"]
        }
