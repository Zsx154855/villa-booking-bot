#!/usr/bin/env python3
"""
预订确认单 & 支付收据 PDF 生成模块
使用 LibreOffice CLI 将 ODT 模板转换为专业 PDF

使用方法:
    from generate_pdf import generate_booking_confirmation, generate_payment_receipt
    
    # 生成预订确认单
    booking_data = {
        'booking_id': 'BK20260428001',
        'villa_name': 'Cinq Royal Krungthep Kreetha',
        'region': '曼谷',
        'check_in': '2026-05-01',
        'checkout': '2026-05-05',
        'contact_name': '张三',
        'contact_phone': '+66 88 123 4567',
        'total_price': 60000,
        'status': 'confirmed'
    }
    pdf_path = generate_booking_confirmation(booking_data)
    
    # 生成支付收据
    payment_data = {
        'receipt_id': 'RCP20260428001',
        'booking_id': 'BK20260428001',
        'villa_name': 'Cinq Royal Krungthep Kreetha',
        'contact_name': '张三',
        'total_price': 60000,
        'payment_method': 'stripe',
        'payment_status': 'paid'
    }
    pdf_path = generate_payment_receipt(payment_data)
"""

import os
import sys
import re
import subprocess
import tempfile
import logging
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 路径配置 - 使用工作目录
WORKSPACE_DIR = Path("/app/data/所有对话/主对话")
BASE_DIR = WORKSPACE_DIR / "villa-booking-bot"
TEMPLATE_DIR = WORKSPACE_DIR / "别墅运营系统" / "docs"
OUTPUT_DIR = BASE_DIR / "docs" / "generated_pdfs"

# 模板文件
BOOKING_TEMPLATE = TEMPLATE_DIR / "booking_confirmation.odt"
RECEIPT_TEMPLATE = TEMPLATE_DIR / "payment_receipt.odt"

def ensure_output_dir():
    """确保输出目录存在"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR

def extract_and_modify_odt(template_path, data, output_path):
    """
    解压ODT模板，修改content.xml中的占位符，然后重新打包
    ODT文件本质上是ZIP格式
    """
    if not template_path.exists():
        raise FileNotFoundError(f"模板文件不存在: {template_path}")
    
    # 读取模板文件
    with zipfile.ZipFile(template_path, 'r') as zip_ref:
        content_xml = zip_ref.read('content.xml').decode('utf-8')
        
        # 替换占位符
        for key, value in data.items():
            if isinstance(value, datetime):
                value = value.strftime("%Y-%m-%d")
            elif value is None:
                value = ""
            
            # 替换 ${key} 占位符
            placeholder = f"${{{key}}}"
            content_xml = content_xml.replace(placeholder, str(value))
        
        # 创建新的ODT文件
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for item in zip_ref.namelist():
                if item == 'content.xml':
                    zipf.writestr(item, content_xml)
                else:
                    zipf.writestr(item, zip_ref.read(item))
    
    logger.info(f"✅ ODT文件已创建: {output_path}")
    return True

def convert_odt_to_pdf(odt_path, output_dir=None, output_name=None):
    """
    使用LibreOffice将ODT转换为PDF
    
    Args:
        odt_path: ODT文件路径
        output_dir: 输出目录
        output_name: 输出文件名（不含扩展名）
    
    Returns:
        PDF文件路径，失败返回None
    """
    if output_dir is None:
        output_dir = OUTPUT_DIR
    
    ensure_output_dir()
    
    # 确保路径是绝对路径
    odt_path = Path(odt_path).resolve()
    output_dir = Path(output_dir).resolve()
    
    if not odt_path.exists():
        raise FileNotFoundError(f"ODT文件不存在: {odt_path}")
    
    try:
        # 使用LibreOffice headless模式转换
        cmd = [
            'libreoffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', str(output_dir),
            str(odt_path)
        ]
        
        logger.info(f"执行命令: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            # 如果指定了输出名称，重命名生成的PDF
            if output_name:
                pdf_name = output_name + ".pdf"
                pdf_path = output_dir / pdf_name
                
                # 查找最近生成的PDF
                for f in output_dir.glob("*.pdf"):
                    if f.stat().st_mtime > odt_path.stat().st_mtime - 5:
                        if f != pdf_path:
                            # 移动并重命名
                            f.rename(pdf_path)
                        break
                
                if pdf_path.exists():
                    logger.info(f"✅ PDF已生成: {pdf_path}")
                    return str(pdf_path)
            else:
                # 查找最近生成的PDF
                for f in output_dir.glob("*.pdf"):
                    if f.stat().st_mtime > odt_path.stat().st_mtime - 5:
                        logger.info(f"✅ PDF已生成: {f}")
                        return str(f)
        
        logger.error(f"LibreOffice转换失败: {result.stderr}")
        return None
        
    except subprocess.TimeoutExpired:
        logger.error("LibreOffice转换超时")
        return None
    except Exception as e:
        logger.error(f"PDF转换错误: {e}")
        return None

def generate_booking_confirmation(booking_data, output_dir=None):
    """
    生成预订确认单PDF
    
    Args:
        booking_data: 预订信息字典，包含:
            - booking_id: 预订编号
            - villa_name: 别墅名称
            - region: 所在地区
            - bedrooms: 卧室数
            - bathrooms: 浴室数
            - max_guests: 最大入住人数
            - check_in: 入住日期 (YYYY-MM-DD)
            - checkout: 退房日期 (YYYY-MM-DD)
            - nights: 入住晚数（可选，会自动计算）
            - guests: 入住人数
            - contact_name: 联系人姓名
            - contact_phone: 联系电话
            - contact_note: 特殊要求
            - price_per_night: 每晚价格
            - total_price: 总价
            - status: 预订状态 (pending/confirmed/cancelled/completed)
            - created_at: 创建时间
        output_dir: 输出目录
    
    Returns:
        PDF文件路径，失败返回None
    """
    booking_id = booking_data.get('booking_id', 'unknown')
    logger.info(f"生成预订确认单: {booking_id}")
    
    try:
        # 计算天数
        if 'check_in' in booking_data and 'checkout' in booking_data:
            try:
                check_in = datetime.strptime(str(booking_data['check_in']), "%Y-%m-%d")
                checkout = datetime.strptime(str(booking_data['checkout']), "%Y-%m-%d")
                booking_data['nights'] = (checkout - check_in).days
            except:
                booking_data['nights'] = booking_data.get('nights', 1)
        
        # 格式化日期
        if 'created_at' in booking_data:
            try:
                created = datetime.strptime(str(booking_data['created_at']), "%Y-%m-%d %H:%M:%S")
                booking_data['created_date'] = created.strftime("%Y-%m-%d")
            except:
                booking_data['created_date'] = str(booking_data.get('created_at', ''))[:10]
        
        # 设置状态显示
        status_map = {
            'pending': '待确认',
            'confirmed': '已确认',
            'cancelled': '已取消',
            'completed': '已完成'
        }
        booking_data['status'] = status_map.get(booking_data.get('status', 'pending'), booking_data.get('status'))
        
        # 创建临时ODT文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.odt', delete=False, encoding='utf-8') as f:
            temp_odt = Path(f.name)
        
        # 解压、修改、重新打包ODT
        extract_and_modify_odt(BOOKING_TEMPLATE, booking_data, temp_odt)
        
        # 转换为PDF，使用预订ID命名
        pdf_path = convert_odt_to_pdf(temp_odt, output_dir, f"booking_confirmation_{booking_id}")
        
        # 清理临时文件
        try:
            temp_odt.unlink()
        except:
            pass
        
        return pdf_path
        
    except Exception as e:
        logger.error(f"生成预订确认单失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_payment_receipt(payment_data, output_dir=None):
    """
    生成支付收据PDF
    
    Args:
        payment_data: 支付信息字典，包含:
            - receipt_id: 收据编号
            - booking_id: 预订编号
            - villa_name: 别墅名称
            - region: 所在地区
            - check_in/check_in_date: 入住日期
            - check_out/check_out_date: 退房日期
            - nights: 入住晚数（可选，会自动计算）
            - contact_name: 客户姓名
            - contact_phone: 联系方式
            - price_per_night: 每晚价格
            - total_price: 实付金额
            - payment_date: 付款日期
            - payment_method: 支付方式 (stripe/transfer/alipay/wechat/cash)
            - payment_status: 支付状态 (paid/pending/failed/refunded)
        output_dir: 输出目录
    
    Returns:
        PDF文件路径，失败返回None
    """
    receipt_id = payment_data.get('receipt_id', 'unknown')
    logger.info(f"生成支付收据: {receipt_id}")
    
    try:
        # 标准化字段名
        if 'check_in_date' in payment_data and 'check_in' not in payment_data:
            payment_data['check_in'] = payment_data['check_in_date']
        if 'check_out_date' in payment_data and 'checkout' not in payment_data:
            payment_data['checkout'] = payment_data['check_out_date']
        
        # 计算天数
        if 'check_in' in payment_data and 'checkout' in payment_data:
            try:
                check_in = datetime.strptime(str(payment_data['check_in']), "%Y-%m-%d")
                checkout = datetime.strptime(str(payment_data['checkout']), "%Y-%m-%d")
                payment_data['nights'] = (checkout - check_in).days
            except:
                payment_data['nights'] = payment_data.get('nights', 1)
        
        # 格式化日期
        if 'payment_date' not in payment_data:
            payment_data['payment_date'] = datetime.now().strftime("%Y-%m-%d")
        
        if 'created_at' in payment_data:
            try:
                created = datetime.strptime(str(payment_data['created_at']), "%Y-%m-%d %H:%M:%S")
                payment_data['created_date'] = created.strftime("%Y-%m-%d")
            except:
                pass
        
        # 设置支付状态显示
        payment_status_map = {
            'paid': '已支付 ✓',
            'pending': '待支付',
            'failed': '支付失败',
            'refunded': '已退款'
        }
        payment_data['payment_status'] = payment_status_map.get(
            payment_data.get('payment_status', 'paid'), 
            payment_data.get('payment_status', '已支付')
        )
        
        # 设置支付方式显示
        payment_method_map = {
            'stripe': 'Stripe 信用卡',
            'transfer': '银行转账',
            'alipay': '支付宝',
            'wechat': '微信支付',
            'cash': '现金'
        }
        payment_data['payment_method'] = payment_method_map.get(
            payment_data.get('payment_method', 'stripe'),
            payment_data.get('payment_method', '其他')
        )
        
        # 创建临时ODT文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.odt', delete=False, encoding='utf-8') as f:
            temp_odt = Path(f.name)
        
        # 解压、修改、重新打包ODT
        extract_and_modify_odt(RECEIPT_TEMPLATE, payment_data, temp_odt)
        
        # 转换为PDF，使用收据ID命名
        pdf_path = convert_odt_to_pdf(temp_odt, output_dir, f"payment_receipt_{receipt_id}")
        
        # 清理临时文件
        try:
            temp_odt.unlink()
        except:
            pass
        
        return pdf_path
        
    except Exception as e:
        logger.error(f"生成支付收据失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_booking_from_db(booking_id):
    """
    从数据库获取预订信息
    """
    try:
        # 尝试导入数据库模块
        sys.path.insert(0, str(BASE_DIR))
        import database
        
        booking = database.get_booking(booking_id)
        return booking
        
    except ImportError:
        logger.warning("无法导入数据库模块，返回示例数据")
        return get_sample_booking_data(booking_id)
    except Exception as e:
        logger.error(f"获取预订信息失败: {e}")
        return None

def get_sample_booking_data(booking_id="BK20260428001"):
    """获取示例预订数据"""
    return {
        'booking_id': booking_id,
        'villa_name': 'Cinq Royal Krungthep Kreetha',
        'region': '曼谷 - Klongton区',
        'bedrooms': 6,
        'bathrooms': 7,
        'max_guests': 12,
        'check_in': '2026-05-01',
        'checkout': '2026-05-05',
        'nights': 4,
        'guests': 8,
        'contact_name': '张三',
        'contact_phone': '+66 88 123 4567',
        'contact_note': '需要婴儿床',
        'price_per_night': 15000,
        'total_price': 60000,
        'status': 'confirmed',
        'created_at': '2026-04-28 10:00:00'
    }

def get_sample_payment_data(receipt_id="RCP20260428001", booking_id="BK20260428001"):
    """获取示例支付数据"""
    return {
        'receipt_id': receipt_id,
        'booking_id': booking_id,
        'villa_name': 'Cinq Royal Krungthep Kreetha',
        'region': '曼谷 - Klongton区',
        'check_in_date': '2026-05-01',
        'check_out_date': '2026-05-05',
        'nights': 4,
        'contact_name': '张三',
        'contact_phone': '+66 88 123 4567',
        'price_per_night': 15000,
        'total_price': 60000,
        'payment_date': '2026-04-28',
        'payment_method': 'stripe',
        'payment_status': 'paid'
    }

# ============ CLI 测试 ============

if __name__ == "__main__":
    print("=" * 60)
    print("预订确认单 & 支付收据 PDF 生成器")
    print("=" * 60)
    
    # 测试生成预订确认单
    print("\n📋 测试生成预订确认单...")
    sample_booking = get_sample_booking_data()
    pdf_path = generate_booking_confirmation(sample_booking)
    
    if pdf_path:
        print(f"✅ 预订确认单PDF已生成: {pdf_path}")
    else:
        print("❌ 预订确认单PDF生成失败")
    
    # 测试生成支付收据
    print("\n💳 测试生成支付收据...")
    sample_payment = get_sample_payment_data()
    pdf_path = generate_payment_receipt(sample_payment)
    
    if pdf_path:
        print(f"✅ 支付收据PDF已生成: {pdf_path}")
    else:
        print("❌ 支付收据PDF生成失败")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
