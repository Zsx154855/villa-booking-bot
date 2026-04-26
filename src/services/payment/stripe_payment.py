"""
Taimili Villa Booking - Stripe Payment Module
Stripe支付集成
"""

import stripe
import hmac
import hashlib
from typing import Dict, Any, Optional

from .base import PaymentService, PaymentRequest, PaymentResult, PaymentStatus


class StripePaymentService(PaymentService):
    """Stripe支付服务实现"""
    
    def __init__(self, api_key: str, webhook_secret: Optional[str] = None):
        super().__init__(api_key, webhook_secret)
        stripe.api_key = api_key
    
    async def create_payment(self, request: PaymentRequest) -> PaymentResult:
        """
        创建Stripe Payment Intent
        
        Args:
            request: 支付请求
            
        Returns:
            PaymentResult: 支付结果
        """
        try:
            # 创建Payment Intent
            intent = stripe.PaymentIntent.create(
                amount=int(request.amount * 100),  # Stripe使用分为单位
                currency=request.currency.lower(),
                metadata={
                    'booking_id': request.booking_id,
                    **request.metadata
                },
                description=request.description or f"Villa Booking {request.booking_id}",
                receipt_email=request.customer_email
            )
            
            return PaymentResult(
                success=True,
                payment_id=intent.id,
                status=PaymentStatus.PENDING,
                amount=request.amount,
                currency=request.currency,
                message="Payment intent created",
                metadata={
                    'client_secret': intent.client_secret,
                    'stripe_intent': intent.id
                }
            )
            
        except stripe.error.StripeError as e:
            return PaymentResult(
                success=False,
                payment_id="",
                status=PaymentStatus.FAILED,
                amount=request.amount,
                currency=request.currency,
                message=str(e)
            )
    
    async def verify_payment(self, payment_id: str) -> PaymentResult:
        """
        验证Stripe支付状态
        
        Args:
            payment_id: Payment Intent ID
            
        Returns:
            PaymentResult: 支付结果
        """
        try:
            intent = stripe.PaymentIntent.retrieve(payment_id)
            
            status_map = {
                'succeeded': PaymentStatus.SUCCESS,
                'processing': PaymentStatus.PROCESSING,
                'requires_payment_method': PaymentStatus.PENDING,
                'requires_confirmation': PaymentStatus.PENDING,
                'requires_action': PaymentStatus.PENDING,
                'canceled': PaymentStatus.CANCELLED,
            }
            
            return PaymentResult(
                success=intent.status == 'succeeded',
                payment_id=intent.id,
                status=status_map.get(intent.status, PaymentStatus.PENDING),
                amount=intent.amount / 100,
                currency=intent.currency.upper(),
                metadata=intent.metadata
            )
            
        except stripe.error.StripeError as e:
            return PaymentResult(
                success=False,
                payment_id=payment_id,
                status=PaymentStatus.FAILED,
                amount=0,
                message=str(e)
            )
    
    async def refund(self, payment_id: str, amount: Optional[float] = None) -> PaymentResult:
        """
        创建Stripe退款
        
        Args:
            payment_id: Payment Intent ID
            amount: 退款金额（可选）
            
        Returns:
            PaymentResult: 退款结果
        """
        try:
            refund_data = {'payment_intent': payment_id}
            if amount:
                refund_data['amount'] = int(amount * 100)
            
            refund = stripe.Refund.create(**refund_data)
            
            return PaymentResult(
                success=True,
                payment_id=refund.id,
                status=PaymentStatus.REFUNDED if refund.status == 'succeeded' else PaymentStatus.FAILED,
                amount=refund.amount / 100,
                message="Refund processed"
            )
            
        except stripe.error.StripeError as e:
            return PaymentResult(
                success=False,
                payment_id=payment_id,
                status=PaymentStatus.FAILED,
                amount=0,
                message=str(e)
            )
    
    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """
        验证Stripe Webhook签名
        
        Args:
            payload: 请求体
            signature: Stripe-Signature header
            
        Returns:
            bool: 验证结果
        """
        if not self.webhook_secret:
            return False
        
        try:
            stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            return True
        except stripe.error.SignatureVerificationError:
            return False
    
    def parse_webhook_event(self, payload: bytes) -> Dict[str, Any]:
        """
        解析Stripe Webhook事件
        
        Args:
            payload: 请求体
            
        Returns:
            Dict: 事件数据
        """
        try:
            import json
            return json.loads(payload)
        except Exception:
            return {}
