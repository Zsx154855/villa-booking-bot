#!/usr/bin/env python3
"""
Multi-Agent System - Hub&Spoke Architecture
别墅Bot多Agent协作框架
"""

from .context import (
    AgentRequest,
    AgentResponse,
    AgentType,
    IntentType,
    UserContext,
    ConversationContext,
    ContextBuilder
)

from .base import BaseAgent, CoordinatorMixin

from .coordinator import Coordinator

from .booking_agent import BookingAgent
from .service_agent import ServiceAgent
from .info_agent import InfoAgent
from .payment_agent import PaymentAgent

from .router import (
    MultiAgentRouter,
    router,
    process_message,
    get_router_status,
    enable_multi_agent,
    disable_multi_agent,
    MULTI_AGENT_ENABLED
)

__all__ = [
    # Context Protocol
    "AgentRequest",
    "AgentResponse", 
    "AgentType",
    "IntentType",
    "UserContext",
    "ConversationContext",
    "ContextBuilder",
    
    # Base
    "BaseAgent",
    "CoordinatorMixin",
    
    # Agents
    "Coordinator",
    "BookingAgent",
    "ServiceAgent",
    "InfoAgent",
    "PaymentAgent",
    
    # Router
    "MultiAgentRouter",
    "router",
    "process_message",
    "get_router_status",
    "enable_multi_agent",
    "disable_multi_agent",
    "MULTI_AGENT_ENABLED"
]
