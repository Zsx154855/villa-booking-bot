"""
AI Chat Handler - AI 对话处理模块
集成 Token 优化的 DeepSeek AI 助手
"""

import os
import logging
from typing import Optional, Tuple

import database
from src.services.ai import VillaBookingAI, UserContext

logger = logging.getLogger(__name__)

# 全局 AI 实例
_ai_client: Optional[VillaBookingAI] = None


def get_ai_client() -> Optional[VillaBookingAI]:
    """获取 AI 客户端实例"""
    global _ai_client

    if _ai_client is not None:
        return _ai_client

    # 检查 API Key
    api_key = os.environ.get('DEEPSEEK_API_KEY')
    if not api_key:
        logger.warning("⚠️ DEEPSEEK_API_KEY 未配置，AI 功能暂时不可用")
        return None

    # 检查是否启用 AI
    if os.environ.get('ENABLE_AI_CHAT', 'false').lower() != 'true':
        logger.info("AI Chat 功能未启用（ENABLE_AI_CHAT != true）")
        return None

    try:
        # 加载别墅数据
        villas = database.get_all_villas()
        if not villas:
            logger.warning("⚠️ 数据库中没有别墅数据")
            villas = []

        _ai_client = VillaBookingAI(api_key, villas)
        logger.info(f"✅ AI 助手初始化成功（{len(villas)} 套别墅）")

        return _ai_client

    except Exception as e:
        logger.error(f"❌ AI 助手初始化失败: {e}")
        return None


async def handle_ai_message(update, context, user_id: str) -> Tuple[str, Optional[str]]:
    """
    处理 AI 对话消息

    Args:
        update: Telegram Update
        context: Bot context
        user_id: 用户 ID

    Returns:
        (回复文本, 回复模式)
        - 回复模式: "ai" - AI 回复, "fallback" - 回退到帮助
    """
    message_text = update.message.text.strip()

    if not message_text:
        return "请输入您的问题 😊", "fallback"

    # 检查是否以命令开头（命令由 handlers 处理）
    if message_text.startswith('/'):
        return "", "fallback"

    # 获取 AI 客户端
    ai = get_ai_client()
    if not ai:
        return "", "fallback"

    try:
        # 从 context 加载用户状态
        _update_user_context_from_context(context, user_id, ai)

        # 调用 AI
        response, meta = ai.chat(user_id, message_text)

        logger.info(
            f"[AI Chat] User {user_id}: {message_text[:50]}... -> "
            f"{len(response)} chars, {meta.get('tokens_used', 0)} tokens"
        )

        return response, "ai"

    except Exception as e:
        logger.error(f"[AI Chat] Error: {e}")
        return "抱歉，AI 服务暂时不可用，请稍后重试 🙏", "fallback"


def _update_user_context_from_context(context, user_id: str, ai: VillaBookingAI):
    """从 bot context 更新用户上下文"""
    try:
        # 从 user_data 读取状态
        user_data = context.user_data or {}

        # 更新语言偏好
        language = user_data.get('language', 'zh')
        ai.update_user_context(user_id, language=language)

        # 更新预订状态
        booking_status = user_data.get('booking_status', '')
        ai.update_user_context(user_id, current_booking_status=booking_status)

        # 更新预算范围
        budget_min = user_data.get('budget_min', 0)
        budget_max = user_data.get('budget_max', 5000)
        if budget_min or budget_max:
            ai.update_user_context(user_id, budget_range=(budget_min, budget_max))

        # 更新偏好地区
        preferred_region = user_data.get('preferred_region', '')
        if preferred_region:
            ai.update_user_context(user_id, preferred_region=preferred_region)

    except Exception as e:
        logger.debug(f"Update context error: {e}")


def update_user_booking_context(
    user_id: str,
    booking_id: str = None,
    booking_status: str = None,
    preferred_region: str = None,
    preferred_dates: str = None,
    guest_count: int = None,
    booking_intent: str = None
):
    """
    更新用户预订上下文（供其他 handler 调用）

    Args:
        user_id: 用户 ID
        booking_id: 预订 ID
        booking_status: 预订状态
        preferred_region: 偏好地区
        preferred_dates: 偏好日期
        guest_count: 入住人数
        booking_intent: 预订意向
    """
    ai = get_ai_client()
    if not ai:
        return

    updates = {}
    if booking_id:
        updates['booking_id'] = booking_id
    if booking_status:
        updates['current_booking_status'] = booking_status
    if preferred_region:
        updates['preferred_region'] = preferred_region
    if preferred_dates:
        updates['preferred_dates'] = preferred_dates
    if guest_count:
        updates['guest_count'] = guest_count
    if booking_intent:
        updates['booking_intent'] = booking_intent

    if updates:
        ai.update_user_context(user_id, **updates)


def get_ai_stats(user_id: str = None) -> dict:
    """获取 AI 使用统计"""
    ai = get_ai_client()
    if not ai:
        return {"enabled": False}

    return ai.get_stats(user_id)


def reset_ai_conversation(user_id: str):
    """重置用户 AI 对话"""
    ai = get_ai_client()
    if ai:
        ai.client.clear_conversation(user_id)
        logger.info(f"[AI] Reset conversation for user {user_id}")
