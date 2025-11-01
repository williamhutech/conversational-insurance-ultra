# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Conversational Finance** is an AI-powered conversational insurance platform that enables customers to discover, compare, and purchase travel insurance through natural conversations on Claude/ChatGPT using the Model Context Protocol (MCP).

**Critical Context:** Always use context7 MCP to fetch the latest documentation for any library before implementation.

### 3-Tier Architecture
```
Claude/ChatGPT Client (UI Layer)
        ↓ MCP Protocol
FastMCP Server (12 Tools) - mcp_server/
        ↓ HTTP/REST
FastAPI Backend (Business Logic) - backend/
        ↓
Multiple Databases (Supabase, Neo4j, Mem0, DynamoDB, Stripe)
```

### Implementation Status
- ✅ **Block 4 (Payment):** Fully implemented - Stripe checkout, DynamoDB payments, webhooks
- ⏳ **Blocks 1-3, 5:** Scaffolding complete, business logic pending
- **Database:** Schemas not created yet, data assets ready to load

## Development Commands

### Setup & Installation
```bash
# Create virtual environment (Python 3.11+)
python3.11 -m venv venv
source venv/bin/activate

# Install with UV (recommended - this project uses UV)
uv pip install -e .

# Or with pip
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with API keys
```

### Running the Application
```bash
# Start FastAPI backend (http://localhost:8000)
uvicorn backend.main:app --reload

# Start MCP server (IMPORTANT: use underscore, not hyphen)
python -m mcp_server.server

# Or test with MCP Inspector
npx @modelcontextprotocol/inspector uv run python -m mcp_server.server

# Start local databases (Neo4j, Redis, DynamoDB)
docker-compose up -d

# Initialize DynamoDB payments table
python -m database.dynamodb.init_payments_table

# View DynamoDB Admin UI
open http://localhost:8010
```

### Testing
```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run specific test
pytest tests/test_policies.py

# Run with coverage
pytest --cov=backend --cov=mcp_server

# Test pattern matching
pytest -k "test_payment"
```

### Code Quality
```bash
# Format code
black .

# Lint
ruff check .

# Type check
mypy backend/ mcp_server/

# All checks
black . && ruff check . && mypy backend/ mcp_server/
```

## Critical Architecture Patterns

### 1. MCP Tool Constraints
**IMPORTANT:** FastMCP does NOT support `**kwargs`:
```python
# ❌ WRONG - Will fail in MCP Inspector
@mcp.tool()
async def my_tool(**kwargs):
    pass

# ✅ CORRECT - Use Dict[str, Any] instead
@mcp.tool()
async def my_tool(user_info: Dict[str, Any] | None = None):
    pass
```

### 2. Async-First Design
All route handlers, database clients, and HTTP calls must be async:
```python
@router.get("/policies/{policy_id}")
async def get_policy(policy_id: str, service: PolicyService = Depends()):
    return await service.get_policy(policy_id)
```

### 3. Pydantic Settings & Dependency Injection
- Configuration: `backend/config.py` uses Pydantic Settings (122 env vars)
- DI: `backend/dependencies.py` defines all injectable dependencies
- Models: All data validation uses Pydantic 2.5+ with strict typing

### 4. Dual-Layer Policy Intelligence
Critical business requirement - always store BOTH:
- **Normalized taxonomy data** (Supabase) - enables apples-to-apples comparison
- **Original policy text** (multi-language) - provides source of truth

### 5. Feature Flags
All 5 blocks have `.env` feature flags for gradual rollout:
- `ENABLE_BLOCK_1_POLICY_INTELLIGENCE=true`
- `ENABLE_BLOCK_2_FAQ=true`
- `ENABLE_BLOCK_3_DOCUMENT_INTELLIGENCE=true`
- `ENABLE_BLOCK_4_PURCHASE=true`
- `ENABLE_BLOCK_5_ANALYTICS=true`

## Module Path Conventions

**CRITICAL:** Module paths use underscores, not hyphens:
- ✅ `python -m mcp_server.server`
- ❌ `python -m mcp-server.server`
- ✅ `from mcp_server.client import backend_client`
- ❌ `from mcp-server.client import backend_client`

Directory names: `mcp_server/`, `backend/`, `libs/`

## Multi-Database Strategy

### Supabase (Postgres + pgvector)
- **Purpose:** Normalized policies, benefits, quotations, policy_embeddings
- **Client:** `backend/database/postgres_client.py`
- **Not Created Yet:** Run schema creation scripts in `database/postgres/`

### Neo4j (Graph Database)
- **Purpose:** Policy relationships, claims analysis for recommendations
- **Client:** `backend/database/neo4j_client.py`
- **URL:** `bolt://localhost:7687` (local) or Neo4j Aura (production)
- **Requires:** APOC plugin (included in docker-compose)

### DynamoDB (Payment Records) ✅ **Implemented**
- **Purpose:** Payment transactions, session tracking
- **Client:** `backend/database/dynamodb_client.py`
- **Table:** `lea-payments-local` with GSIs (user_id, quote_id, stripe_session_id)
- **Local Dev:** DynamoDB Local on port 8000, Admin UI on port 8010

### Mem0 (Conversation Memory)
- **Purpose:** Customer context, preferences across sessions
- **Client:** `backend/database/mem0_client.py`
- **API Key:** Required in `.env`

### Stripe (Payment Processing) ✅ **Implemented**
- **Service:** `backend/services/stripe_integration.py`
- **Webhooks:** `backend/services/payment/stripe_webhook.py`
- **Test Mode:** Use `sk_test_...` keys from Stripe dashboard

## Data Assets Ready to Load

1. **Taxonomy_Hackathon.json** - `database/supabase/taxonomy/` (5,484 lines)
2. **3 Policy PDFs** - `database/policy_wordings/` (original policy documents)
3. **Claims_Data_DB.pdf** - `database/neo4j/claims/` (proprietary MSIG data)

## FastMCP Server Tools (12 Total)

**Block 1: Policy Intelligence** (3 tools) - TODO
- `compare_policies`, `explain_coverage`, `search_policies`

**Block 2: FAQ** (1 tool) - TODO
- `answer_question`

**Block 3: Document Intelligence** (3 tools) - TODO
- `upload_document`, `extract_travel_data`, `generate_quotation`

**Block 4: Purchase** (4 tools) ✅ **COMPLETE**
- `initiate_purchase` - Create Stripe checkout session
- `check_payment_status` - Poll payment status (DynamoDB)
- `complete_purchase` - Generate policy after successful payment
- `cancel_payment` - Cancel pending payment

**Block 5: Analytics** (2 tools) - TODO
- `get_recommendations`, `analyze_destination_risk`

**Memory** (1 tool) - TODO
- `manage_conversation_memory`

## Testing MCP Tools

**Two approaches:**

### 1. MCP Inspector (Visual UI)
```bash
npx @modelcontextprotocol/inspector uv run python -m mcp_server.server
```

### 2. FastMCP Client (Python Script)
```python
from fastmcp import Client
from mcp_server.server import mcp

async def test_tools():
    async with Client(mcp) as client:
        # List available tools
        tools = await client.list_tools()

        # Call a tool
        result = await client.call_tool("initiate_purchase", {
            "user_id": "user_123",
            "quote_id": "quote_456",
            "amount": 15000,
            "currency": "SGD",
            "product_name": "Premium Travel Insurance",
            "customer_email": "test@example.com"
        })
        print(result)
```

## Common Issues

### MCP Server Module Import Errors
- Use `python -m mcp_server.server`, NOT `python -m mcp-server.server`
- Ensure `__init__.py` exists in `mcp_server/` directory

### Backend Not Connecting
- Verify FastAPI is running: `curl http://localhost:8000/health`
- Check `.env` has correct `BACKEND_URL=http://localhost:8000`

### DynamoDB Connection Fails
- Ensure Docker is running: `docker ps | grep dynamodb`
- Check port 8000 not in use by other services
- Re-initialize table: `python -m database.dynamodb.init_payments_table`

### Stripe Webhook Not Receiving Events
- For local dev, use Stripe CLI: `stripe listen --forward-to localhost:8000/webhook/stripe`
- Copy webhook secret from CLI output to `.env` as `STRIPE_WEBHOOK_SECRET`

## Key Files

- **[backend/config.py](backend/config.py)** - All 122 environment variables with Pydantic Settings
- **[mcp_server/server.py](mcp_server/server.py)** - Main MCP server with 12 tool definitions
- **[backend/main.py](backend/main.py)** - FastAPI application entry point
- **[backend/routers/purchase_router.py](backend/routers/purchase_router.py)** - Payment API endpoints (9 routes)
- **[backend/services/purchase_service.py](backend/services/purchase_service.py)** - Purchase orchestration logic
- **.env.example** - Complete environment template with all required keys

## Type Safety

Python 3.11+ type hints are required everywhere. MyPy strict mode is enabled:
```python
from typing import Optional, List, Dict, Any

async def search_policies(
    query: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    ...
```
