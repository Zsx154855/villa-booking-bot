"""
Taimili Villa Booking - Payment Service
支持多支付渠道：Stripe、支付宝、微信支付
"""

from .base import PaymentService, PaymentResult
from .stripe_payment import StripePaymentService

__all__ = [
    'PaymentService',
    'PaymentResult', 
    'StripePaymentService'
]
