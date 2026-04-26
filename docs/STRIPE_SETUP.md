# Stripe 配置完整指南

本文档详细说明如何配置 Stripe 支付功能，包括账号设置、环境变量配置、测试验证和生产部署。

---

## 目录

1. [Stripe 账号设置](#1-stripe-账号设置)
2. [Render 环境变量配置](#2-render-环境变量配置)
3. [测试流程](#3-测试流程)
4. [生产部署](#4-生产部署)

---

## 1. Stripe 账号设置

### 1.1 注册 Stripe 账号

1. 访问 [Stripe 官网](https://stripe.com)
2. 点击 "Sign up" 注册账号
3. 使用邮箱进行注册验证
4. 完成基础信息填写

> **注意**：Stripe 目前支持 40+ 个国家/地区，中国大陆用户可能需要使用海外公司主体或第三方服务注册。

### 1.2 获取 API 密钥

#### 测试密钥（用于开发）

1. 登录 [Stripe Dashboard](https://dashboard.stripe.com)
2. 进入 **Developers** → **API keys**
3. 复制 **Publishable key**（以 `pk_test_` 开头）
4. 复制 **Secret key**（以 `sk_test_` 开头）

#### 生产密钥（用于正式环境）

1. 在 API keys 页面，将 **Test mode** 切换为 **Live mode**
2. 复制 **Publishable key**（以 `pk_live_` 开头）
3. 复制 **Secret key**（以 `sk_live_` 开头）

> ⚠️ **安全警告**：Secret Key 如同密码，切勿暴露在客户端代码、Git 仓库或公开场合。

### 1.3 配置 Webhook

Webhook 用于接收 Stripe 的支付事件通知（如支付成功、退款等）。

#### 步骤 1：获取 Webhook 签名密钥

1. 进入 **Developers** → **Webhooks**
2. 点击 **Add endpoint**
3. 填写 Endpoint URL：`https://your-domain.com/api/stripe/webhook`
4. 选择监听事件：
   - `checkout.session.completed`
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
   - `charge.refunded`
5. 点击 **Add endpoint**
6. 复制生成的 **Webhook Secret**（以 `whsec_` 开头）

#### 步骤 2：本地 Webhook 测试（可选）

使用 Stripe CLI 进行本地测试：

```bash
# 登录 Stripe CLI
stripe login

# 监听本地端口（适用于 ngrok 或 Render 的本地预览）
stripe listen --forward-to localhost:3000/api/stripe/webhook

# 复制返回的 Webhook signing secret
```

---

## 2. Render 环境变量配置

在 Render Dashboard 中配置以下环境变量：

### 2.1 必需的环境变量

| 变量名 | 描述 | 示例值 |
|--------|------|--------|
| `STRIPE_SECRET_KEY` | Stripe Secret Key | `sk_test_51...` |
| `STRIPE_PUBLISHABLE_KEY` | Stripe Publishable Key | `pk_test_51...` |
| `STRIPE_WEBHOOK_SECRET` | Webhook 签名密钥 | `whsec_...` |

### 2.2 配置步骤

1. 登录 [Render Dashboard](https://dashboard.render.com)
2. 选择你的 **Service**
3. 进入 **Environment** 标签页
4. 添加上述环境变量
5. 点击 **Save Changes**

> 💡 **提示**：在本地开发时，可在 `.env` 文件中配置对应变量，但确保该文件被 `.gitignore` 忽略。

### 2.3 环境变量示例

```bash
# .env 示例（本地开发）
STRIPE_SECRET_KEY=sk_test_YOUR_TEST_KEY_HERE
STRIPE_PUBLISHABLE_KEY=pk_test_YOUR_PUBLISHABLE_KEY_HERE
STRIPE_WEBHOOK_SECRET=whsec_YOUR_WEBHOOK_SECRET_HERE
```

```bash
# Render 生产环境
STRIPE_SECRET_KEY=sk_live_YOUR_LIVE_KEY_HERE
STRIPE_PUBLISHABLE_KEY=pk_live_YOUR_PUBLISHABLE_KEY_HERE
STRIPE_WEBHOOK_SECRET=whsec_YOUR_WEBHOOK_SECRET_HERE
```

---

## 3. 测试流程

### 3.1 测试卡号

Stripe 提供官方测试卡号，**不会产生真实扣款**：

| 卡号 | 用途 |
|------|------|
| `4242 4242 4242 4242` | 成功支付 |
| `4000 0000 0000 0002` | 支付被拒绝 |
| `4000 0025 0000 3155` | 需要 3D Secure 验证 |
| `4000 0000 0000 9995` | 余额不足 |

**通用测试信息**：
- **有效期**：任意未来日期（如 `12/28`）
- **CVC**：任意 3 位数字（如 `123`）
- **邮编**：任意 5 位数字（如 `12345`）

### 3.2 验证支付流程

#### 前端测试检查清单

- [ ] Stripe Elements 正确加载
- [ ] 卡号验证正常工作
- [ ] 表单提交触发支付
- [ ] 支付成功/失败提示正确显示

#### 后端 Webhook 测试

1. 在 Stripe Dashboard 进入 **Developers** → **Webhooks**
2. 选择你的 endpoint
3. 点击 **Send test event**
4. 选择事件类型（如 `checkout.session.completed`）
5. 点击 **Send test event**
6. 确认收到事件并正确处理

#### 使用 Stripe CLI 测试

```bash
# 触发测试支付事件
stripe trigger checkout.session.completed

# 查看 Webhook 转发日志
stripe logs tail
```

### 3.3 测试场景覆盖

| 场景 | 测试方法 | 预期结果 |
|------|----------|----------|
| 正常支付 | 使用 `4242 4242 4242 4242` | 支付成功 |
| 卡片拒付 | 使用 `4000 0000 0000 0002` | 显示拒绝原因 |
| 3D Secure | 使用 `4000 0025 0000 3155` | 弹出认证框 |
| Webhook | 发送测试事件 | 订单状态更新 |

---

## 4. 生产部署

### 4.1 切换到生产密钥

1. **确认测试完成**
   - 所有测试场景已通过
   - Webhook 事件处理正确
   - 错误处理逻辑完善

2. **更新环境变量**
   ```
   # Render Dashboard → Environment
   STRIPE_SECRET_KEY = sk_live_51...
   STRIPE_PUBLISHABLE_KEY = pk_live_51...
   ```

3. **更新 Webhook URL**
   - 确认生产环境的 Webhook endpoint 已配置
   - 更新为正式域名

### 4.2 安全注意事项

#### 🔒 必须做到

- [ ] Secret Key 仅存储在服务端环境变量
- [ ] Publishable Key 可暴露在客户端
- [ ] Webhook 签名验证必须启用
- [ ] 使用 HTTPS 加密传输
- [ ] 定期轮换 API 密钥

#### 🚫 禁止事项

- ❌ 将 Secret Key 提交到 Git 仓库
- ❌ 在前端代码中暴露 Secret Key
- ❌ 在日志中打印敏感信息
- ❌ 使用测试密钥处理真实交易

### 4.3 支付安全最佳实践

1. **启用 Stripe Radar**（可选）
   - 机器学习风控检测
   - 自定义规则配置

2. **PCI 合规**
   - 使用 Stripe Elements 收集卡号（无需接触原始数据）
   - 确保服务器符合 PCI DSS 要求

3. **监控与告警**
   - 设置 Stripe Dashboard 告警
   - 监控异常支付模式
   - 定期审查交易日志

### 4.4 生产检查清单

- [ ] 使用生产密钥（`sk_live_` / `pk_live_`）
- [ ] Webhook 指向正式域名
- [ ] 启用 HTTPS
- [ ] 启用 Webhook 签名验证
- [ ] 配置支付失败处理逻辑
- [ ] 设置退款流程
- [ ] 测试一笔真实小额支付

---

## 常见问题

### Q1: Webhook 未触发？

**检查项**：
1. Webhook URL 是否可公网访问
2. 是否正确返回 200 状态码
3. Webhook Secret 是否正确配置
4. 查看 Stripe Dashboard → Developers → Webhooks → Logs

### Q2: 支付成功但订单未更新？

**排查步骤**：
1. 检查 Webhook 是否收到事件
2. 检查事件处理逻辑是否有异常
3. 确认数据库更新代码正确
4. 查看服务端日志

### Q3: 如何查看 API 请求日志？

在 Stripe Dashboard → Developers → Logs 中查看所有 API 请求记录。

---

## 参考链接

- [Stripe 官方文档](https://stripe.com/docs)
- [Stripe API 参考](https://stripe.com/docs/api)
- [Webhook 最佳实践](https://stripe.com/docs/webhooks/best-practices)
- [测试卡号文档](https://stripe.com/docs/testing)
- [Render 部署指南](https://render.com/docs/deploys)

---

*文档版本：1.0.0*  
*最后更新：2024年*
