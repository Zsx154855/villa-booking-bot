#!/usr/bin/env python3
"""
RAG Generator - 答案生成模块
基于检索结果的LLM生成
支持多语言输出和来源标注
"""

import os
import logging
from typing import Dict, List, Optional, Any

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class Generator:
    """答案生成器"""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.min_confidence = 0.05  # TF-IDF分数较低
    
    def set_llm_client(self, llm_client):
        """设置LLM客户端"""
        self.llm_client = llm_client
    
    def generate(self, query: str, retrieval_results: List[Dict],
                 language: str = 'zh', include_source: bool = True) -> str:
        """
        生成答案
        
        Args:
            query: 用户问题
            retrieval_results: 检索结果
            language: 输出语言 (zh/en/th)
            include_source: 是否标注信息来源
        
        Returns:
            生成的答案
        """
        if not retrieval_results:
            return self._no_answer_response(query, language)
        
        # 检查置信度
        avg_score = sum(r.get('relevance_score', 0) for r in retrieval_results) / len(retrieval_results)
        if avg_score < self.min_confidence:
            logger.warning(f"置信度不足: {avg_score:.2f} < {self.min_confidence}")
            return self._low_confidence_response(query, language)
        
        # 构建上下文
        context = self._build_context(retrieval_results, max_chars=2500)
        
        # 构建prompt
        prompt = self._build_prompt(query, context, language)
        
        # 调用LLM
        if self.llm_client:
            try:
                response = self.llm_client.chat(messages=[
                    {"role": "system", "content": self._get_system_prompt(language)},
                    {"role": "user", "content": prompt}
                ])
                
                if include_source:
                    response += self._format_source_citation(retrieval_results)
                
                return response
            except Exception as e:
                logger.error(f"LLM生成失败: {e}")
                return self._fallback_generate(query, retrieval_results, language)
        else:
            # 无LLM时使用模板生成
            return self._template_generate(query, retrieval_results, language)
    
    def _build_context(self, results: List[Dict], max_chars: int = 2500) -> str:
        """构建检索上下文"""
        context_parts = []
        total_chars = 0
        
        for result in results:
            doc_type = result.get('doc_type', 'unknown')
            source = result.get('source', '')
            content = result.get('content', '')
            
            part = f"[{doc_type.upper()}] {source}\n{content}\n"
            
            if total_chars + len(part) > max_chars:
                remaining = max_chars - total_chars
                if remaining > 50:
                    part = part[:remaining] + "..."
                else:
                    break
            
            context_parts.append(part)
            total_chars += len(part)
        
        return '\n---\n'.join(context_parts)
    
    def _build_prompt(self, query: str, context: str, language: str) -> str:
        """构建生成prompt"""
        lang_instruction = {
            'zh': '请用中文回答',
            'en': 'Please answer in English',
            'th': 'กรุณาตอบเป็นภาษาไทย'
        }
        
        prompt = f"""{lang_instruction.get(language, '请用中文回答')}

用户问题: {query}

参考信息:
{context}

请根据参考信息回答用户问题。如果参考信息不足以回答，请明确说明。
"""
        return prompt
    
    def _get_system_prompt(self, language: str) -> str:
        """获取系统提示"""
        prompts = {
            'zh': """你是一个热情的别墅预订助手，为用户提供专业的别墅咨询服务。

回答要求：
1. 亲切友好，像朋友一样交流
2. 准确引用参考信息中的数据
3. 如果信息不足，诚实告知用户
4. 适当使用emoji增加亲和力
5. 回答简洁有条理，不要过于冗长
6. 涉及价格时，使用泰铢฿格式""",
            
            'en': """You are a friendly villa booking assistant providing professional villa consulting services.

Guidelines:
1. Be warm and approachable
2. Accurately quote data from reference information
3. Be honest if information is insufficient
4. Use appropriate emojis
5. Keep answers concise and organized
6. Use ฿ for prices in Thai Baht""",
            
            'th': """คุณเป็นผู้ช่วยจองวิลล่าที่เป็นมิตร ให้บริการให้คำปรึกษาเกี่ยวกับการเช่าวิลล่าแบบมืออาชีพ

แนวทาง:
1. มีมารยาทดีและเข้าถึงง่าย
2. อ้างอิงข้อมูลจากแหล่งข้อมูลอย่างถูกต้อง
3. บอกความจริงหากข้อมูลไม่เพียงพอ
4. ใช้อิโมจิที่เหมาะสม
5. ตอบกระชับและเป็นระบบ
6. ใช้สกุลเงิน ฿ สำหรับราคาเป็นบาท"""
        }
        return prompts.get(language, prompts['zh'])
    
    def _format_source_citation(self, results: List[Dict]) -> str:
        """格式化信息来源"""
        if not results:
            return ""
        
        citations = ["\n\n📚 信息来源:"]
        for i, result in enumerate(results, 1):
            doc_type = result.get('doc_type', '')
            source = result.get('source', '')
            score = result.get('relevance_score', 0)
            
            if doc_type == 'villa':
                emoji = '🏠'
            elif doc_type == 'faq':
                emoji = '❓'
            elif doc_type == 'guide':
                emoji = '📖'
            elif doc_type == 'nearby':
                emoji = '📍'
            else:
                emoji = '📄'
            
            citations.append(f"{emoji} {source} (相关度: {score:.0%})")
        
        return '\n'.join(citations)
    
    def _no_answer_response(self, query: str, language: str) -> str:
        """无答案响应"""
        responses = {
            'zh': f"""抱歉，我目前没有找到与"{query}"相关的信息 😅

建议您：
• 换个关键词试试
• 告诉我您想了解的具体方面（价格、设施、位置等）
• 或者直接说出您的需求，我来帮您推荐！""",
            
            'en': f"""Sorry, I couldn't find information related to "{query}" 😅

Suggestions:
• Try different keywords
• Tell me what specific aspect you want to know (price, facilities, location, etc.)
• Or just describe your needs and I'll help you find the perfect villa!""",
            
            'th': f"""ขออภัย ไม่พบข้อมูลที่เกี่ยวข้องกับ "{query}" 😅

คำแนะนำ:
• ลองค้นหาด้วยคำอื่น
• บอกว่าต้องการทราบรายละเอียดอะไร (ราคา, สิ่งอำนวยความสะดวก, ทำเล ฯลฯ)
• หรือบอกความต้องการของคุณ แล้วผมจะช่วยหาวิลล่าที่เหมาะกับคุณ!"""
        }
        return responses.get(language, responses['zh'])
    
    def _low_confidence_response(self, query: str, language: str) -> str:
        """低置信度响应"""
        responses = {
            'zh': f"""我找到了一些可能相关的信息，但不太确定是否准确 🤔

建议您直接告诉我：
• 您想预订哪套别墅
• 或者描述您的需求（地区、人数、预算等）
• 我会为您提供更详细的信息！""",
            
            'en': f"""I found some potentially relevant information, but I'm not sure if it's accurate 🤔

Please tell me directly:
• Which villa you're interested in
• Or describe your needs (region, number of guests, budget, etc.)
• I'll provide you with more detailed information!""",
            
            'th': f"""พบข้อมูลบางส่วนที่อาจเกี่ยวข้อง แต่ไม่แน่ใจว่าถูกต้อง 🤔

กรุณาบอกผมโดยตรง:
• คุณสนใจวิลล่าหลังไหน
• หรือบอกความต้องการของคุณ (ภูมิภาค, จำนวนแขก, งบประมาณ ฯลฯ)
• ผมจะให้ข้อมูลโดยละเอียดกว่านี้!"""
        }
        return responses.get(language, responses['zh'])
    
    def _fallback_generate(self, query: str, results: List[Dict], language: str) -> str:
        """降级生成"""
        return self._template_generate(query, results, language)
    
    def _template_generate(self, query: str, results: List[Dict], language: str) -> str:
        """模板生成（无LLM时）"""
        if not results:
            return self._no_answer_response(query, language)
        
        # 按类型分组
        villas = [r for r in results if r.get('doc_type') == 'villa']
        faqs = [r for r in results if r.get('doc_type') == 'faq']
        
        parts = []
        
        # 别墅信息
        if villas:
            parts.append("🏠 **相关别墅推荐：**\n")
            for v in villas[:2]:
                parts.append(f"• {v.get('source')}\n")
                parts.append(f"  {v.get('content', '')[:150]}...\n\n")
        
        # FAQ信息
        if faqs:
            parts.append("\n❓ **相关问答：**\n")
            for f in faqs[:1]:
                parts.append(f"• {f.get('content', '')[:200]}\n")
        
        parts.append(self._format_source_citation(villas + faqs))
        
        return '\n'.join(parts)


# 全局生成器
_generator: Optional[Generator] = None


def get_generator(llm_client=None) -> Generator:
    """获取生成器单例"""
    global _generator
    if _generator is None:
        _generator = Generator(llm_client)
    return _generator


def generate_answer(query: str, retrieval_results: List[Dict],
                   language: str = 'zh', llm_client=None) -> str:
    """便捷生成函数"""
    gen = get_generator(llm_client)
    return gen.generate(query, retrieval_results, language)
