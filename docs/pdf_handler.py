#!/usr/bin/env python3
"""
PDF生成命令处理器
为Bot添加 /receipt 和 /confirmation 命令
"""

import sys
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 路径配置
WORKSPACE_DIR = Path("/app/data/所有对话/主对话")
BASE_DIR = WORKSPACE_DIR / "villa-booking-bot"

# 添加模块路径
sys.path.insert(0, str(BASE_DIR / "docs"))

async def receipt_cmd(update, context, bot_token=None):
    """
    /receipt 命令处理器 - 发送预订收据PDF
    
    使用方式:
        /receipt <预订ID>
    
    示例:
        /receipt BK20260428001
    """
    try:
        from generate_pdf import generate_payment_receipt, get_sample_payment_data
        import database
        
        user_id = update.effective_user.id
        args = context.args
        
        if not args:
            await update.message.reply_text(
                "📋 请提供预订编号！\n\n"
                "使用方法: /receipt <预订ID>\n"
                "示例: /receipt BK20260428001"
            )
            return
        
        booking_id = args[0].strip()
        
        # 尝试从数据库获取预订信息
        try:
            booking = database.get_booking_by_booking_id(booking_id)
            
            if not booking:
                await update.message.reply_text(
                    f"❌ 未找到预订: {booking_id}\n\n"
                    "请检查预订编号是否正确。"
                )
                return
            
            # 检查预订是否属于当前用户
            if str(booking.get('user_id')) != str(user_id):
                await update.message.reply_text(
                    "❌ 您没有权限查看此预订的收据。"
                )
                return
            
        except Exception as e:
            logger.error(f"获取预订失败: {e}")
            await update.message.reply_text(
                "⚠️ 数据库查询失败，将使用示例数据生成。"
            )
            booking = get_sample_payment_data(receipt_id=f"RCP{booking_id}", booking_id=booking_id)
        
        # 生成收据
        await update.message.reply_text("⏳ 正在生成支付收据PDF...")
        
        # 准备收据数据
        receipt_data = {
            'receipt_id': f"RCP{booking_id}",
            'booking_id': booking_id,
            'villa_name': booking.get('villa_name', '未知别墅'),
            'region': booking.get('villa_region', ''),
            'check_in': booking.get('checkin', ''),
            'checkout': booking.get('checkout', ''),
            'nights': booking.get('nights', 1),
            'contact_name': booking.get('contact_name', '未知客户'),
            'contact_phone': booking.get('contact_phone', ''),
            'price_per_night': booking.get('price_per_night', 0),
            'total_price': booking.get('total_price', 0),
            'payment_date': booking.get('updated_at', ''),
            'payment_method': booking.get('payment_method', 'stripe'),
            'payment_status': 'paid' if booking.get('status') == 'confirmed' else 'pending'
        }
        
        pdf_path = generate_payment_receipt(receipt_data)
        
        if pdf_path:
            # 发送PDF文件
            with open(pdf_path, 'rb') as pdf_file:
                await update.message.reply_document(
                    document=pdf_file,
                    filename=f"payment_receipt_{booking_id}.pdf",
                    caption=f"✅ 支付收据 - {booking_id}\n\n"
                           f"🏠 {receipt_data['villa_name']}\n"
                           f"💰 {receipt_data['total_price']:,.0f} THB"
                )
            
            # 清理PDF文件
            try:
                Path(pdf_path).unlink()
            except:
                pass
        else:
            await update.message.reply_text(
                "❌ 生成收据PDF失败，请稍后重试。"
            )
        
    except Exception as e:
        logger.error(f"生成收据失败: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(
            "⚠️ 生成收据时发生错误，请联系客服。"
        )

async def confirmation_cmd(update, context):
    """
    /confirmation 命令处理器 - 发送预订确认单PDF
    
    使用方式:
        /confirmation <预订ID>
    
    示例:
        /confirmation BK20260428001
    """
    try:
        from generate_pdf import generate_booking_confirmation, get_sample_booking_data
        import database
        
        user_id = update.effective_user.id
        args = context.args
        
        if not args:
            await update.message.reply_text(
                "📋 请提供预订编号！\n\n"
                "使用方法: /confirmation <预订ID>\n"
                "示例: /confirmation BK20260428001"
            )
            return
        
        booking_id = args[0].strip()
        
        # 尝试从数据库获取预订信息
        try:
            booking = database.get_booking_by_booking_id(booking_id)
            
            if not booking:
                await update.message.reply_text(
                    f"❌ 未找到预订: {booking_id}\n\n"
                    "请检查预订编号是否正确。"
                )
                return
            
            # 检查预订是否属于当前用户
            if str(booking.get('user_id')) != str(user_id):
                await update.message.reply_text(
                    "❌ 您没有权限查看此预订的确认单。"
                )
                return
            
        except Exception as e:
            logger.error(f"获取预订失败: {e}")
            await update.message.reply_text(
                "⚠️ 数据库查询失败，将使用示例数据生成。"
            )
            booking = get_sample_booking_data(booking_id=booking_id)
        
        # 生成确认单
        await update.message.reply_text("⏳ 正在生成预订确认单PDF...")
        
        # 准备确认单数据
        confirmation_data = {
            'booking_id': booking_id,
            'villa_name': booking.get('villa_name', '未知别墅'),
            'region': booking.get('villa_region', ''),
            'bedrooms': booking.get('bedrooms', 0),
            'bathrooms': booking.get('bathrooms', 0),
            'max_guests': booking.get('max_guests', 0),
            'check_in': booking.get('checkin', ''),
            'checkout': booking.get('checkout', ''),
            'nights': booking.get('nights', 1),
            'guests': booking.get('guests', 1),
            'contact_name': booking.get('contact_name', '未知客户'),
            'contact_phone': booking.get('contact_phone', ''),
            'contact_note': booking.get('contact_note', ''),
            'price_per_night': booking.get('price_per_night', 0),
            'total_price': booking.get('total_price', 0),
            'status': booking.get('status', 'pending'),
            'created_at': booking.get('created_at', '')
        }
        
        pdf_path = generate_booking_confirmation(confirmation_data)
        
        if pdf_path:
            # 发送PDF文件
            with open(pdf_path, 'rb') as pdf_file:
                await update.message.reply_document(
                    document=pdf_file,
                    filename=f"booking_confirmation_{booking_id}.pdf",
                    caption=f"✅ 预订确认单 - {booking_id}\n\n"
                           f"🏠 {confirmation_data['villa_name']}\n"
                           f"📅 {confirmation_data['check_in']} 至 {confirmation_data['checkout']}\n"
                           f"💰 {confirmation_data['total_price']:,.0f} THB"
                )
            
            # 清理PDF文件
            try:
                Path(pdf_path).unlink()
            except:
                pass
        else:
            await update.message.reply_text(
                "❌ 生成确认单PDF失败，请稍后重试。"
            )
        
    except Exception as e:
        logger.error(f"生成确认单失败: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(
            "⚠️ 生成确认单时发生错误，请联系客服。"
        )

def register_pdf_handlers(application):
    """
    注册PDF相关命令处理器
    """
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    # 注册 /receipt 命令
    application.add_handler(
        telegram.ext.CommandHandler("receipt", receipt_cmd)
    )
    
    # 注册 /confirmation 命令
    application.add_handler(
        telegram.ext.CommandHandler("confirmation", confirmation_cmd)
    )
    
    # 注册 /booking 命令 (别名)
    application.add_handler(
        telegram.ext.CommandHandler("booking", confirmation_cmd)
    )
    
    logger.info("✅ PDF命令处理器已注册")

# 需要导入telegram
import telegram
