"""
Customer Management Module
客户管理模块 - 用户数据、偏好设置、会员等级
"""

import logging
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# ============ 客户数据模型 ============
class Customer:
    """客户数据类"""
    
    def __init__(self, telegram_id: int, username: str = None, first_name: str = None):
        self.telegram_id = telegram_id
        self.username = username
        self.first_name = first_name
        self.created_at = datetime.now()
        self.last_seen = datetime.now()
        
        # 会员信息
        self.total_spent = 0.0
        self.points = 0
        self.vip_level = "普通会员"
        self.vip_benefits = []
        
        # 偏好设置
        self.preferred_regions = []
        self.preferred_price_range = (0, 999999)
        self.language = "zh"
        
        # 统计信息
        self.total_bookings = 0
        self.completed_bookings = 0
        self.total_nights = 0
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'telegram_id': self.telegram_id,
            'username': self.username,
            'first_name': self.first_name,
            'created_at': self.created_at.isoformat(),
            'last_seen': self.last_seen.isoformat(),
            'total_spent': self.total_spent,
            'points': self.points,
            'vip_level': self.vip_level,
            'vip_benefits': self.vip_benefits,
            'preferred_regions': self.preferred_regions,
            'language': self.language,
            'total_bookings': self.total_bookings,
            'completed_bookings': self.completed_bookings,
            'total_nights': self.total_nights
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Customer':
        """从字典创建"""
        customer = cls(
            telegram_id=int(data.get('telegram_id', 0)),
            username=data.get('username'),
            first_name=data.get('first_name')
        )
        
        if 'created_at' in data:
            try:
                customer.created_at = datetime.fromisoformat(data['created_at'])
            except:
                pass
        
        customer.last_seen = datetime.now()
        customer.total_spent = float(data.get('total_spent', 0))
        customer.points = int(data.get('points', 0))
        customer.vip_level = data.get('vip_level', '普通会员')
        customer.vip_benefits = data.get('vip_benefits', [])
        customer.preferred_regions = data.get('preferred_regions', [])
        customer.language = data.get('language', 'zh')
        customer.total_bookings = int(data.get('total_bookings', 0))
        customer.completed_bookings = int(data.get('completed_bookings', 0))
        customer.total_nights = int(data.get('total_nights', 0))
        
        return customer


# ============ VIP等级系统 ============
VIP_LEVELS = [
    {
        'name': '普通会员',
        'min_spent': 0,
        'discount': 0,
        'benefits': ['新用户首单优惠', '积分加倍']
    },
    {
        'name': '银卡会员',
        'min_spent': 5000,
        'discount': 5,
        'benefits': ['9.5折优惠', '生日特惠', '优先客服']
    },
    {
        'name': '金卡会员',
        'min_spent': 20000,
        'discount': 10,
        'benefits': ['9折优惠', '免费接机', '优先客服', '专属管家']
    },
    {
        'name': '钻石会员',
        'min_spent': 50000,
        'discount': 15,
        'benefits': ['专属折扣', '私人管家', '优先预订', '免费升级', '机场贵宾通道']
    }
]


def calculate_vip_level(total_spent: float) -> Dict:
    """根据消费金额计算VIP等级"""
    current_level = VIP_LEVELS[0]
    next_level = None
    
    for i, level in enumerate(VIP_LEVELS):
        if total_spent >= level['min_spent']:
            current_level = level
            if i < len(VIP_LEVELS) - 1:
                next_level = VIP_LEVELS[i + 1]
        else:
            break
    
    points_to_next = 0
    if next_level:
        points_to_next = next_level['min_spent'] - total_spent
    
    return {
        'current': current_level,
        'next': next_level,
        'points_to_next': points_to_next
    }


def calculate_points(total_spent: float) -> int:
    """计算可获得积分（每100铢得1积分）"""
    return int(total_spent / 100)


# ============ 客户管理器 ============
class CustomerManager:
    """客户管理器"""
    
    def __init__(self):
        self._customers: Dict[int, Customer] = {}
    
    def get_customer(self, telegram_id: int) -> Optional[Customer]:
        """获取客户"""
        return self._customers.get(telegram_id)
    
    def create_customer(self, telegram_id: int, username: str = None, first_name: str = None) -> Customer:
        """创建客户"""
        customer = Customer(telegram_id, username, first_name)
        self._customers[telegram_id] = customer
        logger.info(f"新客户创建: {telegram_id}")
        return customer
    
    def get_or_create(self, telegram_id: int, username: str = None, first_name: str = None) -> Customer:
        """获取或创建客户"""
        customer = self.get_customer(telegram_id)
        if not customer:
            customer = self.create_customer(telegram_id, username, first_name)
        else:
            customer.last_seen = datetime.now()
        return customer
    
    def update_customer(self, telegram_id: int, **kwargs) -> bool:
        """更新客户信息"""
        customer = self.get_customer(telegram_id)
        if not customer:
            return False
        
        for key, value in kwargs.items():
            if hasattr(customer, key):
                setattr(customer, key, value)
        
        # 更新VIP等级
        vip_info = calculate_vip_level(customer.total_spent)
        customer.vip_level = vip_info['current']['name']
        customer.vip_benefits = vip_info['current']['benefits']
        customer.points = calculate_points(customer.total_spent)
        
        return True


# 全局客户管理器实例
customer_manager = CustomerManager()
