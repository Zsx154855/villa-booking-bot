# PDF生成功能集成指南

## 功能概述

已实现预订确认单和支付收据PDF自动生成功能，可为每个预订自动生成专业的PDF文档。

## 文件结构

```
.
├── 别墅运营系统/docs/
│   ├── booking_confirmation.odt    # 预订确认单模板
│   ├── payment_receipt.odt          # 支付收据模板
│   ├── create_booking_template.py   # 模板生成脚本
│   └── create_receipt_template.py   # 收据模板生成脚本
│
└── villa-booking-bot/docs/
    ├── generate_pdf.py               # PDF生成核心模块
    ├── pdf_handler.py                # Bot命令处理器
    └── generated_pdfs/               # 生成的PDF文件目录
```

## 使用方法

### 1. 直接使用Python模块

```python
from generate_pdf import generate_booking_confirmation, generate_payment_receipt

# 生成预订确认单
booking_data = {
    'booking_id': 'BK20260428001',
    'villa_name': 'Cinq Royal Krungthep Kreetha',
    'region': '曼谷 - Klongton区',
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
```

### 2. Bot命令集成

在 `bot.py` 中添加以下代码：

```python
from docs.pdf_handler import receipt_cmd, confirmation_cmd, register_pdf_handlers

# 在应用初始化时注册处理器
def setup_handlers(application):
    # ... 其他处理器 ...
    
    # 注册PDF命令
    application.add_handler(CommandHandler("receipt", receipt_cmd))
    application.add_handler(CommandHandler("confirmation", confirmation_cmd))
    application.add_handler(CommandHandler("booking", confirmation_cmd))
```

### 3. 自动发送

在预订确认后自动生成PDF：

```python
async def confirm_booking_callback(update, context):
    # ... 确认预订逻辑 ...
    
    # 生成确认单
    from docs.generate_pdf import generate_booking_confirmation
    pdf_path = generate_booking_confirmation(booking_data)
    
    if pdf_path:
        # 发送PDF给客户
        with open(pdf_path, 'rb') as pdf:
            await update.callback_query.message.reply_document(
                document=pdf,
                filename=f"booking_confirmation_{booking_id}.pdf",
                caption="✅ 您的预订已确认！这是您的预订确认单"
            )
```

## 模板变量

### 预订确认单模板 (`booking_confirmation.odt`)

| 变量 | 描述 |
|------|------|
| `${booking_id}` | 预订编号 |
| `${created_date}` | 确认日期 |
| `${villa_name}` | 别墅名称 |
| `${region}` | 所在地区 |
| `${bedrooms}` | 卧室数 |
| `${bathrooms}` | 浴室数 |
| `${max_guests}` | 最大入住人数 |
| `${check_in_date}` | 入住日期 |
| `${check_out_date}` | 退房日期 |
| `${nights}` | 入住晚数 |
| `${guests}` | 入住人数 |
| `${contact_name}` | 联系人姓名 |
| `${contact_phone}` | 联系电话 |
| `${contact_note}` | 特殊要求 |
| `${price_per_night}` | 每晚价格 |
| `${total_price}` | 总价 |
| `${status}` | 预订状态 |

### 支付收据模板 (`payment_receipt.odt`)

| 变量 | 描述 |
|------|------|
| `${receipt_id}` | 收据编号 |
| `${booking_id}` | 预订编号 |
| `${payment_date}` | 付款日期 |
| `${villa_name}` | 别墅名称 |
| `${region}` | 所在地区 |
| `${check_in_date}` | 入住日期 |
| `${check_out_date}` | 退房日期 |
| `${nights}` | 入住晚数 |
| `${contact_name}` | 客户姓名 |
| `${contact_phone}` | 联系方式 |
| `${price_per_night}` | 每晚价格 |
| `${total_price}` | 实付金额 |
| `${payment_method}` | 支付方式 |
| `${payment_status}` | 支付状态 |

## CLI测试

```bash
# 测试生成
python3 ./villa-booking-bot/docs/generate_pdf.py
```

## 依赖

- LibreOffice CLI (headless模式)
- Python 3.8+
- zipfile (标准库)

## 扩展功能

1. **自动发送** - 预订确认后自动发送PDF
2. **邮件附件** - 将PDF作为邮件附件发送给客户
3. **多语言** - 为不同语言创建对应模板
4. **Logo** - 在模板中添加公司Logo

## 注意事项

1. PDF生成使用临时文件，请确保有足够磁盘空间
2. LibreOffice转换约需3-5秒，请设置适当超时
3. 生成的PDF文件会自动清理，也可手动保存
