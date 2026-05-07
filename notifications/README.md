# 通知系统使用指南

## 📋 概述

Taimili Villa Booking Bot 的通知系统提供自动化客户通知功能，包括：
- ✅ 预订确认通知
- ✅ 支付成功通知
- ✅ 入住前1天提醒
- ✅ 入住当天提醒
- ✅ 退房前1天提醒

## 🗂️ 文件结构

```
villa-booking-bot/
└── notifications/
    ├── __init__.py                 # 模块入口
    ├── notifier.py                 # 核心通知逻辑
    ├── notification_queue.py      # 通知队列（HTTP上下文用）
    └── templates/                  # 通知模板
        ├── booking_confirmation_zh.txt  # 预订确认（中文）
        ├── booking_confirmation_en.txt  # 预订确认（英文）
        ├── booking_confirmation_th.txt  # 预订确认（泰文）
        ├── checkin_reminder_zh.txt      # 入住提醒（中文）
        ├── checkin_reminder_en.txt      # 入住提醒（英文）
        ├── checkin_reminder_th.txt      # 入住提醒（泰文）
        ├── checkout_reminder_zh.txt     # 退房提醒（中文）
        ├── checkout_reminder_en.txt     # 退房提醒（英文）
        └── checkout_reminder_th.txt     # 退房提醒（泰文）
```

## ⚙️ 定时任务配置

Bot启动时自动配置以下定时任务：

| 任务 | 执行时间 | 说明 |
|------|----------|------|
| 入住前1天提醒 | 每天09:00 | 提醒明天入住的客户 |
| 入住当天提醒 | 每天09:00 | 提醒今天入住的客户 |
| 退房前1天提醒 | 每天09:00 | 提醒明天退房的客户 |
| 待处理通知处理 | 每15分钟 | 处理支付成功等队列通知 |

## 📝 集成方式

### 预订确认通知

预订成功后自动发送（在 `book_confirm` 函数中调用）：

```python
from notifications import send_booking_confirmation

await send_booking_confirmation(context.bot, str(user_id), booking)
```

### 支付成功通知

支付成功后通过队列机制发送（HTTP上下文无法直接发送TG消息）：

```python
# 在 payment/handlers.py 的 _handle_payment_success 中
# 自动将通知加入队列

# 由 job_process_pending_notifications 定时任务处理
```

## 🎨 自定义通知模板

模板使用 Python 格式化语法，支持以下变量：

### 预订确认模板变量
- `{booking_id}` - 预订编号
- `{villa_name}` - 别墅名称
- `{villa_region}` - 别墅地区
- `{checkin}` - 入住日期
- `{checkout}` - 退房日期
- `{nights}` - 住宿晚数
- `{contact_name}` - 联系人姓名
- `{total_price}` - 总价
- `{emoji}` - 地区emoji

### 入住提醒模板变量
- `{booking_id}` - 预订编号
- `{villa_name}` - 别墅名称
- `{checkin}` - 入住日期
- `{checkout}` - 退房日期
- `{emoji}` - 地区emoji

### 退房提醒模板变量
- `{booking_id}` - 预订编号
- `{villa_name}` - 别墅名称
- `{checkout}` - 退房日期
- `{emoji}` - 地区emoji

## 🔧 扩展指南

### 添加新语言

1. 在 `templates/` 目录创建新语言模板，命名规则：`{type}_{lang}.txt`
2. 在 `notifier.py` 的 `load_template` 函数中处理新语言

### 添加新通知类型

1. 在 `notifier.py` 中添加新的 NotificationType 枚举值
2. 创建对应的通知函数
3. 在 `setup_notification_jobs` 中添加定时任务
4. 创建对应模板文件

## 📊 数据库字段

通知系统使用以下预订字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| pending_notifications | TEXT | JSON数组，存储待处理通知类型 |

## ⚠️ 注意事项

1. **Koyeb部署**：确保Bot进程持续运行，JobQueue才能正常工作
2. **模板编码**：所有模板文件必须使用 UTF-8 编码
3. **通知频率**：避免过度通知，建议同一预订同一类型通知只发送一次
