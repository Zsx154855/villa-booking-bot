"""
Taimili Villa Booking - Internationalization (i18n) Module
多语言支持模块
"""

import json
import os
from typing import Dict, Any, Optional


class I18n:
    """国际化支持类"""
    
    DEFAULT_LANGUAGE = 'zh'
    SUPPORTED_LANGUAGES = ['zh', 'en', 'th']
    
    def __init__(self, locales_dir: str = None):
        """
        初始化i18n
        
        Args:
            locales_dir: 语言文件目录路径
        """
        if locales_dir is None:
            locales_dir = os.path.join(os.path.dirname(__file__), 'locales')
        
        self.locales_dir = locales_dir
        self.translations: Dict[str, Dict[str, Any]] = {}
        self._load_translations()
    
    def _load_translations(self):
        """加载所有语言翻译"""
        for lang in self.SUPPORTED_LANGUAGES:
            file_path = os.path.join(self.locales_dir, f'{lang}.json')
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.translations[lang] = json.load(f)
    
    def get(self, key: str, lang: str = None, **kwargs) -> str:
        """
        获取翻译文本
        
        Args:
            key: 翻译键 (支持点号分隔，如 "bot.welcome")
            lang: 语言代码 (zh/en/th)
            **kwargs: 模板变量
            
        Returns:
            str: 翻译后的文本
        """
        if lang is None:
            lang = self.DEFAULT_LANGUAGE
        
        if lang not in self.translations:
            lang = self.DEFAULT_LANGUAGE
        
        # 解析嵌套键
        keys = key.split('.')
        value = self.translations.get(lang, {})
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, '')
            else:
                value = ''
                break
        
        # 如果找不到翻译，尝试默认语言
        if not value and lang != self.DEFAULT_LANGUAGE:
            value = self.get(key, self.DEFAULT_LANGUAGE)
        
        # 模板变量替换
        if isinstance(value, str) and kwargs:
            try:
                value = value.format(**kwargs)
            except KeyError:
                pass
        
        return value
    
    def detect_language(self, text: str) -> str:
        """
        检测文本语言
        
        Args:
            text: 输入文本
            
        Returns:
            str: 语言代码
        """
        # 简单的语言检测逻辑
        thai_chars = any('\u0E00' <= c <= '\u0E7F' for c in text)
        chinese_chars = any('\u4E00' <= c <= '\u9FFF' for c in text)
        
        if thai_chars:
            return 'th'
        elif chinese_chars:
            return 'zh'
        else:
            return 'en'
    
    def get_language_name(self, lang: str) -> str:
        """获取语言的本地名称"""
        names = {
            'zh': '中文',
            'en': 'English',
            'th': 'ไทย'
        }
        return names.get(lang, lang)


# 全局实例
_i18n = None

def get_i18n() -> I18n:
    """获取i18n实例"""
    global _i18n
    if _i18n is None:
        _i18n = I18n()
    return _i18n

def t(key: str, lang: str = None, **kwargs) -> str:
    """
    翻译函数的快捷方式
    
    Args:
        key: 翻译键
        lang: 语言代码
        **kwargs: 模板变量
        
    Returns:
        str: 翻译后的文本
    """
    return get_i18n().get(key, lang, **kwargs)
