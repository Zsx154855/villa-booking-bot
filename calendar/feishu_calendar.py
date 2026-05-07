#!/usr/bin/env python3
"""
飞书日历 API 集成模块
使用飞书开放平台 API 进行日历操作
"""

import os
import logging
import time
import requests
from typing import Dict, Any, Optional, List

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 飞书 API 地址
FEISHU_API_BASE = 'https://open.feishu.cn/open-apis'

# 日历相关 API
CALENDAR_API_BASE = f'{FEISHU_API_BASE}/calendar/v4'

# Token 缓存
_token_cache = {
    'token': None,
    'expires_at': 0
}


class FeishuCalendarSync:
    """飞书日历同步类"""
    
    def __init__(self, app_id: str, app_secret: str):
        """
        初始化飞书日历客户端
        
        Args:
            app_id: 飞书应用 App ID (格式: cli_xxx)
            app_secret: 飞书应用 App Secret
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.tenant_access_token = self._get_tenant_access_token()
        logger.info("✅ 飞书日历服务已初始化")
    
    def _get_tenant_access_token(self) -> str:
        """
        获取 tenant_access_token
        
        Returns:
            访问令牌
        """
        global _token_cache
        
        # 检查缓存是否有效
        if _token_cache['token'] and time.time() < _token_cache['expires_at']:
            return _token_cache['token']
        
        # 获取新的 token
        url = f'{FEISHU_API_BASE}/auth/v3/tenant_access_token/internal'
        payload = {
            'app_id': self.app_id,
            'app_secret': self.app_secret
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('code') != 0:
                raise Exception(f"获取 token 失败: {data.get('msg')}")
            
            token = data.get('tenant_access_token')
            expire = data.get('expire', 7200)  # 默认2小时
            
            # 缓存 token
            _token_cache['token'] = token
            _token_cache['expires_at'] = time.time() + expire - 300  # 提前5分钟过期
            
            logger.info("🔄 已获取飞书 tenant_access_token")
            
            return token
        
        except Exception as e:
            logger.error(f"❌ 获取飞书 token 失败: {e}")
            raise
    
    def _refresh_token(self):
        """刷新 token"""
        global _token_cache
        _token_cache['token'] = None
        _token_cache['expires_at'] = 0
        self.tenant_access_token = self._get_tenant_access_token()
    
    def _request(self, method: str, path: str, data: Dict = None, params: Dict = None) -> Dict:
        """
        发送 API 请求
        
        Args:
            method: HTTP 方法 (GET, POST, PUT, DELETE)
            path: API 路径
            data: 请求数据
            params: URL 参数
        
        Returns:
            API 响应数据
        """
        url = f'{CALENDAR_API_BASE}{path}'
        headers = {
            'Authorization': f'Bearer {self.tenant_access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params,
                timeout=30
            )
            
            result = response.json()
            
            # 如果 token 过期，刷新后重试
            if result.get('code') == 99991663:  # token 过期错误码
                self._refresh_token()
                headers['Authorization'] = f'Bearer {self.tenant_access_token}'
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                    params=params,
                    timeout=30
                )
                result = response.json()
            
            if result.get('code') != 0:
                logger.warning(f"飞书 API 返回错误: {result}")
            
            return result
        
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 飞书 API 请求失败: {e}")
            raise
    
    def create_booking_event(self, booking_info: Dict[str, Any], calendar_id: str = 'primary') -> Dict[str, Any]:
        """
        在飞书日历中创建预订事件
        
        Args:
            booking_info: 预订信息字典，包含:
                - summary: 事件标题
                - description: 事件描述
                - location: 地点
                - start_date: 开始日期 (YYYY-MM-DD)
                - end_date: 结束日期 (YYYY-MM-DD)
                - booking_id: 预订ID
            calendar_id: 日历 ID (默认 'primary' 为主日历)
        
        Returns:
            创建结果字典
        """
        try:
            # 构造事件数据
            event_data = {
                'summary': booking_info.get('summary', '别墅预订'),
                'description': booking_info.get('description', ''),
                'location': {
                    'name': booking_info.get('location', '')
                },
                'color': 5,  # 颜色 ID
                'start': {
                    'date': booking_info.get('start_date'),
                    'timezone': 'Asia/Shanghai'
                },
                'end': {
                    'date': booking_info.get('end_date'),
                    'timezone': 'Asia/Shanghai'
                },
                'reminders': [
                    {
                        'minutes': 24 * 60,  # 提前1天
                        'method': 'email'
                    },
                    {
                        'minutes': 60,  # 提前1小时
                        'method': 'popup'
                    }
                ]
            }
            
            # 创建事件
            result = self._request(
                'POST',
                f'/calendars/{calendar_id}/events',
                data=event_data
            )
            
            if result.get('code') == 0:
                event = result.get('data', {}).get('event', {})
                logger.info(f"✅ 飞书日历事件已创建: {event.get('event_id')}")
                
                return {
                    'success': True,
                    'event_id': event.get('event_id'),
                    'html_link': event.get('html_link'),
                    'calendar': 'feishu'
                }
            else:
                return {
                    'success': False,
                    'error': result.get('msg', 'Unknown error'),
                    'code': result.get('code'),
                    'calendar': 'feishu'
                }
        
        except Exception as e:
            logger.error(f"❌ 创建飞书日历事件失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'calendar': 'feishu'
            }
    
    def update_booking_event(self, event_id: str, booking_info: Dict[str, Any], calendar_id: str = 'primary') -> Dict[str, Any]:
        """
        更新预订事件
        
        Args:
            event_id: 事件ID
            booking_info: 更新的预订信息
            calendar_id: 日历 ID
        
        Returns:
            更新结果字典
        """
        try:
            # 构造更新数据
            update_data = {}
            
            if 'summary' in booking_info:
                update_data['summary'] = booking_info['summary']
            if 'description' in booking_info:
                update_data['description'] = booking_info['description']
            if 'location' in booking_info:
                update_data['location'] = {'name': booking_info['location']}
            if 'start_date' in booking_info:
                update_data['start'] = {
                    'date': booking_info['start_date'],
                    'timezone': 'Asia/Shanghai'
                }
            if 'end_date' in booking_info:
                update_data['end'] = {
                    'date': booking_info['end_date'],
                    'timezone': 'Asia/Shanghai'
                }
            
            # 更新事件
            result = self._request(
                'PATCH',
                f'/calendars/{calendar_id}/events/{event_id}',
                data=update_data
            )
            
            if result.get('code') == 0:
                event = result.get('data', {}).get('event', {})
                logger.info(f"✅ 飞书日历事件已更新: {event_id}")
                
                return {
                    'success': True,
                    'event_id': event.get('event_id'),
                    'html_link': event.get('html_link'),
                    'calendar': 'feishu'
                }
            else:
                return {
                    'success': False,
                    'error': result.get('msg', 'Unknown error'),
                    'code': result.get('code'),
                    'calendar': 'feishu'
                }
        
        except Exception as e:
            logger.error(f"❌ 更新飞书日历事件失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'calendar': 'feishu'
            }
    
    def delete_event(self, event_id: str, calendar_id: str = 'primary') -> Dict[str, Any]:
        """
        删除事件
        
        Args:
            event_id: 事件ID
            calendar_id: 日历 ID
        
        Returns:
            删除结果字典
        """
        try:
            result = self._request(
                'DELETE',
                f'/calendars/{calendar_id}/events/{event_id}'
            )
            
            if result.get('code') == 0:
                logger.info(f"✅ 飞书日历事件已删除: {event_id}")
                
                return {
                    'success': True,
                    'event_id': event_id,
                    'calendar': 'feishu'
                }
            else:
                return {
                    'success': False,
                    'error': result.get('msg', 'Unknown error'),
                    'code': result.get('code'),
                    'calendar': 'feishu'
                }
        
        except Exception as e:
            logger.error(f"❌ 删除飞书日历事件失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'calendar': 'feishu'
            }
    
    def get_event(self, event_id: str, calendar_id: str = 'primary') -> Optional[Dict[str, Any]]:
        """
        获取事件详情
        
        Args:
            event_id: 事件ID
            calendar_id: 日历 ID
        
        Returns:
            事件详情字典
        """
        try:
            result = self._request(
                'GET',
                f'/calendars/{calendar_id}/events/{event_id}'
            )
            
            if result.get('code') == 0:
                return result.get('data', {}).get('event')
            return None
        
        except Exception as e:
            logger.error(f"❌ 获取飞书日历事件失败: {e}")
            return None
    
    def list_events(self, start_date: str, end_date: str, calendar_id: str = 'primary') -> List[Dict]:
        """
        获取日期范围内的事件列表
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            calendar_id: 日历 ID
        
        Returns:
            事件列表
        """
        try:
            params = {
                'time_min': f'{start_date}T00:00:00+08:00',
                'time_max': f'{end_date}T23:59:59+08:00'
            }
            
            result = self._request(
                'GET',
                f'/calendars/{calendar_id}/events',
                params=params
            )
            
            if result.get('code') == 0:
                events = result.get('data', {}).get('items', [])
                return events
            return []
        
        except Exception as e:
            logger.error(f"❌ 获取飞书日历事件列表失败: {e}")
            return []
    
    def check_date_availability(self, start_date: str, end_date: str, calendar_id: str = 'primary') -> Dict[str, Any]:
        """
        检查日期范围内的预订情况
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            calendar_id: 日历 ID
        
        Returns:
            可用性检查结果
        """
        try:
            events = self.list_events(start_date, end_date, calendar_id)
            
            return {
                'available': True,
                'events': events,
                'calendar': 'feishu'
            }
        
        except Exception as e:
            logger.error(f"❌ 检查飞书日历可用性失败: {e}")
            return {
                'available': False,
                'error': str(e),
                'calendar': 'feishu'
            }
    
    def get_calendar_list(self) -> List[Dict]:
        """
        获取日历列表
        
        Returns:
            日历列表
        """
        try:
            result = self._request('GET', '/calendars')
            
            if result.get('code') == 0:
                calendars = result.get('data', {}).get('calendar_list', [])
                return calendars
            return []
        
        except Exception as e:
            logger.error(f"❌ 获取飞书日历列表失败: {e}")
            return []
