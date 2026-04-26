"""
Taimili Villa Booking - Payment Base Module
支付服务基类，定义统一接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class PaymentStatus(Enum):
    """支付状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


@dataclass
class PaymentResult:
    """支付结果"""
    success: bool
    payment_id: str
    status: PaymentStatus
    amount: float
    currency: str = "THB"
    message: str = ""
    redirect_url: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class PaymentRequest:
    """支付请求"""
    booking_id: str
    amount: float
    currency: str = "THB"
    description: str = ""
    customer_email: Optional[str] = None
    customer_name: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class PaymentService(ABC):
    """支付服务抽象基类"""
    
    def __init__(self, api_key: str, webhook_secret: Optional[str] = None):
        self.api_key = api_key
        self.webhook_secret = webhook_secret
    
    @abstractmethod
    async def create_payment(self, request: PaymentRequest) -> PaymentResult:
        """
        创建支付
        
        Args:
            request: 支付请求对象
            
        Returns:
            PaymentResult: 支付结果
        """
        pass
    
    @abstractmethod
    async def verify_payment(self, payment_id: str) -> PaymentResult:
        """
        验证支付状态
        
        Args:
            payment_id: 支付ID
            
        Returns:
            PaymentResult: 支付结果
        """
        pass
    
    @abstractmethod
    async def refund(self, payment_id: str, amount: Optional[float] = None) -> PaymentResult:
        """
        退款
        
        Args:
            payment_id: 支付ID
            amount: 退款金额（可选，默认全额退款）
            
        Returns:
            PaymentResult: 退款结果
        """
        pass
    
    @abstractmethod
    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """
        验证Webhook签名
        
        Args:
            payload: 请求体
            signature: 签名
            
        Returns:
            bool: 验证结果
        """
        pass
    
    @abstractmethod
    def parse_webhook_event(self, payload: bytes) -> Dict[str, Any]:
        """
        解析Webhook事件
        
        Args:
            payload: 请求体
            
        Returns:
            Dict: 事件数据
        """
        pass
