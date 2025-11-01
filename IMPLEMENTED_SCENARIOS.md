# 已实现场景说明 (Implemented Scenarios)

## 概述 (Overview)

本项目目前已完整实现 **Quotation（报价）** 和 **Purchase（购买）** 两大核心功能流程，可以支持完整的旅游保险购买体验。

**实施状态：** ✅ 可在生产环境运行

---

## 🎯 完整实现的场景

### 场景 1: 端到端购买流程 (End-to-End Purchase Flow)

**用户旅程:**
```
用户咨询 → 生成报价 → 选择产品 → 发起支付 → 完成支付 → 生成保单
    ↓          ↓          ↓          ↓          ↓          ↓
  Claude    Ancileo    Supabase   Stripe    Webhook   Ancileo
           Quotation   Selection  Checkout  Handler   Purchase
            API                   Session
```

**详细步骤:**

#### 步骤 1: 用户咨询旅游保险
```
用户: "我需要去日本旅游的保险，3月15日出发，3月22日回来，2个成人"
Claude: "好的，让我为您生成报价..."
```

#### 步骤 2: 生成报价 (通过 MCP Tool)
```python
# Claude 调用 MCP Tool: generate_quotation
result = await generate_quotation(
    customer_id="user_leo_123",
    trip_type="RT",  # Round Trip
    departure_date="2025-03-15",
    return_date="2025-03-22",
    departure_country="SG",
    arrival_country="JP",
    adults_count=2,
    children_count=0,
    market="SG",
    language_code="en"
)

# 返回结果包含:
{
    "quotation_id": "QT-ancileo-xyz789",  # Ancileo Quote ID
    "offers": [
        {
            "id": "offer_premium_001",
            "product_code": "TRVL-PREMIUM-JP",
            "unit_price": 75.00,
            "currency": "SGD",
            "product_information": {
                "name": "Premium Travel Insurance - Japan 7 Days",
                "coverage_details": {...}
            }
        },
        {
            "id": "offer_basic_002",
            "product_code": "TRVL-BASIC-JP",
            "unit_price": 45.00,
            "currency": "SGD",
            "product_information": {
                "name": "Basic Travel Insurance - Japan 7 Days"
            }
        }
    ],
    "trip_summary": {
        "trip_type": "RT",
        "departure_date": "2025-03-15",
        "return_date": "2025-03-22",
        "adults_count": 2
    },
    "created_at": "2025-01-02T10:30:00Z"
}
```

**后端处理:**
- ✅ 调用 Ancileo Quotation API 获取实时报价
- ✅ 保存报价到 Supabase `quotes` 表
- ✅ 使用 Ancileo Quote ID 作为主键（无需内部ID映射）

#### 步骤 3: 用户选择产品
```
用户: "我想要 Premium 保险"
Claude: "好的，Premium Travel Insurance 总价 SGD 150.00 (2人 × SGD 75.00)。
       请提供投保人信息以便继续..."
```

#### 步骤 4: 发起支付 (通过 MCP Tool)
```python
# Claude 调用 MCP Tool: initiate_purchase
result = await initiate_purchase(
    user_id="user_leo_123",
    quote_id="QT-ancileo-xyz789",  # Ancileo Quote ID
    selected_offer_id="offer_premium_001",  # Ancileo Offer ID
    amount=15000,  # 150.00 SGD in cents
    currency="SGD",
    product_name="Premium Travel Insurance - Japan 7 Days",
    customer_email="leo@example.com",
    insureds=[
        {
            "firstName": "Leo",
            "lastName": "Wang",
            "dateOfBirth": "1990-05-15",
            "passportNumber": "E1234567",
            "relationship": "self"
        },
        {
            "firstName": "Mary",
            "lastName": "Wang",
            "dateOfBirth": "1992-08-20",
            "passportNumber": "E7654321",
            "relationship": "spouse"
        }
    ],
    main_contact={
        "firstName": "Leo",
        "lastName": "Wang",
        "email": "leo@example.com",
        "phone": "+6591234567"
    }
)

# 返回结果 (OpenAI Apps SDK Widget 格式):
{
    "content": [
        {
            "type": "text",
            "text": "✅ Payment initiated! Total: SGD 150.00\n\nClick 'Pay via Stripe' below to complete."
        }
    ],
    "_meta": {
        "openai/outputTemplate": "http://localhost:8085/widgets/payment-widget.html"
    },
    "widgetState": {
        "payment_intent_id": "pi_abc123def456",
        "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_...",
        "product_name": "Premium Travel Insurance - Japan 7 Days",
        "amount": "150.00",
        "currency": "SGD",
        "status": "pending"
    }
}
```

**后端处理:**
1. ✅ 检查重复支付（同一 quote_id 只能有一个 pending/completed 支付）
2. ✅ 创建 DynamoDB 支付记录 (status: `pending`)
3. ✅ 创建 Stripe Checkout Session (24小时有效期)
4. ✅ 创建 Supabase `selections` 记录（关联 quote、offer、payment）
5. ✅ 返回带 Widget 的响应（适配 ChatGPT/Claude）

#### 步骤 5: 用户完成支付
```
1. 用户点击 Claude 消息中的 "Pay via Stripe" 按钮
2. 跳转到 Stripe Checkout 页面
3. 输入信用卡信息并完成支付
4. Stripe 触发 webhook 事件: checkout.session.completed
```

**Webhook 自动处理:**
```python
# backend/services/payment/stripe_webhook.py

# 接收 Stripe Event: checkout.session.completed
{
    "type": "checkout.session.completed",
    "data": {
        "object": {
            "id": "cs_test_...",
            "payment_intent": "pi_stripe_789xyz",
            "payment_status": "paid",
            "metadata": {
                "payment_intent_id": "pi_abc123def456"
            }
        }
    }
}

# 自动更新 DynamoDB 支付状态
await dynamodb.update_payment_status(
    payment_intent_id="pi_abc123def456",
    status="completed",
    stripe_payment_intent="pi_stripe_789xyz"
)
```

✅ **Webhook 处理完整实现:**
- `checkout.session.completed` → 更新为 `completed`
- `checkout.session.expired` → 更新为 `expired`
- `payment_intent.payment_failed` → 更新为 `failed`

#### 步骤 6: 完成购买并生成保单
```python
# 方式 1: 用户主动查询
user: "支付完成了吗？"
result = await check_payment_status(payment_intent_id="pi_abc123def456")
# 返回: {"payment_status": "completed"}

# 方式 2: Claude 自动调用
result = await complete_purchase(payment_intent_id="pi_abc123def456")
```

**后端处理:**
1. ✅ 验证支付状态为 `completed`
2. ✅ 从 Supabase 获取 selection 记录（包含 Ancileo mapping）
3. ✅ **调用 Ancileo Purchase API** 完成真实保单购买
4. ✅ 生成内部 Policy ID 和 Policy Number
5. ✅ 保存保单记录到 Supabase `policies` 表（预留，待实现）
6. ✅ 返回完整的保单信息

```python
# 返回结果:
{
    "policy_id": "pol_x8y9z0a1b2c3",
    "policy_number": "POL-2025-A7B8C9D0",
    "status": "completed",
    "payment_intent_id": "pi_abc123def456",
    "quote_id": "QT-ancileo-xyz789",
    "user_id": "user_leo_123",
    "amount": 15000,
    "currency": "SGD",
    "product_name": "Premium Travel Insurance - Japan 7 Days",
    "ancileo_purchase_id": "PUR-ancileo-abc123",  # 实际保单ID
    "purchased_offers": [
        {
            "offerId": "offer_premium_001",
            "productCode": "TRVL-PREMIUM-JP",
            "policyNumber": "MSIG-JP-2025-001234",
            "coverStartDate": "2025-03-15",
            "coverEndDate": "2025-03-22",
            "documents": [
                {
                    "type": "policy",
                    "url": "https://ancileo.com/policies/..."
                }
            ]
        }
    ],
    "policy_document_url": null,  # TODO: 生成 PDF
    "created_at": "2025-01-02T11:15:00Z"
}
```

---

## 🎨 支持的对话场景

### 场景 A: 快速购买（Happy Path）
```
用户: "我要去日本旅游保险"
AI: 生成报价 → 展示选项
用户: "选 Premium"
AI: 发起支付 → 显示支付按钮
用户: [完成支付]
AI: 检查状态 → 生成保单 → "您的保单号是 POL-2025-..."
```
**所需时间:** 2-3 分钟

### 场景 B: 分步式购买（允许中断）
```
Day 1:
用户: "我要去日本旅游保险"
AI: 生成报价 → 保存到 Supabase

Day 2:
用户: "我昨天询问的日本保险呢？"
AI: 从 Supabase 检索报价 → "您的报价还在，选择..."
用户: "选 Premium"
AI: 发起支付...
```

### 场景 C: 支付失败处理
```
用户: [支付失败/超时]
Webhook: 更新状态为 failed/expired
用户: "我的支付怎么样了？"
AI: 检查状态 → "支付失败，需要重新支付吗？"
```

### 场景 D: 重复支付检测
```
用户: "我要购买这个报价"
AI: 发起支付 → "已为您创建支付链接"
用户: "再帮我购买一次"
AI: 检测到重复 → "您已经有一个待支付的订单，请先完成..."
```

---

## 🔧 技术实现细节

### 1. Quotation（报价）模块

**入口:** MCP Tool `generate_quotation`
**后端:**
- Router: `backend/routers/quotation.py`
- API: `POST /api/quotation/generate`
- Client: `backend/services/ancileo_client.py`

**数据流:**
```
MCP Tool → Backend API → Ancileo Quotation API → Supabase quotes
                                                        ↓
                                              quote_id = Ancileo Quote ID
                                              (无需额外映射)
```

**Supabase Schema: `quotes`**
```sql
CREATE TABLE quotes (
    quote_id TEXT PRIMARY KEY,  -- Ancileo Quote ID directly
    user_id TEXT NOT NULL,
    trip_type TEXT NOT NULL,  -- RT or ST
    departure_date DATE NOT NULL,
    return_date DATE,
    departure_country TEXT,
    arrival_country TEXT,
    adults_count INTEGER,
    children_count INTEGER,
    offer_id TEXT,  -- Selected offer (after user chooses)
    product_code TEXT,
    unit_price NUMERIC,
    currency TEXT,
    quotation_response JSONB,  -- Full Ancileo response
    market TEXT,
    language_code TEXT,
    channel TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2. Selection（选择）模块

**入口:** Backend API `POST /api/quotation/selection/create`
**用途:** 链接 Quote、Selected Offer、Payment

**数据流:**
```
User selects offer → Create selection record
                           ↓
                    Link quote_id + offer_id + payment_id
```

**Supabase Schema: `selections`**
```sql
CREATE TABLE selections (
    selection_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    quote_id TEXT NOT NULL,  -- Ancileo Quote ID (FK to quotes)
    payment_id TEXT,  -- Payment Intent ID (FK to DynamoDB)
    selected_offer_id TEXT NOT NULL,  -- Ancileo Offer ID
    selected_product_code TEXT,
    product_type TEXT DEFAULT 'travel-insurance',
    quantity INTEGER DEFAULT 1,
    total_price NUMERIC,
    insureds JSONB,  -- Insured persons array
    main_contact JSONB,  -- Main contact info
    is_send_email BOOLEAN DEFAULT true,
    status TEXT DEFAULT 'draft',  -- draft | pending_payment | completed
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3. Purchase（购买）模块

**入口:** MCP Tool `initiate_purchase`
**后端:**
- Service: `backend/services/purchase_service.py`
- Router: `backend/routers/block_4_purchase.py`
- Stripe: `backend/services/stripe_integration.py`
- DynamoDB: `backend/database/dynamodb_client.py`

**完整数据流:**
```
MCP Tool (initiate_purchase)
    ↓
PurchaseService.initiate_payment()
    ↓
1. Check duplicate payment (DynamoDB query by quote_id)
2. Create DynamoDB payment record (status: pending)
3. Create Stripe Checkout Session
4. Update payment with stripe_session_id
5. Create Supabase selection record
    ↓
Return checkout_url to user
    ↓
User completes payment on Stripe
    ↓
Stripe Webhook (checkout.session.completed)
    ↓
Update DynamoDB (status: completed)
    ↓
MCP Tool (complete_purchase)
    ↓
PurchaseService.complete_purchase_after_payment()
    ↓
1. Verify payment status = completed
2. Get selection from Supabase
3. Call Ancileo Purchase API
4. Generate policy_id and policy_number
5. Save to Supabase policies table
    ↓
Return policy info to user
```

**DynamoDB Schema: `lea-payments-local`**
```python
{
    "payment_intent_id": "pi_abc123",  # Primary Key
    "user_id": "user_leo_123",
    "quote_id": "QT-ancileo-xyz789",
    "amount": 15000,  # cents
    "currency": "SGD",
    "product_name": "Premium Travel Insurance",
    "payment_status": "completed",  # pending | completed | failed | expired | cancelled
    "stripe_session_id": "cs_test_...",
    "stripe_payment_intent": "pi_stripe_...",
    "created_at": "2025-01-02T10:30:00Z",
    "updated_at": "2025-01-02T11:00:00Z",
    "metadata": {...}
}

# GSIs (Global Secondary Indexes):
# - user_id-index: Query all payments by user
# - quote_id-index: Query payment by quote (for duplicate detection)
# - stripe_session_id-index: Query by Stripe session
```

---

## 🧪 测试场景

### 本地测试环境

```bash
# 1. 启动后端
uvicorn backend.main:app --reload

# 2. 启动 DynamoDB Local + Admin UI
docker-compose up -d dynamodb dynamodb-admin

# 3. 初始化 DynamoDB
python -m database.dynamodb.init_payments_table

# 4. 启动 MCP Server
python -m mcp_server.server

# 5. 配置 Stripe Webhook (本地测试)
stripe listen --forward-to localhost:8000/webhook/stripe
```

### 测试用例

#### Test 1: 完整购买流程
```python
# Step 1: Generate quotation
POST /api/quotation/generate
{
    "customer_id": "test_user_001",
    "trip_type": "RT",
    "departure_date": "2025-03-15",
    "return_date": "2025-03-22",
    "departure_country": "SG",
    "arrival_country": "JP",
    "adults_count": 1
}

# Step 2: Create selection
POST /api/quotation/selection/create
{
    "user_id": "test_user_001",
    "quote_id": "<quotation_id from step 1>",
    "selected_offer_id": "<offer_id from step 1>",
    "insureds": [...],
    "main_contact": {...},
    "total_price": 75.00
}

# Step 3: Initiate payment
POST /api/purchase/initiate
{
    "user_id": "test_user_001",
    "quote_id": "<quotation_id>",
    "amount": 7500,
    "currency": "SGD",
    "product_name": "Premium Travel Insurance"
}

# Step 4: Complete payment (use Stripe test card)
# Navigate to checkout_url
# Card: 4242 4242 4242 4242, Exp: 12/34, CVV: 123

# Step 5: Check status
GET /api/purchase/payment/{payment_intent_id}

# Step 6: Complete purchase
POST /api/purchase/complete/{payment_intent_id}
```

#### Test 2: 重复支付检测
```python
# 同一 quote_id 发起第二次支付
POST /api/purchase/initiate
{
    "quote_id": "<same_quote_id>",
    ...
}

# 预期返回错误:
{
    "detail": "This quote already has a pending payment. Payment ID: pi_..."
}
```

#### Test 3: 支付超时
```bash
# 不完成支付，等待 24 小时
# Stripe 自动触发: checkout.session.expired

# Webhook 自动更新状态为 expired
```

---

## 📊 当前支持的 API 端点

### Quotation APIs
- ✅ `POST /api/quotation/generate` - 生成报价
- ✅ `POST /api/quotation/selection/create` - 创建选择记录
- ✅ `GET /api/quotation/selection/payment/{payment_id}` - 根据 payment_id 获取选择

### Purchase APIs
- ✅ `POST /api/purchase/initiate` - 发起支付
- ✅ `GET /api/purchase/payment/{payment_intent_id}` - 查询支付状态
- ✅ `POST /api/purchase/complete/{payment_intent_id}` - 完成购买
- ✅ `POST /api/purchase/cancel/{payment_intent_id}` - 取消支付
- ✅ `GET /api/purchase/user/{user_id}/payments` - 获取用户支付历史
- ✅ `GET /api/purchase/quote/{quote_id}/payment` - 获取报价的支付记录

### Webhook APIs
- ✅ `POST /webhook/stripe` - Stripe webhook 处理
- ✅ `GET /success` - 支付成功页面
- ✅ `GET /cancel` - 支付取消页面

### MCP Tools
- ✅ `generate_quotation` - 生成报价
- ✅ `initiate_purchase` - 发起购买
- ✅ `check_payment_status` - 检查支付状态
- ✅ `complete_purchase` - 完成购买
- ✅ `cancel_payment` - 取消支付

---

## 🚀 生产环境配置

### 必需的环境变量

```bash
# Ancileo API
ANCILEO_API_BASE_URL=https://api.ancileo.com
ANCILEO_API_KEY=your_ancileo_api_key
ANCILEO_USERNAME=your_username
ANCILEO_PASSWORD=your_password

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key

# Stripe
STRIPE_SECRET_KEY=sk_live_...  # 生产环境使用 live key
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...  # 从 Stripe Dashboard 获取

# DynamoDB (使用 AWS DynamoDB)
AWS_REGION=ap-southeast-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
DYNAMODB_TABLE_NAME=lea-payments-production

# Backend
BACKEND_URL=https://api.your-domain.com
WIDGET_BASE_URL=https://widgets.your-domain.com
```

### 部署检查清单

- [ ] Ancileo API credentials 已配置
- [ ] Supabase tables 已创建 (quotes, selections, policies)
- [ ] DynamoDB table 已创建 (with GSIs)
- [ ] Stripe webhook endpoint 已配置
- [ ] Stripe webhook secret 已设置
- [ ] SSL 证书已配置 (HTTPS required for Stripe)
- [ ] CORS 已正确配置
- [ ] 日志监控已启用
- [ ] 错误追踪已配置 (Sentry/CloudWatch)

---

## 🎯 下一步计划

### 待实现功能

1. **Block 1: Policy Intelligence**
   - [ ] `compare_policies` - 多产品对比
   - [ ] `explain_coverage` - 保障详解
   - [ ] `search_policies` - 语义搜索

2. **Block 2: FAQ**
   - [ ] `answer_question` - 智能问答
   - [ ] Mem0 集成 - 对话记忆

3. **Block 3: Document Intelligence**
   - [ ] `upload_document` - 文档上传
   - [ ] `extract_travel_data` - OCR 提取
   - [ ] 自动表单填充

4. **Block 5: Analytics**
   - [ ] `get_recommendations` - 数据驱动推荐
   - [ ] `analyze_destination_risk` - 目的地风险分析

5. **Policy Generation**
   - [ ] PDF 保单生成
   - [ ] Email 发送
   - [ ] 保单下载

---

## 💡 使用建议

1. **测试时使用 Stripe 测试卡:**
   - 成功: 4242 4242 4242 4242
   - 拒绝: 4000 0000 0000 0002
   - 需要 3DS: 4000 0027 6000 3184

2. **重复支付检测:**
   - 同一 quote_id 只能有一个 pending/completed 支付
   - 如需重新支付，先取消旧支付或创建新报价

3. **Webhook 测试:**
   - 使用 `stripe listen` 进行本地测试
   - 生产环境需配置公网可访问的 webhook URL

4. **Selection 记录:**
   - 包含 insureds 和 main_contact 才能调用 Ancileo Purchase API
   - 如果缺失，complete_purchase 会优雅降级（只生成内部保单）

---

## 📞 支持

如有问题，请联系:
- **技术负责人:** Leo Wang
- **项目仓库:** https://github.com/williamhutech/conversational-finance
- **文档:** 参见 CLAUDE.md, README.md, API_Documentation.md
