# OpenAI Apps SDK Widgets

This directory contains custom React widgets for the Insurance MCP platform, designed to work with the OpenAI Apps SDK.

## Overview

Widgets transform MCP tool responses from plain text into interactive UI components that render directly in ChatGPT conversations. Each widget is a standalone React application bundled with Vite.

## Available Widgets

### 1. Payment Widget (`/payment/`)

**Purpose:** Display insurance payment checkout with Stripe integration

**Features:**
- Product details with formatted pricing
- Color-coded status badge (pending/succeeded/failed)
- "Pay via Stripe" button with external link
- Payment intent ID for tracking

**Used by:** `initiate_purchase` MCP tool

**Documentation:** See `payment/README.md`

## Quick Start

### Automated Setup (Recommended)

```bash
./setup-widgets.sh
```

This script:
1. Checks Node.js/npm installation
2. Installs dependencies for all widgets
3. Builds production bundles
4. Verifies build output

### Manual Setup

```bash
# Build payment widget
cd payment
npm install
npm run build

# Verify
ls -lh dist/
```

## Architecture

```
┌─────────────────────────────────────┐
│       ChatGPT / Claude UI           │
│     (OpenAI Apps SDK Client)        │
└───────────────┬─────────────────────┘
                │
                │ 1. MCP Tool Response with:
                │    _meta.openai/outputTemplate
                │    widgetState: { data }
                │
┌───────────────▼─────────────────────┐
│         FastAPI Backend             │
│       (Port 8085)                   │
│                                     │
│  GET /widgets/payment-widget.html  │←─── 2. SDK fetches widget
│  Returns: Built React bundle       │
└───────────────┬─────────────────────┘
                │
                │ 3. Injects widgetState
                │    into window.openai
                │
┌───────────────▼─────────────────────┐
│       React Widget Component        │
│  - Reads window.openai.widgetState  │
│  - Validates with Zod               │
│  - Renders interactive UI           │
└─────────────────────────────────────┘
```

## Widget Development

### 1. Create New Widget

```bash
# Create directory
mkdir -p new-widget/src

# Copy structure from payment widget
cp payment/package.json new-widget/
cp payment/tsconfig.json new-widget/
cp payment/vite.config.ts new-widget/

# Update configs
cd new-widget
# Edit package.json, vite.config.ts
```

### 2. Create Widget Component

```tsx
// src/NewWidget.tsx
import { Card, Text } from "@openai/apps-sdk"
import WidgetState from "./types"

export default function NewWidget() {
  const state = WidgetState.parse(window.openai.widgetState)

  return (
    <Card>
      <Text value={state.someField} />
    </Card>
  )
}
```

### 3. Define State Schema

```typescript
// src/types.ts
import { z } from "zod"

const WidgetState = z.strictObject({
  someField: z.string(),
  // ... other fields
})

export default WidgetState
```

### 4. Create Entry Point

```tsx
// src/index.tsx
import { render } from "@openai/apps-sdk"
import NewWidget from "./NewWidget"

render(<NewWidget />)
```

### 5. Build and Serve

```bash
npm install
npm run build

# Add router endpoint in backend/routers/widgets.py
@router.get("/new-widget.html")
async def serve_new_widget():
    widget_path = WIDGETS_DIR / "new-widget" / "dist" / "index.html"
    return FileResponse(widget_path, ...)
```

### 6. Update MCP Tool

```python
# In mcp_server/server.py
@mcp.tool()
async def some_tool():
    return {
        "content": [{"type": "text", "text": "..."}],
        "_meta": {
            "openai/outputTemplate": "http://localhost:8085/widgets/new-widget.html"
        },
        "widgetState": {
            "someField": "value"
        }
    }
```

## Common Patterns

### Reading Widget State

```tsx
import { useEffect, useState } from "react"

function MyWidget() {
  const [state, setState] = useState(window.openai.widgetState)

  // Widget state can update (e.g., status changes)
  useEffect(() => {
    const handleStateChange = () => {
      setState(window.openai.widgetState)
    }

    window.addEventListener('openai:widgetStateChange', handleStateChange)
    return () => window.removeEventListener('openai:widgetStateChange', handleStateChange)
  }, [])

  return <div>{state.someField}</div>
}
```

### Calling MCP Tools from Widget

```tsx
import { Button } from "@openai/apps-sdk"

function MyWidget() {
  const handleRefresh = () => {
    window.openai.callTool({
      name: "check_payment_status",
      parameters: {
        payment_intent_id: window.openai.widgetState.payment_intent_id
      }
    })
  }

  return <Button label="Refresh Status" onClickAction={{ type: "custom", handler: handleRefresh }} />
}
```

### Theme Support

```tsx
import { useEffect, useState } from "react"

function MyWidget() {
  const [theme, setTheme] = useState(window.openai.theme || 'light')

  useEffect(() => {
    const handleThemeChange = () => setTheme(window.openai.theme)
    window.addEventListener('openai:themeChange', handleThemeChange)
    return () => window.removeEventListener('openai:themeChange', handleThemeChange)
  }, [])

  return <div className={theme === 'dark' ? 'dark-mode' : 'light-mode'}>...</div>
}
```

## OpenAI Apps SDK Components

Available components from `@openai/apps-sdk`:

**Layout:**
- `Card` - Container with shadow
- `Col` - Vertical stack
- `Row` - Horizontal flex
- `Spacer` - Flexible space
- `Divider` - Horizontal line

**Typography:**
- `Title` - Large heading
- `Caption` - Small label
- `Text` - Body text

**Interactive:**
- `Button` - Action button
- `Badge` - Status indicator
- `Icon` - Icon display

**Actions:**
```tsx
<Button
  label="Click Me"
  onClickAction={{
    type: "url",           // Open URL
    url: "https://..."
  }}
/>

<Button
  label="Call Tool"
  onClickAction={{
    type: "toolCall",      // Call MCP tool
    toolName: "my_tool",
    parameters: {...}
  }}
/>

<Button
  label="Send Message"
  onClickAction={{
    type: "message",       // Send chat message
    message: "Hello!"
  }}
/>
```

## Build Configuration

### Vite Config Template

```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteSingleFile } from 'vite-plugin-singlefile'

export default defineConfig({
  plugins: [react(), viteSingleFile()],
  build: {
    outDir: 'dist',
    assetsDir: '',
    cssCodeSplit: false,
    rollupOptions: {
      output: {
        entryFileNames: 'widget-name.js',
        assetFileNames: 'widget-name.[ext]',
      },
    },
  },
  server: {
    port: 4444,
    cors: true,
  },
})
```

### TypeScript Config

```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "jsx": "react-jsx",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true
  },
  "include": ["src"]
}
```

## Testing

### Development Mode

```bash
cd payment
npm run dev
```

Open `http://localhost:4444` and inject test state:

```javascript
window.openai = {
  widgetState: {
    // Your test data
  },
  theme: 'light',
  callTool: (args) => console.log('Tool called:', args)
}
```

### Integration Testing

1. Build widget: `npm run build`
2. Start backend: `uvicorn backend.main:app --reload --port 8085`
3. Test serving: `curl http://localhost:8085/widgets/payment-widget.html`
4. Start MCP server: `python -m mcp_server.server`
5. Test with MCP Inspector

### End-to-End Testing

Test in ChatGPT:
1. Connect MCP server to ChatGPT
2. Ask Claude to initiate payment
3. Verify widget renders
4. Click button, verify action works

## Deployment

### Development (Current)

Widgets served by FastAPI backend:
- URL: `http://localhost:8085/widgets/payment-widget.html`
- CORS: Enabled for all origins
- Caching: Minimal (for development)

### Production Option 1: FastAPI Serving

**Pros:** Simple, single deployment
**Cons:** Backend serves static files

```bash
# Build all widgets
cd payment && npm run build

# Deploy backend (widgets included)
# No additional config needed
```

### Production Option 2: CDN/S3

**Pros:** Better performance, scales independently
**Cons:** More complex setup

```bash
# Build widgets
cd payment && npm run build

# Upload to S3
aws s3 sync dist/ s3://your-bucket/widgets/payment/ --acl public-read

# Update MCP tools to use CDN URLs
"_meta": {
  "openai/outputTemplate": "https://cdn.yourdomain.com/widgets/payment-widget.html"
}
```

## Performance

### Bundle Size Targets

- HTML: < 5 KB
- JavaScript: < 100 KB (including React + SDK)
- CSS: < 10 KB

### Optimization Tips

1. **Tree shaking:** Vite automatically removes unused code
2. **Code splitting:** Not needed for single-file widgets
3. **Minification:** Enabled by default in production
4. **Compression:** Enable gzip/brotli on server

### Monitoring

```bash
# Check bundle size
ls -lh dist/

# Analyze bundle
npm run build -- --mode analyze
```

## Troubleshooting

### Build Fails

```bash
# Clear and rebuild
rm -rf node_modules package-lock.json dist
npm install
npm run build
```

### Widget Not Loading

1. Check build exists: `ls dist/`
2. Check backend serving: `curl http://localhost:8085/widgets/health`
3. Check browser console for errors
4. Verify CORS headers

### State Validation Fails

1. Check Zod schema matches MCP tool output
2. Verify all required fields present
3. Check data types (string vs number)

### Button Actions Not Working

1. Verify OpenAI SDK initialized: `window.openai`
2. Check action type is valid
3. Check browser console for errors
4. Verify payload structure

## File Structure

```
widgets/
├── README.md              # This file
├── BUILD.md               # Build documentation
├── setup-widgets.sh       # Setup script
│
└── payment/               # Payment widget
    ├── src/
    │   ├── index.tsx      # Entry point
    │   ├── PaymentWidget.tsx
    │   └── types.ts       # State schema
    ├── dist/              # Build output
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    └── README.md          # Widget-specific docs
```

## Resources

**Documentation:**
- [OpenAI Apps SDK Examples](https://github.com/openai/openai-apps-sdk-examples)
- [Custom UX Documentation](https://developers.openai.com/apps-sdk/build/custom-ux)
- [Vite Documentation](https://vitejs.dev)
- [React Documentation](https://react.dev)

**Internal Docs:**
- `/WIDGET_INTEGRATION.md` - Complete integration guide
- `/CHANGES_SUMMARY.md` - Summary of changes
- `BUILD.md` - Build and deployment guide

## Contributing

### Adding a New Widget

1. Create widget directory and structure
2. Implement React component
3. Add backend router endpoint
4. Update MCP tool to return widget metadata
5. Build and test
6. Update this README

### Widget Guidelines

- Keep bundle size < 100 KB
- Validate all state with Zod
- Support light/dark themes
- Handle loading and error states
- Provide meaningful fallback text
- Test in both dev and production

## License

Part of the Conversational Insurance Ultra MCP Server

---

For detailed setup and integration instructions, see `/WIDGET_INTEGRATION.md`
