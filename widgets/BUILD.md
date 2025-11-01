# Building Widgets

This guide explains how to build and deploy the OpenAI Apps SDK widgets for the Insurance MCP platform.

## Quick Start

```bash
# Build payment widget
cd widgets/payment
npm install
npm run build

# Verify build
ls -lh dist/
```

## Build Process

### 1. Install Dependencies

First time setup for each widget:

```bash
cd widgets/payment
npm install
```

This installs:
- React & React DOM
- OpenAI Apps SDK
- TypeScript & Vite
- Zod for validation

### 2. Development Mode

Run widget in development mode with hot reload:

```bash
npm run dev
```

Widget available at: `http://localhost:4444`

**Note:** In dev mode, you need to manually inject `window.openai.widgetState` in the browser console to see the widget with data.

### 3. Build for Production

Build optimized bundle:

```bash
npm run build
```

Output in `dist/`:
- `index.html` - Entry point
- `payment-widget.js` - Bundled JavaScript
- `payment-widget.css` - Bundled styles (if any)

### 4. Verify Build

Check that files exist:

```bash
ls -lh widgets/payment/dist/
```

Expected output:
```
index.html         (~2KB)
payment-widget.js  (~50-100KB depending on dependencies)
```

### 5. Start Backend Server

The FastAPI backend serves the built widgets:

```bash
# From project root
cd conversational-insurance-ultra
uvicorn backend.main:app --reload --port 8085
```

Widget endpoint: `http://localhost:8085/widgets/payment-widget.html`

### 6. Test Widget Serving

Check widget health:

```bash
curl http://localhost:8085/widgets/health
```

Expected response:
```json
{
  "status": "healthy",
  "widgets": {
    "payment": {
      "built": true,
      "path": "/path/to/widgets/payment/dist"
    }
  }
}
```

Fetch widget:
```bash
curl http://localhost:8085/widgets/payment-widget.html
```

## Integration with MCP Server

The widget is automatically integrated when you:

1. Build the widget (`npm run build`)
2. Start the FastAPI backend (serves widgets)
3. Start MCP server (returns widget metadata)

### Testing Full Flow

1. **Start all services:**

```bash
# Terminal 1: Start DynamoDB Local
docker-compose up -d

# Terminal 2: Start Backend
cd conversational-insurance-ultra
uvicorn backend.main:app --reload --port 8085

# Terminal 3: Start MCP Server
python -m mcp_server.server
```

2. **Test via MCP Inspector:**

```bash
npx @modelcontextprotocol/inspector python -m mcp_server.server
```

3. **Call `initiate_purchase` tool:**

```json
{
  "user_id": "user_123",
  "quote_id": "quote_456",
  "amount": 15000,
  "currency": "SGD",
  "product_name": "Premium Travel Insurance",
  "customer_email": "test@example.com"
}
```

4. **Expected response:**

```json
{
  "content": [{
    "type": "text",
    "text": "✅ Payment initiated..."
  }],
  "_meta": {
    "openai/outputTemplate": "http://localhost:8085/widgets/payment-widget.html"
  },
  "widgetState": {
    "payment_intent_id": "pi_...",
    "checkout_url": "https://checkout.stripe.com/...",
    "product_name": "Premium Travel Insurance",
    "amount": "150.00",
    "currency": "SGD",
    "status": "pending"
  }
}
```

## Production Deployment

### Build for Production

```bash
cd widgets/payment
npm run build
```

### Deployment Options

**Option 1: Serve from FastAPI (Current Setup)**
- Widgets served at `/widgets/*` endpoints
- Simple deployment, single service
- Good for MVP and testing

**Option 2: CDN/S3 Hosting**
- Upload `dist/` contents to S3/CDN
- Update `_meta.openai/outputTemplate` URLs in MCP tools
- Better performance, scales independently
- Set `BASE_URL` env var for assets

Example for S3:
```python
# In mcp_server/server.py
"_meta": {
    "openai/outputTemplate": "https://your-cdn.com/widgets/payment-widget.html"
}
```

### Environment Variables

For production, update URLs:

```env
# .env
WIDGET_BASE_URL=https://your-domain.com/widgets
```

Then in MCP tools:
```python
from backend.config import settings

"_meta": {
    "openai/outputTemplate": f"{settings.widget_base_url}/payment-widget.html"
}
```

## Troubleshooting

### Build Fails

**Error: `Cannot find module '@openai/apps-sdk'`**
```bash
# Solution: Install dependencies
npm install
```

**Error: `TypeScript errors`**
```bash
# Solution: Type check
npm run type-check

# Fix errors, then rebuild
npm run build
```

### Widget Not Loading

**404 on `/widgets/payment-widget.html`**
- Ensure widget is built: `npm run build`
- Check backend includes widget router: `backend/main.py`
- Verify path exists: `ls widgets/payment/dist/index.html`

**CORS Errors**
- Widget router has CORS headers enabled
- Check browser console for specific errors
- Verify backend CORS settings in `backend/main.py`

### State Validation Errors

**"Invalid widget state"**
- Check `widgetState` matches schema in `types.ts`
- Ensure amount is string: `"150.00"` not `15000`
- Verify all required fields present

### Widget Displays But Button Doesn't Work

**Check OpenAI SDK initialization:**
- Verify `window.openai` exists
- Check browser console for SDK errors
- Ensure action type is correct: `"payment.openCheckout"`

## File Structure

```
widgets/
├── payment/
│   ├── src/
│   │   ├── index.tsx          # Entry point
│   │   ├── PaymentWidget.tsx  # Main component
│   │   └── types.ts          # State schema
│   ├── dist/                 # Build output (gitignored)
│   │   ├── index.html
│   │   └── payment-widget.js
│   ├── package.json          # Dependencies
│   ├── tsconfig.json         # TypeScript config
│   ├── vite.config.ts        # Vite bundler config
│   └── README.md            # Widget docs
└── BUILD.md                 # This file
```

## Adding New Widgets

To create a new widget:

1. **Create widget directory:**
```bash
mkdir -p widgets/new-widget/src
cd widgets/new-widget
```

2. **Copy payment widget structure:**
```bash
cp ../payment/package.json .
cp ../payment/tsconfig.json .
cp ../payment/vite.config.ts .
```

3. **Update configs:**
- Change output filename in `vite.config.ts`
- Update widget name in `package.json`

4. **Create component:**
```tsx
// src/NewWidget.tsx
import { Card } from "@openai/apps-sdk"

export default function NewWidget() {
  const state = window.openai.widgetState
  return <Card>Your content</Card>
}
```

5. **Add router endpoint:**
```python
# backend/routers/widgets.py
@router.get("/new-widget.html")
async def serve_new_widget():
    widget_path = WIDGETS_DIR / "new-widget" / "dist" / "index.html"
    return FileResponse(widget_path, media_type="text/html", headers={"Access-Control-Allow-Origin": "*"})
```

6. **Build and test:**
```bash
npm install
npm run build
```

## Performance Optimization

**Bundle Size**
- Target: < 100KB bundled
- Use tree-shaking (Vite default)
- Avoid large dependencies
- Check size: `ls -lh dist/payment-widget.js`

**Load Time**
- Single file bundle (Vite plugin)
- Minification enabled in production
- No external requests except Stripe

**Caching**
- FastAPI serves with caching headers
- Browser caches widget bundle
- Rebuild with version hash for cache busting

## References

- [OpenAI Apps SDK Examples](https://github.com/openai/openai-apps-sdk-examples)
- [Custom UX Documentation](https://developers.openai.com/apps-sdk/build/custom-ux)
- [Vite Documentation](https://vitejs.dev)
- [React Documentation](https://react.dev)
