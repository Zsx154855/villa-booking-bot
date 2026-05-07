"""
OpenClaw Token Optimizer - 上下文裁剪与压缩模块
实现 OpenClaw 的三大 Token 优化策略：
1. contextPruning - 上下文裁剪
2. contextInjection - 上下文注入
3. compact - 对话历史压缩
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class ConversationMessage:
    """对话消息"""
    role: str  # 'user' | 'assistant' | 'system'
    content: str
    timestamp: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'ConversationMessage':
        return cls(**data)


@dataclass
class UserContext:
    """用户上下文（关键信息，保留在 system prompt 中）"""
    user_id: str = ""
    language: str = "zh"  # 用户语言偏好
    current_booking_status: str = ""  # 当前预订状态
    booking_intent: str = ""  # 预订意向
    budget_range: Tuple[int, int] = (0, 5000)  # 预算范围
    preferred_region: str = ""  # 偏好地区
    preferred_dates: str = ""  # 偏好日期
    guest_count: int = 0  # 入住人数
    booking_id: str = ""  # 当前预订ID

    def to_injection_text(self) -> str:
        """转换为注入文本"""
        parts = []
        if self.language and self.language != "zh":
            parts.append(f"用户语言偏好: {self.language}")
        if self.booking_intent:
            parts.append(f"用户预订意向: {self.booking_intent}")
        if self.preferred_region:
            parts.append(f"用户偏好地区: {self.preferred_region}")
        if self.budget_range != (0, 5000):
            parts.append(f"用户预算范围: ฿{self.budget_range[0]:,} - ฿{self.budget_range[1]:,}")
        if self.preferred_dates:
            parts.append(f"用户偏好日期: {self.preferred_dates}")
        if self.guest_count > 0:
            parts.append(f"入住人数: {self.guest_count}人")
        if self.current_booking_status:
            parts.append(f"当前预订状态: {self.current_booking_status}")
        if self.booking_id:
            parts.append(f"当前预订ID: {self.booking_id}")
        return "；".join(parts) if parts else "新用户"


class TokenOptimizer:
    """Token 优化器"""

    # 保留最近对话轮数
    KEEP_RECENT_TURNS = 5

    # 触发压缩的对话轮数
    COMPACT_THRESHOLD = 10

    # 压缩后保留的轮数
    COMPACT_KEEP_TURNS = 5

    def __init__(self, villas_data: List[Dict], compact_threshold: int = 10):
        """
        初始化 Token 优化器

        Args:
            villas_data: 别墅数据列表
            compact_threshold: 触发压缩的对话轮数
        """
        self.villas_data = villas_data
        self.COMPACT_THRESHOLD = compact_threshold
        self._build_villa_summary()

    def _build_villa_summary(self):
        """构建别墅摘要（用于 contextInjection）"""
        self.villa_summary = self._generate_villa_summary()

    def _generate_villa_summary(self) -> str:
        """生成别墅列表摘要"""
        regions = {}
        for villa in self.villas_data:
            region = villa.get('region', '未知')
            if region not in regions:
                regions[region] = []
            regions[region].append({
                'id': villa.get('id'),
                'name': villa.get('name'),
                'price': villa.get('price_per_night'),
                'max_guests': villa.get('max_guests'),
                'bedrooms': villa.get('bedrooms')
            })

        summary_parts = ["【可用别墅列表】"]
        for region, villas in sorted(regions.items()):
            region_prices = [v['price'] for v in villas]
            summary_parts.append(
                f"\n{region} ({len(villas)}套): "
                f"价格 ฿{min(region_prices):,} - ฿{max(region_prices):,}/晚"
            )
            # 列出前3套
            for v in sorted(villas, key=lambda x: x['price'])[:3]:
                summary_parts.append(
                    f"  • {v['name']} (ID:{v['id']}) - ฿{v['price']:,}/晚 "
                    f"({v['bedrooms']}卧, 最多{v['max_guests']}人)"
                )

        return "\n".join(summary_parts)

    def get_price_range(self) -> str:
        """获取价格范围摘要"""
        if not self.villas_data:
            return "暂无别墅数据"
        prices = [v.get('price_per_night', 0) for v in self.villas_data]
        return f"฿{min(prices):,} - ฿{max(prices):,}/晚"

    def prune_messages(
        self,
        messages: List[ConversationMessage],
        user_context: UserContext,
        max_tokens: int = 3000
    ) -> List[ConversationMessage]:
        """
        contextPruning: 裁剪不相关的历史消息

        Args:
            messages: 原始消息列表
            user_context: 用户上下文
            max_tokens: 最大 token 数（约等于字符数）

        Returns:
            裁剪后的消息列表
        """
        if not messages:
            return messages

        # 保留最近 N 轮对话
        if len(messages) <= self.KEEP_RECENT_TURNS:
            return messages

        # 保留最后 KEEP_RECENT_TURNS 条消息
        pruned = messages[-self.KEEP_RECENT_TURNS:]

        logger.info(
            f"[TokenOptimizer] Pruned {len(messages)} -> {len(pruned)} messages "
            f"(kept last {self.KEEP_RECENT_TURNS})"
        )

        return pruned

    def inject_context(
        self,
        base_system_prompt: str,
        user_context: UserContext
    ) -> str:
        """
        contextInjection: 在 system prompt 中注入关键信息

        Args:
            base_system_prompt: 基础 system prompt
            user_context: 用户上下文

        Returns:
            增强后的 system prompt
        """
        injection_parts = [
            "\n\n【用户当前状态】",
            user_context.to_injection_text(),
            "\n\n【别墅信息】",
            f"价格范围: {self.get_price_range()}",
            self.villa_summary,
            "\n\n【重要】上述用户状态和别墅信息已经过验证，请直接使用，"
            "不要让用户重复提供已确认的信息。"
        ]

        injection_text = "\n".join(injection_parts)

        # 检查长度（默认最大 4000 字符）
        max_chars = getattr(self, 'max_tokens', 4000)
        if len(base_system_prompt) + len(injection_text) > max_chars:
            # 如果太长，只注入用户状态
            injection_text = (
                f"\n\n【用户当前状态】\n{user_context.to_injection_text()}\n\n"
                f"【价格范围】: {self.get_price_range()}"
            )

        return base_system_prompt + injection_text

    def compact_history(
        self,
        messages: List[ConversationMessage],
        user_context: UserContext
    ) -> Tuple[List[ConversationMessage], str]:
        """
        compact: 对话历史压缩

        当对话超过阈值时，将早期对话压缩为摘要

        Args:
            messages: 完整消息列表
            user_context: 用户上下文

        Returns:
            (压缩后的消息列表, 压缩摘要)
        """
        if len(messages) <= self.COMPACT_THRESHOLD:
            return messages, ""

        # 保留最近 KEEP_TURNS 轮对话
        # 压缩早期对话为摘要
        early_messages = messages[:-self.COMPACT_KEEP_TURNS]
        recent_messages = messages[-self.COMPACT_KEEP_TURNS:]

        # 生成压缩摘要
        summary = self._generate_summary(early_messages, user_context)

        # 创建摘要消息
        summary_message = ConversationMessage(
            role="system",
            content=f"【对话摘要 - 早期历史】\n{summary}",
            metadata={"type": "compact_summary", "original_count": len(early_messages)}
        )

        compacted = [summary_message] + recent_messages

        logger.info(
            f"[TokenOptimizer] Compacted {len(messages)} -> {len(compacted)} messages "
            f"(compressed {len(early_messages)} early messages)"
        )

        return compacted, summary

    def _generate_summary(
        self,
        messages: List[ConversationMessage],
        user_context: UserContext
    ) -> str:
        """
        生成对话摘要

        提取关键信息：预订意向、预算、日期等
        """
        # 统计用户意图
        intents = []
        dates_mentioned = []
        budgets = []
        regions_mentioned = []

        for msg in messages:
            if msg.role != "user":
                continue
            content = msg.content.lower()

            # 检测意图关键词
            intent_keywords = {
                'booking': ['预订', '预定', '订', 'booking', 'book', '入住'],
                'price': ['价格', 'price', '多少钱', '贵'],
                'cancel': ['取消', '取消预订', 'cancel'],
                'question': ['问', '怎么', '如何', '可以']
            }

            for intent, keywords in intent_keywords.items():
                if any(kw in content for kw in keywords):
                    if intent not in intents:
                        intents.append(intent)

            # 检测日期
            import re
            date_pattern = r'\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}'
            dates_mentioned.extend(re.findall(date_pattern, msg.content))

            # 检测预算相关
            budget_pattern = r'\d+'
            budgets.extend(re.findall(budget_pattern, msg.content))

        # 构建摘要
        summary_parts = []

        if intents:
            summary_parts.append(f"用户意图: {', '.join(intents)}")
        if user_context.booking_intent:
            summary_parts.append(f"预订类型: {user_context.booking_intent}")
        if user_context.preferred_region:
            summary_parts.append(f"偏好地区: {user_context.preferred_region}")
        if user_context.budget_range != (0, 5000):
            summary_parts.append(
                f"预算范围: ฿{user_context.budget_range[0]:,} - ฿{user_context.budget_range[1]:,}"
            )
        if dates_mentioned:
            summary_parts.append(f"提及日期: {', '.join(set(dates_mentioned))}")
        if user_context.preferred_dates:
            summary_parts.append(f"确认日期: {user_context.preferred_dates}")
        if user_context.guest_count > 0:
            summary_parts.append(f"入住人数: {user_context.guest_count}人")

        if not summary_parts:
            return "早期对话为一般性闲聊，未涉及预订流程。"

        return "；".join(summary_parts)


class ConversationManager:
    """对话管理器 - 管理用户对话历史和上下文"""

    def __init__(self, villas_data: List[Dict]):
        self.optimizer = TokenOptimizer(villas_data)
        self.user_conversations: Dict[str, Dict] = {}

    def get_or_create_conversation(self, user_id: str) -> Dict:
        """获取或创建用户对话"""
        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = {
                'messages': [],
                'user_context': UserContext(user_id=user_id),
                'created_at': datetime.now().timestamp()
            }
        return self.user_conversations[user_id]

    def add_message(
        self,
        user_id: str,
        role: str,
        content: str,
        metadata: Dict = None
    ) -> None:
        """添加消息"""
        conv = self.get_or_create_conversation(user_id)
        message = ConversationMessage(
            role=role,
            content=content,
            timestamp=datetime.now().timestamp(),
            metadata=metadata or {}
        )
        conv['messages'].append(message)

    def update_user_context(self, user_id: str, **kwargs) -> None:
        """更新用户上下文"""
        conv = self.get_or_create_conversation(user_id)
        ctx = conv['user_context']

        for key, value in kwargs.items():
            if hasattr(ctx, key):
                setattr(ctx, key, value)

    def get_optimized_messages(
        self,
        user_id: str,
        base_system_prompt: str,
        enable_compact: bool = True
    ) -> Tuple[List[Dict], str]:
        """
        获取优化后的消息列表

        Returns:
            (消息列表, 使用的摘要)
        """
        conv = self.get_or_create_conversation(user_id)
        messages = conv['messages']
        user_context = conv['user_context']

        # 1. Compact 压缩（如果启用且超过阈值）
        summary = ""
        if enable_compact:
            messages, summary = self.optimizer.compact_history(messages, user_context)

        # 2. Pruning 裁剪
        messages = self.optimizer.prune_messages(messages, user_context)

        # 3. 转换为 dict 格式（供 API 使用）
        result = [msg.to_dict() for msg in messages]

        return result, summary

    def get_enhanced_system_prompt(
        self,
        user_id: str,
        base_system_prompt: str
    ) -> str:
        """获取增强后的 system prompt（含 contextInjection）"""
        conv = self.get_or_create_conversation(user_id)
        user_context = conv['user_context']

        return self.optimizer.inject_context(base_system_prompt, user_context)

    def clear_conversation(self, user_id: str) -> None:
        """清除对话历史"""
        if user_id in self.user_conversations:
            self.user_conversations[user_id]['messages'] = []

    def get_conversation_stats(self, user_id: str) -> Dict:
        """获取对话统计"""
        conv = self.get_or_create_conversation(user_id)
        return {
            'message_count': len(conv['messages']),
            'created_at': datetime.fromtimestamp(conv['created_at']).isoformat(),
            'user_context': conv['user_context'].to_injection_text()
        }
