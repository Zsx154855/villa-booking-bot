# Render 部署检查清单

## 📋 部署前检查

### 1. 代码检查 ✅
- [x] 所有 .py 文件语法正确 (Python 3.9 兼容)
- [x] 所有模块导入成功
- [x] 数据库路径正确 (`data/villas.db`)
- [x] handlers 所有函数正确导出

### 2. 配置文件 ✅
- [x] `requirements.txt` - 包含所有依赖
- [x] `runtime.txt` - Python 3.9.16
- [x] `render.yaml` - Render 部署配置
- [x] `koyeb.yaml` - 备用部署配置

### 3. 本地测试 ✅
- [x] 数据库初始化成功
- [x] Bot Application 构建成功
- [x] 所有 Handler 注册成功
- [x] 健康检查端点正常

---

## 🚀 Render 控制台设置

### 必填项
- [ ] **连接 GitHub 仓库**: `Zsx154855/villa-booking-bot`
- [ ] **设置环境变量**:
  - [ ] `TELEGRAM_BOT_TOKEN` = 你的 Bot Token

### 可选项 (已有默认值)
- [ ] `PYTHON_VERSION` = 3.9.16
- [ ] `PORT` = 8080

---

## 📝 部署后验证

### 健康检查
```bash
curl https://taimili-villa-bot.onrender.com/health
```

### 预期响应
```json
{
  "status": "ok",
  "bot": "Taimili Villa Booking Bot v4.0 (SQLite)",
  "database": "ok",
  "villas_count": 14,
  "bookings_count": 1,
  "new_features": ["用户画像", "优惠券", "积分系统", "促销码兑换", "评价系统"]
}
```

### Telegram Bot 测试
发送 `/start` 命令，确认 Bot 响应欢迎消息

---

## ⚠️ 常见问题

### 1. Bot 无响应
- 检查 `TELEGRAM_BOT_TOKEN` 是否正确设置
- 查看 Render 日志确认 Bot 启动成功

### 2. 数据库错误
- 确认 `data/` 目录存在
- 检查数据库文件权限

### 3. 部署失败
- 检查 `requirements.txt` 是否有不兼容的依赖
- 确认 GitHub 仓库代码已更新

---

## 📞 支持

如有问题，请检查:
1. Render 部署日志
2. Telegram Bot @BotFather 设置
3. 数据库连接状态
