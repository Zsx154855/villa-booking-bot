"""
Coupon Management Module
优惠券管理模块 - 优惠券发放、验证、使用
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# ============ 优惠券类型 ============
COUPON_TYPES = {
    'discount': '满减券',      # 满X减Y
    'cash': '现金券',           # 直接抵扣
    'percent': '折扣券',        # X%折扣
    'points': '积分券'          # 赠送积分
}

COUPON_STATUS = {
    'available': '可用',
    'used': '已使用',
    'expired': '已过期',
    'disabled': '已失效'
}


# ============ 优惠券数据模型 ============
class Coupon:
    """优惠券数据类"""
    
    def __init__(self, coupon_id: str, name: str, coupon_type: str,
                 discount_value: float, min_amount: float = 0,
                 expire_days: int = 30, description: str = ''):
        self.coupon_id = coupon_id
        self.name = name
        self.coupon_type = coupon_type
        self.discount_value = discount_value
        self.min_amount = min_amount
        self.expire_date = datetime.now() + timedelta(days=expire_days)
        self.description = description
        self.created_at = datetime.now()
    
    def is_valid(self) -> bool:
        """检查优惠券是否有效"""
        return datetime.now() < self.expire_date
    
    def can_use(self, order_amount: float) -> bool:
        """检查优惠券是否可用"""
        if not self.is_valid():
            return False
        return order_amount >= self.min_amount
    
    def calculate_discount(self, order_amount: float) -> float:
        """计算折扣金额"""
        if not self.can_use(order_amount):
            return 0
        
        if self.coupon_type == 'discount':
            return min(self.discount_value, order_amount)
        elif self.coupon_type == 'percent':
            return order_amount * (self.discount_value / 100)
        elif self.coupon_type == 'cash':
            return min(self.discount_value, order_amount)
        else:
            return 0
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'coupon_id': self.coupon_id,
            'name': self.name,
            'type': self.coupon_type,
            'type_name': COUPON_TYPES.get(self.coupon_type, '未知'),
            'discount_value': self.discount_value,
            'min_amount': self.min_amount,
            'expire_date': self.expire_date.strftime('%Y-%m-%d'),
            'description': self.description,
            'is_valid': self.is_valid()
        }


# ============ 用户优惠券 ============
class UserCoupon:
    """用户持有的优惠券"""
    
    def __init__(self, user_id: int, coupon: Coupon):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.coupon = coupon
        self.status = 'available'
        self.assigned_at = datetime.now()
        self.used_at = None
        self.used_for_booking = None
    
    def use(self, booking_id: str) -> bool:
        """使用优惠券"""
        if self.status != 'available':
            return False
        if not self.coupon.is_valid():
            return False
        
        self.status = 'used'
        self.used_at = datetime.now()
        self.used_for_booking = booking_id
        return True
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'coupon': self.coupon.to_dict(),
            'status': self.status,
            'status_name': COUPON_STATUS.get(self.status, '未知'),
            'assigned_at': self.assigned_at.strftime('%Y-%m-%d %H:%M:%S'),
            'used_at': self.used_at.strftime('%Y-%m-%d %H:%M:%S') if self.used_at else None,
            'used_for_booking': self.used_for_booking
        }


# ============ 促销码 ============
class PromoCode:
    """促销码"""
    
    def __init__(self, code: str, coupon: Coupon, max_uses: int = 1, 
                 valid_from: datetime = None, valid_until: datetime = None):
        self.code = code.upper()
        self.coupon = coupon
        self.max_uses = max_uses
        self.current_uses = 0
        self.valid_from = valid_from or datetime.now()
        self.valid_until = valid_until or coupon.expire_date
        self.is_active = True
        self.created_at = datetime.now()
    
    def can_use(self) -> bool:
        """检查促销码是否可用"""
        if not self.is_active:
            return False
        if datetime.now() < self.valid_from or datetime.now() > self.valid_until:
            return False
        if self.current_uses >= self.max_uses:
            return False
        return True
    
    def consume(self) -> bool:
        """使用促销码"""
        if not self.can_use():
            return False
        self.current_uses += 1
        return True
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'code': self.code,
            'coupon': self.coupon.to_dict(),
            'max_uses': self.max_uses,
            'current_uses': self.current_uses,
            'remaining_uses': self.max_uses - self.current_uses,
            'valid_from': self.valid_from.strftime('%Y-%m-%d'),
            'valid_until': self.valid_until.strftime('%Y-%m-%d'),
            'is_active': self.is_active,
            'can_use': self.can_use()
        }


# ============ 优惠券管理器 ============
class CouponManager:
    """优惠券管理器"""
    
    def __init__(self):
        # 用户优惠券映射: {user_id: [UserCoupon]}
        self._user_coupons: Dict[int, List[UserCoupon]] = {}
        
        # 促销码映射: {code: PromoCode}
        self._promo_codes: Dict[str, PromoCode] = {}
        
        # 初始化示例促销码
        self._init_sample_promo_codes()
    
    def _init_sample_promo_codes(self):
        """初始化示例促销码"""
        sample_codes = [
            ('SUMMER2026', '夏季特惠券', 'discount', 300, 1500, 90),
            ('WELCOME50', '欢迎礼券', 'discount', 200, 1000, 365),
            ('VIP1000', 'VIP专属券', 'discount', 500, 2000, 365),
            ('HOLIDAY666', '假日狂欢券', 'discount', 666, 3000, 30),
            ('POINTS50', '积分奖励', 'points', 500, 0, 365),
        ]
        
        for code, name, ctype, value, min_amt, days in sample_codes:
            coupon = Coupon(
                coupon_id=code,
                name=name,
                coupon_type=ctype,
                discount_value=value,
                min_amount=min_amt,
                expire_days=days,
                description=f'{name}活动促销码'
            )
            promo = PromoCode(code, coupon, max_uses=100)
            self._promo_codes[code] = promo
    
    def get_user_coupons(self, user_id: int, status: str = None) -> List[UserCoupon]:
        """获取用户的优惠券"""
        coupons = self._user_coupons.get(user_id, [])
        if status:
            coupons = [c for c in coupons if c.status == status]
        return coupons
    
    def add_coupon_to_user(self, user_id: int, coupon: Coupon) -> UserCoupon:
        """给用户添加优惠券"""
        user_coupon = UserCoupon(user_id, coupon)
        if user_id not in self._user_coupons:
            self._user_coupons[user_id] = []
        self._user_coupons[user_id].append(user_coupon)
        logger.info(f"用户 {user_id} 获得优惠券: {coupon.name}")
        return user_coupon
    
    def redeem_promo_code(self, user_id: int, code: str) -> Dict:
        """兑换促销码"""
        code = code.upper()
        
        if code not in self._promo_codes:
            return {'success': False, 'error': 'invalid_code', 'message': '促销码无效'}
        
        promo = self._promo_codes[code]
        
        if not promo.can_use():
            if promo.current_uses >= promo.max_uses:
                return {'success': False, 'error': 'max_uses', 'message': '促销码已用完'}
            if not promo.is_active:
                return {'success': False, 'error': 'disabled', 'message': '促销码已失效'}
            return {'success': False, 'error': 'expired', 'message': '促销码已过期'}
        
        # 使用促销码
        promo.consume()
        
        # 添加优惠券到用户账户
        user_coupon = self.add_coupon_to_user(user_id, promo.coupon)
        
        return {
            'success': True,
            'coupon': user_coupon.to_dict(),
            'message': f'成功兑换 {promo.coupon.name}'
        }
    
    def use_coupon(self, user_id: int, coupon_id: str, booking_id: str) -> Dict:
        """使用优惠券"""
        coupons = self.get_user_coupons(user_id, 'available')
        
        for user_coupon in coupons:
            if user_coupon.id == coupon_id:
                if user_coupon.use(booking_id):
                    return {
                        'success': True,
                        'discount': user_coupon.coupon.discount_value,
                        'message': '优惠券使用成功'
                    }
                else:
                    return {
                        'success': False,
                        'error': 'invalid',
                        'message': '优惠券不可用'
                    }
        
        return {
            'success': False,
            'error': 'not_found',
            'message': '优惠券不存在'
        }
    
    def get_promo_code(self, code: str) -> Optional[PromoCode]:
        """获取促销码"""
        return self._promo_codes.get(code.upper())


# 全局优惠券管理器实例
coupon_manager = CouponManager()
