#!/usr/bin/env python3
"""
LangGraph集成层 - Villa Booking Bot
将LangGraph流程集成到现有bot.py架构中
"""

import os
import logging
from typing import Dict, Any, Optional, Callable
from enum import Enum

from .langgraph_flows import (
    VillaState,
    BookingStatus,
    ComplaintStatus,
    booking_graph,
    complaint_graph,
)

logger = logging.getLogger(__name__)


class FlowType(str, Enum):
    BOOKING = "booking"
    COMPLAINT = "complaint"
    GENERAL = "general"


class LangGraphManager:
    """LangGraph对话管理器"""
    
    def __init__(self, checkpointer=None):
        self._booking_graph = booking_graph
        self._complaint_graph = complaint_graph
        self._user_states: Dict[str, Dict[str, Any]] = {}
        self._active_flows: Dict[str, FlowType] = {}
        self._callbacks: Dict[str, Callable] = {}
        logger.info("✅ LangGraphManager initialized")
    
    def set_callback(self, event: str, callback: Callable):
        """设置回调函数"""
        self._callbacks[event] = callback
    
    def start_booking_flow(self, user_id: str, initial_message: str = "") -> Dict[str, Any]:
        """开始预订流程"""
        self._active_flows[user_id] = FlowType.BOOKING
        
        initial_state: VillaState = {
            "messages": [{"role": "user", "content": initial_message}] if initial_message else [],
            "flow_type": "booking",
            "current_step": "init",
            "booking_status": BookingStatus.IDLE,
            "booking_data": {},
            "booking_errors": [],
            "user_id": user_id,
            "user_language": "zh",
            "max_steps": 20,
            "error_count": 0
        }
        
        try:
            result = self._booking_graph.invoke(
                initial_state,
                config={"configurable": {"thread_id": f"booking_{user_id}"}}
            )
            self._user_states[user_id] = result
            return {"success": True, "response": self._format_response(result), "state": result}
        except Exception as e:
            logger.error(f"Booking flow error: {e}")
            return {"success": False, "error": str(e), "response": "处理出错，请重试。"}
    
    def continue_booking_flow(self, user_id: str, message: str) -> Dict[str, Any]:
        """继续预订流程"""
        if self._active_flows.get(user_id) != FlowType.BOOKING:
            return {"success": False, "response": "当前没有活跃的预订流程"}
        
        current_state = self._user_states.get(user_id, {})
        messages = current_state.get("messages", [])
        messages.append({"role": "user", "content": message})
        
        new_state: VillaState = {
            **current_state,
            "messages": messages,
            "user_id": user_id,
            "max_steps": current_state.get("max_steps", 20) - 1,
        }
        
        try:
            result = self._booking_graph.invoke(
                new_state,
                config={"configurable": {"thread_id": f"booking_{user_id}"}}
            )
            self._user_states[user_id] = result
            return {
                "success": True,
                "response": self._format_response(result),
                "state": result,
                "is_complete": result.get("booking_status") == BookingStatus.AWAITING_PAYMENT
            }
        except Exception as e:
            logger.error(f"Continue booking error: {e}")
            return {"success": False, "error": str(e), "response": "处理失败，请重试。"}
    
    def start_complaint_flow(self, user_id: str, initial_message: str = "") -> Dict[str, Any]:
        """开始客诉流程"""
        self._active_flows[user_id] = FlowType.COMPLAINT
        
        initial_state: VillaState = {
            "messages": [{"role": "user", "content": initial_message}] if initial_message else [],
            "flow_type": "complaint",
            "current_step": "init",
            "complaint_status": ComplaintStatus.IDLE,
            "complaint_data": {},
            "user_id": user_id,
            "user_language": "zh",
            "max_steps": 15,
            "error_count": 0
        }
        
        try:
            result = self._complaint_graph.invoke(
                initial_state,
                config={"configurable": {"thread_id": f"complaint_{user_id}"}}
            )
            self._user_states[user_id] = result
            return {"success": True, "response": self._format_response(result), "state": result}
        except Exception as e:
            logger.error(f"Complaint flow error: {e}")
            return {"success": False, "error": str(e), "response": "处理出错，请重试。"}
    
    def continue_complaint_flow(self, user_id: str, message: str) -> Dict[str, Any]:
        """继续客诉流程"""
        if self._active_flows.get(user_id) != FlowType.COMPLAINT:
            return {"success": False, "response": "当前没有活跃的客诉流程"}
        
        current_state = self._user_states.get(user_id, {})
        messages = current_state.get("messages", [])
        messages.append({"role": "user", "content": message})
        
        new_state: VillaState = {
            **current_state,
            "messages": messages,
            "user_id": user_id,
            "max_steps": current_state.get("max_steps", 15) - 1
        }
        
        try:
            result = self._complaint_graph.invoke(
                new_state,
                config={"configurable": {"thread_id": f"complaint_{user_id}"}}
            )
            self._user_states[user_id] = result
            return {
                "success": True,
                "response": self._format_response(result),
                "state": result,
                "is_resolved": result.get("complaint_status") == ComplaintStatus.RESOLVED
            }
        except Exception as e:
            logger.error(f"Continue complaint error: {e}")
            return {"success": False, "error": str(e), "response": "处理失败，请重试。"}
    
    def detect_flow_type(self, message: str) -> FlowType:
        """检测消息意图"""
        message_lower = message.lower()
        complaint_keywords = ["投诉", "反馈", "问题", "不满"]
        booking_keywords = ["预订", "预定", "订房"]
        
        for kw in complaint_keywords:
            if kw in message_lower:
                return FlowType.COMPLAINT
        for kw in booking_keywords:
            if kw in message_lower:
                return FlowType.BOOKING
        return FlowType.GENERAL
    
    def handle_message(self, user_id: str, message: str) -> Dict[str, Any]:
        """统一消息处理入口"""
        active_flow = self._active_flows.get(user_id)
        
        if active_flow == FlowType.BOOKING:
            return self.continue_booking_flow(user_id, message)
        elif active_flow == FlowType.COMPLAINT:
            return self.continue_complaint_flow(user_id, message)
        
        flow_type = self.detect_flow_type(message)
        
        if flow_type == FlowType.BOOKING:
            return self.start_booking_flow(user_id, message)
        elif flow_type == FlowType.COMPLAINT:
            return self.start_complaint_flow(user_id, message)
        
        return {
            "success": True,
            "response": "您好！我是Taimili别墅预订助手。\n\n🏠 输入「预订」开始预订\n📝 输入「投诉」反馈问题"
        }
    
    def cancel_flow(self, user_id: str) -> Dict[str, Any]:
        """取消当前流程"""
        if user_id in self._active_flows:
            del self._active_flows[user_id]
        if user_id in self._user_states:
            del self._user_states[user_id]
        return {"success": True, "response": "流程已取消。"}
    
    def get_user_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self._user_states.get(user_id)
    
    def is_flow_active(self, user_id: str) -> bool:
        return user_id in self._active_flows
    
    def get_active_flow_type(self, user_id: str) -> Optional[FlowType]:
        return self._active_flows.get(user_id)
    
    def get_booking_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        state = self._user_states.get(user_id)
        return state.get("booking_data") if state else None
    
    def reset_user(self, user_id: str):
        if user_id in self._active_flows:
            del self._active_flows[user_id]
        if user_id in self._user_states:
            del self._user_states[user_id]
    
    def _format_response(self, state: Dict[str, Any]) -> str:
        messages = state.get("messages", [])
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if isinstance(content, list):
                    return "\n".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in content])
                return str(content)
        return "处理中..."


# ============ 全局实例 ============

langgraph_manager: Optional[LangGraphManager] = None


def init_langgraph():
    global langgraph_manager
    if langgraph_manager is None:
        langgraph_manager = LangGraphManager()
        logger.info("✅ LangGraph system initialized")
    return langgraph_manager


def get_langgraph_manager() -> LangGraphManager:
    global langgraph_manager
    if langgraph_manager is None:
        langgraph_manager = init_langgraph()
    return langgraph_manager


# ============ Telegram Handler集成示例 ============

async def langgraph_message_handler(update, context) -> None:
    """LangGraph消息处理器示例"""
    user_id = str(update.effective_user.id)
    message = update.message.text
    
    manager = get_langgraph_manager()
    
    if message in ["取消", "退出", "/cancel"]:
        result = manager.cancel_flow(user_id)
        await update.message.reply_text(result["response"])
        return
    
    result = manager.handle_message(user_id, message)
    
    if result["success"]:
        await update.message.reply_text(result["response"])
        if result.get("is_complete"):
            logger.info(f"Booking completed: {manager.get_booking_data(user_id)}")
    else:
        await update.message.reply_text(result.get("response", "处理失败，请重试。"))


"""
集成到bot.py的步骤：

1. 添加导入：
   from langgraph_integration import get_langgraph_manager, langgraph_message_handler

2. 在初始化时调用：
   langgraph_manager = init_langgraph()

3. 添加消息处理器：
   app.add_handler(MessageHandler(
       filters.TEXT & ~filters.COMMAND,
       langgraph_message_handler
   ))
"""
