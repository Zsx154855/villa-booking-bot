# Villa Booking Bot

🏖️ 泰米丽别墅预订 Telegram 机器人

一个基于 Python + Telegram Bot API 的别墅预订服务，支持多地区（芭提雅、曼谷、普吉岛）别墅查询与预订功能。

## 功能列表

### 核心功能
- 🏠 **别墅查询** - 支持按地区浏览可用别墅
- 📅 **在线预订** - 便捷的预订流程（选房型→选日期→填信息→确认）
- 🔍 **预订管理** - 查看和管理自己的预订记录
- 🔄 **状态追踪** - 实时追踪预订状态（待确认/已确认/已完成/已取消）
- 📝 **数据迁移** - 支持从 JSON 格式迁移到 SQLite 数据库

### 支持地区
- 🏖️ 芭提雅
- 🏙️ 曼谷
- 🏝️ 普吉岛

## 技术栈

- **语言**: Python 3.9+
- **框架**: python-telegram-bot v21
- **数据库**: SQLite
- **部署**: Koyeb

## 快速开始

### 前置要求

1. Telegram Bot Token（从 [@BotFather](https://t.me/BotFather) 获取）
2. Koyeb 账号

### 本地运行

```bash
# 1. 克隆项目
git clone https://github.com/Zsx154855/villa-booking-bot.git
cd villa-booking-bot

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 TELEGRAM_BOT_TOKEN

# 5. 初始化数据库
python migrate.py

# 6. 运行机器人
python bot.py
```

### Koyeb 部署

#### 方式一：使用 Koyeb CLI 部署

```bash
# 安装 Koyeb CLI
curl -fsSL https://cli.koyeb.com/install.sh | sh

# 登录
koyeb login

# 部署（自动检测项目配置）
cd villa-booking-bot
koyeb app create villa-booking-bot
koyeb service create --port 8080 -- python bot.py
```

#### 方式二：从 GitHub 部署

1. Fork 本仓库到你的 GitHub
2. 登录 [Koyeb](https://app.koyeb.com)
3. 点击 **Create App** → 选择 **GitHub**
4. 授权 Koyeb 访问你的 GitHub 仓库
5. 选择 `villa-booking-bot` 仓库
6. 配置环境变量：
   - `TELEGRAM_BOT_TOKEN`: 你的 Telegram Bot Token
7. 点击 **Deploy**

#### 方式三：使用 koyeb.yaml 部署

项目已包含 `koyeb.yaml` 配置文件，可直接使用：

```bash
koyeb app create villa-booking-bot --filename koyeb.yaml
```

## 环境变量

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `TELEGRAM_BOT_TOKEN` | ✅ | Telegram Bot Token，从 @BotFather 获取 |
| `PORT` | ❌ | 服务器端口，默认 8080 |

### 获取 Telegram Bot Token

1. 在 Telegram 搜索 [@BotFather](https://t.me/BotFather)
2. 发送 `/newbot`
3. 按提示设置机器人名称和用户名
4. 获取生成的 Token

## 项目结构

```
villa-booking-bot/
├── bot.py              # 主程序入口
├── database.py         # 数据库操作模块
├── migrate.py          # 数据迁移脚本
├── schema.sql          # 数据库表结构
├── requirements.txt    # Python 依赖
├── runtime.txt         # Python 运行时版本
├── Procfile            # 部署启动命令
├── koyeb.yaml          # Koyeb 部署配置
├── .env.example        # 环境变量模板
├── .gitignore          # Git 忽略文件
├── villas.json         # 别墅数据（JSON 备份）
├── bookings.json       # 预订数据（JSON 备份）
└── data/               # SQLite 数据库存储目录
```

## 常用命令

| 命令 | 说明 |
|------|------|
| `/start` | 启动机器人 |
| `/help` | 显示帮助信息 |
| `/info` | 查看别墅信息 |
| `/book` | 开始预订流程 |

## 数据库迁移

如需从 JSON 格式迁移到 SQLite：

```bash
python migrate.py
```

迁移脚本会：
1. 创建 SQLite 数据库
2. 导入别墅数据
3. 导入历史预订记录

## 部署检查清单

在推送 GitHub 和部署到 Koyeb 前，请确认：

- [ ] `.env` 文件已创建并包含有效的 `TELEGRAM_BOT_TOKEN`
- [ ] `.env` 已添加到 `.gitignore`
- [ ] 数据库已初始化（运行过 `python migrate.py`）
- [ ] 本地测试运行正常
- [ ] GitHub 仓库已创建或已 Fork

## 故障排除

### 机器人无响应
- 检查 `TELEGRAM_BOT_TOKEN` 是否正确
- 检查日志输出是否有错误信息

### 数据库错误
- 确保 `data/` 目录存在且有写入权限
- 尝试重新运行 `python migrate.py`

### Koyeb 部署失败
- 检查环境变量是否正确配置
- 查看 Koyeb 日志定位问题

## License

MIT License
