# 日历同步模块使用说明

## 模块结构

```
calendar/
├── __init__.py          # 主模块入口，提供 CalendarSync 类
├── google_calendar.py    # Google Calendar 集成
└── feishu_calendar.py   # 飞书日历集成
```

## 快速开始

### 1. 安装依赖

```bash
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2 requests
```

### 2. 配置环境变量

创建 `.env` 文件或设置环境变量：

```bash
# Google Calendar
GOOGLE_CREDENTIALS_PATH=./credentials/google_credentials.json

# 飞书日历
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. Google Cloud 配置

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建新项目
3. 启用 Google Calendar API
4. 创建 OAuth 2.0 客户端 ID（选择"桌面应用"）
5. 下载 JSON 文件并保存为 `./credentials/google_credentials.json`

### 4. 飞书开放平台配置

1. 前往[飞书开放平台](https://open.feishu.cn/)
2. 创建自建应用
3. 获取 App ID 和 App Secret
4. 在应用权限管理中添加日历相关权限：
   - `calendar:calendar:readonly`
   - `calendar:calendar:write`
   - `calendar:event:readonly`
   - `calendar:event:write`

## 使用示例

### 基本使用

```python
from calendar import get_calendar_sync

# 获取日历同步实例
calendar_sync = get_calendar_sync()

# 创建预订事件
booking_info = {
    'booking_id': 'ABC123',
    'villa_name': 'Cinq Royal 豪华别墅',
    'villa_location': '泰国曼谷',
    'guest_name': '张三',
    'guest_phone': '+66 8X XXX XXXX',
    'check_in_date': '2026-06-15',
    'check_out_date': '2026-06-18',
    'total_price': 15000,
    'status': 'confirmed'
}

result = calendar_sync.create_booking_event(booking_info)
print(result)
```

### 取消预订事件

```python
# 删除日历事件
result = calendar_sync.cancel_booking_event(
    booking_id='ABC123',
    calendar_event_ids={
        'google': 'google_event_id',
        'feishu': 'feishu_event_id'
    }
)
```

## 集成到 Bot

### 修改 bot.py

在 `bot.py` 中添加以下导入：

```python
# 导入日历同步模块
from calendar import get_calendar_sync
```

在预订确认成功后添加日历同步（在 `book_confirm` 函数中）：

```python
# 在预订成功后同步日历
if save_booking(booking):
    # ... 现有代码 ...
    
    # 添加日历同步
    calendar_sync = get_calendar_sync()
    booking_info = {
        'booking_id': booking_id,
        'villa_name': villa.get('name', ''),
        'villa_location': villa.get('region', ''),
        'guest_name': contact.get('name', ''),
        'guest_phone': contact.get('phone', ''),
        'check_in_date': checkin,
        'check_out_date': checkout,
        'total_price': booking['total_price'],
        'status': 'pending'
    }
    
    try:
        sync_result = calendar_sync.create_booking_event(booking_info)
        if sync_result.get('success'):
            logger.info(f"✅ 日历同步成功")
        else:
            logger.warning(f"⚠️ 日历同步失败: {sync_result.get('errors')}")
    except Exception as e:
        logger.error(f"日历同步出错: {e}")
```

## 管理员命令

添加 `/sync` 命令手动同步日历：

```python
async def sync_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """手动同步日历"""
    from calendar import get_calendar_sync
    
    if not is_admin(update.message.from_user.id):
        await update.message.reply_text("❌ 此命令仅管理员可用")
        return
    
    calendar_sync = get_calendar_sync()
    
    await update.message.reply_text("🔄 正在同步日历...")
    
    # 获取最近预订
    recent_bookings = database.get_recent_bookings(limit=10)
    
    synced = 0
    failed = 0
    
    for booking in recent_bookings:
        booking_info = {
            'booking_id': booking.get('id'),
            'villa_name': booking.get('villa_name', ''),
            'guest_name': booking.get('contact_name', ''),
            'check_in_date': booking.get('checkin'),
            'check_out_date': booking.get('checkout'),
            'status': booking.get('status')
        }
        
        try:
            result = calendar_sync.create_booking_event(booking_info)
            if result.get('success'):
                synced += 1
            else:
                failed += 1
        except:
            failed += 1
    
    await update.message.reply_text(
        f"📅 日历同步完成\n\n"
        f"✅ 成功: {synced}\n"
        f"❌ 失败: {failed}"
    )
```

## API 响应格式

### 创建事件响应

```python
{
    'success': True,
    'google': {
        'success': True,
        'event_id': 'abc123',
        'html_link': 'https://calendar.google.com/...'
    },
    'feishu': {
        'success': True,
        'event_id': '1234567890',
        'html_link': 'https://feishu.cn/...'
    },
    'errors': []
}
```

### 错误处理

```python
{
    'success': False,
    'google': None,
    'feishu': {
        'success': False,
        'error': 'Token expired'
    },
    'errors': ['飞书: Token expired']
}
```

## 故障排除

### Google Calendar

1. **Token 过期**：删除 `credentials/google_token.pickle` 重新授权
2. **权限不足**：检查 Google Cloud Console 中的 OAuth 范围
3. **API 未启用**：确保在 Google Cloud Console 中启用了 Calendar API

### 飞书日历

1. **App ID/Secret 错误**：检查环境变量配置
2. **权限不足**：在飞书开放平台添加日历读写权限
3. **Token 过期**：SDK 会自动刷新，无需手动处理

## 安全建议

1. **凭证管理**：不要将 `google_credentials.json` 和飞书密钥提交到 Git
2. **Token 存储**：确保 `google_token.pickle` 权限设置为 600
3. **环境变量**：生产环境使用环境变量而非 `.env` 文件
