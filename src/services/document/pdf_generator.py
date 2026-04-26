#!/usr/bin/env python3
"""
预订确认单 PDF 生成器
Taimili Villa Booking System

依赖: ReportLab (纯Python，无需外部依赖)
安装: pip install reportlab
"""

import os
import io
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm, cm
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, KeepTogether
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    raise ImportError("请安装 reportlab: pip install reportlab")

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 路径配置
BASE_DIR = Path(__file__).parent.parent.parent.parent
FONTS_DIR = BASE_DIR / "fonts"

# 尝试注册中文字体
def _register_chinese_fonts():
    """注册中文字体"""
    font_paths = [
        FONTS_DIR / "NotoSansSC-Regular.ttf",
        Path("/usr/share/fonts/truetype/noto/NotoSansSC-Regular.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansSC-Regular.otf"),
        Path("C:/Windows/Fonts/msyh.ttc"),  # Windows 微软雅黑
    ]
    
    for font_path in font_paths:
        if font_path.exists():
            try:
                pdfmetrics.registerFont(TTFont('NotoSansSC', str(font_path)))
                logger.info(f"✅ 已注册中文字体: {font_path}")
                return 'NotoSansSC'
            except Exception as e:
                logger.warning(f"字体注册失败 {font_path}: {e}")
    
    logger.warning("未找到中文字体，PDF中文可能显示为方块")
    return 'Helvetica'

# 注册字体
CHINESE_FONT = _register_chinese_fonts()


class PDFGenerator:
    """预订确认单 PDF 生成器"""
    
    # 颜色配置
    PRIMARY_COLOR = colors.HexColor("#1a5f7a")      # 深青色
    SECONDARY_COLOR = colors.HexColor("#57c5b6")    # 浅青色
    ACCENT_COLOR = colors.HexColor("#159895")       # 强调色
    TEXT_COLOR = colors.HexColor("#2c3e50")         # 深灰文字
    LIGHT_BG = colors.HexColor("#f8f9fa")           # 浅灰背景
    BORDER_COLOR = colors.HexColor("#dee2e6")        # 边框色
    SUCCESS_COLOR = colors.HexColor("#28a745")      # 成功绿
    WARNING_COLOR = colors.HexColor("#ffc107")      # 警告黄
    
    def __init__(self, output_dir: Optional[str] = None):
        """初始化 PDF 生成器
        
        Args:
            output_dir: PDF 输出目录，默认为 data/pdfs
        """
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = BASE_DIR / "data" / "pdfs"
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化样式
        self.styles = self._create_styles()
    
    def _create_styles(self) -> Dict[str, ParagraphStyle]:
        """创建自定义样式"""
        base_styles = getSampleStyleSheet()
        
        styles = {
            # 标题
            'Title': ParagraphStyle(
                'Title',
                fontName=CHINESE_FONT,
                fontSize=24,
                textColor=self.PRIMARY_COLOR,
                alignment=TA_CENTER,
                spaceAfter=6*mm,
                spaceBefore=0,
            ),
            # 副标题
            'Subtitle': ParagraphStyle(
                'Subtitle',
                fontName=CHINESE_FONT,
                fontSize=12,
                textColor=self.TEXT_COLOR,
                alignment=TA_CENTER,
                spaceAfter=10*mm,
            ),
            # 预订编号
            'BookingID': ParagraphStyle(
                'BookingID',
                fontName=CHINESE_FONT,
                fontSize=16,
                textColor=self.ACCENT_COLOR,
                alignment=TA_CENTER,
                spaceAfter=8*mm,
            ),
            # 区块标题
            'SectionTitle': ParagraphStyle(
                'SectionTitle',
                fontName=CHINESE_FONT,
                fontSize=13,
                textColor=self.PRIMARY_COLOR,
                alignment=TA_LEFT,
                spaceBefore=8*mm,
                spaceAfter=4*mm,
            ),
            # 正文
            'BodyText': ParagraphStyle(
                'BodyText',
                fontName=CHINESE_FONT,
                fontSize=10,
                textColor=self.TEXT_COLOR,
                alignment=TA_LEFT,
                spaceAfter=3*mm,
                leading=14,
            ),
            # 正文居中
            'BodyTextCenter': ParagraphStyle(
                'BodyTextCenter',
                fontName=CHINESE_FONT,
                fontSize=10,
                textColor=self.TEXT_COLOR,
                alignment=TA_CENTER,
                spaceAfter=3*mm,
            ),
            # 表格标签
            'TableLabel': ParagraphStyle(
                'TableLabel',
                fontName=CHINESE_FONT,
                fontSize=10,
                textColor=self.TEXT_COLOR,
                alignment=TA_LEFT,
            ),
            # 表格内容
            'TableValue': ParagraphStyle(
                'TableValue',
                fontName=CHINESE_FONT,
                fontSize=10,
                textColor=self.TEXT_COLOR,
                alignment=TA_LEFT,
            ),
            # 重要信息
            'Important': ParagraphStyle(
                'Important',
                fontName=CHINESE_FONT,
                fontSize=10,
                textColor=self.SUCCESS_COLOR,
                alignment=TA_LEFT,
                spaceAfter=2*mm,
                leading=14,
            ),
            # 页脚
            'Footer': ParagraphStyle(
                'Footer',
                fontName=CHINESE_FONT,
                fontSize=8,
                textColor=colors.gray,
                alignment=TA_CENTER,
            ),
            # 须知
            'Notice': ParagraphStyle(
                'Notice',
                fontName=CHINESE_FONT,
                fontSize=9,
                textColor=self.TEXT_COLOR,
                alignment=TA_JUSTIFY,
                spaceAfter=2*mm,
                leading=12,
            ),
        }
        
        return styles
    
    def generate(
        self,
        booking_data: Dict[str, Any],
        villa_data: Dict[str, Any],
        output_filename: Optional[str] = None
    ) -> str:
        """生成预订确认单 PDF
        
        Args:
            booking_data: 预订信息
            villa_data: 别墅信息
            output_filename: 输出文件名
            
        Returns:
            PDF 文件路径
        """
        # 生成文件名
        if not output_filename:
            booking_id = booking_data.get('booking_id', booking_data.get('id', 'UNKNOWN'))
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"booking_{booking_id}_{timestamp}.pdf"
        
        output_path = self.output_dir / output_filename
        
        # 创建 PDF
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm,
        )
        
        # 构建 PDF 内容
        story = self._build_content(booking_data, villa_data)
        
        # 生成 PDF
        doc.build(story)
        logger.info(f"✅ PDF 生成成功: {output_path}")
        
        return str(output_path)
    
    def generate_bytes(
        self,
        booking_data: Dict[str, Any],
        villa_data: Dict[str, Any]
    ) -> bytes:
        """生成 PDF 到内存（用于发送）"""
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm,
        )
        
        story = self._build_content(booking_data, villa_data)
        doc.build(story)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def _build_content(
        self,
        booking_data: Dict[str, Any],
        villa_data: Dict[str, Any]
    ) -> list:
        """构建 PDF 内容"""
        story = []
        
        # ===== 标题区域 =====
        story.append(Paragraph("度假别墅预订确认单", self.styles['Title']))
        story.append(Paragraph("VACATION VILLA BOOKING CONFIRMATION", self.styles['Subtitle']))
        story.append(HRFlowable(
            width="100%", thickness=2, color=self.PRIMARY_COLOR, spaceAfter=6*mm
        ))
        
        # ===== 预订编号 =====
        booking_id = booking_data.get('booking_id', booking_data.get('id', 'N/A'))
        story.append(Paragraph(f"预订编号 Booking No: {booking_id}", self.styles['BookingID']))
        
        # ===== 预订状态 =====
        status = booking_data.get('status', 'pending')
        status_text = {
            'pending': '待确认 Pending',
            'confirmed': '已确认 Confirmed',
            'cancelled': '已取消 Cancelled',
            'completed': '已完成 Completed'
        }.get(status, status)
        
        story.append(Paragraph(f"状态: {status_text}", self.styles['BodyTextCenter']))
        story.append(Spacer(1, 5*mm))
        
        # ===== 基本信息区块 =====
        story.append(Paragraph("📋 预订信息 Booking Information", self.styles['SectionTitle']))
        
        basic_info = [
            ['预订日期 Booking Date:', datetime.now().strftime('%Y-%m-%d %H:%M')],
            ['入住日期 Check-in:', booking_data.get('checkin', 'N/A')],
            ['退房日期 Check-out:', booking_data.get('checkout', 'N/A')],
            ['入住人数 Guests:', f"{booking_data.get('guests', 0)} 人"],
        ]
        
        # 计算住宿天数
        try:
            checkin = datetime.strptime(booking_data.get('checkin', ''), '%Y-%m-%d')
            checkout = datetime.strptime(booking_data.get('checkout', ''), '%Y-%m-%d')
            nights = (checkout - checkin).days
            basic_info.insert(3, ['住宿天数 Duration:', f'{nights} 晚'])
        except:
            pass
        
        story.append(self._create_table(basic_info))
        story.append(Spacer(1, 5*mm))
        
        # ===== 别墅信息区块 =====
        story.append(Paragraph("🏠 别墅信息 Villa Details", self.styles['SectionTitle']))
        
        # 获取设施列表
        amenities = villa_data.get('amenities', [])
        if isinstance(amenities, str):
            import json
            try:
                amenities = json.loads(amenities)
            except:
                amenities = []
        
        villa_info = [
            ['别墅名称 Villa:', villa_data.get('name', 'N/A')],
            ['别墅编号 Villa ID:', villa_data.get('id', 'N/A')],
            ['地区 Region:', villa_data.get('region', 'N/A')],
            ['房型 Room Type:', villa_data.get('room_type', 'N/A')],
            ['卧室 Bedrooms:', f"{villa_data.get('bedrooms', 0)} 间"],
            ['卫生间 Bathrooms:', f"{villa_data.get('bathrooms', 0)} 间"],
            ['最大入住 Max Guests:', f"{villa_data.get('max_guests', 0)} 人"],
            ['配套设施 Amenities:', ', '.join(amenities[:5]) if amenities else 'N/A'],
        ]
        
        story.append(self._create_table(villa_info))
        story.append(Spacer(1, 5*mm))
        
        # ===== 客户信息区块 =====
        story.append(Paragraph("👤 客户信息 Guest Information", self.styles['SectionTitle']))
        
        customer_info = [
            ['姓名 Name:', booking_data.get('contact_name', 'N/A')],
            ['电话 Phone:', booking_data.get('contact_phone', 'N/A')],
            ['备注 Note:', booking_data.get('contact_note', '无') or '无'],
        ]
        
        story.append(self._create_table(customer_info))
        story.append(Spacer(1, 5*mm))
        
        # ===== 价格明细区块 =====
        story.append(Paragraph("💰 价格明细 Pricing Details", self.styles['SectionTitle']))
        
        price_per_night = booking_data.get('price_per_night', villa_data.get('price_per_night', 0))
        total_price = booking_data.get('total_price', 0)
        
        # 尝试重新计算
        if total_price == 0 and price_per_night > 0:
            try:
                checkin = datetime.strptime(booking_data.get('checkin', ''), '%Y-%m-%d')
                checkout = datetime.strptime(booking_data.get('checkout', ''), '%Y-%m-%d')
                nights = (checkout - checkin).days
                total_price = price_per_night * nights
            except:
                pass
        
        pricing_info = [
            ['单价 Daily Rate:', f'฿{price_per_night:,.0f} / 晚'],
            ['住宿晚数 Nights:', str(nights) if 'nights' in dir() else 'N/A'],
            ['小计 Subtotal:', f'฿{total_price:,.0f}'],
            ['服务费 Service Fee:', '已含 Included'],
        ]
        
        # 添加价格表格
        price_table = self._create_table(pricing_info)
        
        # 总价行
        total_row = [[
            Paragraph(f'<b>总计 Total:</b>', self.styles['TableLabel']),
            Paragraph(f'<b>฿{total_price:,.0f}</b>', self.styles['TableValue'])
        ]]
        
        full_price_table = Table(
            [[price_table], [total_row]],
            colWidths=[170*mm]
        )
        full_price_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), CHINESE_FONT),
            ('FONTSIZE', (0, -1), (-1, -1), 11),
            ('TEXTCOLOR', (0, -1), (-1, -1), self.SUCCESS_COLOR),
            ('BACKGROUND', (0, -1), (-1, -1), self.LIGHT_BG),
            ('TOPPADDING', (0, -1), (-1, -1), 4*mm),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 4*mm),
            ('ROUNDEDCORNERS', [3*mm]),
        ]))
        
        story.append(full_price_table)
        story.append(Spacer(1, 8*mm))
        
        # ===== 入住须知区块 =====
        story.append(HRFlowable(width="100%", thickness=1, color=self.BORDER_COLOR, spaceAfter=6*mm))
        story.append(Paragraph("📌 入住须知 Check-in Instructions", self.styles['SectionTitle']))
        
        instructions = [
            "1. 请在入住当天 14:00 后办理入住，退房时间为次日 12:00 前。",
            "2. 入住时请出示有效身份证件（护照或身份证）。",
            "3. 请妥善保管别墅钥匙和门禁卡，如有遗失需照价赔偿。",
            "4. 别墅内禁止吸烟，违规将收取清洁费。",
            "5. 退房时请将钥匙交还前台或放置指定位置。",
            "6. 如需延迟退房，请提前与前台联系，可能产生额外费用。",
            "7. 预订确认后如需修改或取消，请提前 48 小时通知。",
        ]
        
        for instruction in instructions:
            story.append(Paragraph(instruction, self.styles['Notice']))
        
        story.append(Spacer(1, 8*mm))
        
        # ===== 联系方式区块 =====
        story.append(Paragraph("📞 联系我们 Contact Us", self.styles['SectionTitle']))
        
        contact_info = [
            ['客服热线:', '+66 XX XXX XXXX'],
            ['微信号:', '@TaimiliSupport'],
            ['邮箱:', 'support@taimili.com'],
            ['工作时间:', '09:00 - 21:00 (泰国时间)'],
        ]
        
        story.append(self._create_table(contact_info))
        story.append(Spacer(1, 10*mm))
        
        # ===== 页脚 =====
        story.append(HRFlowable(width="100%", thickness=1, color=self.BORDER_COLOR, spaceAfter=4*mm))
        footer_text = (
            f"Taimili Villa Booking © {datetime.now().year} | "
            f"Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
            "This is an automated confirmation document."
        )
        story.append(Paragraph(footer_text, self.styles['Footer']))
        
        return story
    
    def _create_table(self, data: list, col_widths: Optional[list] = None) -> Table:
        """创建表格
        
        Args:
            data: 表格数据 [[label, value], ...]
            col_widths: 列宽列表
            
        Returns:
            Table 对象
        """
        if not col_widths:
            col_widths = [60*mm, 110*mm]
        
        # 构建表格数据
        table_data = []
        for label, value in data:
            table_data.append([
                Paragraph(f'<b>{label}</b>', self.styles['TableLabel']),
                Paragraph(str(value), self.styles['TableValue'])
            ])
        
        table = Table(table_data, colWidths=col_widths)
        table.setStyle(TableStyle([
            # 表格样式
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # 内边距
            ('TOPPADDING', (0, 0), (-1, -1), 3*mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            # 边框
            ('LINEBELOW', (0, 0), (-1, -2), 0.5, self.BORDER_COLOR),
            # 交替行背景
            ('BACKGROUND', (0, 0), (-1, 0), self.LIGHT_BG),
        ]))
        
        return table


# ============ 便捷函数 ============

def generate_confirmation_pdf(
    booking_data: Dict[str, Any],
    villa_data: Dict[str, Any],
    output_dir: Optional[str] = None
) -> str:
    """生成预订确认单 PDF（便捷函数）
    
    Args:
        booking_data: 预订信息
        villa_data: 别墅信息
        output_dir: 输出目录
        
    Returns:
        PDF 文件路径
    """
    generator = PDFGenerator(output_dir)
    return generator.generate(booking_data, villa_data)


def generate_confirmation_pdf_bytes(
    booking_data: Dict[str, Any],
    villa_data: Dict[str, Any]
) -> bytes:
    """生成预订确认单 PDF 到内存（便捷函数）
    
    Args:
        booking_data: 预订信息
        villa_data: 别墅信息
        
    Returns:
        PDF 字节数据
    """
    generator = PDFGenerator()
    return generator.generate_bytes(booking_data, villa_data)


# ============ 测试代码 ============

if __name__ == "__main__":
    # 测试数据
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
        'amenities': ['私人泳池', '海景阳台', '厨房', 'WiFi', '停车场', '烧烤区', '管家服务'],
        'description': '距离海滩仅50米，三卧独栋别墅'
    }
    
    # 生成 PDF
    generator = PDFGenerator()
    pdf_path = generator.generate(test_booking, test_villa)
    print(f"✅ 测试 PDF 已生成: {pdf_path}")
