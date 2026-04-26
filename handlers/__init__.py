"""
命令处理器模块
"""
from .profile_handler import profile_cmd, register_profile_handlers
from .mybookings_handler import mybookings_cmd, mybookings_detail_cmd, register_mybookings_handlers
from .coupons_handler import coupons_cmd, register_coupons_handlers
from .points_handler import points_cmd, register_points_handlers
from .redeem_handler import redeem_cmd, register_redeem_handlers
from .review_handler import review_cmd, review_submit, register_review_handlers
from .help_handler import help_cmd, faq_cmd, register_help_handlers
from .report_handler import report_cmd, admin_report_cmd, register_report_handlers

__all__ = [
    'profile_cmd',
    'register_profile_handlers',
    'mybookings_cmd',
    'mybookings_detail_cmd',
    'register_mybookings_handlers',
    'coupons_cmd',
    'register_coupons_handlers',
    'points_cmd',
    'register_points_handlers',
    'redeem_cmd',
    'register_redeem_handlers',
    'review_cmd',
    'review_submit',
    'register_review_handlers',
    'help_cmd',
    'faq_cmd',
    'register_help_handlers',
    'report_cmd',
    'admin_report_cmd',
    'register_report_handlers',
]
