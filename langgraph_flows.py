#!/usr/bin/env python3
"""
LangGraph对话流程定义 - Villa Booking Bot
实现复杂对话流程：预订流程 + 客诉流程

基于LangGraph 2024-2025最佳实践:
- StateGraph状态机管理
- Conditional Edge条件路由
- Checkpoint持久化
- 多轮对话状态管理
"""

import os
import json
import logging
from typing import TypedDict, Annotated, Literal, Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# LangGraph核心
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)


# ============ 状态定义 ============

class BookingStatus(str, Enum):
    """预订状态枚举"""
    IDLE = "idle"
    SELECTING_REGION = "selecting_region"
    SELECTING_DATES = "selecting_dates"
    SELECTING_VILLA = "selecting_villa"
    ENTERING_GUESTS = "entering_guests"
    ENTERING_CONTACT = "entering_contact"
    CONFIRMING = "confirming"
    AWAITING_PAYMENT = "awaiting_payment"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ComplaintStatus(str, Enum):
    """客诉状态枚举"""
    IDLE = "idle"
    RECEIVING = "receiving"
    CLASSIFYING = "classifying"
    AUTO_HANDLING = "auto_handling"
    ESCALATING = "escalating"
    FOLLOWING_UP = "following_up"
    RESOLVED = "resolved"
    CLOSED = "closed"


class VillaState(TypedDict, total=False):
    """主状态定义 - Villa Bot核心状态"""
    messages: Annotated[list, add_messages]
    flow_type: Literal["booking", "complaint", "general"]
    current_step: str
    booking_status: BookingStatus
    booking_data: Dict[str, Any]
    booking_errors: List[str]
    complaint_status: ComplaintStatus
    complaint_data: Dict[str, Any]
    complaint_category: Optional[str]
    user_id: Optional[str]
    user_language: str
    max_steps: int
    error_count: int


# ============ 预订流程节点 ============

def booking_entry_node(state: VillaState) -> Dict[str, Any]:
    """预订流程入口节点"""
    booking_data = state.get("booking_data", {})
    booking_data.update({
        "step": "region_selection",
        "started_at": datetime.now().isoformat(),
        "user_id": state.get("user_id"),
    })
    
    return {
        "flow_type": "booking",
        "booking_status": BookingStatus.SELECTING_REGION,
        "booking_data": booking_data,
        "current_step": "booking_entry",
        "messages": [{
            "role": "assistant",
            "content": "🏠 欢迎使用别墅预订服务！\n\n请问您想在哪里度假呢？\n\n🏖️ 芭提雅 - 海滨度假\n🏙️ 曼谷 - 都市风情\n🏝️ 普吉岛 - 海岛风光\n\n请直接回复地区名称，如「芭提雅」"
        }]
    }


def classify_region_node(state: VillaState) -> Dict[str, Any]:
    """地区分类节点"""
    user_msg = state["messages"][-1]["content"].lower()
    
    regions = {
        "芭提雅": "pattaya", "pattaya": "pattaya",
        "曼谷": "bangkok", "bangkok": "bangkok",
        "普吉岛": "phuket", "phuket": "phuket"
    }
    
    region_key = None
    for key, value in regions.items():
        if key in user_msg:
            region_key = value
            break
    
    booking_data = state.get("booking_data", {})
    booking_data.update({"region": region_key, "step": "date_selection"})
    
    if region_key:
        region_display = {"pattaya": "🏖️ 芭提雅", "bangkok": "🏙️ 曼谷", "phuket": "🏝️ 普吉岛"}
        return {
            "booking_status": BookingStatus.SELECTING_DATES,
            "booking_data": booking_data,
            "current_step": "region_confirmed",
            "messages": [{
                "role": "assistant",
                "content": f"好的，您选择了{region_display.get(region_key, region_key)}！\n\n📅 请告诉我您的入住日期和退房日期\n\n格式示例：2024-06-01 到 2024-06-05"
            }]
        }
    else:
        return {
            "booking_status": BookingStatus.SELECTING_REGION,
            "booking_errors": state.get("booking_errors", []) + ["无法识别地区"],
            "current_step": "region_selection_failed",
            "messages": [{
                "role": "assistant",
                "content": "抱歉，我无法识别您选择的地区。\n\n请输入：🏖️ 芭提雅 / 🏙️ 曼谷 / 🏝️ 普吉岛"
            }]
        }


def parse_dates_node(state: VillaState) -> Dict[str, Any]:
    """日期解析节点"""
    import re
    user_msg = state["messages"][-1]["content"]
    booking_data = state.get("booking_data", {})
    
    patterns = [r"(\d{4}-\d{2}-\d{2})\s*[至到]\s*(\d{4}-\d{2}-\d{2})"]
    
    for pattern in patterns:
        match = re.search(pattern, user_msg)
        if match:
            checkin, checkout = match.group(1), match.group(2)
            try:
                from datetime import timedelta
                checkin_dt = datetime.strptime(checkin, "%Y-%m-%d")
                checkout_dt = datetime.strptime(checkout, "%Y-%m-%d")
                if checkout_dt <= checkin_dt:
                    raise ValueError("退房日期必须在入住日期之后")
                nights = (checkout_dt - checkin_dt).days
                
                booking_data.update({"checkin": checkin, "checkout": checkout, "nights": nights, "step": "villa_selection"})
                return {
                    "booking_status": BookingStatus.SELECTING_VILLA,
                    "booking_data": booking_data,
                    "current_step": "dates_confirmed",
                    "messages": [{
                        "role": "assistant",
                        "content": f"✅ 日期确认！\n📅 入住：{checkin}\n📅 退房：{checkout}\n🌙 共 {nights} 晚\n\n正在为您查找可用别墅..."
                    }]
                }
            except ValueError as e:
                return {
                    "booking_status": BookingStatus.SELECTING_DATES,
                    "booking_errors": state.get("booking_errors", []) + [str(e)],
                    "messages": [{"role": "assistant", "content": f"日期格式有误：{str(e)}\n\n请重新输入：2024-06-01 到 2024-06-05"}]
                }
    
    return {
        "booking_status": BookingStatus.SELECTING_DATES,
        "messages": [{"role": "assistant", "content": "我无法理解您的日期输入。\n\n格式：2024-06-01 到 2024-06-05"}]
    }


def select_villa_node(state: VillaState) -> Dict[str, Any]:
    """别墅选择节点"""
    booking_data = state.get("booking_data", {})
    region = booking_data.get("region", "pattaya")
    
    villas = _get_available_villas(region)
    
    if not villas:
        return {
            "booking_status": BookingStatus.CANCELLED,
            "current_step": "no_villas_available",
            "messages": [{"role": "assistant", "content": "抱歉，该地区当前没有可用别墅。\n\n请选择其他地区或调整日期。"}]
        }
    
    booking_data.update({"available_villas": villas, "step": "guest_selection"})
    
    villa_list = "\n".join([
        f"{i+1}. {v['name']}\n   💰 {v['price']:,}/晚 | 👥 可住{v['max_guests']}人"
        for i, v in enumerate(villas[:3])
    ])
    
    return {
        "booking_status": BookingStatus.ENTERING_GUESTS,
        "booking_data": booking_data,
        "current_step": "villas_listed",
        "messages": [{
            "role": "assistant",
            "content": f"为您找到 {len(villas)} 套可用别墅：\n\n{villa_list}\n\n请输入别墅编号（1-3）"
        }]
    }


def parse_guests_node(state: VillaState) -> Dict[str, Any]:
    """人数解析节点"""
    import re
    user_msg = state["messages"][-1]["content"]
    booking_data = state.get("booking_data", {})
    villas = booking_data.get("available_villas", [])
    
    villa_index = None
    if user_msg.isdigit() and 1 <= int(user_msg) <= len(villas):
        villa_index = int(user_msg) - 1
    
    match = re.search(r"(\d+)\s*[人位名]", user_msg)
    guests = int(match.group(1)) if match else 2
    
    if villa_index is not None:
        selected_villa = villas[villa_index]
        nights = booking_data.get("nights", 1)
        total_price = selected_villa.get("price", 0) * nights
        
        booking_data.update({
            "selected_villa": selected_villa,
            "villa_name": selected_villa.get("name"),
            "villa_id": selected_villa.get("id"),
            "guests": guests,
            "price_per_night": selected_villa.get("price", 0),
            "total_price": total_price,
            "step": "contact_info"
        })
        
        return {
            "booking_status": BookingStatus.ENTERING_CONTACT,
            "booking_data": booking_data,
            "current_step": "villa_selected",
            "messages": [{
                "role": "assistant",
                "content": f"✅ 已选择：{selected_villa.get('name')}\n\n👥 入住人数：{guests}人\n🌙 住宿晚数：{nights}晚\n💵 总价：฿{total_price:,}\n\n请提供联系信息：\n📝 姓名：\n📱 电话："
            }]
        }
    
    return {
        "booking_status": BookingStatus.ENTERING_GUESTS,
        "messages": [{"role": "assistant", "content": "请选择别墅编号（1-3）"}]
    }


def collect_contact_node(state: VillaState) -> Dict[str, Any]:
    """联系信息收集节点"""
    import re
    user_msg = state["messages"][-1]["content"]
    booking_data = state.get("booking_data", {})
    
    name_match = re.search(r"[姓名字叫]([^电话\d]+?)(?=电话|$)", user_msg)
    phone_match = re.search(r"1[3-9]\d{9}", user_msg)
    
    name = name_match.group(1).strip() if name_match else None
    phone = phone_match.group() if phone_match else None
    
    if name and phone:
        booking_data.update({
            "contact_name": name,
            "contact_phone": phone,
            "step": "confirmation"
        })
        
        return {
            "booking_status": BookingStatus.CONFIRMING,
            "booking_data": booking_data,
            "current_step": "ready_to_confirm",
            "messages": [{
                "role": "assistant",
                "content": f"""📋 预订确认
━━━━━━━━━━━━━━━━━━
🏠 别墅：{booking_data.get('villa_name')}
📅 {booking_data.get('checkin')} 至 {booking_data.get('checkout')}
💵 总价：฿{booking_data.get('total_price', 0):,}
━━━━━━━━━━━━━━━━━━

📝 联系人：{name}
📱 电话：{phone}

请回复「确认」完成预订，或「修改」重新调整"""
            }]
        }
    
    return {
        "booking_status": BookingStatus.ENTERING_CONTACT,
        "messages": [{"role": "assistant", "content": "请提供完整的联系信息：\n\n📝 姓名：XXX\n📱 电话：138-xxxx-xxxx"}]
    }


def confirm_booking_node(state: VillaState) -> Dict[str, Any]:
    """预订确认节点"""
    user_msg = state["messages"][-1]["content"].lower()
    booking_data = state.get("booking_data", {})
    
    if "确认" in user_msg or "confirm" in user_msg:
        booking_id = f"BK{datetime.now().strftime('%Y%m%d%H%M%S')}"
        booking_data.update({
            "booking_id": booking_id,
            "status": "pending_payment",
            "confirmed_at": datetime.now().isoformat()
        })
        
        return {
            "booking_status": BookingStatus.AWAITING_PAYMENT,
            "booking_data": booking_data,
            "current_step": "booking_created",
            "messages": [{
                "role": "assistant",
                "content": f"""✅ 预订成功！
━━━━━━━━━━━━━━━━━━
📋 订单号：{booking_id}
🏠 别墅：{booking_data.get('villa_name')}
💵 总价：฿{booking_data.get('total_price', 0):,}
━━━━━━━━━━━━━━━━━━

请在24小时内完成支付。"""
            }]
        }
    elif "修改" in user_msg or "cancel" in user_msg:
        return {
            "booking_status": BookingStatus.CANCELLED,
            "current_step": "user_cancelled",
            "messages": [{"role": "assistant", "content": "好的，预订已取消。"}]
        }
    
    return {
        "booking_status": BookingStatus.CONFIRMING,
        "messages": [{"role": "assistant", "content": "请回复「确认」完成预订，或「修改」调整信息"}]
    }


# ============ 客诉流程节点 ============

def complaint_entry_node(state: VillaState) -> Dict[str, Any]:
    """客诉流程入口"""
    return {
        "flow_type": "complaint",
        "complaint_status": ComplaintStatus.RECEIVING,
        "complaint_data": {"step": "complaint_received", "started_at": datetime.now().isoformat()},
        "current_step": "complaint_entry",
        "messages": [{
            "role": "assistant",
            "content": """😔 抱歉给您带来不便，我们会认真对待您的反馈。

请描述您遇到的问题：
1. 🏠 房源问题
2. 💰 支付问题
3. 🔧 服务问题
4. 📋 其他"""
        }]
    }


def classify_complaint_node(state: VillaState) -> Dict[str, Any]:
    """客诉分类节点"""
    user_msg = state["messages"][-1]["content"]
    complaint_data = state.get("complaint_data", {})
    
    text_lower = user_msg.lower()
    categories = {
        "支付问题": ["支付", "扣款", "退款", "钱"],
        "房源问题": ["房间", "设施", "卫生", "图片"],
        "服务问题": ["服务", "态度", "沟通"],
    }
    
    category = "其他问题"
    for cat, keywords in categories.items():
        if any(kw in text_lower for kw in keywords):
            category = cat
            break
    
    complaint_data.update({"complaint_text": user_msg, "category": category})
    
    auto_handlable = ["支付问题", "其他问题"]
    
    if category in auto_handlable:
        return {
            "complaint_status": ComplaintStatus.AUTO_HANDLING,
            "complaint_data": complaint_data,
            "complaint_category": category,
            "messages": [{"role": "assistant", "content": f"📂 已收到您的{category}反馈，正在处理..."}]
        }
    else:
        return {
            "complaint_status": ComplaintStatus.ESCALATING,
            "complaint_data": complaint_data,
            "complaint_category": category,
            "messages": [{
                "role": "assistant",
                "content": f"""📂 问题类型：{category}

您的问题已记录，我们的客服团队会尽快与您联系。
⏰ 预计响应时间：2小时内"""
            }]
        }


def auto_handle_complaint_node(state: VillaState) -> Dict[str, Any]:
    """自动处理客诉节点"""
    category = state.get("complaint_category", "")
    
    response_map = {
        "支付问题": "💳 请提供订单号和支付信息，我们会在24小时内核实。",
        "其他问题": "感谢您的反馈，我们已记录您的问题。"
    }
    
    return {
        "complaint_status": ComplaintStatus.FOLLOWING_UP,
        "complaint_data": state.get("complaint_data", {}),
        "messages": [{"role": "assistant", "content": response_map.get(category, "感谢您的反馈。")}]
    }


def escalate_complaint_node(state: VillaState) -> Dict[str, Any]:
    """人工转接节点"""
    complaint_data = state.get("complaint_data", {})
    complaint_data.update({"escalated_at": datetime.now().isoformat()})
    
    return {
        "complaint_status": ComplaintStatus.FOLLOWING_UP,
        "complaint_data": complaint_data,
        "messages": [{"role": "assistant", "content": "👤 正在为您转接人工客服，请稍候..."}]
    }


def follow_up_node(state: VillaState) -> Dict[str, Any]:
    """客诉跟进节点"""
    user_msg = state["messages"][-1]["content"].lower()
    
    if any(word in user_msg for word in ["解决", "好的", "可以", "满意"]):
        return {
            "complaint_status": ComplaintStatus.RESOLVED,
            "messages": [{"role": "assistant", "content": "🌟 感谢您的反馈！祝您生活愉快！"}]
        }
    
    return {
        "complaint_status": ComplaintStatus.FOLLOWING_UP,
        "messages": [{"role": "assistant", "content": "请问您的问题解决了吗？\n✅ 已解决\n❌ 还有问题"}]
    }


# ============ 辅助函数 ============

def _get_available_villas(region: str) -> List[Dict]:
    """获取可用别墅列表（模拟数据）"""
    villa_templates = {
        "pattaya": [
            {"id": "V001", "name": "海景阳光别墅", "price": 4500, "max_guests": 6},
            {"id": "V002", "name": "花园度假屋", "price": 3200, "max_guests": 4},
            {"id": "V003", "name": "沙滩海岸别墅", "price": 5800, "max_guests": 8},
        ],
        "bangkok": [
            {"id": "V101", "name": "湄南河景套房", "price": 3800, "max_guests": 4},
            {"id": "V102", "name": "素坤逸豪华公寓", "price": 2900, "max_guests": 3},
            {"id": "V103", "name": "皇家花园别墅", "price": 5200, "max_guests": 6},
        ],
        "phuket": [
            {"id": "V201", "name": "卡塔海滩别墅", "price": 6500, "max_guests": 8},
            {"id": "V202", "name": "普吉镇复古洋房", "price": 2800, "max_guests": 4},
            {"id": "V203", "name": "苏林海滩私宅", "price": 4800, "max_guests": 6},
        ]
    }
    return villa_templates.get(region, villa_templates["pattaya"])


# ============ 条件路由函数 ============

def booking_route_after_region(state: VillaState) -> Literal["parse_dates", "booking_error"]:
    return "parse_dates" if state.get("booking_data", {}).get("region") else "booking_error"


def booking_route_after_dates(state: VillaState) -> Literal["select_villa", "parse_dates"]:
    return "select_villa" if state.get("booking_data", {}).get("checkin") else "parse_dates"


def booking_route_after_villa(state: VillaState) -> Literal["collect_contact", "parse_guests"]:
    return "collect_contact" if state.get("booking_data", {}).get("selected_villa") else "parse_guests"


def booking_route_after_contact(state: VillaState) -> Literal["confirm_booking", "collect_contact"]:
    return "confirm_booking" if state.get("booking_data", {}).get("contact_name") else "collect_contact"


def complaint_route_after_classify(state: VillaState) -> Literal["auto_handle", "escalate"]:
    return "auto_handle" if state.get("complaint_category") in ["支付问题", "其他问题"] else "escalate"


# ============ 图构建 ============

def create_booking_graph() -> StateGraph:
    """创建预订流程图"""
    workflow = StateGraph(VillaState)
    
    workflow.add_node("booking_entry", booking_entry_node)
    workflow.add_node("classify_region", classify_region_node)
    workflow.add_node("parse_dates", parse_dates_node)
    workflow.add_node("select_villa", select_villa_node)
    workflow.add_node("parse_guests", parse_guests_node)
    workflow.add_node("collect_contact", collect_contact_node)
    workflow.add_node("confirm_booking", confirm_booking_node)
    
    workflow.add_edge(START, "booking_entry")
    workflow.add_edge("classify_region", "parse_dates")
    
    workflow.add_conditional_edges("booking_entry", 
        lambda s: "classify_region" if s.get("booking_data", {}).get("region") else "classify_region",
        {"classify_region": "classify_region"}
    )
    
    workflow.add_conditional_edges("parse_dates", booking_route_after_dates,
        {"select_villa": "select_villa", "parse_dates": "parse_dates"})
    workflow.add_conditional_edges("parse_guests", booking_route_after_villa,
        {"collect_contact": "collect_contact", "select_villa": "select_villa"})
    workflow.add_conditional_edges("collect_contact", booking_route_after_contact,
        {"confirm_booking": "confirm_booking", "collect_contact": "collect_contact"})
    workflow.add_edge("select_villa", "parse_guests")
    
    return workflow.compile(checkpointer=MemorySaver())


def create_complaint_graph() -> StateGraph:
    """创建客诉流程图"""
    workflow = StateGraph(VillaState)
    
    workflow.add_node("complaint_entry", complaint_entry_node)
    workflow.add_node("classify_complaint", classify_complaint_node)
    workflow.add_node("auto_handle", auto_handle_complaint_node)
    workflow.add_node("escalate", escalate_complaint_node)
    workflow.add_node("follow_up", follow_up_node)
    
    workflow.add_edge(START, "complaint_entry")
    workflow.add_edge("complaint_entry", "classify_complaint")
    workflow.add_conditional_edges("classify_complaint", complaint_route_after_classify,
        {"auto_handle": "auto_handle", "escalate": "escalate"})
    workflow.add_edge("auto_handle", "follow_up")
    workflow.add_edge("escalate", "follow_up")
    
    return workflow.compile(checkpointer=MemorySaver())


# 预编译的图实例
booking_graph = create_booking_graph()
complaint_graph = create_complaint_graph()
