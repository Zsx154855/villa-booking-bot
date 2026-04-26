"""
Review Module
评价管理模块 - 评价收集、分析、回复
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# ============ 评价状态 ============
REVIEW_STATUS = {
    'pending': '待审核',
    'approved': '已发布',
    'rejected': '已拒绝',
    'hidden': '已隐藏'
}

# ============ 评分维度 ============
RATING_DIMENSIONS = [
    {'key': 'overall', 'name': '总体评分', 'icon': '⭐'},
    {'key': 'cleanliness', 'name': '清洁程度', 'icon': '🧹'},
    {'key': 'location', 'name': '地理位置', 'icon': '📍'},
    {'key': 'service', 'name': '服务水平', 'icon': '🤝'},
    {'key': 'facilities', 'name': '设施配置', 'icon': '🔧'},
    {'key': 'value', 'name': '性价比', 'icon': '💰'}
]


# ============ 评价数据模型 ============
class Review:
    """评价数据类"""
    
    def __init__(self, user_id: int, villa_id: str, booking_id: str):
        self.review_id = str(uuid.uuid4())[:8].upper()
        self.user_id = user_id
        self.villa_id = villa_id
        self.booking_id = booking_id
        
        # 评分（1-5星）
        self.overall_rating = 0
        self.ratings = {}
        
        # 评价内容
        self.content = ''
        self.images = []
        self.tags = []
        
        # 元数据
        self.status = 'pending'
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
        # 互动数据
        self.likes = 0
        self.reply = None
        self.reply_at = None
    
    def set_rating(self, rating: int):
        """设置总体评分"""
        if 1 <= rating <= 5:
            self.overall_rating = rating
            self.ratings['overall'] = rating
    
    def add_dimension_rating(self, dimension: str, rating: int):
        """添加维度评分"""
        if 1 <= rating <= 5:
            self.ratings[dimension] = rating
            # 重新计算总体评分（平均值）
            if self.ratings:
                self.overall_rating = round(sum(self.ratings.values()) / len(self.ratings), 1)
    
    def set_content(self, content: str):
        """设置评价内容"""
        self.content = content.strip()
    
    def add_tag(self, tag: str):
        """添加标签"""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def approve(self):
        """审核通过"""
        self.status = 'approved'
        self.updated_at = datetime.now()
    
    def reject(self, reason: str = ''):
        """审核拒绝"""
        self.status = 'rejected'
        self.updated_at = datetime.now()
        if reason:
            self.reply = f'拒绝原因: {reason}'
    
    def hide(self):
        """隐藏评价"""
        self.status = 'hidden'
        self.updated_at = datetime.now()
    
    def add_reply(self, reply_content: str):
        """添加回复"""
        self.reply = reply_content
        self.reply_at = datetime.now()
    
    def like(self):
        """点赞"""
        self.likes += 1
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        rating_text = '⭐' * int(self.overall_rating) + '☆' * (5 - int(self.overall_rating))
        
        return {
            'review_id': self.review_id,
            'user_id': self.user_id,
            'villa_id': self.villa_id,
            'booking_id': self.booking_id,
            'overall_rating': self.overall_rating,
            'rating_text': rating_text,
            'ratings': self.ratings,
            'content': self.content,
            'images': self.images,
            'tags': self.tags,
            'status': self.status,
            'status_name': REVIEW_STATUS.get(self.status, '未知'),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            'likes': self.likes,
            'reply': self.reply,
            'reply_at': self.reply_at.strftime('%Y-%m-%d %H:%M:%S') if self.reply_at else None
        }


# ============ 评价标签 ============
REVIEW_TAGS = [
    '海景超美', '房间干净', '服务热情', '设施完善', '位置便利',
    '性价比高', '安静舒适', '适合家庭', '泳池很棒', '早餐好吃',
    '需要改善', '性价比一般', '设施陈旧', '位置偏远的', '噪音较大'
]


# ============ 评价分析 ============
class ReviewAnalytics:
    """评价分析"""
    
    def __init__(self):
        self._reviews: List[Review] = []
    
    def add_review(self, review: Review):
        """添加评价"""
        self._reviews.append(review)
    
    def get_villa_reviews(self, villa_id: str) -> List[Review]:
        """获取别墅的所有评价"""
        return [r for r in self._reviews if r.villa_id == villa_id and r.status == 'approved']
    
    def get_average_rating(self, villa_id: str = None) -> Dict:
        """获取平均评分"""
        if villa_id:
            reviews = self.get_villa_reviews(villa_id)
        else:
            reviews = [r for r in self._reviews if r.status == 'approved']
        
        if not reviews:
            return {
                'count': 0,
                'overall': 0,
                'dimensions': {}
            }
        
        # 计算各维度平均
        dimension_sums = {}
        dimension_counts = {}
        
        for review in reviews:
            for dim, rating in review.ratings.items():
                if dim not in dimension_sums:
                    dimension_sums[dim] = 0
                    dimension_counts[dim] = 0
                dimension_sums[dim] += rating
                dimension_counts[dim] += 1
        
        dimensions = {}
        for dim in dimension_sums:
            dimensions[dim] = round(dimension_sums[dim] / dimension_counts[dim], 1)
        
        overall_avg = round(sum(d.overall_rating for d in reviews) / len(reviews), 1)
        
        return {
            'count': len(reviews),
            'overall': overall_avg,
            'dimensions': dimensions
        }
    
    def get_rating_distribution(self, villa_id: str = None) -> Dict:
        """获取评分分布"""
        reviews = self.get_villa_reviews(villa_id) if villa_id else \
                  [r for r in self._reviews if r.status == 'approved']
        
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        for review in reviews:
            rating = int(review.overall_rating)
            if 1 <= rating <= 5:
                distribution[rating] += 1
        
        return distribution
    
    def get_common_tags(self, villa_id: str = None, limit: int = 10) -> List[Dict]:
        """获取热门标签"""
        reviews = self.get_villa_reviews(villa_id) if villa_id else \
                  [r for r in self._reviews if r.status == 'approved']
        
        tag_counts = {}
        for review in reviews:
            for tag in review.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [{'tag': tag, 'count': count} for tag, count in sorted_tags[:limit]]
    
    def get_recent_reviews(self, villa_id: str = None, limit: int = 5) -> List[Review]:
        """获取最新评价"""
        reviews = self.get_villa_reviews(villa_id) if villa_id else \
                  [r for r in self._reviews if r.status == 'approved']
        
        # 按时间倒序
        sorted_reviews = sorted(reviews, key=lambda x: x.created_at, reverse=True)
        
        return sorted_reviews[:limit]


# ============ 评价管理器 ============
class ReviewManager:
    """评价管理器"""
    
    def __init__(self):
        self._reviews: Dict[str, Review] = {}  # review_id -> Review
        self._booking_reviews: Dict[str, str] = {}  # booking_id -> review_id
        self._analytics = ReviewAnalytics()
    
    def create_review(self, user_id: int, villa_id: str, booking_id: str) -> Review:
        """创建评价"""
        # 检查是否已评价
        if booking_id in self._booking_reviews:
            return self._reviews[self._booking_reviews[booking_id]]
        
        review = Review(user_id, villa_id, booking_id)
        self._reviews[review.review_id] = review
        self._booking_reviews[booking_id] = review.review_id
        
        return review
    
    def get_review(self, review_id: str) -> Optional[Review]:
        """获取评价"""
        return self._reviews.get(review_id)
    
    def get_review_by_booking(self, booking_id: str) -> Optional[Review]:
        """通过预订ID获取评价"""
        review_id = self._booking_reviews.get(booking_id)
        if review_id:
            return self._reviews.get(review_id)
        return None
    
    def submit_review(self, review_id: str, rating: int, content: str = '', 
                      tags: List[str] = None) -> Dict:
        """提交评价"""
        review = self._reviews.get(review_id)
        if not review:
            return {'success': False, 'error': 'not_found'}
        
        review.set_rating(rating)
        if content:
            review.set_content(content)
        if tags:
            for tag in tags:
                review.add_tag(tag)
        
        # 自动审核通过（实际应该人工审核）
        review.approve()
        
        # 添加到分析器
        self._analytics.add_review(review)
        
        logger.info(f"用户 {review.user_id} 提交评价: {review.review_id}, 评分: {rating}")
        
        return {
            'success': True,
            'review': review.to_dict(),
            'points_earned': rating * 10  # 每星10积分
        }
    
    def get_user_reviews(self, user_id: int) -> List[Dict]:
        """获取用户的所有评价"""
        user_reviews = [r for r in self._reviews.values() if r.user_id == user_id]
        return [r.to_dict() for r in sorted(user_reviews, key=lambda x: x.created_at, reverse=True)]
    
    def get_villa_rating_summary(self, villa_id: str) -> Dict:
        """获取别墅评分摘要"""
        avg = self._analytics.get_average_rating(villa_id)
        dist = self._analytics.get_rating_distribution(villa_id)
        tags = self._analytics.get_common_tags(villa_id, 5)
        
        return {
            'villa_id': villa_id,
            'total_reviews': avg['count'],
            'average_rating': avg['overall'],
            'rating_distribution': dist,
            'top_tags': tags
        }


# 全局评价管理器实例
review_manager = ReviewManager()
