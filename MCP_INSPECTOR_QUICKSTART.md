# MCP Inspector Quick Start Guide

Quick guide to set up and test your 7 payment MCP tools in the browser.

## Prerequisites

Make sure these services are running:

```bash
# Terminal 1: Start DynamoDB Local
docker-compose up -d

# Terminal 2: Start Backend API
source venv/bin/activate
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8085

# Terminal 3: Start Stripe Webhook Listener
stripe listen --forward-to localhost:8085/webhook/stripe

# Terminal 4: Create Test Data (one-time)
python -m database.dynamodb.create_test_data
```

## Step 1: Start MCP Inspector

```bash
# Terminal 5: Start MCP Inspector
npx @modelcontextprotocol/inspector python -m mcp-server.server
```

**What happens:**
- Inspector will automatically open in your browser at `http://localhost:5173`
- You'll see a web interface with two panels: Tools list (left) and Tool execution (right)

## Step 2: Verify Connection

In the MCP Inspector browser window:

1. **Check connection status** - Top of the page should show "Connected" in green
2. **Count tools** - You should see **12 tools** listed in the left panel
3. **Locate payment tools** - Look for these 7 tools:
   - `initiate_purchase`
   - `check_payment_status`
   - `complete_purchase`
   - `cancel_payment`
   - `save_quote_for_later`
   - `send_payment_link`
   - `get_payment_link`

## Step 3: Test Tool #1 - Initiate Purchase

1. **Click** `initiate_purchase` in the tools list (left panel)
2. **Fill in the parameters** (right panel):

```json
{
  "user_id": "user_test_001",
  "quote_id": "quote_test_001",
  "amount": 15000,
  "currency": "SGD",
  "product_name": "Premium Travel Insurance - 7 Days Asia",
  "customer_email": "test@example.com"
}
```

3. **Click "Execute Tool"** button
4. **Expected Response:**
```json
{
  "payment_intent_id": "pi_abc123...",
  "checkout_url": "https://checkout.stripe.com/...",
  "session_id": "cs_test_...",
  "amount": 15000,
  "currency": "SGD",
  "expires_at": "2025-11-01T..."
}
```

5. **Copy the `payment_intent_id`** - You'll need this for other tests!

## Step 4: Test Tool #2 - Check Payment Status

1. **Click** `check_payment_status` in tools list
2. **Fill in parameters:**

```json
{
  "payment_intent_id": "pi_abc123..."
}
```
(Use the payment_intent_id from Step 3)

3. **Click "Execute Tool"**
4. **Expected Response:**
```json
{
  "payment_intent_id": "pi_abc123...",
  "payment_status": "pending",
  "amount": 15000,
  "currency": "SGD",
  "product_name": "Premium Travel Insurance - 7 Days Asia",
  "user_id": "user_test_001",
  "quote_id": "quote_test_001",
  "created_at": "...",
  "updated_at": "..."
}
```

## Step 5: Test Tool #3 - Save Quote for Later

1. **Click** `save_quote_for_later` in tools list
2. **Fill in parameters:**

```json
{
  "quote_id": "quote_test_002",
  "user_id": "user_test_002",
  "customer_email": "customer@example.com",
  "product_name": "Basic Travel Insurance - 14 Days Europe",
  "amount": 25000,
  "currency": "SGD",
  "notes": "Customer wants to think about it"
}
```

3. **Click "Execute Tool"**
4. **Expected Response:**
```json
{
  "success": true,
  "payment_link_id": "link_...",
  "payment_link_url": "http://localhost:8085/payment/quote_test_002",
  "expires_at": "2025-11-08T...",
  "message": "Quote saved! Payment link valid for 7 days."
}
```

## Step 6: Test Tool #4 - Get Payment Link

1. **Click** `get_payment_link` in tools list
2. **Fill in parameters:**

```json
{
  "quote_id": "quote_test_002"
}
```

3. **Click "Execute Tool"**
4. **Expected Response:**
```json
{
  "payment_link_url": "http://localhost:8085/payment/quote_test_002",
  "expires_at": "2025-11-08T...",
  "is_active": true,
  "quote_id": "quote_test_002"
}
```

## Step 7: Test Tool #5 - Cancel Payment

1. **Click** `cancel_payment` in tools list
2. **Fill in parameters:**

```json
{
  "payment_intent_id": "pi_abc123...",
  "reason": "Customer changed their mind"
}
```
(Use a payment_intent_id from a pending payment)

3. **Click "Execute Tool"**
4. **Expected Response:**
```json
{
  "success": true,
  "payment_intent_id": "pi_abc123...",
  "status": "cancelled",
  "message": "Payment cancelled successfully"
}
```

## Step 8: Test with Pre-Created Test Data

You can also test with the pre-created test payment records:

### Test a Completed Payment
```json
{
  "payment_intent_id": "pi_test_completed_001"
}
```

### Test a Failed Payment
```json
{
  "payment_intent_id": "pi_test_failed_001"
}
```

### Test an Expired Payment
```json
{
  "payment_intent_id": "pi_test_expired_001"
}
```

### Test a Pending Payment
```json
{
  "payment_intent_id": "pi_test_pending_001"
}
```

## Testing Payment Completion Flow

To test the full payment flow with Stripe webhooks:

1. **Initiate purchase** (Step 3) - Get payment_intent_id
2. **Simulate payment** in Terminal:
   ```bash
   stripe trigger checkout.session.completed
   ```
3. **Check webhook logs** - You'll see webhook received in Terminal 3
4. **Check payment status** - Should now show "completed"
5. **Complete purchase** - Generate policy:
   ```json
   {
     "payment_intent_id": "pi_abc123..."
   }
   ```

## Common Issues & Solutions

### Issue: "Connection Failed" in Inspector
**Solution:**
- Check MCP server is running (Terminal 5)
- Restart: `Ctrl+C` then re-run `npx @modelcontextprotocol/inspector python -m mcp-server.server`

### Issue: "Backend connection refused"
**Solution:**
- Check backend is running on port 8085 (Terminal 2)
- Visit http://localhost:8085/docs to verify

### Issue: "Payment not found"
**Solution:**
- Use `check_payment_status` to verify payment_intent_id exists
- Or create new payment with `initiate_purchase`

### Issue: "Table not found"
**Solution:**
```bash
# Reinitialize DynamoDB tables
python -m database.dynamodb.init_payments_table
python -m database.dynamodb.create_test_data
```

### Issue: Tool returns "Not implemented"
**Solution:**
- This is expected for Blocks 1-3, 5 tools (not yet implemented)
- Only Block 4 payment tools (7 tools) are fully implemented

## MCP Inspector Tips

1. **Auto-fill feature** - Inspector remembers your last parameters for each tool
2. **JSON validation** - Inspector will highlight JSON syntax errors
3. **Response formatting** - Click to expand/collapse nested JSON
4. **Tool descriptions** - Hover over tool name to see full description
5. **Copy response** - Click copy icon to copy entire response

## Viewing Data

### DynamoDB Admin UI
```bash
# Open in browser
open http://localhost:8010
```
- Browse `lea-payments-local` table
- View payment records in real-time
- See GSI indexes (user_id-index, quote_id-index)

### Backend API Docs
```bash
# Open Swagger UI
open http://localhost:8085/docs
```
- Test API endpoints directly
- View request/response schemas
- Try alternative endpoints

## Next Steps

Once comfortable with MCP Inspector:

1. **Test error scenarios** - Try duplicate payments, invalid IDs, etc.
2. **Test payment links** - Copy payment_link_url and open in browser
3. **Monitor webhooks** - Watch Terminal 3 for Stripe events
4. **Review test scenarios** - See `MCP_TEST_SCENARIOS.md` for comprehensive testing

## Quick Reference

| Tool | Purpose | Key Parameter |
|------|---------|---------------|
| `initiate_purchase` | Start payment | `quote_id`, `amount` |
| `check_payment_status` | Get status | `payment_intent_id` |
| `complete_purchase` | Generate policy | `payment_intent_id` |
| `cancel_payment` | Cancel pending | `payment_intent_id` |
| `save_quote_for_later` | Create payment link | `quote_id` |
| `get_payment_link` | Retrieve link | `quote_id` |
| `send_payment_link` | Email link | `quote_id`, `customer_email` |

## Support

- **Full test scenarios:** See `MCP_TEST_SCENARIOS.md`
- **Architecture:** See `README.md`
- **Environment setup:** See `.env.example`
- **Backend logs:** Check Terminal 2 for errors

Happy testing! 🚀
