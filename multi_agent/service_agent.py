#!/usr/bin/env python3
"""
ServiceAgent - 运营服务专家Agent
处理入住/退房、清洁、维修等运营服务
"""

import os
import logging
from typing import Dict, Any, List

from .context import (
    AgentRequest, AgentResponse, AgentType, IntentType, ContextBuilder
)
from .base import BaseAgent

logger = logging.getLogger(__name__)


class ServiceAgent(BaseAgent):
    """运营服务专家Agent"""
    
    def __init__(self):
        super().__init__(AgentType.SERVICE)
    
    SYSTEM_PROMPT = """你是一个别墅运营服务专家，专注于入住后的各项服务。

你负责：
1. 入住指引 - 房间位置、钥匙获取、入住流程
2. 退房服务 - 退房时间、钥匙归还、行李寄存
3. 清洁服务 - 房间清洁、加床加枕
4. 维修服务 - 设施故障报修
5. 其他服务 - 接送机、旅游定制、购物服务

服务时间：24小时在线
响应速度：一般问题30分钟内回复

回复要求：
- 耐心、细致、有同理心
- 主动询问具体情况
- 提供清晰的解决步骤"""
    
    def get_system_prompt(self) -> str:
        return self.SYSTEM_PROMPT
    
    def get_supported_intents(self) -> List[IntentType]:
        return [IntentType.SERVICE]
    
    def get_intent_keywords(self) -> Dict[IntentType, List[str]]:
        return {
            IntentType.SERVICE: [
                "入住", "退房", "钥匙", "门卡", "清洁", "打扫",
                "维修", "坏了", "坏了", "空调", "热水器", "wifi",
                "问题", "投诉", "反馈", "服务", "接送", "行李"
            ]
        }
    
    async def process(self, request: AgentRequest) -> AgentResponse:
        """处理服务相关请求"""
        message = request.raw_message
        user = request.user_context
        
        # 分析服务类型
        action = self._classify_service_action(message)
        
        logger.info(f"🛠️ ServiceAgent processing: {action}")
        
        if action == "checkin_guide":
            return await self._checkin_guide(request)
        elif action == "checkout_service":
            return await self._checkout_service(request)
        elif action == "cleaning":
            return await self._cleaning_service(request)
        elif action == "maintenance":
            return await self._maintenance_service(request)
        elif action == "complaint":
            return await self._complaint_handler(request)
        elif action == "transport":
            return await self._transport_service(request)
        else:
            return await self._general_service(request)
    
    def _classify_service_action(self, message: str) -> str:
        """分类服务动作"""
        message_lower = message.lower()
        
        if any(kw in message_lower for kw in ["入住", "钥匙", "门卡", "怎么进"]):
            return "checkin_guide"
        elif any(kw in message_lower for kw in ["退房", "还钥匙", "离开"]):
            return "checkout_service"
        elif any(kw in message_lower for kw in ["清洁", "打扫", "换床单", "整理"]):
            return "cleaning"
        elif any(kw in message_lower for kw in ["维修", "坏了", "坏了", "空调", "热水器", "马桶", "wifi"]):
            return "maintenance"
        elif any(kw in message_lower for kw in ["投诉", "不满", "反馈"]):
            return "complaint"
        elif any(kw in message_lower for kw in ["接送", "接机", "送机", "交通"]):
            return "transport"
        else:
            return "general_service"
    
    async def _checkin_guide(self, request: AgentRequest) -> AgentResponse:
        """入住指引"""
        message = """🔑 *入住指南*

亲爱的客人，欢迎入住！请按以下步骤完成入住：

📍 *地址获取*
预订确认后，您会收到详细的别墅地址和定位链接。

🔐 *入住方式*
1. **密码锁**：别墅大门使用密码锁，密码已发送至您的邮箱/手机
2. **智能钥匙**：部分别墅支持手机NFC解锁

📋 *入住流程*
1. 到达别墅后，先确认别墅外观与照片一致
2. 输入密码或使用钥匙进入
3. 检查屋内设施是否完好
4. 如有问题请在30分钟内联系我们

🕐 *入住时间*：14:00 后
🔚 *退房时间*：12:00 前

有任何问题请随时联系我们！"""
        
        return ContextBuilder.create_success_response(
            request.request_id,
            self.agent_type,
            IntentType.SERVICE,
            result={"action": "checkin_guide"},
            message=message,
            suggested_actions=["查看退房指南", "联系客服", "预约清洁"]
        )
    
    async def _checkout_service(self, request: AgentRequest) -> AgentResponse:
        """退房服务"""
        message = """🔚 *退房指南*

请在中午12:00前完成退房：

📋 *退房流程*
1. 检查个人物品，不要遗漏
2. 将使用过的毛巾/床单放在指定位置
3. 处理垃圾（厨房、卫生间）
4. 关闭空调、灯光
5. 锁好门窗

🔑 *还钥匙*
- 密码锁：直接离开即可，系统自动失效密码
- 实体钥匙：放在客厅茶几上或联系管家取回

📦 *行李寄存*
如需寄存行李，请提前1小时告知我们。

⚠️ *超时费用*
每超1小时加收房费的10%，敬请配合。"""
        
        return ContextBuilder.create_success_response(
            request.request_id,
            self.agent_type,
            IntentType.SERVICE,
            result={"action": "checkout_service"},
            message=message,
            suggested_actions=["延时退房", "预约接机", "评价服务"]
        )
    
    async def _cleaning_service(self, request: AgentRequest) -> AgentResponse:
        """清洁服务"""
        message = """🧹 *清洁服务*

我们提供以下清洁服务：

⏰ *服务时间*：9:00 - 21:00

💰 *服务项目及价格*
• 基础打扫：300฿/次（垃圾清理、地面清扫）
• 深度清洁：500฿/次（床单更换、卫生间消毒）
• 换洗床单：200฿/套
• 加浴巾：50฿/条

📝 *预约方式*
请提前2小时预约，告诉管家：
- 需要的清洁类型
- 希望清洁的时间
- 别墅地址/房间号

🏠 *免费服务*
入住超过3晚可享受一次免费基础打扫！"""
        
        return ContextBuilder.create_success_response(
            request.request_id,
            self.agent_type,
            IntentType.SERVICE,
            result={"action": "cleaning", "service_type": "cleaning"},
            message=message,
            suggested_actions=["立即预约", "查看更多服务", "联系管家"]
        )
    
    async def _maintenance_service(self, request: AgentRequest) -> AgentResponse:
        """维修服务"""
        message = """🔧 *维修服务*

设施出现问题？我们来帮您解决！

⚡ *常见问题快速处理*

🌡️ **空调不制冷**
1. 检查遥控器是否开启
2. 温度设置是否正确（建议24-26℃）
3. 滤网是否需要清洗
4. 如仍不行，请联系我们

🚿 **热水器问题**
1. 检查电源是否开启
2. 等待2-3分钟出水
3. 部分热水器需等待加热

📶 **WiFi连接**
1. 检查路由器是否通电（一般在大门旁）
2. 搜索WiFi名称：Villa-XXX
3. 密码：12345678 或询问管家

🆘 *仍有问题？*
请描述具体情况（别墅名称、设施问题、您的房号）
我们会尽快安排人员上门处理！

⏱️ 响应时间：白天30分钟内，夜间1小时内"""
        
        return ContextBuilder.create_success_response(
            request.request_id,
            self.agent_type,
            IntentType.SERVICE,
            result={"action": "maintenance"},
            message=message,
            suggested_actions=["预约维修", "联系管家", "紧急求助"]
        )
    
    async def _complaint_handler(self, request: AgentRequest) -> AgentResponse:
        """投诉处理"""
        message = """😔 *感谢您的反馈*

对服务有任何不满，请告诉我们，我们会立即处理！

📝 *请简单描述*
1. 遇到了什么问题？
2. 发生的时间和地点？
3. 您的别墅/房间号？

🔔 *我们承诺*
• 24小时内给出解决方案
• 合理的赔偿或补偿
• 持续跟进直到您满意

📞 *紧急情况*
如需立即处理，请拨打客服热线：
+66 XX XXX XXXX

您的反馈是我们改进的动力，感谢您的理解与支持！"""
        
        return ContextBuilder.create_success_response(
            request.request_id,
            self.agent_type,
            IntentType.SERVICE,
            result={"action": "complaint"},
            message=message,
            suggested_actions=["提交反馈", "联系客服", "查看常见问题"]
        )
    
    async def _transport_service(self, request: AgentRequest) -> AgentResponse:
        """交通服务"""
        message = """🚗 *交通服务*

我们提供以下接送服务：

🚕 **送机服务**
• 芭提雅 → 机场：800฿
• 曼谷 → 机场：600฿
• 普吉岛 → 机场：500฿

🚙 **接机服务**（同价）

🚘 **包车服务**
• 半天（4小时）：1,200฿
• 全天（8小时）：2,000฿
• 含中文司机

📍 **周边出行**
• 曼谷：BTS/MRT地铁票代购
• 普吉岛：双条车/摩的预约
• 芭提雅：双条车随叫随停

📝 **预约方式**
请提前至少6小时预约，提供：
- 日期和时间
- 人数
- 目的地
- 别墅地址"""
        
        return ContextBuilder.create_success_response(
            request.request_id,
            self.agent_type,
            IntentType.SERVICE,
            result={"action": "transport"},
            message=message,
            suggested_actions=["预约送机", "包车一日游", "查看交通攻略"]
        )
    
    async def _general_service(self, request: AgentRequest) -> AgentResponse:
        """一般服务咨询"""
        message = """🛎️ *服务咨询*

我可以帮您处理以下事项：

🏠 **入住/退房**
• 入住指南、钥匙获取
• 退房流程、延时服务

🧹 **清洁服务**
• 日常打扫、床单换洗
• 深度清洁

🔧 **维修服务**
• 设施故障报修
• 快速问题排查

🚗 **交通服务**
• 接机/送机
• 包车一日游

🛒 **增值服务**
• 旅游定制
• 购物代购
• 餐厅预约

请告诉我您需要什么帮助？"""
        
        return ContextBuilder.create_success_response(
            request.request_id,
            self.agent_type,
            IntentType.SERVICE,
            result={"action": "general"},
            message=message,
            suggested_actions=["入住指南", "预约清洁", "联系客服"]
        )
