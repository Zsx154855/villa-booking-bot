# Google Calendar 配置指南

本文档详细介绍如何配置 Google 服务账号以实现日历同步功能。

---

## 1. Google Cloud 设置

### 1.1 创建项目

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 点击顶部导航栏的 **项目选择器**
3. 点击 **新建项目**
4. 填写项目信息：
   - 项目名称：`calendar-sync-app`
   - 项目ID（自动生成，可自定义）
5. 点击 **创建**

### 1.2 启用 Calendar API

1. 在 Google Cloud Console 中，进入 **API 和服务** > **库**
2. 在搜索框中输入 `Google Calendar API`
3. 点击 **Google Calendar API** 卡片
4. 点击 **启用**

### 1.3 创建服务账号

1. 进入 **API 和服务** > **凭据**
2. 点击 **创建凭据** > **服务账号**
3. 填写服务账号信息：
   - 服务账号名称：`calendar-sync-service`
   - 服务账号ID（自动生成）
4. 点击 **创建并继续**
5. （可选）添加角色：选择 **项目** > **编辑者**
6. 点击 **完成**

---

## 2. 凭据配置

### 2.1 下载 JSON 凭据文件

1. 在 **凭据** 页面，找到刚创建的服务账号
2. 点击服务账号名称进入详情页
3. 切换到 **密钥** 标签页
4. 点击 **添加密钥** > **创建新密钥**
5. 选择密钥类型：**JSON**
6. 点击 **创建**，文件将自动下载

> ⚠️ **重要**：妥善保管此文件，不要将其提交到版本控制系统

### 2.2 配置环境变量

将下载的 JSON 文件重命名为 `google-calendar-credentials.json`，并配置环境变量：

```bash
# Linux / macOS
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/google-calendar-credentials.json"

# Windows (PowerShell)
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\google-calendar-credentials.json"

# Windows (CMD)
set GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\google-calendar-credentials.json
```

### 2.3 共享日历给服务账号

1. 打开 [Google Calendar](https://calendar.google.com/)
2. 进入要共享的日历设置：
   - 左侧点击日历名称旁的 **⋮** 菜单
   - 选择 **设置和共享**
3. 在 **与特定人员共享** 部分，点击 **添加人员**
4. 输入服务账号的电子邮件地址（格式：`服务账号名称@项目ID.iam.gserviceaccount.com`）
5. 权限选择：**查看所有活动详情**
6. 点击 **发送**

---

## 3. 功能测试

### 3.1 Python 示例代码

```python
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# 凭据文件路径
CREDENTIALS_PATH = "google-calendar-credentials.json"
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service():
    """初始化日历服务"""
    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIALS_PATH,
        scopes=SCOPES
    )
    return build("calendar", "v3", credentials=credentials)

def create_test_event():
    """创建测试事件"""
    service = get_calendar_service()
    
    # 获取主日历ID（使用 "primary" 或具体日历ID）
    calendar_id = "primary"
    
    # 定义事件
    now = datetime.utcnow()
    event = {
        "summary": "测试事件 - Calendar Sync",
        "description": "这是由日历同步功能创建的测试事件",
        "start": {
            "dateTime": (now + timedelta(hours=1)).isoformat(),
            "timeZone": "Asia/Shanghai",
        },
        "end": {
            "dateTime": (now + timedelta(hours=2)).isoformat(),
            "timeZone": "Asia/Shanghai",
        },
    }
    
    try:
        # 创建事件
        event = service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()
        print(f"✅ 事件创建成功！")
        print(f"   事件ID: {event['id']}")
        print(f"   事件链接: {event.get('htmlLink', 'N/A')}")
        return event
    except Exception as e:
        print(f"❌ 创建事件失败: {e}")
        return None

def list_upcoming_events(max_results=10):
    """列出即将到来的事件"""
    service = get_calendar_service()
    
    now = datetime.utcnow().isoformat() + "Z"
    
    try:
        events_result = service.events().list(
            calendarId="primary",
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        
        events = events_result.get("items", [])
        
        if not events:
            print("📅 没有即将到来的事件")
            return []
        
        print(f"📅 即将到来的事件 (共 {len(events)} 个):")
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            print(f"   - {start}: {event['summary']}")
        
        return events
    except Exception as e:
        print(f"❌ 获取事件失败: {e}")
        return []

if __name__ == "__main__":
    print("=" * 50)
    print("Google Calendar API 功能测试")
    print("=" * 50)
    
    # 测试1: 创建测试事件
    print("\n[测试1] 创建测试事件...")
    create_test_event()
    
    # 测试2: 列出即将到来的事件
    print("\n[测试2] 列出即将到来的事件...")
    list_upcoming_events()
```

### 3.2 Node.js 示例代码

```javascript
const { google } = require("googleapis");

// 凭据文件路径
const CREDENTIALS_PATH = "./google-calendar-credentials.json";

// 初始化日历服务
async function getCalendarService() {
  const credentials = require(CREDENTIALS_PATH);
  
  const auth = new google.auth.GoogleAuth({
    credentials,
    scopes: ["https://www.googleapis.com/auth/calendar"],
  });
  
  return google.calendar({ version: "v3", auth });
}

// 创建测试事件
async function createTestEvent() {
  const calendar = await getCalendarService();
  const now = new Date();
  const startTime = new Date(now.getTime() + 60 * 60 * 1000);
  const endTime = new Date(now.getTime() + 2 * 60 * 60 * 1000);
  
  const event = {
    summary: "测试事件 - Calendar Sync",
    description: "这是由日历同步功能创建的测试事件",
    start: {
      dateTime: startTime.toISOString(),
      timeZone: "Asia/Shanghai",
    },
    end: {
      dateTime: endTime.toISOString(),
      timeZone: "Asia/Shanghai",
    },
  };
  
  try {
    const response = await calendar.events.insert({
      calendarId: "primary",
      resource: event,
    });
    console.log("✅ 事件创建成功！");
    console.log(`   事件ID: ${response.data.id}`);
    return response.data;
  } catch (error) {
    console.error("❌ 创建事件失败:", error.message);
    return null;
  }
}

// 列出即将到来的事件
async function listUpcomingEvents(maxResults = 10) {
  const calendar = await getCalendarService();
  const now = new Date().toISOString();
  
  try {
    const response = await calendar.events.list({
      calendarId: "primary",
      timeMin: now,
      maxResults,
      singleEvents: true,
      orderBy: "startTime",
    });
    
    const events = response.data.items;
    
    if (!events || events.length === 0) {
      console.log("📅 没有即将到来的事件");
      return [];
    }
    
    console.log(`📅 即将到来的事件 (共 ${events.length} 个):`);
    events.forEach((event) => {
      const start = event.start.dateTime || event.start.date;
      console.log(`   - ${start}: ${event.summary}`);
    });
    
    return events;
  } catch (error) {
    console.error("❌ 获取事件失败:", error.message);
    return [];
  }
}

// 运行测试
(async () => {
  console.log("=".repeat(50));
  console.log("Google Calendar API 功能测试");
  console.log("=".repeat(50));
  
  console.log("\n[测试1] 创建测试事件...");
  await createTestEvent();
  
  console.log("\n[测试2] 列出即将到来的事件...");
  await listUpcomingEvents();
})();
```

### 3.3 运行测试

```bash
# Python 环境
pip install google-api-python-client google-auth

# Node.js 环境
npm install googleapis

# 运行测试脚本
python test_calendar.py
# 或
node test_calendar.js
```

---

## 4. 错误处理

### 常见错误及解决方案

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `PERMISSION_DENIED` | 服务账号未被授予日历访问权限 | 确保已按 2.3 节完成日历共享 |
| `NOT_FOUND` | 日历ID不正确 | 确认使用正确的日历ID |
| `INVALID_CREDENTIALS` | 凭据文件路径错误或文件损坏 | 检查 `GOOGLE_APPLICATION_CREDENTIALS` 环境变量 |
| `The caller does not have permission` | 服务账号权限不足 | 在日历共享设置中添加服务账号邮箱 |

### 日志记录建议

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    event = service.events().insert(calendarId=calendar_id, body=event).execute()
    logger.info(f"事件创建成功: {event['id']}")
except googleapiclient.errors.HttpError as e:
    logger.error(f"API错误: {e.error_details}")
except Exception as e:
    logger.exception(f"未知错误: {e}")
```

---

## 5. 安全建议

1. **保护凭据文件**：不要将 JSON 凭据文件提交到 Git
   ```gitignore
   # .gitignore
   *.json
   !example-credentials.json
   ```

2. **使用环境变量**：在生产环境中使用密钥管理服务（如 AWS Secrets Manager）

3. **最小权限原则**：只为服务账号分配必要的 Calendar API 权限

4. **定期轮换密钥**：定期创建新的服务账号密钥并更新配置

---

## 6. 参考链接

- [Google Calendar API 文档](https://developers.google.com/calendar/api/guides/overview)
- [Google Cloud Console](https://console.cloud.google.com/)
- [服务账号文档](https://cloud.google.com/iam/docs/service-accounts)
