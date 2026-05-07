#!/usr/bin/env python3
"""
InfoAgent - Information Expert Agent
Handles scenic spots, transportation, attractions information queries
"""

import os
import logging
from typing import Dict, Any, List

from .context import (
    AgentRequest, AgentResponse, AgentType, IntentType, ContextBuilder
)
from .base import BaseAgent

logger = logging.getLogger(__name__)


class InfoAgent(BaseAgent):
    """Information Expert Agent"""
    
    def __init__(self):
        super().__init__(AgentType.INFO)
    
    SYSTEM_PROMPT = """You are a travel information expert, specializing in Thailand travel destination guides.

Your responsibilities:
1. Attraction recommendations - Hot spots and hidden gems in various regions
2. Transportation guides - How to get to attractions, public transit guides
3. Food guides - Local specialties, restaurant recommendations
4. Shopping guides - Malls, night markets, specialty products
5. Practical information - Weather, safety, precautions

Regional coverage:
- Pattaya: Beach vacation, nightlife, cabaret shows
- Bangkok: Temples, shopping paradise, food capital
- Phuket: Island scenery, snorkeling, beach relaxation

Response requirements:
- Accurate and practical information
- Recommend based on user needs
- Use emoji appropriately for better readability"""
    
    def get_system_prompt(self) -> str:
        return self.SYSTEM_PROMPT
    
    def get_supported_intents(self) -> List[IntentType]:
        return [IntentType.INFO]
    
    def get_intent_keywords(self) -> Dict[IntentType, List[str]]:
        return {
            IntentType.INFO: [
                "attractions", "spots", "recommend", "play", "sightseeing",
                "transport", "how to get", "mrt", "bus", "taxi",
                "food", "restaurant", "delicious", "night market",
                "shopping", "mall", "duty free",
                "weather", "temperature", "rain",
                "nearby", "around", "beach"
            ]
        }
    
    async def process(self, request: AgentRequest) -> AgentResponse:
        """Process information query requests"""
        message = request.raw_message
        region = request.conversation_context.active_region or request.parameters.get("region")
        
        # Analyze information type
        action = self._classify_info_action(message)
        
        logger.info(f"InfoAgent processing: {action}")
        
        if action == "attractions":
            return await self._attractions_info(request, region)
        elif action == "food":
            return await self._food_info(request, region)
        elif action == "transport":
            return await self._transport_info(request, region)
        elif action == "shopping":
            return await self._shopping_info(request, region)
        elif action == "weather":
            return await self._weather_info(request, region)
        elif action == "nearby":
            return await self._nearby_info(request, region)
        else:
            return await self._general_guide(request, region)
    
    def _classify_info_action(self, message: str) -> str:
        """Classify information types"""
        message_lower = message.lower()
        
        if any(kw in message_lower for kw in ["景点", "玩", "推荐", "好玩", "观光"]):
            return "attractions"
        elif any(kw in message_lower for kw in ["美食", "餐厅", "好吃", "夜市", "海鲜"]):
            return "food"
        elif any(kw in message_lower for kw in ["交通", "怎么去", "地铁", "bus", "tutu"]):
            return "transport"
        elif any(kw in message_lower for kw in ["购物", "商场", "免税", "买"]):
            return "shopping"
        elif any(kw in message_lower for kw in ["天气", "温度", "下雨", "热"]):
            return "weather"
        elif any(kw in message_lower for kw in ["附近", "周边", "海滩"]):
            return "nearby"
        else:
            return "general"
    
    async def _attractions_info(self, request: AgentRequest, region: str = None) -> AgentResponse:
        """Attractions information"""
        region = region or self._extract_region(request.raw_message)
        
        if not region:
            msg = "Please tell me which area attractions you want to know about?\nPattaya | Bangkok | Phuket"
            return ContextBuilder.create_success_response(
                request.request_id,
                self.agent_type,
                IntentType.INFO,
                result={},
                message=msg
            )
        
        attractions_map = {
            "Pattaya": """Pattaya Attractions:

Must-visit:
- Sanctuary of Truth - Wood carving art, 150 years history
- Nong Nooch Tropical Garden - Shows + garden, 4 hours
- Floating Market - Water trading experience

Nightlife:
- Walking Street - Bar street
- Tiffany Show - Top cabaret performance

Island Tours:
- Koh Lan - Closest island, 30 min by boat
- Koh Samet - Crystal clear water

Budget: 200-500 THB for tickets""",
            "Bangkok": """Bangkok Attractions:

Temples:
- Grand Palace + Emerald Buddha - Must visit, 500 THB
- Wat Arun - Beautiful sunset, 100 THB

Modern Landmarks:
- Iconsiam - Super mall
- Khao San Road - Backpacker area
- Ratchada Train Night Market - Food + shopping

Experiences:
- Somboon Seafood - Curry crab must-eat
- Lets Relax - Budget Thai massage

Budget: 0-500 THB for tickets""",
            "Phuket": """Phuket Attractions:

Beaches:
- Patong Beach - Most lively, party vibes
- Karon Beach - Big waves, surfing
- Kata Beach - Quiet, relaxing

Activities:
-皇帝岛浮潜 - Half day 1500 THB
- 皮皮岛一日游 - 2500 THB
- 幻多奇乐园 - Night show

Must-visit:
- Promthep Cape - Best sunset
- Wat Chalong - Thai architecture
- Old Town - Colorful houses

Budget: 1500-3000 THB for island tours"""
        }
        
        message = attractions_map.get(region, f"No attractions info for {region}")
        
        return ContextBuilder.create_success_response(
            request.request_id,
            self.agent_type,
            IntentType.INFO,
            result={"region": region, "category": "attractions"},
            message=message
        )
    
    async def _food_info(self, request: AgentRequest, region: str = None) -> AgentResponse:
        """Food information"""
        region = region or self._extract_region(request.raw_message) or "Bangkok"
        
        foods = {
            "Pattaya": """Pattaya Food Guide:

Must-eat seafood:
- Mango sticky rice - Street stall 50 THB
- Grilled prawns - Beach restaurant 300 THB/piece
- Tom Yum Kung - Thai sour soup

Local food:
- Pad Thai - 60 THB
- Fried rice - 50 THB

Recommended:
- Night market seafood - Good value
- Hilton front street stalls - Locals love""",
            "Bangkok": """Bangkok Food Guide:

Must-eat:
- Somboon Seafood - Best curry crab
- Khao Man Gai - Hainan chicken rice classic
- After You - Toast desserts

Street food:
- Khao San Night Market
- Ratchada Train Market -火山排骨
- Asiatique - View + food

Budget: 20-100 THB street, 300-800 THB restaurant""",
            "Phuket": """Phuket Food Guide:

Seafood paradise:
- Banzaan Fresh Market - Live seafood + processing
- Rawai Seafood Market - Local market
- Jungceylon Night Market

Specialties:
- Southern curry - Different from Bangkok
- Coconut milk soup noodles - Local breakfast
- Fruit shakes - Cheap and delicious 30 THB

Recommended:
- Blue Elephant - Royal Thai cuisine
- Baan Rim Pa - Cliff restaurant""",
        }
        
        message = foods.get(region, f"No food info for {region}")
        
        return ContextBuilder.create_success_response(
            request.request_id,
            self.agent_type,
            IntentType.INFO,
            result={"region": region, "category": "food"},
            message=message
        )
    
    async def _transport_info(self, request: AgentRequest, region: str = None) -> AgentResponse:
        """Transport information"""
        region = region or self._extract_region(request.raw_message) or "Bangkok"
        
        transport = {
            "Pattaya": """Pattaya Transport:

From Bangkok:
- Bus: Ekkamai/North Bus Station, 131 THB, 2 hours
- Mini Van: Victory Monument, 150 THB, 2 hours
- Private car: 1500 THB, 1.5 hours

Local transport:
- Songthaew: 10-40 THB, flag down
- Tuk-tuk: Bargain, usually 50-200 THB
- Grab/Bolt: Recommended""",
            "Bangkok": """Bangkok Transport:

Rail:
- BTS Skytrain: 15-60 THB
- MRT Subway: 15-40 THB

Bus:
- Regular bus: 8-20 THB
- Air-conditioned slightly more

Taxi/Motorcycle:
- Grab/Bolt: Recommended
- Taxi: Meter is cheapest
- Motorcycle: 50-100 THB, good for traffic""",
            "Phuket": """Phuket Transport:

Airport:
- Airport bus: 100 THB
- Mini Van: 180 THB to hotel
- Private pickup: 500 THB

Island:
- Rent motorcycle: 200-400 THB/day
- Songthaew: Island tour 1500 THB/day
- Shared ride: 100-200 THB between beaches

App:
- Grab/Bolt: Within town
- Island transfers expensive, bargain first"""
        }
        
        message = transport.get(region, f"No transport info for {region}")
        
        return ContextBuilder.create_success_response(
            request.request_id,
            self.agent_type,
            IntentType.INFO,
            result={"region": region, "category": "transport"},
            message=message
        )
    
    async def _shopping_info(self, request: AgentRequest, region: str = None) -> AgentResponse:
        """Shopping information"""
        message = """Shopping Guide:

Large Malls:
- Icon Siam (Bangkok) - Luxury riverside
- Central World (Bangkok) - Central business district
- Jungceylon (Patong) - Biggest in Phuket

Specialty Markets:
- Chatuchak Weekend Market - Biggest in Bangkok
- Ratchada Train Market - Trendy clothes
- Jungceylon Night Market - Phuket nightlife

Must-buy:
- Thai jasmine rice - 5kg about 300 THB
- Thai spices - Easy to carry
- Latex pillow - Good value
- Duty free - Cheapest at airport

Tips:
- Tax refund: 5000 THB purchase = 7% refund
- Alipay/WeChat: Some stores have discounts
- Bargain at night markets"""
        
        return ContextBuilder.create_success_response(
            request.request_id,
            self.agent_type,
            IntentType.INFO,
            result={"category": "shopping"},
            message=message
        )
    
    async def _weather_info(self, request: AgentRequest, region: str = None) -> AgentResponse:
        """Weather information"""
        message = """Thailand Weather Guide:

Best time:
- Nov-Feb: Cool season, most comfortable (25-32 C)
- Mar-May: Hot season, up to 40 C
- Jun-Oct: Rainy season, mainly showers

Current advice:
- High temperature year-round, bring sunscreen
- Indoor/outdoor temp difference, light jacket
- Rainy season bring rain gear, doesn't affect travel

Clothing:
- Breathable long sleeves: Temple dress code
- Shorts/skirts: Beach essential
- Sandals: Easy for beach/temple进出

Check real-time weather:
Use Google Weather or Apple Weather"""
        
        return ContextBuilder.create_success_response(
            request.request_id,
            self.agent_type,
            IntentType.INFO,
            result={"category": "weather"},
            message=message
        )
    
    async def _nearby_info(self, request: AgentRequest, region: str = None) -> AgentResponse:
        """Nearby information"""
        region = region or self._extract_region(request.raw_message) or "Bangkok"
        
        message = f"""{region} Area Exploration:

Based on your location, I recommend nearby activities:

Beach:
- Walking distance beach (please tell me exact location)
- Nearby water activities

Dining:
- Walking distance restaurants
- 24-hour convenience stores

Facilities:
- Nearest 7-11
- Nearby supermarket/mall

Suggestion:
Tell me your villa location or specific needs, I can give more accurate recommendations!"""
        
        return ContextBuilder.create_success_response(
            request.request_id,
            self.agent_type,
            IntentType.INFO,
            result={"region": region, "category": "nearby"},
            message=message
        )
    
    async def _general_guide(self, request: AgentRequest, region: str = None) -> AgentResponse:
        """General guide"""
        message = """Travel Assistant:

I can provide:

Destination guides:
- Regional attractions
- Food maps
- Transportation guides

Shopping info:
- Shopping guides
- Weather advice
- Safety precautions

Customized service:
- Itinerary based on your trip
- Activity recommendations

What would you like to know?

Examples:
- "What to do in Phuket?"
- "How to take the subway in Bangkok?"
- "Good restaurants nearby?" """
        
        return ContextBuilder.create_success_response(
            request.request_id,
            self.agent_type,
            IntentType.INFO,
            result={"category": "general"},
            message=message
        )
    
    def _extract_region(self, message: str) -> str:
        """Extract region"""
        regions = {"Pattaya": "Pattaya", "Bangkok": "Bangkok", "Phuket": "Phuket", "Phuket": "Phuket"}
        for region, name in regions.items():
            if region in message:
                return name
        return None
