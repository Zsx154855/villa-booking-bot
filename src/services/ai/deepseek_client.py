"""
DeepSeek API Client - 集成 Token 优化的 AI 对话客户端
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Tuple, Callable

import httpx

from .token_optimizer import (
    TokenOptimizer,
    ConversationManager,
    ConversationMessage,
    UserContext
)

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """DeepSeek API 客户端"""

    API_URL = "https://api.deepseek.com/chat/completions"

    def __init__(
        self,
        api_key: str,
        villas_data: List[Dict],
        model: str = "deepseek-chat",
        max_tokens: int = 1000,
        temperature: float = 0.7
    ):
        """
        初始化 DeepSeek 客户端

        Args:
            api_key: DeepSeek API Key
            villas_data: 别墅数据列表
            model: 模型名称
            max_tokens: 最大生成 token 数
            temperature: 温度参数
        """
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

        # 初始化 Token 优化器
        self.optimizer = TokenOptimizer(villas_data)
        self.conversation_manager = ConversationManager(villas_data)

        # Token 统计
        self.total_tokens_used = 0
        self.total_requests = 0

    def _build_headers(self) -> Dict:
        """构建请求头"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def _count_tokens(self, text: str) -> int:
        """简单估算 token 数（中文约 1.5-2 字符 = 1 token）"""
        # 简单估算：中文按 2 字符 1 token，英文按 4 字符 1 token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 2 + other_chars / 4)

    def _estimate_tokens(self, messages: List[Dict]) -> int:
        """估算消息列表的总 token 数"""
        total = 0
        for msg in messages:
            # 角色标记
            total += self._count_tokens(f"{msg['role']}: ")
            # 内容
            total += self._count_tokens(msg.get('content', ''))
        return total

    def chat(
        self,
        user_id: str,
        user_message: str,
        system_prompt: str,
        enable_optimization: bool = True,
        **kwargs
    ) -> Tuple[str, Dict]:
        """
        发送对话请求

        Args:
            user_id: 用户 ID
            user_message: 用户消息
            system_prompt: 基础 system prompt
            enable_optimization: 是否启用 Token 优化

        Returns:
            (assistant 回复, 元数据)
        """
        # 添加用户消息
        self.conversation_manager.add_message(user_id, "user", user_message)

        # 构建消息列表
        if enable_optimization:
            # 使用优化后的消息
            messages = self.conversation_manager.get_optimized_messages(
                user_id, system_prompt
            )

            # 注入增强的 system prompt
            enhanced_system = self.conversation_manager.get_enhanced_system_prompt(
                user_id, system_prompt
            )

            # 替换 system 消息
            if messages and messages[0]['role'] == 'system':
                messages[0]['content'] = enhanced_system
            else:
                messages.insert(0, {
                    "role": "system",
                    "content": enhanced_system
                })
        else:
            # 不使用优化
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            conv = self.conversation_manager.get_or_create_conversation(user_id)
            for msg in conv['messages'][-10:]:
                messages.append({"role": msg.role, "content": msg.content})

        # 估算 token 使用量
        estimated_tokens = self._estimate_tokens(messages)
        logger.info(
            f"[DeepSeek] Request tokens estimate: {estimated_tokens} "
            f"(messages: {len(messages)})"
        )

        # 调用 API
        try:
            response = self._make_request(messages)
            assistant_message = response['choices'][0]['message']['content']

            # 添加助手回复
            self.conversation_manager.add_message(user_id, "assistant", assistant_message)

            # 更新统计
            usage = response.get('usage', {})
            tokens_used = usage.get('total_tokens', estimated_tokens)
            self.total_tokens_used += tokens_used
            self.total_requests += 1

            logger.info(
                f"[DeepSeek] Response: {len(assistant_message)} chars, "
                f"{tokens_used} tokens used, "
                f"total: {self.total_tokens_used} tokens"
            )

            return assistant_message, {
                'tokens_used': tokens_used,
                'messages_count': len(messages),
                'optimization_enabled': enable_optimization
            }

        except Exception as e:
            logger.error(f"[DeepSeek] API Error: {e}")
            raise

    def _make_request(self, messages: List[Dict]) -> Dict:
        """发送 API 请求"""
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }

        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                self.API_URL,
                headers=self._build_headers(),
                json=payload
            )

            if response.status_code != 200:
                logger.error(f"[DeepSeek] API Error: {response.status_code} - {response.text}")
                raise Exception(f"API Error: {response.status_code}")

            return response.json()

    def update_user_context(self, user_id: str, **kwargs) -> None:
        """更新用户上下文"""
        self.conversation_manager.update_user_context(user_id, **kwargs)

    def get_stats(self, user_id: str = None) -> Dict:
        """获取统计信息"""
        stats = {
            'total_tokens_used': self.total_tokens_used,
            'total_requests': self.total_requests,
            'active_conversations': len(self.conversation_manager.user_conversations)
        }

        if user_id:
            stats['user_stats'] = self.conversation_manager.get_conversation_stats(user_id)

        return stats

    def clear_conversation(self, user_id: str) -> None:
        """清除用户对话"""
        self.conversation_manager.clear_conversation(user_id)


class VillaBookingAI:
    """别墅预订 AI 助手"""

    # 默认 System Prompt
    DEFAULT_SYSTEM_PROMPT = """你是一个专业的泰国别墅预订助手，负责帮助用户预订泰国芭提雅、曼谷、普吉岛的度假别墅。

【核心职责】
1. 解答用户关于别墅的问题（价格、设施、位置等）
2. 协助用户完成预订流程
3. 提供入住信息和注意事项

【服务规范】
- 使用友好、专业的语气
- 用中文交流（除非用户使用其他语言）
- 提供准确的价格和可用性信息
- 引导用户使用 /book 命令开始预订

【重要限制】
- 不提供虚假信息或夸大别墅描述
- 不承诺无法保证的事项
- 不处理与预订无关的问题

【回复格式】
- 简洁明了，突出关键信息
- 价格使用泰铢（฿）标注
- 需要用户确认的信息要明确列出"""

    def __init__(self, api_key: str, villas_data: List[Dict]):
        """
        初始化别墅预订 AI

        Args:
            api_key: DeepSeek API Key
            villas_data: 别墅数据
        """
        self.client = DeepSeekClient(api_key, villas_data)
        self.system_prompt = self.DEFAULT_SYSTEM_PROMPT

    def chat(self, user_id: str, message: str) -> Tuple[str, Dict]:
        """
        处理用户消息

        Args:
            user_id: 用户 ID
            message: 用户消息

        Returns:
            (AI 回复, 元数据)
        """
        return self.client.chat(
            user_id=user_id,
            user_message=message,
            system_prompt=self.system_prompt
        )

    def update_user_context(self, user_id: str, **kwargs) -> None:
        """更新用户上下文"""
        self.client.update_user_context(user_id, **kwargs)

    def set_system_prompt(self, prompt: str) -> None:
        """设置自定义 System Prompt"""
        self.system_prompt = prompt

    def get_stats(self, user_id: str = None) -> Dict:
        """获取统计信息"""
        return self.client.get_stats(user_id)
