# Payment Widget for OpenAI Apps SDK

This widget displays insurance payment checkout information with Stripe integration for the Insurance MCP conversational platform.

## Features

- **Product Details Display**: Shows insurance product name, amount, and currency
- **Payment Status Badge**: Visual indicator for payment status (pending/succeeded/failed/canceled)
- **Stripe Checkout Button**: Direct link to complete payment via Stripe
- **Payment Tracking**: Displays payment intent ID for reference

## Prerequisites

- Node.js 18+ and npm
- Backend FastAPI server running on port 8085
- Stripe account configured

## Installation

```bash
cd widgets/payment
npm install
```

## Development

Start the development server with hot reload:

```bash
npm run dev
```

The widget will be available at `http://localhost:4444`

## Build for Production

Build the widget as a single bundled file:

```bash
npm run build
```

This creates optimized files in the `dist/` directory:
- `index.html` - Main HTML entry point
- `payment-widget.js` - Bundled JavaScript

## Usage with MCP Server

The widget is automatically served by the FastAPI backend at:
```
http://localhost:8085/widgets/payment-widget.html
```

### MCP Tool Integration

The `initiate_purchase` tool returns widget metadata:

```python
return {
    "content": [...],
    "_meta": {
        "openai/outputTemplate": "http://localhost:8085/widgets/payment-widget.html"
    },
    "widgetState": {
        "payment_intent_id": "pi_abc123...",
        "checkout_url": "https://checkout.stripe.com/...",
        "product_name": "Premium Travel Insurance",
        "amount": "150.00",
        "currency": "SGD",
        "status": "pending"
    }
}
```

### Widget State Schema

The widget expects the following state structure (validated via Zod):

```typescript
{
  payment_intent_id: string;  // e.g., "pi_abc123..."
  checkout_url: string;        // Stripe checkout URL
  product_name: string;        // e.g., "Premium Travel Insurance"
  amount: string;              // Formatted amount e.g., "150.00"
  currency: string;            // e.g., "SGD", "USD"
  status: string;              // "pending" | "succeeded" | "failed" | "canceled"
}
```

## Component Structure

```
src/
├── index.tsx           # Entry point - renders PaymentWidget
├── PaymentWidget.tsx   # Main React component with UI
└── types.ts           # Zod schema for widget state
```

## Status Badge Colors

- **succeeded** → Green (success)
- **pending** → Yellow (warning)
- **requires_action** → Blue (info)
- **canceled/failed** → Red (danger)
- **default** → Gray (secondary)

## Button Action

The "Pay via Stripe" button triggers:

```typescript
{
  type: "payment.openCheckout",
  payload: {
    url: checkout_url,
    intentId: payment_intent_id
  }
}
```

This is handled by the OpenAI Apps SDK to open the Stripe checkout in a new context.

## Testing

Test the widget in isolation:

1. Start dev server: `npm run dev`
2. Open `http://localhost:4444` in browser
3. Use browser console to inject test state:

```javascript
window.openai = {
  widgetState: {
    payment_intent_id: "pi_test123",
    checkout_url: "https://checkout.stripe.com/test",
    product_name: "Test Insurance",
    amount: "100.00",
    currency: "SGD",
    status: "pending"
  }
}
```

## Integration Testing

Test with full MCP stack:

1. Start DynamoDB Local: `docker-compose up -d`
2. Start FastAPI backend: `uvicorn backend.main:app --reload --port 8085`
3. Build widget: `cd widgets/payment && npm run build`
4. Start MCP server: `python -m mcp_server.server`
5. Test in ChatGPT with MCP connection

## Troubleshooting

**Widget not loading:**
- Ensure widget is built: `npm run build`
- Check backend logs for CORS errors
- Verify widget router is mounted in `backend/main.py`

**State validation errors:**
- Check widgetState matches Zod schema in `types.ts`
- Ensure amounts are formatted as strings (e.g., "150.00" not 15000)

**Button not working:**
- Verify OpenAI Apps SDK is properly initialized
- Check browser console for action handler errors
- Ensure checkout_url is valid Stripe URL

## Dependencies

- **@openai/apps-sdk** - OpenAI Apps SDK components and rendering
- **react** - UI framework
- **zod** - Runtime type validation
- **vite** - Build tool
- **typescript** - Type safety

## Configuration

### Vite Config (`vite.config.ts`)

- **Output**: Single bundled file via `vite-plugin-singlefile`
- **Dev Server**: Port 4444 with CORS enabled
- **Build**: Optimized for production with minification

### TypeScript Config (`tsconfig.json`)

- **Target**: ES2020
- **JSX**: react-jsx
- **Strict Mode**: Enabled for type safety

## Extending the Widget

To add new features:

1. Update `types.ts` with new state properties
2. Modify `PaymentWidget.tsx` to display new data
3. Update MCP tool to include new fields in `widgetState`
4. Rebuild: `npm run build`

## License

Part of the Conversational Insurance Ultra MCP Server
