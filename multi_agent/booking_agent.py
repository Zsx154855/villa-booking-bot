#!/usr/bin/env python3
"""
BookingAgent - 预订专家Agent
处理预订查询、房源推荐、价格计算
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional

from .context import (
    AgentRequest, AgentResponse, AgentType, IntentType, ContextBuilder
)
from .base import BaseAgent

logger = logging.getLogger(__name__)


class BookingAgent(BaseAgent):
    """预订专家Agent"""
    
    SYSTEM_PROMPT = """你是一个别墅预订专家，专注于房源查询和预订服务。

你负责：
1. 房源查询 - 根据地区、日期、人数筛选可用别墅
2. 房源推荐 - 根据用户偏好推荐合适的别墅
3. 价格计算 - 计算总价、优惠价
4. 预订引导 - 引导用户完成预订流程

可用地区：
- 芭提雅 🏖️ 海滨度假
- 曼谷 🏙️ 都市风情
- 普吉岛 🏝️ 海岛风光

回复要求：
- 专业、热情、有耐心
- 主动提供有用信息
- 复杂问题给出多个选项"""
    
    def __init__(self):
        super().__init__(AgentType.BOOKING)
        self._load_villas()
    
    def _load_villas(self):
        """加载别墅数据"""
        try:
            # 尝试从数据库加载
            import sys
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            import database
            
            self.villas = database.get_all_villas()
            logger.info(f"📦 Loaded {len(self.villas)} villas from database")
        except Exception as e:
            logger.warning(f"⚠️ Failed to load villas: {e}, using mock data")
            self.villas = self._get_mock_villas()
    
    def _get_mock_villas(self) -> List[Dict]:
        """模拟别墅数据"""
        return [
            {"id": "v001", "name": "海景花园别墅", "region": "芭提雅", "price": 3500, "bedrooms": 3},
            {"id": "v002", "name": "都市豪华公寓", "region": "曼谷", "price": 2800, "bedrooms": 2},
            {"id": "v003", "name": "悬崖海景别墅", "region": "普吉岛", "price": 5500, "bedrooms": 4},
        ]
    
    def get_system_prompt(self) -> str:
        return self.SYSTEM_PROMPT
    
    def get_supported_intents(self) -> List[IntentType]:
        return [IntentType.BOOKING]
    
    def get_intent_keywords(self) -> Dict[IntentType, List[str]]:
        return {
            IntentType.BOOKING: [
                "预订", "订房", "预定", "房间", "别墅", "房源", 
                "价格", "推荐", "入住日期", "退房", "几晚", 
                "有哪些", "看看", "查询"
            ]
        }
    
    async def process(self, request: AgentRequest) -> AgentResponse:
        """处理预订相关请求"""
        message = request.raw_message
        params = request.parameters
        user = request.user_context
        
        # 分析意图子类型
        action = self._classify_booking_action(message, params)
        
        logger.info(f"🏠 BookingAgent processing: {action}")
        
        if action == "list_villas":
            return await self._list_villas(request)
        elif action == "filter_villas":
            return await self._filter_villas(request)
        elif action == "recommend":
            return await self._recommend_villas(request)
        elif action == "calculate_price":
            return await self._calculate_price(request)
        elif action == "start_booking":
            return await self._start_booking(request)
        else:
            return await self._general_inquiry(request)
    
    def _classify_booking_action(self, message: str, params: Dict) -> str:
        """分类预订动作"""
        message_lower = message.lower()
        
        if any(kw in message_lower for kw in ["有哪些", "列表", "看看", "全部", "所有"]):
            return "list_villas"
        elif any(kw in message_lower for kw in ["推荐", "哪个好", "适合"]):
            return "recommend"
        elif any(kw in message_lower for kw in ["价格", "多少钱", "算", "费用"]):
            return "calculate_price"
        elif any(kw in message_lower for kw in ["预订", "预定", "订", "开始"]):
            return "start_booking"
        elif params.get("region") or params.get("checkin") or params.get("guests"):
            return "filter_villas"
        else:
            return "general_inquiry"
    
    async def _list_villas(self, request: AgentRequest) -> AgentResponse:
        """列出所有别墅"""
        try:
            region = request.parameters.get("region")
            
            villas = self.villas
            if region:
                villas = [v for v in villas if v.get("region") == region]
            
            if not villas:
                return ContextBuilder.create_success_response(
                    request.request_id,
                    self.agent_type,
                    IntentType.BOOKING,
                    result={"villas": [], "count": 0},
                    message="当前没有找到符合条件的别墅，请尝试其他地区或日期。",
                    suggested_actions=["查看其他地区", "调整筛选条件"]
                )
            
            # 构建消息
            lines = ["🏠 *可用别墅列表：*\n"]
            for v in villas:
                lines.append(f"• {v.get('name', '未知')} ({v.get('region', '')})")
                lines.append(f"  💰 {v.get('price', 0):,} ฿/晚 | 🛏️ {v.get('bedrooms', 0)}卧室\n")
            
            message = "\n".join(lines)
            message += "\n输入\"预订\"开始预订流程"
            
            return ContextBuilder.create_success_response(
                request.request_id,
                self.agent_type,
                IntentType.BOOKING,
                result={"villas": villas, "count": len(villas)},
                message=message,
                suggested_actions=["预订别墅", "查看详情", "筛选地区"]
            )
            
        except Exception as e:
            logger.error(f"List villas error: {e}")
            return ContextBuilder.create_error_response(
                request.request_id,
                self.agent_type,
                IntentType.BOOKING,
                str(e),
                "获取别墅列表失败"
            )
    
    async def _filter_villas(self, request: AgentRequest) -> AgentResponse:
        """筛选别墅"""
        region = request.parameters.get("region")
        checkin = request.parameters.get("checkin")
        checkout = request.parameters.get("checkout")
        guests = request.parameters.get("guests")
        
        try:
            villas = self.villas
            
            if region:
                villas = [v for v in villas if v.get("region") == region]
            
            if guests:
                villas = [v for v in villas if v.get("bedrooms", 0) >= max(1, guests // 2)]
            
            # 如果有日期，检查可用性
            if checkin and checkout:
                try:
                    import sys
                    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    import database
                    
                    available = []
                    for v in villas:
                        if database.check_availability(v['id'], checkin, checkout):
                            available.append(v)
                    villas = available
                except:
                    pass  # 降级处理
            
            if not villas:
                return ContextBuilder.create_success_response(
                    request.request_id,
                    self.agent_type,
                    IntentType.BOOKING,
                    result={},
                    message="没有找到符合条件的别墅。"
                )
            
            # 构建消息
            region_text = f"{region}的" if region else ""
            lines = [f"🔍 *{region_text}筛选结果：*\n"]
            for v in villas[:5]:
                lines.append(f"• {v.get('name')} - {v.get('price', 0):,} ฿/晚")
            
            return ContextBuilder.create_success_response(
                request.request_id,
                self.agent_type,
                IntentType.BOOKING,
                result={"villas": villas, "filters": {"region": region, "checkin": checkin, "guests": guests}},
                message="\n".join(lines)
            )
            
        except Exception as e:
            return ContextBuilder.create_error_response(
                request.request_id,
                self.agent_type,
                IntentType.BOOKING,
                str(e)
            )
    
    async def _recommend_villas(self, request: AgentRequest) -> AgentResponse:
        """推荐别墅"""
        message = """🎯 *智能推荐*

根据您的需求，为您推荐以下热门别墅：

🏖️ **芭提雅推荐**
• 海景花园别墅 - 3卧 | 3,500฿/晚
  ✨ 私人泳池、花园、距海边5分钟

🏙️ **曼谷推荐**
• 都市豪华公寓 - 2卧 | 2,800฿/晚
  ✨ 市中心、天际线景观、购物方便

🏝️ **普吉岛推荐**
• 悬崖海景别墅 - 4卧 | 5,500฿/晚
  ✨ 悬崖景观、无边泳池、私密安静

请告诉我想预订哪个地区的别墅？"""
        
        return ContextBuilder.create_success_response(
            request.request_id,
            self.agent_type,
            IntentType.BOOKING,
            result={"recommended_villas": self.villas[:3]},
            message=message
        )
    
    async def _calculate_price(self, request: AgentRequest) -> AgentResponse:
        """计算价格"""
        checkin = request.parameters.get("checkin")
        checkout = request.parameters.get("checkout")
        
        if not checkin or not checkout:
            message = """💰 *价格计算*

要计算价格，请告诉我：
• 入住日期
• 退房日期
• 别墅选择（可选）

示例：「我想预订普吉岛的别墅，5月10日入住，5月15日退房」"""
        else:
            try:
                from datetime import datetime
                d1 = datetime.strptime(checkin, "%Y-%m-%d")
                d2 = datetime.strptime(checkout, "%Y-%m-%d")
                nights = (d2 - d1).days
                
                if nights <= 0:
                    message = "退房日期必须在入住日期之后"
                else:
                    # 使用第一个别墅计算示例
                    sample_price = self.villas[0].get("price", 3000) if self.villas else 3000
                    total = nights * sample_price
                    
                    message = f"""💰 *价格估算*

📅 入住：{checkin}
📅 退房：{checkout}
🌙 晚数：{nights}晚

🏠 示例价格：{sample_price:,} ฿/晚
💵 总计：约 {total:,} ฿

*实际价格以选择的具体别墅为准*"""
            except Exception as e:
                message = "日期格式有误，请使用 YYYY-MM-DD 格式"
        
        return ContextBuilder.create_success_response(
            request.request_id,
            self.agent_type,
            IntentType.BOOKING,
            result={"checkin": checkin, "checkout": checkout},
            message=message
        )
    
    async def _start_booking(self, request: AgentRequest) -> AgentResponse:
        """开始预订"""
        message = """📝 *开始预订*

请依次告诉我：
1️⃣ 想预订哪个地区？（芭提雅/曼谷/普吉岛）
2️⃣ 入住日期？
3️⃣ 退房日期？
4️⃣ 入住人数？

或者直接说「帮我预订普吉岛别墅，X月X日入住，X日后退房」"""
        
        return ContextBuilder.create_success_response(
            request.request_id,
            self.agent_type,
            IntentType.BOOKING,
            result={"next_step": "collect_booking_info"},
            message=message
        )
    
    async def _general_inquiry(self, request: AgentRequest) -> AgentResponse:
        """一般咨询"""
        message = """🏠 *别墅预订服务*

我可以帮您：
• 查看各地区别墅列表
• 根据日期筛选可用房源
• 推荐适合的别墅
• 计算预订价格
• 引导完成预订

请告诉我您想了解什么？"""
        
        return ContextBuilder.create_success_response(
            request.request_id,
            self.agent_type,
            IntentType.BOOKING,
            result={},
            message=message
        )
