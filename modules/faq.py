"""
FAQ Module
常见问题与客服系统
"""

import logging
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# ============ FAQ分类 ============
FAQ_CATEGORIES = [
    {'id': 'booking', 'name': '预订相关', 'icon': '📋'},
    {'id': 'payment', 'name': '支付问题', 'icon': '💰'},
    {'id': 'villa', 'name': '别墅入住', 'icon': '🏠'},
    {'id': 'transport', 'name': '交通服务', 'icon': '🚗'},
    {'id': 'service', 'name': '增值服务', 'icon': '⭐'},
    {'id': 'account', 'name': '账户问题', 'icon': '👤'}
]


# ============ FAQ数据 ============
FAQ_DATA = {
    'booking': [
        {
            'q': '如何预订别墅？',
            'a': '使用 /book 命令，按照提示选择地区、别墅和日期即可完成预订。您也可以直接发送别墅编号给客服代为预订。'
        },
        {
            'q': '预订后多久确认？',
            'a': '客服将在24小时内与您联系确认订单。高峰期可能稍有延迟，请您耐心等待。'
        },
        {
            'q': '如何取消或修改预订？',
            'a': '在订单确认前可自助取消，已确认订单请提前3天联系客服处理。临时取消可能产生违约金。'
        },
        {
            'q': '可以代朋友预订吗？',
            'a': '可以。请在备注中填写入住人的联系方式，以便管家联系入住。'
        },
        {
            'q': '预订需要支付定金吗？',
            'a': '是的，确认预订需支付总价的30%作为定金，余款入住当天支付。'
        }
    ],
    'payment': [
        {
            'q': '支持哪些支付方式？',
            'a': '支持支付宝、微信支付、银行卡转账、信用卡等多种方式。具体以预订时显示的选项为准。'
        },
        {
            'q': '可以用人民币支付吗？',
            'a': '可以，我们支持人民币结算，系统会自动按当日汇率换算。'
        },
        {
            'q': '支付安全吗？',
            'a': '所有支付均通过正规支付渠道加密处理，您的账户信息安全有保障。'
        },
        {
            'q': '定金可以退吗？',
            'a': '入住7天前取消可全额退款，3-7天取消退50%，3天内取消不予退款。'
        },
        {
            'q': '可以分期付款吗？',
            'a': '目前支持分两次付款（定金+尾款），具体可咨询客服。'
        }
    ],
    'villa': [
        {
            'q': '入住和退房时间是几点？',
            'a': '标准入住时间为下午15:00，退房时间为上午11:00。如需提前入住或延迟退房，请提前与管家沟通。'
        },
        {
            'q': '包含早餐吗？',
            'a': '部分别墅含早餐，详情请查看别墅介绍。也可付费预约早餐服务。'
        },
        {
            'q': '可以带宠物吗？',
            'a': '部分别墅允许携带宠物入住，请在预订前咨询客服确认。'
        },
        {
            'q': '有洗漱用品吗？',
            'a': '所有别墅均提供基本的洗漱用品、毛巾、床品等。部分高端别墅提供高端品牌用品。'
        },
        {
            'q': '可以加床吗？',
            'a': '大部分别墅支持加床服务，费用约为500-1000铢/晚，具体请咨询管家。'
        }
    ],
    'transport': [
        {
            'q': '提供接机服务吗？',
            'a': '是的，金卡及以上会员可享受免费接机服务，其他用户可付费预约。费用根据距离而定。'
        },
        {
            'q': '别墅距离机场多远？',
            'a': '各别墅位置不同。芭提雅机场约30分钟，曼谷机场约1-2小时，普吉岛机场约30-60分钟。'
        },
        {
            'q': '可以包车吗？',
            'a': '可以提供包车服务，配司机。有多种车型可选，费用根据行程而定。'
        },
        {
            'q': '有接送机的服务时间限制吗？',
            'a': '24小时服务，但夜间（22:00-06:00）接送可能收取夜间服务费。'
        }
    ],
    'service': [
        {
            'q': '可以安排私人厨师吗？',
            'a': '可以。我们提供泰式、西式、中式等不同风格的私人厨师服务，费用根据菜单而定。'
        },
        {
            'q': '有SPA服务吗？',
            'a': '大部分别墅提供上门SPA服务，也可以推荐附近的SPA馆。高端别墅配有私人SPA房。'
        },
        {
            'q': '可以安排旅游行程吗？',
            'a': '可以提供定制旅游服务，包括一日游、包车游玩等项目。咨询客服获取详细方案。'
        },
        {
            'q': '有儿童看护服务吗？',
            'a': '可以安排专业的儿童看护人员，费用约为500-800铢/小时。'
        }
    ],
    'account': [
        {
            'q': '如何成为VIP会员？',
            'a': '累计消费达到一定金额自动升级：银卡5000铢，金卡20000铢，钻石50000铢。'
        },
        {
            'q': '会员积分有什么用？',
            'a': '积分可兑换优惠券、抵扣房费、换取增值服务等。100积分=50铢。'
        },
        {
            'q': '如何获取优惠券？',
            'a': '关注活动公告、兑换促销码、使用积分兑换等多种方式获取优惠券。'
        },
        {
            'q': '积分会过期吗？',
            'a': '积分有效期为获得后12个月，请及时使用。'
        },
        {
            'q': '忘记密码怎么办？',
            'a': 'Telegram机器人无需密码登录，如需修改绑定信息请联系客服。'
        }
    ]
}


# ============ 客服会话 ============
class SupportSession:
    """客服会话"""
    
    def __init__(self, user_id: int):
        self.session_id = str(user_id)
        self.user_id = user_id
        self.status = 'active'  # active, waiting, resolved
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.messages = []
        self.category = None
        self.issue = None
        self.resolved_at = None
    
    def add_message(self, role: str, content: str):
        """添加消息"""
        self.messages.append({
            'role': role,
            'content': content,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        self.updated_at = datetime.now()
    
    def set_category(self, category: str):
        """设置问题类别"""
        self.category = category
        self.updated_at = datetime.now()
    
    def set_issue(self, issue: str):
        """设置问题描述"""
        self.issue = issue
        self.updated_at = datetime.now()
    
    def resolve(self):
        """解决会话"""
        self.status = 'resolved'
        self.resolved_at = datetime.now()
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'status': self.status,
            'category': self.category,
            'issue': self.issue,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            'message_count': len(self.messages)
        }


# ============ FAQ管理器 ============
class FAQManager:
    """FAQ管理器"""
    
    def __init__(self):
        self._support_sessions: Dict[int, SupportSession] = {}
    
    def get_categories(self) -> List[Dict]:
        """获取FAQ分类"""
        return FAQ_CATEGORIES
    
    def get_faqs_by_category(self, category_id: str) -> List[Dict]:
        """按分类获取FAQ"""
        return FAQ_DATA.get(category_id, [])
    
    def search_faqs(self, keyword: str) -> List[Dict]:
        """搜索FAQ"""
        results = []
        keyword = keyword.lower()
        
        for category_id, faqs in FAQ_DATA.items():
            for faq in faqs:
                if keyword in faq['q'].lower() or keyword in faq['a'].lower():
                    results.append({
                        'category': category_id,
                        **faq
                    })
        
        return results
    
    def get_all_faqs(self) -> List[Dict]:
        """获取所有FAQ"""
        results = []
        for category_id, faqs in FAQ_DATA.items():
            for faq in faqs:
                results.append({
                    'category': category_id,
                    **faq
                })
        return results
    
    # ============ 客服会话 ============
    def create_support_session(self, user_id: int) -> SupportSession:
        """创建客服会话"""
        session = SupportSession(user_id)
        self._support_sessions[user_id] = session
        return session
    
    def get_support_session(self, user_id: int) -> Optional[SupportSession]:
        """获取客服会话"""
        return self._support_sessions.get(user_id)
    
    def get_or_create_session(self, user_id: int) -> SupportSession:
        """获取或创建客服会话"""
        session = self.get_support_session(user_id)
        if not session or session.status == 'resolved':
            session = self.create_support_session(user_id)
        return session
    
    def resolve_session(self, user_id: int):
        """解决会话"""
        session = self.get_support_session(user_id)
        if session:
            session.resolve()


# 全局FAQ管理器实例
faq_manager = FAQManager()
