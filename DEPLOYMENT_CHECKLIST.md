# 别墅预订机器人 - GitHub 推送与 Koyeb 部署检查清单

## 📋 推送前检查

### 1. 环境配置
- [ ] `.env` 文件已创建
- [ ] `TELEGRAM_BOT_TOKEN` 已填入有效值
- [ ] `.env` 已在 `.gitignore` 中排除

### 2. 敏感信息检查
- [ ] 没有任何硬编码的 Token 或密钥
- [ ] `requirements.txt` 不包含敏感依赖
- [ ] 代码中没有调试输出包含敏感信息

### 3. 数据库状态
- [ ] `data/` 目录已创建
- [ ] 数据库可正常初始化
- [ ] `villas.json` 数据文件存在

### 4. 本地测试
- [ ] `python migrate.py` 运行成功
- [ ] `python bot.py` 可以正常启动
- [ ] Telegram Bot 可以响应 `/start` 命令

### 5. Git 配置
- [ ] 已添加远程仓库: `git remote add origin https://github.com/Zsx154855/villa-booking-bot.git`
- [ ] 所有更改已提交: `git add . && git commit -m "部署准备完成"`
- [ ] 提交不包含 `.env` 文件

## 🚀 Koyeb 部署步骤

### 方式一：从 GitHub 部署（推荐）

1. **推送代码到 GitHub**
   ```bash
   git push -u origin main
   ```

2. **登录 Koyeb**
   - 访问 https://app.koyeb.com
   - 使用 GitHub 登录

3. **创建应用**
   - 点击 **Create App**
   - 选择 **GitHub** 作为部署源
   - 选择 `villa-booking-bot` 仓库
   - 选择 `main` 分支

4. **配置环境变量**
   - 点击 **Environment Variables**
   - 添加 `TELEGRAM_BOT_TOKEN`，填入你的 Bot Token
   - 可选：添加 `PORT=8080`

5. **部署**
   - 点击 **Deploy**
   - 等待构建和部署完成

6. **验证部署**
   - 查看 **Logs** 确认机器人已启动
   - 在 Telegram 中向 Bot 发送 `/start` 测试

### 方式二：使用 Koyeb CLI

```bash
# 安装 CLI
curl -fsSL https://cli.koyeb.com/install.sh | sh

# 登录
koyeb login

# 创建应用（会自动使用 koyeb.yaml 配置）
koyeb app create villa-booking-bot

# 设置环境变量
koyeb secret create telegram-bot-token --value "你的TOKEN"

# 部署
git push origin main
```

## ✅ 部署后验证清单

- [ ] Koyeb 状态显示 **Running**
- [ ] 日志中显示 "Bot is ready to receive requests"
- [ ] Telegram Bot 响应 `/start` 命令
- [ ] 可以正常浏览别墅列表
- [ ] 预订流程可以正常完成

## 🔧 常见问题排查

### 问题：机器人无响应
**检查项：**
- [ ] Koyeb 日志是否有错误
- [ ] `TELEGRAM_BOT_TOKEN` 是否正确
- [ ] Bot 是否已被删除或 Token 已失效

### 问题：部署失败
**检查项：**
- [ ] GitHub 仓库是否可访问
- [ ] `koyeb.yaml` 格式是否正确
- [ ] 环境变量是否已设置

### 问题：数据库错误
**检查项：**
- [ ] `data/` 目录是否存在
- [ ] 是否有足够的磁盘空间
- [ ] 权限是否正确

## 📊 监控信息

### Koyeb 日志命令
```bash
koyeb logs villa-booking-bot
```

### 查看应用状态
```bash
koyeb app get villa-booking-bot
```

## 🔄 更新部署

代码更新后：
```bash
git add .
git commit -m "更新描述"
git push origin main
# Koyeb 会自动重新部署
```

## 📞 支持资源

- [Koyeb 文档](https://koyeb.com/docs)
- [Telegram BotFather](https://t.me/BotFather)
- [python-telegram-bot 文档](https://docs.python-telegram-bot.org/)
