# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Conversational Insurance Ultra** is an AI-powered conversational insurance platform that transforms how customers discover, compare, and purchase travel insurance through natural language conversations on Claude/ChatGPT using the Model Context Protocol (MCP).

**Key Innovation:** Block 3 enables customers to upload flight booking documents instead of filling forms, reducing quote time from 20 minutes to 2 minutes through OCR and AI extraction.

**Current Status:** Architecture is 100% defined and documented. Implementation is 65% complete - project scaffolding, configurations, data models, and interfaces are done. **Block 4 (Purchase Execution) is now fully implemented with complete Stripe payment integration, DynamoDB payment records, and webhook processing.**

## Architecture

### 3-Tier Architecture
```
Claude/ChatGPT (UI Layer)
        ↓ MCP Protocol
FastMCP Server (12 Tools)
        ↓ HTTP/REST
FastAPI Backend (Business Logic)
        ↓
Multiple Databases (Supabase, Neo4j, Mem0, Stripe)
```

### The 5 Revolutionary Blocks
1. **Policy Intelligence Engine** - Dual-layer intelligence with normalized taxonomy + original policy text (16+ languages)
2. **Conversational FAQ & Recommendations** - Natural language Q&A with Mem0 memory
3. **Document Intelligence & Auto-Quotation** - OCR + AI extraction from travel documents (killer feature)
4. **Seamless Purchase Execution** - Complete purchase within conversation using Stripe
5. **Data-Driven Recommendations** - Leveraging proprietary MSIG claims data for competitive advantage

### Multi-Database Strategy
- **Supabase (Postgres + pgvector)** - Normalized policies, benefits, quotations, embeddings for semantic search
- **Neo4j** - Graph database for policy relationships and claims analysis
- **DynamoDB** - Payment records and transaction history (✅ Implemented)
- **Mem0** - Customer conversation memory and context management
- **Stripe** - Payment processing (✅ Implemented)

## Technology Stack

- **Python 3.11+** with modern type hints
- **FastAPI 0.108+** - High-performance async API framework
- **FastMCP 0.1+** - Model Context Protocol server for Claude/ChatGPT
- **Pydantic 2.5+** - Data validation and settings management
- **Document Processing:** Tesseract OCR, EasyOCR, PyPDF, Pillow
- **AI:** Anthropic Claude (claude-3-5-sonnet-20241022), OpenAI embeddings
- **Payments:** Stripe 7.8+

## Development Commands

### Setup
```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e .
# or using UV (recommended)
uv pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your API keys and database credentials
```

### Running the Application
```bash
# Start FastAPI backend (with hot reload)
uvicorn backend.main:app --reload
# Available at http://localhost:8000
# API docs at http://localhost:8000/docs

# Start MCP server
python -m mcp-server.server

# Start local databases (Neo4j + Redis + DynamoDB)
docker-compose up -d

# Initialize DynamoDB payments table
python -m database.dynamodb.init_payments_table

# View DynamoDB Admin UI
# Available at http://localhost:8010

# Stop local databases
docker-compose down
```

### Testing
```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov=mcp-server

# Run specific test file
pytest tests/test_policies.py

# Run tests matching pattern
pytest -k "test_policy"
```

### Code Quality
```bash
# Format code with Black
black .

# Lint with Ruff
ruff check .

# Type check with MyPy
mypy backend/ mcp-server/

# Run all quality checks
black . && ruff check . && mypy backend/ mcp-server/
```

## Project Structure

```
conversational-insurance-ultra/
├── backend/                    # FastAPI Backend (Business Logic)
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Pydantic settings configuration (122 env vars)
│   ├── dependencies.py         # Dependency injection setup
│   ├── routers/                # REST API routers
│   │   ├── block_4_purchase.py # ✅ Block 4: Payment & Purchase (COMPLETE)
│   │   └── ...                 # (Other blocks TODO)
│   ├── services/               # Business logic
│   │   ├── purchase_service.py # ✅ Purchase orchestration (COMPLETE)
│   │   ├── stripe_integration.py # ✅ Stripe API integration (COMPLETE)
│   │   ├── payment/            # ✅ Payment sub-services (COMPLETE)
│   │   │   ├── stripe_webhook.py # Webhook event handler
│   │   │   └── payment_pages.py  # Success/cancel pages
│   │   └── ...                 # (Other services TODO)
│   ├── models/                 # Pydantic models (6 complete models)
│   │   ├── payment.py          # ✅ Payment models (COMPLETE)
│   │   ├── policy.py           # Policy, Benefit, Condition models
│   │   ├── document.py         # Document upload & extraction models
│   │   ├── quotation.py        # Quotation request & response models
│   │   ├── purchase.py         # Purchase & payment models
│   │   └── claim.py            # Claims analysis models
│   └── database/               # Database clients
│       ├── dynamodb_client.py  # ✅ DynamoDB payment records (COMPLETE)
│       ├── postgres_client.py  # Supabase client interface
│       ├── neo4j_client.py     # Neo4j graph DB client
│       ├── vector_client.py    # pgvector search client
│       └── mem0_client.py      # Mem0 memory client
│
├── mcp-server/                 # FastMCP Server (MCP Tools)
│   ├── server.py               # Main MCP server with 12 tool signatures
│   ├── tools/                  # Individual tool implementations (need work)
│   ├── prompts/                # Prompt templates (need implementation)
│   └── client/
│       └── backend_client.py   # Backend API HTTP client interface
│
├── libs/                       # Shared Libraries (need implementation)
│   ├── ocr/                    # OCR implementations
│   ├── storage/                # Document storage
│   └── utils/                  # Utilities
│
└── database/                   # Database Setup & Data Assets
    ├── dynamodb/               # ✅ DynamoDB setup (COMPLETE)
    │   └── init_payments_table.py  # Create payments table script
    ├── policy_wordings/        # 3 source policy PDFs (464KB-1.2MB each)
    ├── supabase/
    │   └── taxonomy/
    │       └── Taxonomy_Hackathon.json  # 5,484 lines, ready to load
    └── neo4j/
        └── claims/
            └── Claims_Data_DB.pdf       # Proprietary claims data
```

## FastMCP Server (12 Tools)

The MCP server exposes 12 tools for Claude/ChatGPT integration:

**Block 1: Policy Intelligence** (3 tools)
- `compare_policies` - Compare multiple policies across criteria
- `explain_coverage` - Explain specific coverage details
- `search_policies` - Semantic policy search

**Block 2: Conversational FAQ** (1 tool)
- `answer_question` - Answer insurance questions with memory

**Block 3: Document Intelligence** (3 tools)
- `upload_document` - Upload travel documents
- `extract_travel_data` - OCR + AI extraction
- `generate_quotation` - Auto-generate personalized quotes

**Block 4: Purchase** (4 tools) ✅ **COMPLETE**
- `initiate_purchase` - Start purchase process and create Stripe checkout
- `check_payment_status` - Poll payment status
- `complete_purchase` - Generate policy after successful payment
- `cancel_payment` - Cancel pending payment

**Block 5: Analytics** (2 tools)
- `get_recommendations` - Data-driven coverage suggestions
- `analyze_destination_risk` - Risk analysis from claims data

**Memory Management** (1 tool)
- `manage_conversation_memory` - Mem0 integration for context

**Current Status:** Block 4 tools are fully implemented and functional. Blocks 1-3, 5 tools have signatures but return "Not implemented" - implementations needed.

## Data Models (Pydantic)

All data models are fully implemented with proper validation in `backend/models/`:

- **Policy Models** (`policy.py`) - PolicyBase, PolicyBenefit, PolicyCondition, PolicyComparison, PolicySearchQuery/Result
- **Document Models** (`document.py`) - DocumentUpload, TravelDataExtraction, TravelDataValidation, ExtractedTravelPlan
- **Quotation Models** (`quotation.py`) - QuotationRequest, QuotationItem, QuotationResponse, QuotationAcceptance
- **Purchase Models** (`purchase.py`) - Payment flow models
- **Claim Models** (`claim.py`) - Analytics and recommendations

## Important Architectural Patterns

### 1. Async-First Design
Use `async`/`await` throughout the codebase. FastAPI, database clients, and HTTP calls are all async.

```python
# All route handlers should be async
@router.get("/policies/{policy_id}")
async def get_policy(policy_id: str, service: PolicyService = Depends()):
    return await service.get_policy(policy_id)
```

### 2. Pydantic for Everything
All data validation uses Pydantic models. Configuration uses Pydantic Settings with environment variables.

```python
# backend/config.py uses Pydantic Settings
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
```

### 3. Dependency Injection
Use FastAPI's dependency injection system for database clients and services.

```python
# backend/dependencies.py defines all dependencies
def get_postgres_client() -> PostgresClient:
    return PostgresClient(settings)
```

### 4. Dual-Layer Intelligence
Always store both normalized taxonomy data AND original policy text:
- **Normalized:** Enables apples-to-apples comparison across policies
- **Original:** Provides accurate source of truth in 16+ languages

### 5. Feature Flags
All 5 blocks have feature flags in `.env` for gradual rollout:
- `ENABLE_BLOCK_1_POLICY_INTELLIGENCE=true`
- `ENABLE_BLOCK_2_FAQ=true`
- `ENABLE_BLOCK_3_DOCUMENT_INTELLIGENCE=true`
- `ENABLE_BLOCK_4_PURCHASE=true`
- `ENABLE_BLOCK_5_ANALYTICS=true`

### 6. Type Safety
Use Python 3.11+ type hints everywhere. MyPy strict mode is enabled.

```python
from typing import Optional, List
async def search_policies(query: str, limit: int = 10) -> List[Policy]:
    ...
```

## Code Organization Conventions

- **Files:** snake_case (e.g., `policy_service.py`)
- **Classes:** PascalCase (e.g., `PolicyService`)
- **Functions:** snake_case (e.g., `get_policy`)
- **Constants:** UPPER_CASE (e.g., `MAX_UPLOAD_SIZE`)
- **Models → Services → API Routers:** Clear separation of concerns
- **Database Clients:** Data access layer abstraction

## Data Assets

### Ready to Load
1. **Taxonomy_Hackathon.json** (`database/supabase/taxonomy/`) - 5,484 lines of normalized policy data
2. **3 Policy PDFs** (`database/policy_wordings/`) - Original policy documents for dual-layer intelligence
3. **Claims_Data_DB.pdf** (`database/neo4j/claims/`) - Proprietary MSIG claims data for Block 5

### Database Schemas
Database schemas are not yet created. Expected tables:
- **Supabase:** policies, benefits, conditions, quotations, purchases, customers, policy_embeddings
- **Neo4j:** Policy, Benefit, Condition, Claim, Destination nodes with relationships

## Implementation Priorities

**✅ Phase 0: Payment Integration (COMPLETE - v0.2.0)**
1. ✅ DynamoDB payment records with GSIs
2. ✅ Stripe checkout session integration
3. ✅ Webhook event processing (completed, failed, expired)
4. ✅ Purchase service orchestration
5. ✅ Payment API endpoints (9 routes)
6. ✅ MCP payment tools (4 tools)
7. ✅ Beautiful success/cancel pages
8. ✅ Local development environment (DynamoDB Local + Admin UI)

**Phase 1: Database Foundation (TODO)**
1. Create Postgres schema and load Taxonomy_Hackathon.json
2. Define Neo4j graph schema
3. Generate embeddings for vector search

**Phase 2: Core Services (TODO)**
1. Implement policy ingestion and normalization (`backend/services/policy_service.py`)
2. Build vector search service (`backend/services/vector_search_service.py`)
3. Create OCR pipeline (`libs/ocr/` and `backend/services/document_service.py`)
4. Implement quotation engine (`backend/services/quotation_service.py`)

**Phase 3: API & MCP Integration (TODO)**
1. Implement API router handlers for Blocks 1-3, 5
2. Implement MCP tool handlers for Blocks 1-3, 5
3. Connect tools to backend API via `backend_client.py`

**Phase 4: Analytics (TODO)**
1. Implement claims analysis and recommendation system
2. Load claims data into Neo4j

## Key Documentation Files

- **README.md** - Complete architecture overview and project vision
- **ARCHITECTURE_STATUS.md** - Detailed implementation progress (41% complete)
- **GETTING_STARTED.md** - Step-by-step 6-week implementation guide
- **.env.example** - Complete environment template with 122 configuration variables
- **database/supabase/taxonomy/Travel Insurance Product Taxonomy - Documentation.pdf** - Taxonomy documentation

## Common Issues & Solutions

### Environment Setup
- Ensure Python 3.11+ is installed (`python --version`)
- All API keys must be set in `.env` (Anthropic, OpenAI, Supabase, Neo4j, Stripe)
- Neo4j requires APOC plugin (included in docker-compose)

### Database Connections
- Supabase URL format: `https://<project>.supabase.co`
- Neo4j URL format: `bolt://localhost:7687`
- Use connection pooling for production (configured in `backend/config.py`)

### OCR Setup
- Tesseract must be installed on system: `brew install tesseract` (macOS)
- EasyOCR downloads models on first run (~100MB)

### MCP Integration
- MCP server runs separately from FastAPI backend
- Tools communicate with backend via HTTP client
- Test tools individually before integration
