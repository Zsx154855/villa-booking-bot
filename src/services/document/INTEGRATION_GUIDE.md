# 预订确认单 PDF 生成功能 - 集成指南

## 📦 依赖安装

首先安装 ReportLab：

```bash
pip install reportlab
```

然后添加到 `requirements.txt`：

```
# PDF 生成
reportlab>=4.0.0
```

---

## 🔧 快速集成

### 1. 导入模块

```python
# 在 bot.py 或 handlers 中导入
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.services.document import generate_confirmation_pdf, generate_confirmation_pdf_bytes
```

### 2. 在预订成功回调中生成 PDF

修改 `villa-booking-bot/bot.py` 中的 `book_confirm` 函数：

```python
async def book_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """预订 - 确认"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm_no":
        # ... 取消处理
    
    # 创建预订记录（原有代码保持不变）
    # ... booking creation code ...
    
    if save_booking(booking):
        # 获取别墅完整信息
        villa_full = database.get_villa(villa.get('id', ''))
        
        try:
            # 生成 PDF
            from src.services.document import generate_confirmation_pdf_bytes
            
            pdf_bytes = generate_confirmation_pdf_bytes(booking, villa_full)
            
            # 发送 PDF 给用户
            await context.bot.send_document(
                chat_id=query.from_user.id,
                document=io.BytesIO(pdf_bytes),
                filename=f"booking_{booking_id}.pdf",
                caption=f"✅ 预订确认单 | Booking #{booking_id}\n\n"
                        f"请保存此确认单作为入住凭证"
            )
        except Exception as e:
            logger.warning(f"PDF 生成失败: {e}")
            # PDF 生成失败不影响主流程
        
        # 显示成功消息（原有代码）
        # ...
```

### 3. 完整的预订成功处理示例

```python
import io
import logging

logger = logging.getLogger(__name__)

async def book_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """预订 - 确认"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm_no":
        await query.edit_message_text(
            "❌ 预订已取消\n\n如需重新预订，请输入 /book",
            reply_markup=get_back_keyboard()
        )
        return ConversationHandler.END
    
    # 创建预订记录
    booking_id = str(uuid.uuidint())[:8].upper()
    user_id = query.from_user.id
    villa = context.user_data.get('villa', {})
    contact = context.user_data.get('contact', {})
    checkin = context.user_data.get('checkin', '')
    checkout = context.user_data.get('checkout', '')
    guests = context.user_data.get('guests', 0)
    
    booking = {
        'id': booking_id,
        'booking_id': booking_id,  # 添加此字段
        'user_id': str(user_id),
        'villa_id': villa.get('id', ''),
        'villa_name': villa.get('name', ''),
        'villa_region': villa.get('region', ''),
        'checkin': checkin,
        'checkout': checkout,
        'guests': guests,
        'contact_name': contact.get('name', ''),
        'contact_phone': contact.get('phone', ''),
        'contact_note': contact.get('note', ''),
        'price_per_night': villa.get('price_per_night', 0),
        'total_price': villa.get('price_per_night', 0) * calculate_nights(checkin, checkout),
        'status': 'confirmed'
    }
    
    if save_booking(booking):
        emoji = REGION_EMOJI.get(villa.get('region', ''), "📍")
        nights = calculate_nights(checkin, checkout)
        
        # ===== 生成并发送 PDF =====
        try:
            # 导入 PDF 生成模块
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from src.services.document import generate_confirmation_pdf_bytes
            
            # 获取别墅完整信息
            villa_full = database.get_villa(villa.get('id', ''))
            
            # 生成 PDF 字节数据
            pdf_bytes = generate_confirmation_pdf_bytes(booking, villa_full or villa)
            
            # 发送 PDF 给用户
            await context.bot.send_document(
                chat_id=user_id,
                document=io.BytesIO(pdf_bytes),
                filename=f"booking_confirmation_{booking_id}.pdf",
                caption=f"📄 预订确认单 | Booking #{booking_id}\n\n"
                        f"请保存此确认单作为入住凭证"
            )
            logger.info(f"PDF 已发送给用户 {user_id}")
        except ImportError as e:
            logger.warning(f"PDF 模块未安装: {e}")
        except Exception as e:
            logger.error(f"PDF 生成失败: {e}")
        
        # 显示成功消息
        success_text = (
            f"✅ *预订提交成功！*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📋 预订编号：*{booking_id}*\n\n"
            f"{emoji} 别墅：{villa.get('name', '')}\n"
            f"📅 {checkin} → {checkout}（{nights}晚）\n"
            f"👤 入住人：{contact.get('name', '')}\n\n"
            f"💰 总价：{format_price(booking['total_price'])}\n\n"
            f"📄 确认单已发送至本对话\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"⏳ 您的预订已提交，客服将在24小时内\n"
            f"与您联系确认订单详情。\n\n"
            f"如有疑问，请联系：@TaimiliSupport"
        )
        
        keyboard = [
            [InlineKeyboardButton("📋 查看我的预订", callback_data="cmd_mybookings")],
            [InlineKeyboardButton("🏠 返回主菜单", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            success_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await query.edit_message_text(
            "❌ 预订保存失败，请联系客服处理",
            reply_markup=get_back_keyboard()
        )
    
    context.user_data.clear()
    return ConversationHandler.END
```

---

## 📄 PDF 内容结构

生成的 PDF 包含以下内容：

| 区块 | 内容 |
|------|------|
| **标题** | 度假别墅预订确认单 |
| **预订编号** | 唯一预订号（带状态） |
| **预订信息** | 日期、入住/退房、人数 |
| **别墅信息** | 名称、编号、地区、设施 |
| **客户信息** | 姓名、电话、备注 |
| **价格明细** | 单价、晚数、总价 |
| **入住须知** | 7条重要注意事项 |
| **联系方式** | 客服热线、微信、邮箱 |
| **页脚** | 生成时间、版权信息 |

---

## 🔍 调试与测试

### 本地测试

```bash
cd villa-booking-bot
python -m src.services.document.pdf_generator
```

### 检查 PDF 输出

```bash
ls -la data/pdfs/
```

---

## ⚙️ 配置选项

### 自定义输出目录

```python
generator = PDFGenerator(output_dir="/custom/path/to/pdfs")
```

### 自定义文件名

```python
pdf_path = generator.generate(
    booking_data,
    villa_data,
    output_filename="my_custom_booking.pdf"
)
```

---

## 🐛 常见问题

### 1. PDF 中文显示为方块

**原因**: 未安装中文字体

**解决**: 安装 Noto Sans SC 或其他中文字体

```bash
# Ubuntu/Debian
sudo apt-get install fonts-noto-cjk

# 或手动下载字体到 fonts/ 目录
```

### 2. ImportError: No module named 'reportlab'

**解决**:

```bash
pip install reportlab
```

### 3. PDF 生成失败

检查日志中的具体错误信息：
- 权限问题：确保输出目录可写
- 字体问题：降级使用 Helvetica

---

## 📁 文件结构

```
villa-booking-bot/
├── bot.py                      # 主程序
├── database.py                 # 数据库模块
├── requirements.txt           # 依赖（需添加 reportlab）
├── data/
│   └── pdfs/                   # PDF 输出目录（自动创建）
├── src/
│   └── services/
│       └── document/
│           ├── __init__.py
│           └── pdf_generator.py  # PDF 生成器
└── templates/                  # HTML 模板（备用）
```
