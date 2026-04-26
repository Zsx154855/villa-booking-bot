# Stripe 支付集成说明

## 功能概述

本系统集成了 Stripe 支付功能，支持用户通过银行卡完成预订支付。

### 主要功能

1. **支付命令** `/pay <booking_id>`
   - 显示支付链接和金额
   - 生成 Stripe Checkout 支付链接
   - 支持检查支付状态

2. **预订后支付按钮**
   - 预订确认后显示「立即支付」按钮
   - 用户可直接点击完成支付

3. **Webhook 回调**
   - 自动接收 Stripe 支付成功回调
   - 自动更新订单状态为已确认
   - 支持退款处理

## 配置步骤

### 1. 获取 Stripe 密钥

1. 访问 [Stripe Dashboard](https://dashboard.stripe.com/)
2. 注册/登录 Stripe 账户
3. 获取 API 密钥：
   - 测试密钥：`sk_test_xxx`（用于开发）
   - 生产密钥：`sk_live_xxx`（用于生产）

### 2. 配置环境变量

```bash
# .env 文件
STRIPE_SECRET_KEY=sk_test_xxx          # Stripe Secret Key
STRIPE_PUBLISHABLE_KEY=pk_test_xxx     # Stripe Publishable Key
STRIPE_WEBHOOK_SECRET=whsec_xxx        # Webhook 签名密钥
```

### 3. 配置 Webhook（重要！）

Webhook 是 Stripe 通知支付结果的方式，必须正确配置：

#### 3.1 在 Stripe Dashboard 创建 Webhook

1. 进入 Stripe Dashboard → Developers → Webhooks
2. 点击 "Add endpoint"
3. 配置端点 URL：
   ```
   https://your-domain.com/webhook/stripe
   ```
4. 选择监听的事件：
   - `payment_intent.succeeded`（支付成功）
   - `payment_intent.payment_failed`（支付失败）
   - `charge.refunded`（退款）
5. 点击 "Add endpoint" 保存

#### 3.2 获取 Webhook 签名密钥

创建 Webhook 后，复制 "Signing secret"（格式：`whsec_xxx`）

### 4. 本地开发测试

使用 Stripe CLI 进行本地测试：

```bash
# 1. 安装 Stripe CLI
brew install stripe/stripe-cli/stripe

# 2. 登录 Stripe
stripe login

# 3. 转发 Webhook 到本地
stripe listen --forward-to localhost:8080/webhook/stripe

# 4. 复制显示的 webhook secret 到 .env
# STRIPE_WEBHOOK_SECRET=whsec_xxx

# 5. 触发测试事件
stripe trigger payment_intent.succeeded
```

## 使用流程

### 用户支付流程

1. **预订确认**
   ```
   用户完成预订 → 收到确认消息 → 点击「立即支付」
   ```

2. **发起支付**
   ```
   /pay ABC12345
   或
   点击支付按钮
   ```

3. **完成支付**
   ```
   跳转到 Stripe Checkout → 选择银行卡 → 完成支付
   ```

4. **支付确认**
   ```
   Stripe 发送 Webhook → 系统更新订单状态 → 用户收到确认
   ```

### 支付状态说明

| 状态 | 说明 |
|------|------|
| `pending` | 待支付（预订已创建） |
| `confirmed` | 已确认（支付成功） |
| `paid` | 已支付（同 confirmed） |
| `cancelled` | 已取消 |
| `completed` | 已完成（退房后） |

## API 端点

### 健康检查
```
GET /
```

返回：
```json
{
  "status": "ok",
  "bot": "Taimili Villa Booking Bot",
  "new_features": ["Stripe支付", ...]
}
```

### Stripe Webhook
```
POST /webhook/stripe
Headers: Stripe-Signature: xxx
Body: (Stripe Event JSON)
```

## 安全说明

1. **密钥保护**
   - 不要将 Secret Key 提交到代码仓库
   - 生产环境使用环境变量或密钥管理服务

2. **Webhook 验证**
   - 所有 Webhook 请求都经过签名验证
   - 使用 `STRIPE_WEBHOOK_SECRET` 验证请求真实性

3. **测试模式**
   - 使用 `sk_test_` 密钥不会产生真实交易
   - 测试卡号：`4242 4242 4242 4242`

## 常见问题

### Q: Webhook 没有收到？
A: 检查：
1. Webhook URL 是否可公网访问
2. 是否选择了正确的事件类型
3. 查看 Stripe Dashboard → Developers → Webhooks → Logs

### Q: 支付成功但订单状态没更新？
A: 检查：
1. Webhook 是否正确配置
2. `STRIPE_WEBHOOK_SECRET` 是否正确
3. 查看日志确认 Webhook 被处理

### Q: 如何测试支付？
A: 使用 Stripe 测试模式：
- 卡号：`4242 4242 4242 4242`
- 有效期：任意未来日期
- CVC：任意3位数字

## 生产部署注意事项

1. **密钥配置**
   ```bash
   # 使用生产密钥
   STRIPE_SECRET_KEY=sk_live_xxx
   STRIPE_PUBLISHABLE_KEY=pk_live_xxx
   STRIPE_WEBHOOK_SECRET=whsec_live_xxx
   ```

2. **Webhook URL**
   - 必须使用 HTTPS
   - 生产环境使用真实域名

3. **监控**
   - 定期检查 Stripe Dashboard 的支付报表
   - 监控 Webhook 失败日志

## 技术架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   User      │────▶│ Telegram Bot │────▶│   Stripe    │
│             │     │             │     │  Checkout   │
└─────────────┘     └─────────────┘     └─────────────┘
                           │                   │
                           │                   │
                           ▼                   │
                    ┌─────────────┐            │
                    │  Database   │◀───────────┘
                    │  (SQLite/   │     (Webhook)
                    │  Postgres)  │
                    └─────────────┘
```

## 相关文件

- `bot.py` - Bot 主程序，支付命令和 Webhook 处理
- `src/services/payment/stripe_payment.py` - Stripe 支付服务
- `src/services/payment/handlers.py` - 支付处理函数
- `database.py` - 数据库操作
- `.env.example` - 环境变量示例
