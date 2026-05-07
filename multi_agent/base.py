#!/usr/bin/env python3
"""
Base Agent - Multi-Agent架构基类
定义所有Agent的通用接口和功能
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import urllib.request
import urllib.error

from .context import (
    AgentRequest, AgentResponse, AgentType, IntentType,
    ContextBuilder
)

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Agent基类"""
    
    def __init__(self, agent_type: AgentType):
        self.agent_type = agent_type
        self.deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        self.deepseek_base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
        
    async def call_llm(self, messages: List[Dict], system_prompt: str = None) -> str:
        """调用DeepSeek LLM"""
        if not self.deepseek_api_key:
            logger.warning("⚠️ DEEPSEEK_API_KEY not set, using fallback")
            return self._fallback_response(messages)
        
        # 构建消息
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)
        
        try:
            import urllib.request
            import urllib.error
            import json as json_lib
            
            url = f"{self.deepseek_base_url}/chat/completions"
            data = json_lib.dumps({
                "model": self.model,
                "messages": full_messages,
                "temperature": 0.7,
                "max_tokens": 2000
            }).encode('utf-8')
            
            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    "Authorization": f"Bearer {self.deepseek_api_key}",
                    "Content-Type": "application/json"
                },
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json_lib.loads(response.read().decode('utf-8'))
                return result["choices"][0]["message"]["content"]
                    
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return self._fallback_response(messages)
    
    def _fallback_response(self, messages: List[Dict]) -> str:
        """降级响应"""
        user_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_msg = msg.get("content", "")
                break
        return f"收到消息: {user_msg[:100]}..."
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """获取Agent系统提示"""
        pass
    
    @abstractmethod
    def get_supported_intents(self) -> List[IntentType]:
        """获取支持的意图类型"""
        pass
    
    @abstractmethod
    async def process(self, request: AgentRequest) -> AgentResponse:
        """处理请求 - 子类实现"""
        pass
    
    def can_handle(self, intent: IntentType) -> bool:
        """检查是否可处理该意图"""
        return intent in self.get_supported_intents()
    
    def get_intent_keywords(self) -> Dict[IntentType, List[str]]:
        """获取意图关键词映射 - 用于快速路由"""
        return {}
    
    def match_intent(self, message: str) -> Optional[IntentType]:
        """根据消息内容匹配意图"""
        message_lower = message.lower()
        keywords_map = self.get_intent_keywords()
        
        for intent, keywords in keywords_map.items():
            for keyword in keywords:
                if keyword in message_lower:
                    return intent
        return None


class CoordinatorMixin:
    """Coordinator混入 - 提供路由功能"""
    
    def __init__(self):
        self.agents: Dict[AgentType, BaseAgent] = {}
    
    def register_agent(self, agent_type: AgentType, agent: BaseAgent):
        """注册Agent"""
        self.agents[agent_type] = agent
        logger.info(f"✅ Registered agent: {agent_type.value}")
    
    def get_agent(self, agent_type: AgentType) -> Optional[BaseAgent]:
        """获取Agent"""
        return self.agents.get(agent_type)
    
    def route_to_agent(self, intent: IntentType) -> Optional[AgentType]:
        """根据意图路由到对应Agent"""
        routing_map = {
            IntentType.BOOKING: AgentType.BOOKING,
            IntentType.SERVICE: AgentType.SERVICE,
            IntentType.INFO: AgentType.INFO,
            IntentType.PAYMENT: AgentType.PAYMENT,
        }
        return routing_map.get(intent)
    
    async def forward_to_agent(
        self, 
        request: AgentRequest, 
        target_type: AgentType
    ) -> AgentResponse:
        """转发请求到目标Agent"""
        target = self.get_agent(target_type)
        if not target:
            return ContextBuilder.create_error_response(
                request.request_id,
                self.agent_type,
                request.intent,
                f"Agent {target_type.value} not found"
            )
        
        # 更新请求目标
        request.target = target_type
        return await target.process(request)
