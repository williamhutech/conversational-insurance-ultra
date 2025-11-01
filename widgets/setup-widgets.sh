#!/bin/bash

# Setup script for OpenAI Apps SDK widgets
# This script installs dependencies and builds all widgets

set -e  # Exit on error

echo "======================================"
echo "OpenAI Apps SDK Widget Setup"
echo "======================================"
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Error: Node.js is not installed"
    echo "Please install Node.js 18+ from https://nodejs.org"
    exit 1
fi

NODE_VERSION=$(node --version)
echo "✅ Node.js detected: $NODE_VERSION"
echo ""

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ Error: npm is not installed"
    exit 1
fi

NPM_VERSION=$(npm --version)
echo "✅ npm detected: v$NPM_VERSION"
echo ""

# Setup payment widget
echo "======================================"
echo "Setting up Payment Widget"
echo "======================================"
cd payment

echo "📦 Installing dependencies..."
npm install

echo "🔨 Building widget..."
npm run build

echo "✅ Payment widget built successfully"
echo ""

# Verify build
if [ -f "dist/index.html" ] && [ -f "dist/payment-widget.js" ]; then
    echo "✅ Build verified:"
    ls -lh dist/
else
    echo "❌ Build verification failed - dist files not found"
    exit 1
fi

cd ..

echo ""
echo "======================================"
echo "✅ Widget Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Start FastAPI backend:"
echo "   cd ../conversational-insurance-ultra"
echo "   uvicorn backend.main:app --reload --port 8085"
echo ""
echo "2. Check widget health:"
echo "   curl http://localhost:8085/widgets/health"
echo ""
echo "3. Start MCP server:"
echo "   python -m mcp_server.server"
echo ""
echo "4. Test with MCP Inspector:"
echo "   npx @modelcontextprotocol/inspector python -m mcp_server.server"
echo ""
echo "For development mode:"
echo "   cd widgets/payment && npm run dev"
echo ""
