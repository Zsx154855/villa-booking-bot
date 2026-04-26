"""
Taimili Villa Booking - Payment Service
支持多支付渠道：Stripe、支付宝、微信支付
"""

from .base import PaymentService, PaymentResult, PaymentRequest, PaymentStatus
from .stripe_payment import StripePaymentService
from .handlers import (
    pay_command, check_payment_status, handle_stripe_webhook,
    get_payment_button, format_payment_message, get_payment_service
)

__all__ = [
    'PaymentService',
    'PaymentResult',
    'PaymentRequest',
    'PaymentStatus',
    'StripePaymentService',
    'pay_command',
    'check_payment_status',
    'handle_stripe_webhook',
    'get_payment_button',
    'format_payment_message',
    'get_payment_service'
]
