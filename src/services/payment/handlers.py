"""
Taimili Villa Booking - Payment Handlers
支付处理函数 - 集成Stripe到Telegram Bot
"""

import os
import logging
from typing import Optional, Dict, Any, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# 导入数据库模块
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import database

# 配置日志
logger = logging.getLogger(__name__)

# ============ 支付服务初始化 ============
_payment_service = None

def get_payment_service():
    """获取支付服务实例（延迟初始化）"""
    global _payment_service
    if _payment_service is None:
        from .stripe_payment import StripePaymentService
        
        stripe_key = os.environ.get("STRIPE_SECRET_KEY")
        webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
        
        if not stripe_key:
            logger.warning("⚠️ STRIPE_SECRET_KEY 未配置，支付功能暂时不可用")
            return None
        
        _payment_service = StripePaymentService(stripe_key, webhook_secret)
        logger.info("✅ Stripe支付服务初始化成功")
    
    return _payment_service

# ============ 支付命令处理 ============
async def pay_command(update, context, booking_id: str = None) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
    """
    处理 /pay 命令
    显示支付链接或二维码
    
    Args:
        update: Telegram Update
        context: Bot context
        booking_id: 预订ID（可选，如果不提供则从 context.args 获取）
        
    Returns:
        (message_text, reply_markup)
    """
    # 解析预订ID
    if not booking_id:
        if context and context.args:
            booking_id = context.args[0].upper().strip()
        else:
            return (
                "📝 *发起支付*\n\n"
                "请提供预订编号：\n"
                "`/pay <预订编号>`\n\n"
                "例如：`/pay ABC12345`\n\n"
                "💡 您可以使用 /mybookings 查看您的预订",
                None
            )
    
    # 获取预订信息
    booking = database.get_booking(booking_id)
    
    if not booking:
        return (
            f"❌ 未找到预订 `{booking_id}`\n\n"
            "请检查预订编号是否正确",
            None
        )
    
    # 检查预订状态
    if booking['status'] in ['confirmed', 'paid', 'completed']:
        return (
            f"✅ 预订 `{booking_id}` 已经支付完成\n\n"
            f"状态：已确认\n"
            f"别墅：{booking.get('villa_name', 'N/A')}\n"
            f"入住：{booking.get('checkin', '')} → {booking.get('checkout', '')}",
            None
        )
    
    if booking['status'] == 'cancelled':
        return (
            f"❌ 预订 `{booking_id}` 已取消\n\n"
            "无法进行支付",
            None
        )
    
    # 获取支付服务
    payment_service = get_payment_service()
    if not payment_service:
        return (
            "⚠️ 支付功能暂时不可用\n\n"
            "请稍后再试或联系客服：@TaimiliSupport",
            None
        )
    
    # 创建支付
    from .base import PaymentRequest
    
    total_price = booking.get('total_price', 0)
    
    # 计算价格（确保有合理金额）
    if total_price <= 0:
        # 如果total_price为0，使用默认价格
        villa = database.get_villa(booking.get('villa_id', ''))
        if villa:
            from datetime import datetime
            checkin = datetime.strptime(booking.get('checkin', ''), "%Y-%m-%d")
            checkout = datetime.strptime(booking.get('checkout', ''), "%Y-%m-%d")
            nights = (checkout - checkin).days
            total_price = villa.get('price_per_night', 0) * nights
    
    # 创建支付请求
    payment_request = PaymentRequest(
        booking_id=booking_id,
        amount=total_price,
        currency="THB",
        description=f"Villa Booking {booking_id} - {booking.get('villa_name', '')}",
        customer_email=None,
        customer_name=booking.get('contact_name'),
        metadata={
            'user_id': booking.get('user_id'),
            'villa_name': booking.get('villa_name', ''),
            'checkin': booking.get('checkin', ''),
            'checkout': booking.get('checkout', '')
        }
    )
    
    # 创建Payment Intent
    result = await payment_service.create_payment(payment_request)
    
    if not result.success:
        return (
            f"❌ 支付创建失败\n\n"
            f"错误：{result.message}\n\n"
            "请联系客服处理",
            None
        )
    
    # 保存payment_id到预订
    database.update_booking_field(booking_id, 'payment_id', result.payment_id)
    
    # 构建支付信息
    client_secret = result.metadata.get('client_secret', '')
    
    # Stripe支付链接（适用于移动端）
    stripe_publishable_key = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
    payment_link = f"https://checkout.stripe.com/pay/{client_secret}" if client_secret else None
    
    message = (
        f"💳 *支付订单*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 预订编号：`{booking_id}`\n"
        f"🏠 别墅：{booking.get('villa_name', 'N/A')}\n"
        f"📅 入住：{booking.get('checkin', '')}\n"
        f"📅 退房：{booking.get('checkout', '')}\n"
        f"💰 支付金额：฿{total_price:,.0f}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"点击下方按钮完成支付："
    )
    
    # 构建支付按钮
    keyboard = []
    
    if payment_link:
        keyboard.append([
            InlineKeyboardButton("💳 用银行卡支付", url=payment_link)
        ])
    
    # 添加测试模式提示
    if "test" in stripe_publishable_key.lower() or "sk_test" in os.environ.get("STRIPE_SECRET_KEY", "").lower():
        message += "\n⚠️ *测试模式：Stripe测试密钥已启用*"
    
    keyboard.append([
        InlineKeyboardButton("🔄 检查支付状态", callback_data=f"check_payment_{booking_id}")
    ])
    keyboard.append([
        InlineKeyboardButton("📋 查看我的预订", callback_data="cmd_mybookings")
    ])
    
    return (message, InlineKeyboardMarkup(keyboard))

# ============ 检查支付状态 ============
async def check_payment_status(update, context, booking_id: str) -> str:
    """
    检查预订的支付状态
    
    Args:
        update: Telegram Update
        context: Bot context
        booking_id: 预订ID
        
    Returns:
        状态消息
    """
    booking = database.get_booking(booking_id)
    
    if not booking:
        return f"❌ 未找到预订 `{booking_id}`"
    
    payment_id = booking.get('payment_id')
    
    if not payment_id:
        return (
            f"📋 预订 `{booking_id}` 状态：{_get_status_text(booking['status'])}\n\n"
            "尚未发起支付"
        )
    
    # 验证支付状态
    payment_service = get_payment_service()
    if not payment_service:
        return "⚠️ 支付服务暂时不可用"
    
    result = await payment_service.verify_payment(payment_id)
    
    if result.success:
        # 支付成功，更新预订状态
        if booking['status'] != 'confirmed':
            database.update_booking_status(booking_id, 'confirmed')
            return (
                f"🎉 *支付成功！*\n\n"
                f"📋 预订编号：`{booking_id}`\n"
                f"💰 已支付：฿{result.amount:,.0f}\n"
                f"✅ 预订已确认！\n\n"
                "感谢您的预订！"
            )
        else:
            return (
                f"✅ *支付已确认*\n\n"
                f"📋 预订编号：`{booking_id}`\n"
                f"💰 已支付：฿{result.amount:,.0f}\n"
                f"🏠 别墅：{booking.get('villa_name', '')}\n"
                f"📅 {booking.get('checkin', '')} → {booking.get('checkout', '')}\n\n"
                "请保存好您的预订确认信息"
            )
    else:
        return (
            f"📋 预订 `{booking_id}` 状态\n\n"
            f"订单状态：{_get_status_text(booking['status'])}\n"
            f"💳 支付状态：{result.status.value}\n\n"
            "如果已完成支付，请稍后重试或联系客服"
        )

# ============ Webhook处理 ============
async def handle_stripe_webhook(payload: bytes, signature: str) -> Dict[str, Any]:
    """
    处理Stripe Webhook回调
    
    Args:
        payload: 请求体
        signature: Stripe-Signature header
        
    Returns:
        处理结果
    """
    payment_service = get_payment_service()
    
    if not payment_service:
        return {"success": False, "message": "支付服务未初始化"}
    
    # 验证签名
    if not payment_service.verify_webhook(payload, signature):
        logger.warning("⚠️ Webhook签名验证失败")
        return {"success": False, "message": "签名验证失败"}
    
    # 解析事件
    event = payment_service.parse_webhook_event(payload)
    
    if not event or 'type' not in event:
        return {"success": False, "message": "无效的事件数据"}
    
    event_type = event['type']
    logger.info(f"📦 收到Webhook事件: {event_type}")
    
    # 处理支付成功事件
    if event_type == 'payment_intent.succeeded':
        return await _handle_payment_success(event)
    
    # 处理支付失败事件
    elif event_type == 'payment_intent.payment_failed':
        return await _handle_payment_failed(event)
    
    # 处理退款事件
    elif event_type == 'charge.refunded':
        return await _handle_refund(event)
    
    return {"success": True, "message": f"事件 {event_type} 已处理"}

async def _handle_payment_success(event: Dict) -> Dict[str, Any]:
    """处理支付成功事件"""
    try:
        payment_intent = event['data']['object']
        booking_id = payment_intent.get('metadata', {}).get('booking_id')
        
        if not booking_id:
            logger.warning("⚠️ PaymentIntent缺少booking_id")
            return {"success": False, "message": "缺少booking_id"}
        
        # 更新预订状态
        success = database.update_booking_status(booking_id, 'confirmed')
        
        if success:
            logger.info(f"✅ 预订 {booking_id} 支付成功，已更新为confirmed")
            
            # 存储payment_id
            payment_id = payment_intent.get('id')
            if payment_id:
                database.update_booking_field(booking_id, 'payment_id', payment_id)
            
            return {
                "success": True,
                "message": f"预订 {booking_id} 已确认",
                "booking_id": booking_id
            }
        else:
            return {"success": False, "message": f"更新预订 {booking_id} 失败"}
            
    except Exception as e:
        logger.error(f"处理支付成功事件失败: {e}")
        return {"success": False, "message": str(e)}

async def _handle_payment_failed(event: Dict) -> Dict[str, Any]:
    """处理支付失败事件"""
    try:
        payment_intent = event['data']['object']
        booking_id = payment_intent.get('metadata', {}).get('booking_id')
        
        if booking_id:
            logger.info(f"⚠️ 预订 {booking_id} 支付失败")
            # 可选：更新预订状态或发送通知
        
        return {"success": True, "message": "支付失败事件已记录"}
        
    except Exception as e:
        logger.error(f"处理支付失败事件失败: {e}")
        return {"success": False, "message": str(e)}

async def _handle_refund(event: Dict) -> Dict[str, Any]:
    """处理退款事件"""
    try:
        charge = event['data']['object']
        payment_intent_id = charge.get('payment_intent')
        
        if payment_intent_id:
            # 查找对应的预订
            # 注意：这里需要根据实际数据结构实现
            logger.info(f"💰 收到退款请求: {payment_intent_id}")
        
        return {"success": True, "message": "退款事件已记录"}
        
    except Exception as e:
        logger.error(f"处理退款事件失败: {e}")
        return {"success": False, "message": str(e)}

# ============ 辅助函数 ============
def _get_status_text(status: str) -> str:
    """获取状态文本"""
    status_map = {
        'pending': '⏳ 待支付',
        'confirmed': '✅ 已确认',
        'paid': '✅ 已支付',
        'cancelled': '❌ 已取消',
        'completed': '🏁 已完成'
    }
    return status_map.get(status, status)

def get_payment_button(booking_id: str) -> InlineKeyboardMarkup:
    """
    获取支付按钮（用于预订确认后）
    
    Args:
        booking_id: 预订ID
        
    Returns:
        包含支付按钮的键盘
    """
    keyboard = [
        [InlineKeyboardButton("💳 立即支付", callback_data=f"pay_{booking_id}")],
        [InlineKeyboardButton("📋 查看预订", callback_data=f"booking_detail_{booking_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def format_payment_message(booking: Dict) -> str:
    """
    格式化支付消息
    
    Args:
        booking: 预订信息
        
    Returns:
        格式化的消息文本
    """
    total_price = booking.get('total_price', 0)
    
    return (
        f"💳 *订单待支付*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 预订编号：`{booking.get('booking_id', '')}`\n"
        f"🏠 别墅：{booking.get('villa_name', 'N/A')}\n"
        f"📅 入住：{booking.get('checkin', '')}\n"
        f"📅 退房：{booking.get('checkout', '')}\n"
        f"👤 联系人：{booking.get('contact_name', '')}\n"
        f"💰 应付金额：*฿{total_price:,.0f}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        "点击下方「立即支付」完成付款"
    )
