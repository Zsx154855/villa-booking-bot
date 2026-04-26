# Google Calendar 配置状态报告

## 1. 配置状态概览

| 项目 | 状态 | 说明 |
|------|------|------|
| 代码实现 | ✅ 已完成 | `src/services/calendar/google_calendar.py` |
| 依赖项 | ⚠️ 需补充 | `requirements.txt` 缺少 Google API 依赖 |
| 环境变量 | ⚠️ 需配置 | 需添加凭据文件路径 |
| 服务账号 | ❌ 待创建 | 用户需在 Google Cloud 创建 |

---

## 2. 需要的环境变量

### 2.1 必须配置

| 环境变量 | 说明 | 示例值 |
|----------|------|--------|
| `GOOGLE_APPLICATION_CREDENTIALS` | 服务账号 JSON 凭据文件路径 | `/app/credentials/google-calendar-credentials.json` |

### 2.2 可选配置

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `GOOGLE_CALENDAR_ID` | 日历 ID | `primary` (主日历) |

---

## 3. 服务账号凭据 JSON 格式

下载的服务账号 JSON 文件结构如下：

```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "xxxxx",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "calendar-sync@your-project.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/xxx.iam.gserviceaccount.com"
}
```

### 关键字段说明

| 字段 | 用途 |
|------|------|
| `client_email` | 用于共享日历给服务账号（格式：`xxx@project.iam.gserviceaccount.com`） |
| `private_key` | 用于 API 认证 |

---

## 4. 缺失的依赖项

### 问题

`requirements.txt` 缺少 Google Calendar API 依赖包。

### 解决方案

需要在 `requirements.txt` 中添加：

```
google-api-python-client>=2.100.0
google-auth>=2.23.0
```

---

## 5. 配置步骤清单（供用户操作）

### Step 1: 创建 Google Cloud 项目

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 点击 **项目选择器** > **新建项目**
3. 填写项目信息：
   - 项目名称：`taimili-calendar`
   - 项目ID：`taimili-calendar`（自定义）

### Step 2: 启用 Calendar API

1. 进入 **API 和服务** > **库**
2. 搜索 `Google Calendar API`
3. 点击启用

### Step 3: 创建服务账号

1. 进入 **API 和服务** > **凭据**
2. 点击 **创建凭据** > **服务账号**
3. 服务账号名称：`calendar-sync-service`
4. 点击 **创建并继续**
5. （可选）添加角色：**项目** > **编辑者**
6. 点击 **完成**

### Step 4: 下载 JSON 凭据

1. 在凭据页面，点击刚创建的服务账号
2. 切换到 **密钥** 标签
3. 点击 **添加密钥** > **创建新密钥**
4. 选择 **JSON** 类型
5. 下载文件并重命名为 `google-calendar-credentials.json`

### Step 5: 上传凭据到 Render

1. 进入 Render Dashboard
2. 选择你的 Bot 服务
3. 进入 **Environment** 标签
4. 添加环境变量：
   - `GOOGLE_APPLICATION_CREDENTIALS` = `/etc/secrets/google-calendar-credentials.json`
5. 在 **Secrets Files** 部分：
   - File Name: `/etc/secrets/google-calendar-credentials.json`
   - 上传下载的 JSON 文件

### Step 6: 共享日历给服务账号

1. 打开 [Google Calendar](https://calendar.google.com/)
2. 点击要共享的日历旁的 **⋮** 菜单
3. 选择 **设置和共享**
4. 在 **与特定人员共享** 部分，点击 **添加人员**
5. 输入服务账号邮箱：`calendar-sync-service@taimili-calendar.iam.gserviceaccount.com`
6. 权限选择：**查看所有活动详情**
7. 点击 **发送**

### Step 7: 更新 requirements.txt

添加 Google Calendar 依赖：

```
google-api-python-client>=2.100.0
google-auth>=2.23.0
```

### Step 8: 验证配置

部署后可通过日志验证连接是否正常。

---

## 6. 代码使用示例

```python
from src.services.calendar import GoogleCalendarService

# 初始化服务
calendar_service = GoogleCalendarService(
    credentials_path=os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '/app/credentials/google-calendar-credentials.json'),
    calendar_id=os.environ.get('GOOGLE_CALENDAR_ID', 'primary')
)

# 创建事件
event = CalendarEvent(...)
event_id = await calendar_service.create_event(event)
```

---

## 7. 时区说明

代码中时区硬编码为 `Asia/Bangkok`（泰国清迈时区），与 Taimili 别墅所在地一致，无需修改。

---

*报告生成时间：2026-04-27*
