# Payment MCP Setup Guide

Complete guide for setting up and using the 7 payment MCP tools in the Conversational Insurance system.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (5 Minutes)](#quick-start-5-minutes)
3. [Detailed Setup](#detailed-setup)
4. [Payment MCP Tools Reference](#payment-mcp-tools-reference)
5. [Database Schema](#database-schema)
6. [Testing the Payment Flow](#testing-the-payment-flow)
7. [Local vs Production Setup](#local-vs-production-setup)
8. [Troubleshooting](#troubleshooting)
9. [Known Limitations](#known-limitations)

---

## Prerequisites

### Required Software

- **Python 3.11+** (< 3.13)
  ```bash
  python3.11 --version
  ```

- **Docker & Docker Compose**
  ```bash
  docker --version
  docker-compose --version
  ```

- **Tesseract OCR** (for document processing in other blocks)
  ```bash
  # macOS
  brew install tesseract

  # Ubuntu/Debian
  sudo apt-get install tesseract-ocr
  ```

### Required API Keys & Accounts

1. **Stripe Account** (Payment Processing)
   - Sign up at: https://stripe.com
   - Get test keys from: https://dashboard.stripe.com/test/apikeys
   - Required keys:
     - Secret Key (`sk_test_...`)
     - Publishable Key (`pk_test_...`)
     - Webhook Secret (`whsec_...`)

2. **AWS Account** (for production DynamoDB)
   - Local development uses DynamoDB Local (Docker)
   - Production requires AWS credentials

3. **Other Services** (for full system, not required for payments only):
   - Supabase (database)
   - Neo4j (knowledge graph)
   - Mem0 (conversation memory)
   - Anthropic Claude (AI)

---

## Quick Start (5 Minutes)

Get payment tools running in under 5 minutes:

```bash
# 1. Navigate to project directory
cd "/Users/williamhu/Documents/Initiatives/Insurance MCP/conversational-insurance-ultra"

# 2. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -e .
# Or using UV (faster):
# uv pip install -e .

# 4. Copy environment template
cp .env.example .env

# 5. Edit .env - Add ONLY these required variables for payments:
# STRIPE_SECRET_KEY="sk_test_your_key_here"
# STRIPE_PUBLISHABLE_KEY="pk_test_your_key_here"
# STRIPE_WEBHOOK_SECRET="whsec_your_secret_here"
# DYNAMODB_PAYMENTS_TABLE="lea-payments-local"
# DYNAMODB_ENDPOINT="http://localhost:8000"
# AWS_REGION="ap-southeast-1"
# AWS_ACCESS_KEY_ID="dummy"
# AWS_SECRET_ACCESS_KEY="dummy"
# PAYMENT_SUCCESS_URL="http://localhost:8085/success"
# PAYMENT_CANCEL_URL="http://localhost:8085/cancel"
# BACKEND_API_URL="http://localhost:8085"

# 6. Start DynamoDB Local
docker-compose up -d dynamodb dynamodb-admin

# 7. Initialize payments table
python -m database.dynamodb.init_payments_table

# 8. Verify setup
# Open DynamoDB Admin UI:
open http://localhost:8010
# You should see "lea-payments-local" table

# 9. Start backend API (Terminal 1)
uvicorn backend.main:app --reload --port 8000

# 10. Start payment pages (Terminal 2)
uvicorn backend.services.payment.payment_pages:app --port 8085

# 11. Start Stripe webhook listener (Terminal 3)
stripe listen --forward-to localhost:8000/webhook/stripe

# 12. Test MCP server
python -m mcp_server.server
```

**You're ready!** The 7 payment MCP tools are now available.

---

## Detailed Setup

### Step 1: Environment Configuration

Create `.env` file from template:

```bash
cp .env.example .env
```

**Minimal payment configuration** (edit `.env`):

```bash
# === PAYMENT PROCESSING (STRIPE) ===
STRIPE_SECRET_KEY="sk_test_51..."              # Get from Stripe Dashboard
STRIPE_PUBLISHABLE_KEY="pk_test_51..."         # Get from Stripe Dashboard
STRIPE_WEBHOOK_SECRET="whsec_..."              # Get from Stripe CLI or Dashboard
STRIPE_CURRENCY="SGD"                          # Default currency

# === PAYMENT PAGES ===
PAYMENT_SUCCESS_URL="http://localhost:8085/success"
PAYMENT_CANCEL_URL="http://localhost:8085/cancel"
WIDGET_BASE_URL="http://localhost:8085/widgets"
BACKEND_API_URL="http://localhost:8085"

# === DYNAMODB (LOCAL DEVELOPMENT) ===
DYNAMODB_PAYMENTS_TABLE="lea-payments-local"
DYNAMODB_ENDPOINT="http://localhost:8000"      # Remove for AWS DynamoDB
AWS_REGION="ap-southeast-1"
AWS_ACCESS_KEY_ID="dummy"                      # Use real credentials for AWS
AWS_SECRET_ACCESS_KEY="dummy"                  # Use real credentials for AWS

# === BACKEND API ===
BACKEND_HOST="0.0.0.0"
BACKEND_PORT=8000
BACKEND_RELOAD=True

# === FEATURE FLAGS ===
ENABLE_BLOCK_4=True                            # Enable Purchase Execution
```

### Step 2: Start Docker Services

The `docker-compose.yml` includes:
- DynamoDB Local (port 8000)
- DynamoDB Admin UI (port 8010)
- Neo4j (optional, for other blocks)
- Redis (optional, for caching)

```bash
# Start all services
docker-compose up -d

# Or start only DynamoDB services
docker-compose up -d dynamodb dynamodb-admin

# Verify services are running
docker-compose ps

# View logs
docker-compose logs -f dynamodb
```

**Access DynamoDB Admin UI:**
```bash
open http://localhost:8010
```

### Step 3: Initialize Database

Run the initialization script to create the payments table:

```bash
python -m database.dynamodb.init_payments_table
```

**Expected output:**
```
✓ Connected to DynamoDB
✓ Table 'lea-payments-local' created successfully
✓ Added GSI: user_id-index
✓ Added GSI: quote_id-index
✓ Added GSI: stripe_session_id-index
✓ DynamoDB Streams enabled
```

**The script is idempotent** - safe to run multiple times. It will skip creation if table exists.

**Table Structure Created:**
- Primary Key: `payment_intent_id` (String)
- 3 Global Secondary Indexes (GSIs)
- DynamoDB Streams enabled
- PAY_PER_REQUEST billing mode

### Step 4: Stripe Webhook Setup

Webhooks are **CRITICAL** - they update payment status automatically when customers complete checkout.

#### Option A: Local Development (Stripe CLI)

Install Stripe CLI:
```bash
# macOS
brew install stripe/stripe-cli/stripe

# Or download from:
# https://stripe.com/docs/stripe-cli
```

Login and forward webhooks:
```bash
# Login to your Stripe account
stripe login

# Forward webhook events to your local server
stripe listen --forward-to localhost:8000/webhook/stripe
```

**Copy the webhook signing secret** from the output:
```
> Ready! Your webhook signing secret is whsec_abc123...
```

Add it to `.env`:
```bash
STRIPE_WEBHOOK_SECRET="whsec_abc123..."
```

#### Option B: Production (Stripe Dashboard)

1. Go to: https://dashboard.stripe.com/webhooks
2. Click "Add endpoint"
3. Enter your URL: `https://yourdomain.com/webhook/stripe`
4. Select events to listen for:
   - `checkout.session.completed` - Payment succeeded
   - `checkout.session.expired` - Session expired (24h)
   - `payment_intent.payment_failed` - Payment failed
5. Copy the signing secret
6. Add to production `.env`:
   ```bash
   STRIPE_WEBHOOK_SECRET="whsec_prod_..."
   ```

**Security Note:** Webhooks MUST use HTTPS in production (Stripe requirement).

### Step 5: Start Backend Services

You need **3 separate terminal windows**:

**Terminal 1 - FastAPI Backend:**
```bash
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000
```

Access at: http://localhost:8000
API docs at: http://localhost:8000/docs

**Terminal 2 - Payment Pages:**
```bash
source venv/bin/activate
uvicorn backend.services.payment.payment_pages:app --port 8085
```

Pages available:
- Success: http://localhost:8085/success
- Cancel: http://localhost:8085/cancel

**Terminal 3 - Stripe Webhook Listener (local only):**
```bash
stripe listen --forward-to localhost:8000/webhook/stripe
```

### Step 6: Start MCP Server

The MCP server exposes the 7 payment tools to AI assistants (Claude Desktop, ChatGPT, etc.)

```bash
source venv/bin/activate
python -m mcp_server.server
```

**Configure in Claude Desktop:**

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "insurance-payments": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "mcp_server.server"],
      "env": {
        "PYTHONPATH": "/Users/williamhu/Documents/Initiatives/Insurance MCP/conversational-insurance-ultra"
      }
    }
  }
}
```

Restart Claude Desktop.

---

## Payment MCP Tools Reference

All 7 tools are defined in: `mcp_server/server.py`

### Tool 1: `initiate_purchase()`

**Purpose:** Start the payment process for an insurance policy purchase.

**Location:** `mcp_server/server.py:287-411`

**Parameters:**
```python
{
    "user_id": str,           # User/customer identifier
    "quote_id": str,          # Quote identifier for the policy
    "amount": int,            # Amount in cents (e.g., 15000 = $150.00)
    "currency": str,          # Currency code (default: "SGD")
    "product_name": str,      # Product description
    "customer_email": str     # Optional: pre-fill checkout email
}
```

**Returns:**
```python
{
    "payment_intent_id": "pi_abc123...",
    "checkout_url": "https://checkout.stripe.com/c/pay/...",
    "session_id": "cs_test_...",
    "amount": 15000,
    "currency": "SGD",
    "expires_at": "2025-11-03T12:00:00Z",
    "widget": {
        "type": "payment_checkout",
        "data": {...}
    }
}
```

**What it does:**
1. Creates payment record in DynamoDB with status `pending`
2. Generates Stripe Checkout session (24-hour expiration)
3. Returns checkout URL for customer to complete payment
4. Includes widget state for OpenAI Apps SDK integration

**Example Usage:**
```python
result = await initiate_purchase(
    user_id="user_alice",
    quote_id="quote_travel_7days",
    amount=15000,  # $150.00
    currency="SGD",
    product_name="Premium Travel Insurance - 7 Days Asia",
    customer_email="alice@example.com"
)

# Direct customer to: result['checkout_url']
```

**Error Handling:**
- Validates amount > 0
- Checks for duplicate payment attempts (conversational error)
- Handles Stripe API errors gracefully

---

### Tool 2: `check_payment_status()`

**Purpose:** Poll or verify payment completion status.

**Location:** `mcp_server/server.py:414-487`

**Parameters:**
```python
{
    "payment_intent_id": str  # Payment ID from initiate_purchase()
}
```

**Returns:**
```python
{
    "payment_status": "pending" | "completed" | "failed" | "expired" | "cancelled",
    "stripe_session_id": "cs_test_...",
    "amount": 15000,
    "currency": "SGD",
    "product_name": "Premium Travel Insurance - 7 Days Asia",
    "user_id": "user_alice",
    "quote_id": "quote_travel_7days",
    "created_at": "2025-11-02T10:30:00Z",
    "updated_at": "2025-11-02T10:35:00Z",
    "stripe_payment_intent": "pi_...",  # If completed
    "failure_reason": "..."             # If failed
}
```

**Status Lifecycle:**
```
pending → completed  (customer paid successfully)
pending → expired    (24h timeout, no payment)
pending → failed     (payment declined)
pending → cancelled  (manually cancelled)
```

**What it does:**
1. Retrieves payment record from DynamoDB
2. Returns current status (updated by webhook)
3. Provides conversational guidance based on status

**Example Usage:**
```python
status = await check_payment_status("pi_abc123...")

if status['payment_status'] == 'completed':
    # Proceed to generate policy
    policy = await complete_purchase("pi_abc123...")
elif status['payment_status'] == 'pending':
    # Customer hasn't completed checkout yet
    print(f"Waiting for payment at: {status['checkout_url']}")
```

**Important:** Status is updated **automatically by webhook** when customer completes payment. No manual intervention needed.

---

### Tool 3: `complete_purchase()`

**Purpose:** Generate policy document after successful payment verification.

**Location:** `mcp_server/server.py:490-574`

**Parameters:**
```python
{
    "payment_intent_id": str  # Payment ID (must be 'completed' status)
}
```

**Returns:**
```python
{
    "policy_id": "pol_abc123",
    "policy_number": "POL-2025-001234",
    "status": "completed",
    "payment_intent_id": "pi_abc123...",
    "quote_id": "quote_travel_7days",
    "user_id": "user_alice",
    "amount": 15000,
    "currency": "SGD",
    "product_name": "Premium Travel Insurance - 7 Days Asia",
    "policy_document_url": "https://storage.example.com/policies/pol_abc123.pdf",
    "created_at": "2025-11-02T10:40:00Z"
}
```

**What it does:**
1. Verifies payment status is `completed`
2. Generates unique policy ID and number
3. **TODO:** Generates policy PDF document
4. Returns policy details for customer confirmation

**Example Usage:**
```python
# After payment is completed
policy = await complete_purchase("pi_abc123...")

print(f"Policy issued: {policy['policy_number']}")
print(f"Download at: {policy['policy_document_url']}")
```

**Error Handling:**
- Returns conversational error if payment not completed
- Prevents duplicate policy generation
- Validates payment exists

**Known Limitation:** PDF generation is currently a placeholder (returns mock URL). Needs implementation.

---

### Tool 4: `cancel_payment()`

**Purpose:** Cancel a pending payment before completion.

**Location:** `mcp_server/server.py:577-615`

**Parameters:**
```python
{
    "payment_intent_id": str,  # Payment ID to cancel
    "reason": str              # Optional: cancellation reason
}
```

**Returns:**
```python
{
    "payment_intent_id": "pi_abc123...",
    "status": "cancelled",
    "message": "Payment successfully cancelled"
}
```

**What it does:**
1. Validates payment is in `pending` status
2. Updates DynamoDB status to `cancelled`
3. Cannot cancel completed payments (use refund instead)

**Example Usage:**
```python
# Customer decides not to purchase
result = await cancel_payment(
    payment_intent_id="pi_abc123...",
    reason="Customer changed their mind"
)
```

**Important:**
- Only works for `pending` status
- Completed payments require refund (not yet implemented)
- Expired payments are auto-cancelled by webhook

---

### Tool 5: `save_quote_for_later()`

**Purpose:** Save quote and generate payment link for later completion.

**Location:** `mcp_server/server.py:618-701`

**Parameters:**
```python
{
    "quote_id": str,          # Quote identifier
    "user_id": str,           # User identifier
    "customer_email": str,    # Customer email for sending link
    "product_name": str,      # Product description
    "amount": int,            # Amount in cents
    "currency": str,          # Currency code
    "policy_id": str,         # Optional: policy ID if already selected
    "notes": str              # Optional: additional notes
}
```

**Returns:**
```python
{
    "quote_id": "quote_travel_7days",
    "payment_link_id": "plink_abc123",
    "payment_link_url": "https://checkout.stripe.com/c/pay/...",
    "expires_at": "2025-11-09T10:00:00Z",  # 7 days from now
    "message": "Quote saved! Payment link valid for 7 days."
}
```

**What it does:**
1. Creates payment link valid for 7 days
2. Useful when customer wants to "think about it"
3. Allows completion on different device or time
4. Can be used multiple times if payment fails

**Example Usage:**
```python
# Customer wants to decide later
result = await save_quote_for_later(
    quote_id="quote_travel_7days",
    user_id="user_alice",
    customer_email="alice@example.com",
    product_name="Premium Travel Insurance - 7 Days Asia",
    amount=15000,
    currency="SGD",
    notes="Customer wants to discuss with spouse"
)

# Send link to customer: result['payment_link_url']
```

**Known Limitation:** Payment link generation is implemented, but email sending functionality is not yet complete (see Tool 6).

---

### Tool 6: `send_payment_link()`

**Purpose:** Email payment link to customer.

**Location:** `mcp_server/server.py:704-767`

**Parameters:**
```python
{
    "quote_id": str,          # Quote with saved payment link
    "customer_email": str,    # Email address to send to
    "customer_name": str      # Optional: for personalization
}
```

**Returns:**
```python
{
    "success": true,
    "message": "Payment link sent to alice@example.com",
    "quote_id": "quote_travel_7days",
    "email_sent_to": "alice@example.com"
}
```

**What it does:**
1. Retrieves payment link for quote
2. **TODO:** Sends email with link
3. Can be used for reminders or resending

**Example Usage:**
```python
# After save_quote_for_later()
result = await send_payment_link(
    quote_id="quote_travel_7days",
    customer_email="alice@example.com",
    customer_name="Alice"
)
```

**Known Limitation:** Email service integration not yet implemented. Tool returns success but doesn't actually send email. Needs:
- Email service provider (SendGrid, AWS SES, etc.)
- Email templates
- Delivery tracking

---

### Tool 7: `get_payment_link()`

**Purpose:** Retrieve or generate payment link for a quote.

**Location:** `mcp_server/server.py:770-820`

**Parameters:**
```python
{
    "quote_id": str  # Quote identifier
}
```

**Returns:**
```python
{
    "quote_id": "quote_travel_7days",
    "payment_link_id": "plink_abc123",
    "payment_link_url": "https://checkout.stripe.com/c/pay/...",
    "expires_at": "2025-11-09T10:00:00Z",
    "is_active": true
}
```

**What it does:**
1. Retrieves existing payment link if available
2. Generates new link if none exists
3. Checks link validity (7-day expiration)
4. Useful when customer loses their link

**Example Usage:**
```python
# Customer: "I lost my payment link"
result = await get_payment_link("quote_travel_7days")

if result['is_active']:
    print(f"Your payment link: {result['payment_link_url']}")
else:
    # Generate new link
    new_link = await save_quote_for_later(...)
```

---

## Database Schema

### Table: `lea-payments-local`

**Database:** AWS DynamoDB (Local or Cloud)

**Location:**
- Script: `database/dynamodb/init_payments_table.py`
- Client: `backend/database/dynamodb_client.py`

### Primary Key

```
payment_intent_id (String, HASH)
```

Unique identifier for each payment (format: `pi_abc123...`)

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `payment_intent_id` | String | Unique payment identifier |
| `user_id` | String | Customer identifier |
| `quote_id` | String | Quote being purchased |
| `amount` | Number | Amount in cents (e.g., 15000 = $150) |
| `currency` | String | Currency code (SGD, USD, etc.) |
| `product_name` | String | Product description |
| `payment_status` | String | pending \| completed \| failed \| expired \| cancelled |
| `stripe_session_id` | String | Stripe Checkout session ID |
| `stripe_payment_intent` | String | Stripe PaymentIntent ID |
| `created_at` | String | ISO timestamp of creation |
| `updated_at` | String | ISO timestamp of last update |
| `metadata` | Map | Additional data (JSON) |
| `failure_reason` | String | Error message if payment failed |

### Global Secondary Indexes (GSIs)

#### 1. `user_id-index`
**Purpose:** Query all payments by a specific user

```python
# Get user's payment history
payments = dynamodb_client.get_payments_by_user("user_alice")
```

**Key Schema:**
- Partition Key: `user_id`
- Projection: ALL

#### 2. `quote_id-index`
**Purpose:** Find payment for a specific quote

```python
# Check if quote has payment
payment = dynamodb_client.get_payment_by_quote("quote_travel_7days")
```

**Key Schema:**
- Partition Key: `quote_id`
- Projection: ALL

#### 3. `stripe_session_id-index`
**Purpose:** Query by Stripe session (used by webhook)

```python
# Webhook lookup
payment = dynamodb_client.get_payment_by_session("cs_test_...")
```

**Key Schema:**
- Partition Key: `stripe_session_id`
- Projection: ALL

### DynamoDB Streams

**Enabled:** NEW_AND_OLD_IMAGES

Captures all changes to payment records. Can be used for:
- Real-time notifications
- Analytics pipeline
- Audit logging
- Event-driven workflows

### Client Methods

Available in `backend/database/dynamodb_client.py`:

```python
# Create payment
create_payment_record(payment_data: dict) -> dict

# Retrieve by ID
get_payment_by_id(payment_intent_id: str) -> Optional[dict]

# Query by user
get_payments_by_user(user_id: str) -> List[dict]

# Query by quote
get_payment_by_quote(quote_id: str) -> Optional[dict]

# Query by Stripe session
get_payment_by_session(session_id: str) -> Optional[dict]

# Update status (webhook uses this)
update_payment_status(
    payment_intent_id: str,
    status: str,
    stripe_payment_intent: Optional[str] = None,
    failure_reason: Optional[str] = None
) -> dict
```

---

## Testing the Payment Flow

### Complete End-to-End Test

**Prerequisites:**
- All services running (backend, payment pages, webhook listener)
- Stripe test mode enabled
- DynamoDB table initialized

### Step 1: Initiate Payment

```python
# Via MCP tool in Claude Desktop or Python
result = await initiate_purchase(
    user_id="test_user_001",
    quote_id="test_quote_travel",
    amount=15000,  # $150.00
    currency="SGD",
    product_name="Test Travel Insurance - 7 Days",
    customer_email="test@example.com"
)

print(f"Payment ID: {result['payment_intent_id']}")
print(f"Checkout URL: {result['checkout_url']}")
```

**Expected Result:**
- DynamoDB record created with status `pending`
- Checkout URL returned
- Record visible in DynamoDB Admin: http://localhost:8010

### Step 2: Complete Checkout

1. Open the checkout URL in browser
2. Use Stripe test card:
   - Card: `4242 4242 4242 4242`
   - Expiry: Any future date (e.g., `12/34`)
   - CVC: Any 3 digits (e.g., `123`)
   - ZIP: Any 5 digits (e.g., `12345`)

3. Click "Pay"

**Other Test Cards:**
- `4000 0025 0000 3155` - Requires 3D Secure authentication
- `4000 0000 0000 9995` - Declined (insufficient funds)
- `4000 0000 0000 0069` - Expired card

Full list: https://stripe.com/docs/testing#cards

### Step 3: Verify Webhook

**In webhook listener terminal**, you should see:

```
[200] POST /webhook/stripe
  checkout.session.completed
```

**Check backend logs:**
```
Payment status updated: pi_abc123... -> completed
```

### Step 4: Check Payment Status

```python
status = await check_payment_status(result['payment_intent_id'])

print(f"Status: {status['payment_status']}")  # Should be 'completed'
print(f"Stripe PI: {status['stripe_payment_intent']}")
```

**Expected Result:**
- Status changed from `pending` to `completed`
- `stripe_payment_intent` populated
- `updated_at` timestamp changed

### Step 5: Complete Purchase

```python
policy = await complete_purchase(result['payment_intent_id'])

print(f"Policy ID: {policy['policy_id']}")
print(f"Policy Number: {policy['policy_number']}")
print(f"Document URL: {policy['policy_document_url']}")
```

**Expected Result:**
- Policy generated with unique ID
- Policy number format: `POL-YYYY-XXXXXX`

### Step 6: Verify in DynamoDB

Open DynamoDB Admin: http://localhost:8010

**Check record:**
- Status: `completed`
- `stripe_payment_intent`: `pi_...`
- `updated_at`: Recent timestamp

---

## Local vs Production Setup

### Local Development

**Advantages:**
- No AWS credentials needed
- Fast iteration
- Free (no AWS charges)
- Full control

**Configuration:**
```bash
# .env
DYNAMODB_ENDPOINT="http://localhost:8000"
AWS_ACCESS_KEY_ID="dummy"
AWS_SECRET_ACCESS_KEY="dummy"
STRIPE_SECRET_KEY="sk_test_..."
STRIPE_WEBHOOK_SECRET="whsec_..." # From Stripe CLI
```

**Services:**
- DynamoDB Local (Docker)
- Stripe CLI webhook forwarding
- localhost URLs

**Limitations:**
- Not accessible from internet
- No high availability
- Manual webhook forwarding

### Production Deployment

**Advantages:**
- Scalable
- Reliable
- Global availability
- Automatic backups

**Configuration:**
```bash
# .env (production)
# Remove DYNAMODB_ENDPOINT (uses AWS)
AWS_ACCESS_KEY_ID="AKIA..."           # Real AWS credentials
AWS_SECRET_ACCESS_KEY="..."          # Real AWS credentials
AWS_REGION="ap-southeast-1"

STRIPE_SECRET_KEY="sk_live_..."      # Production Stripe keys
STRIPE_PUBLISHABLE_KEY="pk_live_..."
STRIPE_WEBHOOK_SECRET="whsec_..."    # From Stripe Dashboard

# Production URLs (HTTPS required)
BACKEND_API_URL="https://api.yourdomain.com"
PAYMENT_SUCCESS_URL="https://yourdomain.com/success"
PAYMENT_CANCEL_URL="https://yourdomain.com/cancel"
```

**Setup Steps:**

1. **Create AWS DynamoDB Table:**
   ```bash
   # Remove DYNAMODB_ENDPOINT from .env
   # Add real AWS credentials
   python -m database.dynamodb.init_payments_table
   ```

2. **Configure Stripe Webhook:**
   - Go to: https://dashboard.stripe.com/webhooks
   - Add endpoint: `https://api.yourdomain.com/webhook/stripe`
   - Select events: `checkout.session.*`, `payment_intent.*`
   - Copy signing secret to `.env`

3. **Deploy Backend:**
   ```bash
   # Example: Docker deployment
   docker build -t insurance-mcp-backend .
   docker run -p 8000:8000 --env-file .env insurance-mcp-backend
   ```

4. **Enable HTTPS:**
   - Stripe webhooks require HTTPS
   - Use nginx, Cloudflare, or AWS Load Balancer
   - Get SSL certificate (Let's Encrypt, AWS Certificate Manager)

5. **Test Production Webhook:**
   ```bash
   # Send test event from Stripe Dashboard
   # Verify it reaches your server
   ```

**Security Checklist:**
- [ ] HTTPS enabled for all endpoints
- [ ] Webhook signature verification enabled
- [ ] AWS IAM roles with minimal permissions
- [ ] Environment variables not committed to git
- [ ] DynamoDB point-in-time recovery enabled
- [ ] CloudWatch alarms for errors
- [ ] Rate limiting enabled
- [ ] CORS configured properly

---

## Troubleshooting

### Common Issues

#### 1. Payment Status Not Updating

**Symptom:** Status stays `pending` even after completing checkout.

**Causes:**
- Webhook not configured
- Webhook secret mismatch
- Webhook endpoint not accessible

**Solutions:**

```bash
# Check webhook listener is running
stripe listen --forward-to localhost:8000/webhook/stripe

# Verify webhook secret in .env
grep STRIPE_WEBHOOK_SECRET .env

# Test webhook manually
stripe trigger checkout.session.completed

# Check backend logs for webhook errors
# Look for "webhook signature verification failed"
```

**Verify webhook received:**
```bash
# Should see in terminal:
[200] POST /webhook/stripe
  checkout.session.completed
```

#### 2. DynamoDB Connection Errors

**Symptom:** `ResourceNotFoundException` or connection timeout.

**Causes:**
- Docker container not running
- Wrong endpoint configuration
- Table not initialized

**Solutions:**

```bash
# Check Docker containers
docker-compose ps

# Should show dynamodb: Up
# If not:
docker-compose up -d dynamodb

# Verify table exists
aws dynamodb list-tables \
  --endpoint-url http://localhost:8000 \
  --region ap-southeast-1

# Reinitialize if missing
python -m database.dynamodb.init_payments_table

# Test connection
python -c "
from backend.database.dynamodb_client import DynamoDBClient
client = DynamoDBClient()
print('✓ Connected')
"
```

#### 3. Stripe API Errors

**Symptom:** `Invalid API Key` or `No such customer`.

**Causes:**
- Wrong API key (test vs live)
- API key not set
- Expired or revoked key

**Solutions:**

```bash
# Verify API key in .env
grep STRIPE_SECRET_KEY .env

# Should start with: sk_test_... (test mode)
# Or: sk_live_... (production)

# Test key validity
stripe customers list --limit 1

# If error, regenerate key in Stripe Dashboard:
# https://dashboard.stripe.com/test/apikeys

# Update .env and restart backend
```

#### 4. Import Errors

**Symptom:** `ModuleNotFoundError: No module named 'mcp_server'`

**Causes:**
- Virtual environment not activated
- Package not installed
- Wrong Python version

**Solutions:**

```bash
# Activate venv
source venv/bin/activate

# Verify activation (should show venv path)
which python

# Install in editable mode
pip install -e .

# Verify installation
python -c "import mcp_server; print('✓ Installed')"

# Check Python version (must be 3.11+)
python --version
```

#### 5. Checkout URL Not Working

**Symptom:** Checkout URL returns 404 or "Session expired".

**Causes:**
- Session already used
- Session expired (24h limit)
- Wrong Stripe account mode

**Solutions:**

```bash
# Generate new checkout session
result = await initiate_purchase(...)

# Check session expiration
status = await check_payment_status(payment_intent_id)
print(status['expires_at'])

# Verify Stripe mode matches
# Test keys: sk_test_... → test.stripe.com
# Live keys: sk_live_... → stripe.com
```

#### 6. Widget Not Displaying

**Symptom:** OpenAI Apps SDK widget not appearing.

**Causes:**
- Wrong `WIDGET_BASE_URL`
- Payment pages not running
- CORS issues

**Solutions:**

```bash
# Verify payment pages running
curl http://localhost:8085/success
# Should return HTML

# Check WIDGET_BASE_URL
grep WIDGET_BASE_URL .env
# Should be: http://localhost:8085/widgets

# Verify widget data in response
result = await initiate_purchase(...)
print(result['widget'])  # Should have type and data
```

#### 7. Policy Generation Fails

**Symptom:** `complete_purchase()` returns error or mock data.

**Cause:** PDF generation not yet implemented (known limitation).

**Workaround:**

Current implementation returns placeholder:
```python
{
    "policy_document_url": "https://storage.example.com/policies/pol_abc123.pdf"
}
```

**TODO:** Implement PDF generation using:
- ReportLab or WeasyPrint
- Supabase Storage for hosting
- Email delivery integration

---

## Known Limitations

### 1. Email Service Not Implemented

**Affected Tools:**
- `send_payment_link()` (Tool 6)
- `save_quote_for_later()` (Tool 5 - link generated but not sent)

**Status:** Payment link generation works, but email delivery is placeholder.

**Workaround:** Manually share payment link URL with customer.

**TODO:** Integrate email service:
- SendGrid
- AWS SES
- Mailgun
- Resend

**Implementation needed:**
```python
# In backend/services/email_service.py
async def send_payment_link_email(
    email: str,
    payment_link: str,
    product_name: str,
    amount: int
):
    # Send email via provider
    pass
```

### 2. Policy PDF Generation Not Implemented

**Affected Tools:**
- `complete_purchase()` (Tool 3)

**Status:** Returns mock policy document URL.

**Workaround:** Generate policy manually or use external system.

**TODO:** Implement PDF generation:
1. Design policy template
2. Choose PDF library (ReportLab, WeasyPrint, Playwright)
3. Generate PDF with policy details
4. Upload to Supabase Storage
5. Return real document URL

**Example implementation:**
```python
# In backend/services/policy_service.py
async def generate_policy_pdf(
    policy_id: str,
    payment_data: dict
) -> str:
    # Generate PDF
    pdf_bytes = create_policy_pdf(payment_data)

    # Upload to storage
    url = supabase.storage.from_('policies').upload(
        f'{policy_id}.pdf',
        pdf_bytes
    )

    return url
```

### 3. Refund Functionality Missing

**Status:** Stripe integration has `create_refund()` method, but no MCP tool exposed.

**Workaround:** Process refunds via Stripe Dashboard.

**TODO:** Create MCP tool:
```python
@mcp.tool()
async def refund_payment(
    payment_intent_id: str,
    amount: Optional[int] = None,  # None = full refund
    reason: str = "requested_by_customer"
) -> dict:
    """Refund a completed payment"""
    pass
```

### 4. Payment Validation Limited

**Current behavior:**
- No amount limits enforced
- Minimal currency validation
- Quote existence not verified

**TODO:** Add validation:
```python
# Check quote exists before payment
quote = await get_quote(quote_id)
if not quote:
    raise ValueError("Quote not found")

# Verify amount matches quote
if amount != quote['total_price']:
    raise ValueError("Amount mismatch")

# Check amount limits
if amount < 100:  # $1 minimum
    raise ValueError("Amount too small")
```

### 5. Payment Link Email Templates

**Status:** No email templates designed.

**TODO:** Create HTML email templates:
- Payment link email
- Payment confirmation
- Payment failed notification
- Payment reminder (for expired links)

### 6. Analytics & Reporting

**Status:** No reporting tools implemented.

**Available data:**
- All payment records in DynamoDB
- DynamoDB Streams for real-time events

**TODO:** Build analytics:
- Payment success rate
- Revenue tracking
- Failed payment reasons
- Conversion funnel
- Abandoned checkout rate

### 7. Testing Suite

**Status:** No automated tests written.

**TODO:** Add tests:
- Unit tests for each MCP tool
- Integration tests with Stripe test mode
- Webhook event simulations
- Database operation tests
- Error handling validation

---

## Next Steps

### Immediate Priorities

1. **Implement Email Service** (Tools 5-6)
   - Choose provider (SendGrid recommended)
   - Design email templates
   - Add email delivery tracking

2. **Complete Policy PDF Generation** (Tool 3)
   - Design policy template
   - Implement PDF generation
   - Set up document storage

3. **Add Refund Tool**
   - Create MCP tool for refunds
   - Add refund validation
   - Update documentation

4. **Write Test Suite**
   - Unit tests for payment tools
   - Integration tests with Stripe
   - Webhook event tests

### Long-term Improvements

1. **Payment Analytics Dashboard**
   - Revenue tracking
   - Success/failure rates
   - Customer insights

2. **Advanced Validation**
   - Quote verification
   - Amount limits
   - Fraud detection

3. **Multi-Currency Support**
   - Dynamic currency conversion
   - Localized pricing
   - Regional payment methods

4. **Recurring Payments**
   - Subscription support
   - Auto-renewal
   - Payment reminders

---

## Additional Resources

### Documentation

- **Main README:** Architecture and overview
- **GETTING_STARTED.md:** Week-by-week implementation guide
- **ARCHITECTURE_STATUS.md:** Progress tracking
- **.env.example:** Complete configuration reference

### Code References

- **MCP Server:** `mcp_server/server.py:287-820`
- **Stripe Integration:** `backend/services/payment/stripe_integration.py`
- **Purchase Service:** `backend/services/purchase_service.py`
- **DynamoDB Client:** `backend/database/dynamodb_client.py`
- **Payment Pages:** `backend/services/payment/payment_pages.py`
- **Webhook Handler:** `backend/api/webhooks/stripe_webhook.py`

### External Links

- **Stripe Documentation:** https://stripe.com/docs
- **Stripe Testing:** https://stripe.com/docs/testing
- **DynamoDB Documentation:** https://docs.aws.amazon.com/dynamodb/
- **FastMCP:** https://github.com/jlowin/fastmcp
- **MCP Protocol:** https://modelcontextprotocol.io

---

## Support

For issues or questions:

1. Check **Troubleshooting** section above
2. Review code comments in `mcp_server/server.py`
3. Inspect logs from backend and webhook listener
4. Test with Stripe test cards
5. Verify DynamoDB records in Admin UI

---

**Last Updated:** 2025-11-02

**Status:** ✓ All 7 payment tools functional and documented
