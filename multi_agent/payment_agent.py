#!/usr/bin/env python3
"""
PaymentAgent - 支付专家Agent
处理支付、退款、发票等财务相关事务
"""

import os
import logging
from typing import Dict, Any, List

from .context import (
    AgentRequest, AgentResponse, AgentType, IntentType, ContextBuilder
)
from .base import BaseAgent

logger = logging.getLogger(__name__)


class PaymentAgent(BaseAgent):
    """支付专家Agent"""
    
    def __init__(self):
        super().__init__(AgentType.PAYMENT)
    
    SYSTEM_PROMPT = """你是一个支付服务专家，专注于别墅预订的财务相关服务。

你负责：
1. 支付指引 - 多种支付方式说明
2. 退款处理 - 退款政策与流程
3. 发票服务 - 发票开具与寄送
4. 优惠活动 - 优惠券、折扣码使用
5. 积分系统 - 积分获取与兑换

支付方式：
• 支付宝/微信 - 即时到账
• 银行卡 - 国际信用卡
• 银行转账 - 支持泰铢/人民币

回复要求：
- 专业、清晰
- 涉及金额时务必准确
- 强调安全和保障"""
    
    def get_system_prompt(self) -> str:
        return self.SYSTEM_PROMPT
    
    def get_supported_intents(self) -> List[IntentType]:
        return [IntentType.PAYMENT]
    
    def get_intent_keywords(self) -> Dict[IntentType, List[str]]:
        return {
            IntentType.PAYMENT: [
                "支付", "付款", "怎么付", "钱", "转账",
                "退款", "取消", "退钱",
                "发票", "收据", "报销",
                "优惠", "折扣", "优惠券", "promo", "code",
                "积分", "points", "兑换"
            ]
        }
    
    async def process(self, request: AgentRequest) -> AgentResponse:
        """处理支付相关请求"""
        message = request.raw_message
        
        # 分析支付类型
        action = self._classify_payment_action(message)
        
        logger.info(f"💳 PaymentAgent processing: {action}")
        
        if action == "payment_guide":
            return await self._payment_guide(request)
        elif action == "refund":
            return await self._refund_service(request)
        elif action == "invoice":
            return await self._invoice_service(request)
        elif action == "coupon":
            return await self._coupon_service(request)
        elif action == "points":
            return await self._points_service(request)
        else:
            return await self._general_payment(request)
    
    def _classify_payment_action(self, message: str) -> str:
        """分类支付动作"""
        message_lower = message.lower()
        
        if any(kw in message_lower for kw in ["支付", "付款", "怎么付", "转账"]):
            return "payment_guide"
        elif any(kw in message_lower for kw in ["退款", "退钱", "取消预订", "取消订单"]):
            return "refund"
        elif any(kw in message_lower for kw in ["发票", "收据", "报销"]):
            return "invoice"
        elif any(kw in message_lower for kw in ["优惠", "折扣", "优惠券", "promo", "code", "折扣码"]):
            return "coupon"
        elif any(kw in message_lower for kw in ["积分", "points", "兑换"]):
            return "points"
        else:
            return "general_payment"
    
    async def _payment_guide(self, request: AgentRequest) -> AgentResponse:
        """支付指引"""
        message = """💳 *支付指南*

我们支持以下支付方式：

🇨🇳 **中国用户推荐**
• 支付宝 Alipay - 即时到账，汇率最优
• 微信支付 WeChat Pay - 方便快捷
• 银行转账 - 支持中国各大银行

💳 **国际支付**
• Visa/Mastercard 信用卡
• PayPal - 国际支付
• Stripe - 安全支付

💰 **货币选择**
• 泰铢 (THB) - 当地价格
• 人民币 (CNY) - 按实时汇率结算

📋 **支付流程**
1. 选择房型并确认预订信息
2. 选择支付方式
3. 完成支付（扫码/跳转）
4. 收到支付确认

🔒 **安全保障**
• 所有支付经过加密处理
• 支持7天内无条件退款
• 支付失败全额退款

如需支付，请告诉我您的预订信息，我来帮您生成支付链接！"""
        
        return ContextBuilder.create_success_response(
            request.request_id,
            self.agent_type,
            IntentType.PAYMENT,
            result={"action": "payment_guide"},
            message=message,
            suggested_actions=["使用优惠码", "查看积分", "联系客服"]
        )
    
    async def _refund_service(self, request: AgentRequest) -> AgentResponse:
        """退款服务"""
        message = """💰 *退款政策*

🏠 **退款规则**

✅ **可全额退款**
• 入住前7天以上取消
• 房源/房东原因导致无法入住
• 支付后24小时内（犹豫期）

⚠️ **部分退款**
• 入住前3-7天取消：退还50%
• 入住前1-2天取消：退还20%
• 入住当天取消：不退款

❌ **不可退款**
• 已过入住日期
• 提前离店
• 违反房源规定

📋 **退款流程**
1. 提交取消申请
2. 审核通过（1-3个工作日）
3. 原路退回（3-7个工作日）

💳 **退款方式**
• 支付宝/微信：3-5个工作日
• 信用卡：5-7个工作日
• 银行卡：3-5个工作日

⚠️ **注意事项**
• 汇率差由用户承担
• 部分平台手续费不退

如需取消预订，请告诉我您的订单号，我来帮您处理！"""
        
        return ContextBuilder.create_success_response(
            request.request_id,
            self.agent_type,
            IntentType.PAYMENT,
            result={"action": "refund"},
            message=message,
            suggested_actions=["取消预订", "查看退款进度", "联系客服"]
        )
    
    async def _invoice_service(self, request: AgentRequest) -> AgentResponse:
        """发票服务"""
        message = """🧾 *发票服务*

我们可为您提供以下票据：

📄 **可选票据类型**
• 增值税普通发票（电子）
• 收据（非正式票据）
• 行程确认单（包含预订详情）

📝 **发票申请**
请提供以下信息：
1. 发票抬头（公司/个人）
2. 税号（如需公司发票）
3. 接收邮箱
4. 预订确认号

📧 **开具时间**
• 支付完成后3个工作日内
• 电子发票发送至邮箱
• 纸质发票需额外5个工作日

💰 **发票金额**
• 默认为实际支付金额
• 如需分拆发票请提前说明
• 汇率按支付当日计算

📮 **邮寄服务**
• 泰国境内：免费
• 国际邮寄：按实际费用收取
• 预计7-14个工作日到达

🔍 **验证真伪**
发票可通过官网输入发票号验证"""
        
        return ContextBuilder.create_success_response(
            request.request_id,
            self.agent_type,
            IntentType.PAYMENT,
            result={"action": "invoice"},
            message=message,
            suggested_actions=["申请发票", "查看开票进度", "联系客服"]
        )
    
    async def _coupon_service(self, request: AgentRequest) -> AgentResponse:
        """优惠服务"""
        message = """🎟️ *优惠活动*

💰 **当前优惠**

🎁 **新用户专享**
• 首次预订满1000元减100元
• 使用邀请码再减50元

🏷️ **限时折扣**
• 本周特惠：曼谷区域8折
• 周末特惠：连续入住3晚95折

📱 **会员专享**
• 银卡会员：9.5折
• 金卡会员：9折 + 免服务费

💵 **积分抵现**
• 100积分 = 1元
• 入住后自动获得积分

🔑 **折扣码使用**
输入折扣码可享额外优惠：
• FIRST100 - 首单立减100元
• SUMMER20 - 夏季特惠8折
• GROUP30 - 团购满5人减300元

📝 **使用规则**
• 每笔订单限用一张优惠券
• 优惠券不可叠加
• 部分房源不参与优惠
• 有效期至每年12月31日

💡 **如何获取优惠码？**
• 关注公众号获取最新活动
• 老用户邀请新用户
• 参加平台活动"""
        
        return ContextBuilder.create_success_response(
            request.request_id,
            self.agent_type,
            IntentType.PAYMENT,
            result={"action": "coupon"},
            message=message,
            suggested_actions=["输入折扣码", "查看我的优惠券", "邀请好友"]
        )
    
    async def _points_service(self, request: AgentRequest) -> AgentResponse:
        """积分服务"""
        message = """⭐ *积分系统*

💎 **积分获取**
• 每消费1元 = 1积分
• 评价入住体验 = 50积分
• 邀请好友注册 = 100积分
• 邀请好友预订 = 500积分

🎁 **积分兑换**
• 100积分 = 1元
• 500积分 = 清洁服务一次
• 1000积分 = 接机服务一次
• 5000积分 = 免房费200元

👑 **会员等级**
🥉 **银卡**：注册即得
  • 9.5折优惠
  • 积分1:1

🥈 **金卡**：累计消费5000元
  • 9折优惠 + 免服务费
  • 积分1.2倍
  • 优先客服

🥇 **黑卡**：累计消费20000元
  • 8.5折 + 免服务费
  • 积分1.5倍
  • 专属管家服务
  • 生日专属优惠

📊 **查看积分**
发送「积分」可查看当前积分和等级

💡 **积分过期**
• 积分有效期2年
• 过期前30天提醒
• 等级每年重新评估"""
        
        return ContextBuilder.create_success_response(
            request.request_id,
            self.agent_type,
            IntentType.PAYMENT,
            result={"action": "points"},
            message=message,
            suggested_actions=["查看积分余额", "积分兑换", "升级会员"]
        )
    
    async def _general_payment(self, request: AgentRequest) -> AgentResponse:
        """一般支付咨询"""
        message = """💳 *支付服务*

我可以帮您处理：

💰 **支付相关**
• 支付方式介绍
• 支付问题解决
• 支付确认查询

💵 **退款相关**
• 退款政策查询
• 取消预订
• 退款进度查询

🧾 **票据相关**
• 发票申请
• 收据获取
• 报销材料

🎫 **优惠相关**
• 优惠券使用
• 折扣码输入
• 优惠活动查询

⭐ **积分相关**
• 积分查询
• 积分兑换
• 会员等级

请告诉我您需要什么帮助？"""
        
        return ContextBuilder.create_success_response(
            request.request_id,
            self.agent_type,
            IntentType.PAYMENT,
            result={"action": "general"},
            message=message,
            suggested_actions=["支付指南", "查看优惠券", "联系客服"]
        )
