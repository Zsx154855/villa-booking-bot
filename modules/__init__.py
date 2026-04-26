"""
Modules Package
功能模块集合
"""

from .customer import Customer, CustomerManager, calculate_vip_level, calculate_points, customer_manager
from .coupon import Coupon, CouponManager, PromoCode, coupon_manager
from .review import Review, ReviewManager, ReviewAnalytics, review_manager
from .faq import FAQManager, SupportSession, faq_manager, FAQ_CATEGORIES, FAQ_DATA

__all__ = [
    # Customer
    'Customer',
    'CustomerManager', 
    'calculate_vip_level',
    'calculate_points',
    'customer_manager',
    
    # Coupon
    'Coupon',
    'CouponManager',
    'PromoCode',
    'coupon_manager',
    
    # Review
    'Review',
    'ReviewManager',
    'ReviewAnalytics',
    'review_manager',
    
    # FAQ
    'FAQManager',
    'SupportSession',
    'faq_manager',
    'FAQ_CATEGORIES',
    'FAQ_DATA'
]
