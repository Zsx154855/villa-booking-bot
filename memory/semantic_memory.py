#!/usr/bin/env python3
"""
Hermes三层记忆架构 - Layer 3: Semantic Memory
语义记忆管理 - 知识库和规则
生命周期：永久，可更新
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from copy import deepcopy

from .base import BaseMemoryManager, MemoryLayer

logger = logging.getLogger(__name__)


class SemanticMemoryManager(BaseMemoryManager):
    """
    语义记忆管理器
    
    存储：
    - 别墅知识库（房型/价格/位置/设施/周边信息）
    - 运营规则（退改政策/入住流程/常见问题）
    - AGENTS.md 指令
    """
    
    def __init__(self, villas_data_path: str = None, rules_path: str = None):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        if villas_data_path is None:
            # 尝试从项目根目录加载
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            villas_data_path = os.path.join(project_root, "villas.json")
        
        self._villas_data_path = villas_data_path
        self._rules_path = rules_path
        
        # 知识库数据
        self._villas: Dict[str, Dict] = {}
        self._rules: Dict[str, Any] = {}
        self._faq: List[Dict] = []
        self._agents_md: str = ""
        
        # 加载数据
        self._load_knowledge_base()
        
        logger.info(f"✅ Semantic Memory初始化完成 ({len(self._villas)} 套别墅, {len(self._faq)} 条FAQ)")
    
    def _load_knowledge_base(self):
        """加载知识库"""
        # 加载别墅数据
        if os.path.exists(self._villas_data_path):
            try:
                with open(self._villas_data_path, 'r', encoding='utf-8') as f:
                    villas_list = json.load(f)
                    for villa in villas_list:
                        self._villas[villa['id']] = villa
                logger.info(f"加载了 {len(self._villas)} 套别墅数据")
            except Exception as e:
                logger.error(f"加载别墅数据失败: {e}")
        
        # 初始化默认规则
        self._init_default_rules()
        
        # 加载FAQ
        self._init_default_faq()
    
    def _init_default_rules(self):
        """初始化默认运营规则"""
        self._rules = {
            "cancellation_policy": {
                "free_cancellation_before_7days": True,
                "fee_50pct_3to7days": True,
                "fee_100pct_within_3days": True,
                "no_show_fee": "100%",
                "description": "入住日期前7天可免费取消；3-7天收取50%费用；3天内收取100%费用"
            },
            "checkin_checkout": {
                "checkin_time": "14:00",
                "checkout_time": "12:00",
                "early_checkin": "需提前申请，视房态而定",
                "late_checkout": "需提前申请，可能收取额外费用"
            },
            "payment_methods": ["Visa", "Mastercard", "支付宝", "微信支付", "银行转账"],
            "deposit": {
                "amount": "总价的30%",
                "refund": "退房后3个工作日内退还"
            },
            "extra_services": {
                "breakfast": "可选，150元/人/天",
                "airport_pickup": "可选，500元/车",
                "private_chef": "可选，800元/天",
                "spa_service": "可选，需预约"
            },
            "child_policy": {
                "infant_under_2": "免费",
                "child_2_12": "不占床免费，占床需加床位费",
                "extra_bed": "300元/晚"
            },
            "pet_policy": "大部分别墅允许携带宠物，需提前告知并支付清洁费500元"
        }
    
    def _init_default_faq(self):
        """初始化常见问题"""
        self._faq = [
            {
                "question": "入住时间",
                "answer": "我们的入住时间是下午2点，退房时间是中午12点。如需提前入住或延迟退房，请提前告知，我们会尽量安排。"
            },
            {
                "question": "如何支付",
                "answer": "支持Visa、Mastercard、支付宝、微信支付和银行转账。预订时需支付30%订金，余款入住时支付。"
            },
            {
                "question": "取消政策",
                "answer": "入住日期前7天可免费取消；3-7天收取50%费用；3天内不可取消或收取100%费用。"
            },
            {
                "question": "包含早餐吗",
                "answer": "大部分别墅配有设备齐全的厨房，您可以自己烹饪。也可额外付费预订早餐、私人厨师等服务。"
            },
            {
                "question": "可以接机吗",
                "answer": "可以的，我们提供付费接机服务。普吉岛机场500元/车，曼谷和芭提雅机场600元/车。请提前至少24小时预约。"
            },
            {
                "question": "有WiFi吗",
                "answer": "所有别墅都提供免费WiFi，密码会在预订确认后发送给您。"
            },
            {
                "question": "可以带宠物吗",
                "answer": "大部分别墅允许携带宠物，需提前告知并支付500元清洁费。具体请咨询客服。"
            },
            {
                "question": "有停车场吗",
                "answer": "大部分别墅都配有免费停车场，预订时可在别墅详情中查看。"
            },
            {
                "question": "如何联系管家",
                "answer": "预订确认后会收到管家联系方式。紧急情况也可通过客服热线联系我们。"
            },
            {
                "question": "需要押金吗",
                "answer": "不需要现金押金，但会预授权信用卡额度作为担保，退房后3个工作日内解冻。"
            }
        ]
    
    def load(self, key: str) -> Any:
        """加载语义记忆数据"""
        if key == "villas":
            return self._villas
        elif key == "rules":
            return self._rules
        elif key == "faq":
            return self._faq
        elif key == "agents":
            return self._agents_md
        elif key.startswith("villa:"):
            villa_id = key.replace("villa:", "")
            return self._villas.get(villa_id)
        return None
    
    def save(self, key: str, data: Any) -> bool:
        """保存语义记忆数据"""
        try:
            if key == "villas":
                self._villas = data
            elif key == "rules":
                self._rules = data
            elif key == "faq":
                self._faq = data
            elif key == "agents":
                self._agents_md = data
            elif key.startswith("villa:"):
                villa_id = key.replace("villa:", "")
                self._villas[villa_id] = data
            return True
        except Exception as e:
            logger.error(f"保存语义记忆失败: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除语义记忆数据"""
        if key.startswith("villa:"):
            villa_id = key.replace("villa:", "")
            if villa_id in self._villas:
                del self._villas[villa_id]
                return True
        return False
    
    def clear(self) -> bool:
        """清空语义记忆（谨慎使用）"""
        self._villas.clear()
        self._rules.clear()
        self._faq.clear()
        self._agents_md = ""
        return True
    
    # ============ 知识查询方法 ============
    
    def get_all_villas(self) -> List[Dict]:
        """获取所有别墅"""
        return list(self._villas.values())
    
    def get_villas_by_region(self, region: str) -> List[Dict]:
        """按地区获取别墅"""
        return [v for v in self._villas.values() if v.get('region') == region]
    
    def get_villa_by_id(self, villa_id: str) -> Optional[Dict]:
        """根据ID获取别墅"""
        return self._villas.get(villa_id)
    
    def search_villas(self, **criteria) -> List[Dict]:
        """
        搜索别墅
        
        支持的筛选条件：
        - region: 地区
        - min_price: 最低价格
        - max_price: 最高价格
        - min_guests: 最少容纳人数
        - amenities: 设施列表
        - room_type: 房型
        """
        results = list(self._villas.values())
        
        if 'region' in criteria:
            results = [v for v in results if v.get('region') == criteria['region']]
        
        if 'min_price' in criteria:
            results = [v for v in results if v.get('price_per_night', 0) >= criteria['min_price']]
        
        if 'max_price' in criteria:
            results = [v for v in results if v.get('price_per_night', 0) <= criteria['max_price']]
        
        if 'min_guests' in criteria:
            results = [v for v in results if v.get('max_guests', 0) >= criteria['min_guests']]
        
        if 'room_type' in criteria:
            results = [v for v in results if criteria['room_type'].lower() in v.get('type', '').lower()]
        
        if 'amenities' in criteria:
            required = criteria['amenities']
            results = [v for v in results if all(a in v.get('amenities', []) for a in required)]
        
        return results
    
    def get_rules(self) -> Dict[str, Any]:
        """获取运营规则"""
        return deepcopy(self._rules)
    
    def get_rule(self, rule_key: str) -> Any:
        """获取特定规则"""
        keys = rule_key.split('.')
        value = self._rules
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return None
        return deepcopy(value) if value else None
    
    def get_faq(self) -> List[Dict]:
        """获取FAQ列表"""
        return deepcopy(self._faq)
    
    def search_faq(self, query: str) -> List[Dict]:
        """搜索FAQ"""
        query_lower = query.lower()
        results = []
        for faq in self._faq:
            if query_lower in faq['question'].lower() or query_lower in faq['answer'].lower():
                results.append(faq)
        return results
    
    def set_agents_md(self, content: str):
        """设置AGENTS.md内容"""
        self._agents_md = content
        self.save("agents", content)
    
    def get_agents_md(self) -> str:
        """获取AGENTS.md内容"""
        return self._agents_md
    
    # ============ 生成上下文方法 ============
    
    def build_knowledge_context(self, region: str = None, villa_ids: List[str] = None) -> str:
        """
        构建知识库上下文（用于LLM）
        
        可以指定地区或特定别墅ID来限制上下文大小
        """
        context_parts = []
        
        # 添加运营规则
        context_parts.append("【运营规则】")
        rules = self.get_rules()
        context_parts.append(f"取消政策: {rules['cancellation_policy']['description']}")
        context_parts.append(f"入住时间: {rules['checkin_checkout']['checkin_time']}")
        context_parts.append(f"退房时间: {rules['checkin_checkout']['checkout_time']}")
        context_parts.append(f"支付方式: {', '.join(rules['payment_methods'])}")
        context_parts.append(f"订金: {rules['deposit']['amount']}")
        
        # 添加别墅信息
        villas_to_include = []
        if villa_ids:
            villas_to_include = [self._villas.get(vid) for vid in villa_ids if vid in self._villas]
        elif region:
            villas_to_include = self.get_villas_by_region(region)
        else:
            villas_to_include = self.get_all_villas()
        
        if villas_to_include:
            context_parts.append("\n【别墅信息】")
            for villa in villas_to_include:
                context_parts.append(
                    f"- {villa['name']} ({villa['id']}): "
                    f"฿{villa['price_per_night']}/晚, "
                    f"最多{villa['max_guests']}人, "
                    f"{villa['bedrooms']}卧{villa['bathrooms']}卫, "
                    f"设施: {', '.join(villa['amenities'][:3])}"
                )
        
        return "\n".join(context_parts)
    
    def build_faq_context(self, query: str = None) -> str:
        """构建FAQ上下文"""
        faqs = self.search_faq(query) if query else self.get_faq()
        
        context_parts = ["【常见问题】"]
        for faq in faqs[:5]:  # 最多返回5条
            context_parts.append(f"Q: {faq['question']}")
            context_parts.append(f"A: {faq['answer']}\n")
        
        return "\n".join(context_parts)
    
    def get_context_for_intent(self, intent: str, **kwargs) -> Dict[str, str]:
        """
        根据意图获取相关上下文
        
        返回包含不同类型上下文的字典
        """
        contexts = {}
        
        if intent == "booking":
            # 预订意图：返回运营规则和别墅信息
            region = kwargs.get('region')
            villa_ids = kwargs.get('villa_ids', [])
            contexts['knowledge'] = self.build_knowledge_context(region, villa_ids)
            contexts['rules'] = json.dumps(self.get_rules(), ensure_ascii=False)
        
        elif intent == "inquiry":
            # 咨询意图：返回FAQ
            query = kwargs.get('query', '')
            contexts['faq'] = self.build_faq_context(query)
            contexts['knowledge'] = self.build_knowledge_context()
        
        elif intent == "modification":
            # 修改意图：返回修改相关规则
            contexts['rules'] = f"修改政策: 请告知您需要修改的内容，我们会尽力协调。"
        
        elif intent == "cancellation":
            # 取消意图：返回取消政策
            contexts['rules'] = json.dumps(self.get_rule('cancellation_policy'), ensure_ascii=False)
        
        else:
            # 默认：返回基础信息
            contexts['knowledge'] = self.build_knowledge_context()
            contexts['faq'] = self.build_faq_context()
        
        return contexts


# 全局单例
semantic_memory = SemanticMemoryManager()
