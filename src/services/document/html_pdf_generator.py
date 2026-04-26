#!/usr/bin/env python3
"""
HTML to PDF 转换器（备选方案）
当 ReportLab 中文支持有问题时使用此方案

依赖: weasyprint 或 pdfkit
安装: pip install weasyprint
     或: pip install pdfkit && apt install wkhtmltopdf
"""

import os
import io
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from string import Template

logger = logging.getLogger(__name__)

# 路径配置
BASE_DIR = Path(__file__).parent.parent.parent.parent
TEMPLATE_DIR = BASE_DIR / "templates"
DEFAULT_TEMPLATE = TEMPLATE_DIR / "confirmation.html"


class HTMLPDFGenerator:
    """基于 HTML 模板的 PDF 生成器"""
    
    def __init__(self, template_path: Optional[str] = None):
        """初始化 HTML PDF 生成器
        
        Args:
            template_path: HTML 模板路径
        """
        self.template_path = Path(template_path) if template_path else DEFAULT_TEMPLATE
        
        if not self.template_path.exists():
            raise FileNotFoundError(f"模板文件不存在: {self.template_path}")
        
        # 读取模板
        with open(self.template_path, 'r', encoding='utf-8') as f:
            self.template_content = f.read()
    
    def _prepare_data(
        self,
        booking_data: Dict[str, Any],
        villa_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """准备模板数据"""
        from datetime import datetime
        
        # 计算住宿天数
        nights = 0
        try:
            checkin = datetime.strptime(booking_data.get('checkin', ''), '%Y-%m-%d')
            checkout = datetime.strptime(booking_data.get('checkout', ''), '%Y-%m-%d')
            nights = (checkout - checkin).days
        except:
            pass
        
        # 获取设施列表
        amenities = villa_data.get('amenities', [])
        if isinstance(amenities, str):
            import json
            try:
                amenities = json.loads(amenities)
            except:
                amenities = []
        
        # 状态映射
        status = booking_data.get('status', 'pending')
        status_text_map = {
            'pending': '待确认 Pending',
            'confirmed': '已确认 Confirmed',
            'cancelled': '已取消 Cancelled',
            'completed': '已完成 Completed'
        }
        
        return {
            'booking_id': booking_data.get('booking_id', booking_data.get('id', 'N/A')),
            'status': status,
            'status_text': status_text_map.get(status, status),
            'booking_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'checkin': booking_data.get('checkin', 'N/A'),
            'checkout': booking_data.get('checkout', 'N/A'),
            'nights': str(nights),
            'guests': str(booking_data.get('guests', 0)),
            
            'villa_name': villa_data.get('name', 'N/A'),
            'villa_id': villa_data.get('id', 'N/A'),
            'region': villa_data.get('region', 'N/A'),
            'room_type': villa_data.get('room_type', 'N/A'),
            'bedrooms': str(villa_data.get('bedrooms', 0)),
            'bathrooms': str(villa_data.get('bathrooms', 0)),
            'max_guests': str(villa_data.get('max_guests', 0)),
            'amenities': '、'.join(amenities[:5]) if amenities else 'N/A',
            
            'contact_name': booking_data.get('contact_name', 'N/A'),
            'contact_phone': booking_data.get('contact_phone', 'N/A'),
            'contact_note': booking_data.get('contact_note', '无') or '无',
            
            'price_per_night': f"{villa_data.get('price_per_night', 0):,.0f}",
            'total_price': f"{booking_data.get('total_price', 0):,.0f}",
            
            'year': str(datetime.now().year),
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
    
    def generate(
        self,
        booking_data: Dict[str, Any],
        villa_data: Dict[str, Any],
        output_filename: Optional[str] = None
    ) -> str:
        """生成 PDF 文件
        
        Args:
            booking_data: 预订信息
            villa_data: 别墅信息
            output_filename: 输出文件名
            
        Returns:
            PDF 文件路径
        """
        try:
            import weasyprint
            HAS_WEASYPRINT = True
        except ImportError:
            HAS_WEASYPRINT = False
        
        try:
            import pdfkit
            HAS_PDFKIT = True
        except ImportError:
            HAS_PDFKIT = False
        
        if not HAS_WEASYPRINT and not HAS_PDFKIT:
            raise ImportError(
                "请安装 weasyprint 或 pdfkit:\n"
                "  pip install weasyprint\n"
                "  或\n"
                "  pip install pdfkit && apt install wkhtmltopdf"
            )
        
        # 准备数据
        data = self._prepare_data(booking_data, villa_data)
        
        # 渲染 HTML
        html_content = Template(self.template_content).substitute(data)
        
        # 生成文件名
        if not output_filename:
            booking_id = booking_data.get('booking_id', booking_data.get('id', 'UNKNOWN'))
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"booking_{booking_id}_{timestamp}.pdf"
        
        output_path = BASE_DIR / "data" / "pdfs" / output_filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 转换 PDF
        if HAS_WEASYPRINT:
            pdf = weasyprint.HTML(string=html_content).write_pdf()
            with open(output_path, 'wb') as f:
                f.write(pdf)
        else:
            pdfkit.from_string(html_content, str(output_path))
        
        logger.info(f"✅ HTML PDF 生成成功: {output_path}")
        return str(output_path)
    
    def generate_bytes(
        self,
        booking_data: Dict[str, Any],
        villa_data: Dict[str, Any]
    ) -> bytes:
        """生成 PDF 到内存"""
        try:
            import weasyprint
            HAS_WEASYPRINT = True
        except ImportError:
            HAS_WEASYPRINT = False
        
        if not HAS_WEASYPRINT:
            raise ImportError("generate_bytes 需要 weasyprint")
        
        data = self._prepare_data(booking_data, villa_data)
        html_content = Template(self.template_content).substitute(data)
        
        return weasyprint.HTML(string=html_content).write_pdf()


# 便捷函数
def generate_html_pdf(
    booking_data: Dict[str, Any],
    villa_data: Dict[str, Any],
    output_dir: Optional[str] = None
) -> str:
    """生成预订确认单 PDF（HTML方案）"""
    generator = HTMLPDFGenerator()
    return generator.generate(booking_data, villa_data)


# 测试
if __name__ == "__main__":
    test_booking = {
        'booking_id': 'BK20240101ABC',
        'checkin': '2024-01-15',
        'checkout': '2024-01-18',
        'guests': 4,
        'contact_name': '张三',
        'contact_phone': '+86 138 0000 0000',
        'contact_note': '需要婴儿床',
        'price_per_night': 1888,
        'total_price': 5664,
        'status': 'confirmed'
    }
    
    test_villa = {
        'id': 'PAT001',
        'name': '热带风情海景别墅',
        'region': '芭提雅',
        'room_type': '独栋别墅',
        'bedrooms': 3,
        'bathrooms': 2,
        'max_guests': 6,
        'price_per_night': 1888,
        'amenities': ['私人泳池', '海景阳台', '厨房', 'WiFi', '停车场'],
    }
    
    try:
        generator = HTMLPDFGenerator()
        pdf_path = generator.generate(test_booking, test_villa)
        print(f"✅ HTML PDF 已生成: {pdf_path}")
    except ImportError as e:
        print(f"⚠️ {e}")
        print("建议使用 ReportLab 方案（已安装）:")
        print("  python -m src.services.document.pdf_generator")
