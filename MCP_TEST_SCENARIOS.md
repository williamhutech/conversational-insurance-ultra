# MCP Test Scenarios for Payment Integration

Complete test scenarios for testing all 7 payment-related MCP tools using MCP Inspector.

## Prerequisites

1. **Start Backend API**
   ```bash
   source venv/bin/activate
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8085
   ```

2. **Start DynamoDB Local**
   ```bash
   docker-compose up -d
   ```

3. **Create Test Data**
   ```bash
   python -m database.dynamodb.create_test_data
   ```

4. **Start Stripe Webhook Listener**
   ```bash
   stripe listen --forward-to localhost:8085/webhook/stripe
   ```

5. **Start MCP Inspector**
   ```bash
   npx @modelcontextprotocol/inspector python -m mcp-server.server
   ```

---

## Test Scenario 1: Happy Path - Complete Purchase Flow

**Objective:** Test the complete purchase flow from initiation to policy generation.

### Steps:

1. **Initiate Purchase**
   - Tool: `initiate_purchase`
   - Parameters:
     ```json
     {
       "user_id": "user_test_happy",
       "quote_id": "quote_test_001",
       "amount": 15000,
       "currency": "SGD",
       "product_name": "Premium Travel Insurance - 7 Days Asia",
       "customer_email": "test@example.com"
     }
     ```
   - Expected Result:
     - Returns `payment_intent_id`
     - Returns `checkout_url` (Stripe hosted page)
     - Returns `session_id`
     - Payment record created in DynamoDB with status "pending"

2. **Check Payment Status** (before payment)
   - Tool: `check_payment_status`
   - Parameters:
     ```json
     {
       "payment_intent_id": "<from step 1>"
     }
     ```
   - Expected Result:
     - Status: "pending"
     - No `stripe_payment_intent` yet

3. **Simulate Payment Completion** (using Stripe CLI)
   ```bash
   # Trigger successful payment webhook
   stripe trigger checkout.session.completed
   ```

4. **Check Payment Status** (after payment)
   - Tool: `check_payment_status`
   - Parameters:
     ```json
     {
       "payment_intent_id": "<from step 1>"
     }
     ```
   - Expected Result:
     - Status: "completed"
     - Has `stripe_payment_intent`

5. **Complete Purchase**
   - Tool: `complete_purchase`
   - Parameters:
     ```json
     {
       "payment_intent_id": "<from step 1>"
     }
     ```
   - Expected Result:
     - Returns `policy_id`
     - Returns `policy_number`
     - Status: "completed"

**Success Criteria:**
- ✅ Payment initiated successfully
- ✅ Status transitions: pending → completed
- ✅ Policy generated after payment completion
- ✅ All data stored correctly in DynamoDB

---

## Test Scenario 2: Duplicate Payment Prevention

**Objective:** Test that duplicate payments for the same quote are prevented.

### Steps:

1. **First Purchase Attempt**
   - Tool: `initiate_purchase`
   - Parameters:
     ```json
     {
       "user_id": "user_duplicate_test",
       "quote_id": "quote_test_002",
       "amount": 25000,
       "currency": "SGD",
       "product_name": "Basic Travel Insurance - 14 Days Europe"
     }
     ```
   - Expected Result: Success, returns payment_intent_id

2. **Second Purchase Attempt (Same Quote)**
   - Tool: `initiate_purchase`
   - Parameters:
     ```json
     {
       "user_id": "user_duplicate_test",
       "quote_id": "quote_test_002",
       "amount": 25000,
       "currency": "SGD",
       "product_name": "Basic Travel Insurance - 14 Days Europe"
     }
     ```
   - Expected Result:
     - Returns error with `error_code: "duplicate_payment"`
     - Error message explains quote already has pending payment
     - Suggests checking existing payment or creating new quote

**Success Criteria:**
- ✅ First payment created successfully
- ✅ Second payment rejected with clear error
- ✅ Error response includes conversational guidance

---

## Test Scenario 3: Save Quote for Later (Payment Failure Recovery)

**Objective:** Test saving a quote when customer wants to pay later.

### Steps:

1. **Save Quote for Later**
   - Tool: `save_quote_for_later`
   - Parameters:
     ```json
     {
       "quote_id": "quote_test_003",
       "user_id": "user_save_test",
       "customer_email": "customer@example.com",
       "product_name": "Family Travel Insurance - 10 Days USA",
       "amount": 45000,
       "currency": "SGD",
       "notes": "Customer wants to think about it"
     }
     ```
   - Expected Result:
     - Returns `payment_link_id`
     - Returns `payment_link_url`
     - Returns `expires_at` (7 days from now)
     - Confirmation message

2. **Get Payment Link**
   - Tool: `get_payment_link`
   - Parameters:
     ```json
     {
       "quote_id": "quote_test_003"
     }
     ```
   - Expected Result:
     - Returns same payment link from step 1
     - `is_active: true`
     - Valid expiration date

3. **Send Payment Link**
   - Tool: `send_payment_link`
   - Parameters:
     ```json
     {
       "quote_id": "quote_test_003",
       "customer_email": "customer@example.com",
       "customer_name": "John Doe"
     }
     ```
   - Expected Result:
     - `success: true`
     - Confirmation that email would be sent (placeholder)

**Success Criteria:**
- ✅ Quote saved successfully
- ✅ Payment link generated with 7-day expiry
- ✅ Link can be retrieved later
- ✅ Email send endpoint works (placeholder)

---

## Test Scenario 4: Payment Status Monitoring (Pending Payment)

**Objective:** Test checking status of a pending payment.

### Steps:

1. **Check Pending Payment**
   - Tool: `check_payment_status`
   - Parameters:
     ```json
     {
       "payment_intent_id": "pi_test_pending_001"
     }
     ```
   - Expected Result:
     - Status: "pending"
     - Has user_id, quote_id, amount
     - No failure_reason
     - Has stripe_session_id

2. **Check Completed Payment**
   - Tool: `check_payment_status`
   - Parameters:
     ```json
     {
       "payment_intent_id": "pi_test_completed_001"
     }
     ```
   - Expected Result:
     - Status: "completed"
     - Has stripe_payment_intent

3. **Check Failed Payment**
   - Tool: `check_payment_status`
   - Parameters:
     ```json
     {
       "payment_intent_id": "pi_test_failed_001"
     }
     ```
   - Expected Result:
     - Status: "failed"
     - Has failure_reason: "Card declined - insufficient funds"

4. **Check Expired Payment**
   - Tool: `check_payment_status`
   - Parameters:
     ```json
     {
       "payment_intent_id": "pi_test_expired_001"
     }
     ```
   - Expected Result:
     - Status: "expired"

**Success Criteria:**
- ✅ All payment statuses return correctly
- ✅ Appropriate fields populated for each status
- ✅ Error reasons included when applicable

---

## Test Scenario 5: Payment Cancellation

**Objective:** Test cancelling a pending payment.

### Steps:

1. **Create Payment to Cancel**
   - Tool: `initiate_purchase`
   - Parameters:
     ```json
     {
       "user_id": "user_cancel_test",
       "quote_id": "quote_cancel_test",
       "amount": 20000,
       "currency": "SGD",
       "product_name": "Test Policy for Cancellation"
     }
     ```

2. **Cancel the Payment**
   - Tool: `cancel_payment`
   - Parameters:
     ```json
     {
       "payment_intent_id": "<from step 1>",
       "reason": "Customer changed mind"
     }
     ```
   - Expected Result:
     - Cancellation confirmed
     - Status updated to "cancelled"

3. **Verify Cancellation**
   - Tool: `check_payment_status`
   - Parameters:
     ```json
     {
       "payment_intent_id": "<from step 1>"
     }
     ```
   - Expected Result:
     - Status: "cancelled"
     - failure_reason: "Customer changed mind"

4. **Try to Cancel Completed Payment** (should fail)
   - Tool: `cancel_payment`
   - Parameters:
     ```json
     {
       "payment_intent_id": "pi_test_completed_001",
       "reason": "Test"
     }
     ```
   - Expected Result:
     - Error indicating cannot cancel completed payment
     - Suggests refund instead

**Success Criteria:**
- ✅ Pending payment can be cancelled
- ✅ Cancellation reason stored
- ✅ Completed payment cannot be cancelled
- ✅ Appropriate error messages

---

## Test Scenario 6: Error Handling - Payment Not Found

**Objective:** Test error handling when payment doesn't exist.

### Steps:

1. **Check Non-Existent Payment**
   - Tool: `check_payment_status`
   - Parameters:
     ```json
     {
       "payment_intent_id": "pi_does_not_exist"
     }
     ```
   - Expected Result:
     - Error response
     - error_code: "payment_not_found"
     - user_message with conversational guidance
     - suggested_action: "create_new_payment"

2. **Complete Non-Existent Payment**
   - Tool: `complete_purchase`
   - Parameters:
     ```json
     {
       "payment_intent_id": "pi_does_not_exist"
     }
     ```
   - Expected Result:
     - Error response
     - Clear error message
     - Conversational guidance

**Success Criteria:**
- ✅ Errors have standardized format
- ✅ user_message is conversational
- ✅ suggested_action provides next steps
- ✅ can_retry flag is appropriate

---

## Test Scenario 7: User Payment History

**Objective:** Test retrieving all payments for a user.

### Steps:

1. **Get User Payments**
   - Tool: (Need to add this to MCP if not already present)
   - OR use backend API directly:
     ```bash
     curl http://localhost:8085/api/purchase/user/user_alice/payments
     ```
   - Expected Result:
     - List of all payments for user_alice
     - Should include both completed and expired payments
     - Sorted by creation date (newest first)

**Success Criteria:**
- ✅ Returns all user payments
- ✅ Includes all relevant fields
- ✅ Properly sorted

---

## Test Scenario 8: Quote Payment Lookup

**Objective:** Test finding payment for a specific quote.

### Steps:

1. **Get Quote Payment**
   - Use backend API:
     ```bash
     curl http://localhost:8085/api/purchase/quote/quote_test_completed/payment
     ```
   - Expected Result:
     - Returns payment record for that quote
     - Status: "completed"

2. **Get Payment for Quote Without Payment**
   - Use backend API:
     ```bash
     curl http://localhost:8085/api/purchase/quote/quote_test_001/payment
     ```
   - Expected Result:
     - 404 Not Found
     - Clear error message

**Success Criteria:**
- ✅ Can find payment by quote_id
- ✅ Returns 404 when no payment exists
- ✅ Proper error handling

---

## Running Tests with MCP Inspector

### Setup MCP Inspector

1. **Start MCP Inspector**
   ```bash
   npx @modelcontextprotocol/inspector python -m mcp-server.server
   ```

2. **Open Inspector UI**
   - Browser opens automatically
   - If not, go to: `http://localhost:5173`

3. **Connect to MCP Server**
   - Inspector should auto-detect the server
   - Verify all 12 tools are listed
   - Focus on the 7 payment tools:
     - `initiate_purchase`
     - `check_payment_status`
     - `complete_purchase`
     - `cancel_payment`
     - `save_quote_for_later`
     - `send_payment_link`
     - `get_payment_link`

### Testing Workflow

For each scenario:

1. **Read the scenario description** above
2. **Select the tool** in MCP Inspector
3. **Fill in parameters** using the provided JSON
4. **Execute the tool**
5. **Verify response** matches expected result
6. **Check DynamoDB** (optional) to verify data persistence
   - Go to: `http://localhost:8010`
   - Browse payments and quotes tables

### Recording Results

Create a test results log:

```markdown
## Test Results - [Date]

### Scenario 1: Happy Path
- ✅ Step 1: Payment initiated
- ✅ Step 2: Status check (pending)
- ✅ Step 3: Payment completed (webhook)
- ✅ Step 4: Status check (completed)
- ✅ Step 5: Policy generated
- Overall: PASS

### Scenario 2: Duplicate Prevention
- ✅ First payment created
- ✅ Second payment rejected
- ✅ Error response correct
- Overall: PASS

... (continue for all scenarios)
```

---

## Troubleshooting

### Common Issues

1. **"Connection refused" errors**
   - Verify backend is running on port 8085
   - Check `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8085`

2. **"Table not found" errors**
   - Run: `python -m database.dynamodb.init_payments_table`
   - Run: `python -m database.dynamodb.init_quotes_table`
   - Verify DynamoDB is running: `docker ps`

3. **MCP Inspector not connecting**
   - Ensure MCP server starts without errors
   - Check logs for any import errors
   - Verify all dependencies installed: `pip install -e .`

4. **Stripe webhook not working**
   - Verify Stripe CLI is running
   - Check webhook is forwarding to port 8085 (not 8000)
   - Look for webhook events in Stripe CLI output

---

## Next Steps After Testing

Once all scenarios pass:

1. **Document any issues found**
2. **Update error messages** if needed
3. **Add missing test scenarios**
4. **Create production testing plan**
5. **Set up monitoring and logging**
6. **Prepare for Phase 4 (Production Readiness)** (if needed)

---

## Test Data Reference

### Test Users
- `user_alice` - Has completed and expired payments
- `user_bob` - Has pending payment
- `user_charlie` - Has failed payment

### Test Quotes
- `quote_test_001` - Premium Asia 7d ($150 SGD)
- `quote_test_002` - Basic Europe 14d ($250 SGD)
- `quote_test_003` - Family USA 10d ($450 SGD)

### Test Payment Records
- `pi_test_completed_001` - Completed payment
- `pi_test_pending_001` - Pending payment
- `pi_test_failed_001` - Failed payment (card declined)
- `pi_test_expired_001` - Expired payment (>24h old)
