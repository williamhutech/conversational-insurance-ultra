# Conversational Insurance Ultra

> Production-ready AI platform enabling customers to discover, compare, and purchase travel insurance through natural conversations on Claude/ChatGPT—reducing quote time from 20 minutes to 2 minutes.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.108+-green.svg)](https://fastapi.tiangolo.com/)
[![FastMCP](https://img.shields.io/badge/FastMCP-0.1+-orange.svg)](https://github.com/jlowin/fastmcp)
[![Production Ready](https://img.shields.io/badge/status-production%20ready-success.svg)]()

---

<img width="1562" height="898" alt="CleanShot 2025-11-13 at 17 49@2x" src="https://github.com/user-attachments/assets/de4dd6d7-c377-49bd-b5c9-9d416ea1f028" />

## Platform Overview

Conversational Insurance Ultra transforms travel insurance shopping into a seamless AI-powered experience. Built on a sophisticated 3-tier architecture with production-grade integrations, the platform includes:

### 💳 Complete Purchase Flow
**End-to-end payment processing integrated within conversations**
- Stripe checkout with real-time status tracking
- Ancileo insurance API integration for policy generation
- DynamoDB payment records with comprehensive history
- Automated webhook handling for payment events
- Support for multiple currencies and payment methods

### 📄 Document Intelligence & Instant Quotation
**Upload flight bookings instead of filling forms—get quotes in 2 minutes**
- Multi-language OCR (16+ languages) powered by PaddleOCR
- Automatic text extraction from PDFs, images, and documents
- Real-time quotation generation via Ancileo API
- Country code normalization and trip type detection
- Confidence scoring for extracted data

### 🧠 Advanced Policy Search
**Triple-layer search architecture for precise policy information**
- **Concept Search**: Semantic queries on insurance knowledge graph (Neo4j + MemOS)
- **Structured Search**: AI-routed queries across normalized taxonomy (Supabase + vector embeddings)
- **Original Text Search**: Exact legal language from source policy documents (multilingual support)
- OpenAI embeddings for semantic similarity matching

### 📊 Claims Intelligence
**Leverage proprietary claims data for evidence-based recommendations**
- Multi-agent AI system (O3 planning + GPT-4.1 SQL generation)
- Real-time analysis of PostgreSQL claims database
- Actionable insights on destination risks and coverage gaps
- Safety-validated read-only query execution
- Synthesized recommendations based on actual claim patterns

### 💬 Conversation Memory
**Context-aware conversations that remember customer preferences**
- Mem0 Cloud integration for persistent memory
- Semantic search across conversation history
- User-scoped memory isolation
- Multi-turn dialogue support with preference tracking

### 🌐 Platform Capabilities
The platform supports additional features including policy comparison, coverage analysis, FAQ handling, and destination risk assessment through its extensible architecture.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude / ChatGPT                         │
│                  (User Interface Layer)                     │
└────────────────────┬────────────────────────────────────────┘
                     │ MCP Protocol
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastMCP Server                             │
│              (12 Conversational Tools)                      │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │ Payment  │ Document │  Policy  │  Claims  │  Memory  │  │
│  │ & Purchase│   OCR &  │  Search  │  Intel   │Management│  │
│  │ (4 tools)│Quotation │(3 tools) │ (1 tool) │ (1 tool) │  │
│  │    ✅     │(2 tools) │    ✅     │    ✅     │    ✅     │  │
│  │          │    ✅     │          │          │          │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/REST
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Backend                            │
│              (Business Logic Layer)                         │
│  ┌─────────────┬─────────────┬──────────────┬───────────┐  │
│  │ API Routers │  Services   │    Models    │  Database │  │
│  │ (6 routers) │ (7 services)│  (5 models)  │ (5 clients)│ │
│  │24 endpoints │2500+ LOC    │Type-safe     │Production │  │
│  └─────────────┴─────────────┴──────────────┴───────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┬────────────┬────────────┐
        ▼            ▼            ▼            ▼            ▼
   ┌────────┐  ┌────────┐  ┌─────────┐  ┌────────┐  ┌─────────┐
   │Supabase│  │ Neo4j  │  │PostgreSQL│ │DynamoDB│  │  Mem0   │
   │Policies│  │Concept │  │  Claims  │ │Payments│  │ Memory  │
   │+Vector │  │ Graph  │  │   Data   │ │        │  │         │
   └────────┘  └────────┘  └─────────┘  └────────┘  └─────────┘
                                            │
                                            ▼
                                       ┌─────────┐
                                       │ Stripe  │
                                       │ Ancileo │
                                       └─────────┘
```

---

## Technical Specifications

### Production Architecture

**3-Tier System with Production-Grade Components:**
- **Presentation**: Claude/ChatGPT via Model Context Protocol (MCP)
- **Application**: FastAPI async backend with dependency injection
- **Data**: Multi-database strategy with 5 specialized databases

**Code Metrics:**
- 2,500+ lines of production business logic
- 24 REST API endpoints across 6 routers
- 12 MCP conversational tools
- Type-safe Pydantic models throughout
- Comprehensive error handling and retry logic

### Core Technology Stack

**Backend Framework:**
- **FastAPI** - Async API framework with automatic OpenAPI docs
- **FastMCP** - Model Context Protocol server for AI integration
- **Python 3.11+** - Modern type hints and async/await support
- **UV** - High-performance package manager

**AI & Machine Learning:**
- **OpenAI GPT-4.1** - SQL generation and complex reasoning
- **OpenAI O3** - Planning and orchestration
- **OpenAI GPT-4o-mini** - Query routing and classification
- **OpenAI Embeddings** - text-embedding-3-large (3,072 dimensions)
- **MemOS** - TreeTextMemory for knowledge graphs
- **PaddleOCR** - Multi-language document text extraction

**Database Infrastructure:**
- **Supabase (PostgreSQL + pgvector)** - Policy taxonomy and vector search
- **Neo4j Aura** - Insurance concept knowledge graph with MemOS integration
- **PostgreSQL** - Claims data with read-only safety validation
- **DynamoDB** - Payment records with Global Secondary Indexes
- **Mem0 Cloud** - Persistent conversation memory

**Payment & Integration:**
- **Stripe** - Checkout sessions, webhooks, payment intents
- **Ancileo API** - Insurance quotation and policy generation
- **Boto3** - AWS DynamoDB client with connection pooling
- **AsyncPG** - High-performance PostgreSQL async driver
- **HTTPX** - Async HTTP client for external APIs

### Key Architectural Patterns

**Async-First Design:**
All database clients, HTTP calls, and route handlers use async/await for optimal performance and scalability.

**Multi-Agent AI System:**
The claims intelligence feature uses a sophisticated multi-agent architecture where an O3 planning agent coordinates multiple GPT-4.1 SQL generation agents running in parallel.

**LLM-Based Query Routing:**
Semantic routing powered by gpt-4o-mini automatically selects the optimal database and search strategy for each user query.

**Dual-Layer Policy Intelligence:**
Maintains both normalized taxonomy (for apples-to-apples comparison) and original policy text (for legal accuracy) in separate databases.

**Type Safety:**
Pydantic 2.5+ models with strict validation ensure data integrity across all API boundaries and database operations.

---

## Project Structure

```
conversational-insurance-ultra/
├── mcp_server/                    # 🎯 FastMCP Server (12 Conversational Tools)
│   ├── server.py                  # Main MCP entry point
│   ├── client/backend_client.py   # Backend API client
│   └── utils/                     # Utility functions
│
├── backend/                       # 🔧 FastAPI Backend (Business Logic)
│   ├── main.py                    # FastAPI application
│   ├── config.py                  # Configuration (122 env variables)
│   ├── routers/                   # REST API endpoints (24 endpoints)
│   ├── services/                  # Business logic (7 production services)
│   ├── models/                    # Pydantic data models (type-safe)
│   └── database/                  # Database clients (5 databases)
│
├── libs/                          # 📚 Shared Libraries
│   ├── ocr/fast_ocr/              # PaddleOCR implementation
│   └── utils/                     # Common utilities
│
├── database/                      # 🗄️ Database Assets & Setup
│   ├── dynamodb/                  # Payment table initialization
│   ├── supabase/taxonomy/         # Policy taxonomy data
│   ├── neo4j/policies/            # Concept graph data
│   └── policy_wordings/           # Source policy PDFs
│
├── .env.example                   # Environment configuration template
├── pyproject.toml                 # Project dependencies (UV/pip)
├── docker-compose.yml             # Local services (Neo4j, DynamoDB, Redis)
└── README.md                      # Documentation
```

---

## Getting Started

### Prerequisites

**Required:**
- Python 3.11+ installed
- Docker Desktop (for local databases)
- UV package manager (or pip)

**API Keys Required:**
- Supabase (database + storage)
- Neo4j Aura (or use local Docker)
- Mem0 Cloud API key
- OpenAI API key (for embeddings and GPT models)
- Stripe (test mode)
- Ancileo Insurance API

### Quick Start

**1. Clone and Install:**
```bash
git clone https://github.com/williamhutech/conversational-insurance-ultra.git
cd conversational-insurance-ultra

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies (UV recommended)
uv pip install -e .
```

**2. Configure Environment:**
```bash
cp .env.example .env
# Edit .env with your API keys and database credentials
```

**3. Start Services:**
```bash
# Start local databases
docker-compose up -d

# Initialize payment tables
python -m database.dynamodb.init_payments_table

# Start FastAPI backend (http://localhost:8000)
uvicorn backend.main:app --reload
```

**4. Connect to Claude/ChatGPT:**

Add to Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "insurance-ultra": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/path/to/conversational-insurance-ultra"
    }
  }
}
```

Open Claude Desktop and start conversing about travel insurance!


---

## API Documentation

Once the backend is running, explore the interactive API documentation:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### Key API Endpoints

**Purchase & Payment:**
- `POST /api/purchase/initiate` - Create payment and Stripe checkout
- `GET /api/purchase/payment/{id}` - Check payment status
- `POST /api/purchase/complete/{id}` - Complete purchase and generate policy
- `GET /api/purchase/user/{user_id}/payments` - Payment history

**Quotation:**
- `POST /api/quotation/generate` - Generate travel insurance quote

**Policy Search:**
- `POST /api/policy/search/concept` - Search concept knowledge graph
- `POST /api/policy/search/structured` - Search normalized taxonomy
- `POST /api/policy/search/original` - Search original policy text

**Memory:**
- `POST /api/memory/add` - Add conversation memory
- `GET /api/memory/search` - Semantic memory search

---

## Development & Testing

### Environment Configuration

See `.env.example` for all 122+ environment variables. Key configurations:

**Database Connections:**
- `SUPABASE_URL`, `SUPABASE_KEY` - PostgreSQL + vector storage
- `NEO4J_URI`, `NEO4J_PASSWORD` - Concept knowledge graph
- `POSTGRES_CLAIMS_*` - Claims database connection
- `DYNAMODB_ENDPOINT_URL` - Payment records
- `MEM0_API_KEY` - Conversation memory

**AI Services:**
- `OPENAI_API_KEY` - GPT models and embeddings
- `ANTHROPIC_API_KEY` - Claude (optional)

**Payment Integration:**
- `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY` - Payment processing
- `ANCILEO_API_KEY`, `ANCILEO_BASE_URL` - Insurance API

### Code Quality Tools

```bash
# Format code
black .

# Lint
ruff check .

# Type check
mypy backend/ mcp_server/

# Run tests
pytest --cov=backend --cov=mcp_server
```

---

## Security & Production Considerations

**Security Features:**
- Stripe webhook signature verification
- Read-only SQL validation for claims database
- HTTPS-only in production
- Secure credential management via environment variables
- Payment intent idempotency
- User-scoped memory isolation

**Production Readiness:**
- Async-first architecture for scalability
- Connection pooling for all database clients
- Comprehensive error handling with retry logic
- Type-safe Pydantic validation throughout
- Automated webhook handling
- Multi-agent AI with safety validation

---

## Contact & Support

**Organization:** MSIG Insurance
**Repository:** https://github.com/williamhutech/conversational-insurance-ultra

For technical documentation, see:
- [CLAUDE.md](CLAUDE.md) - Development guide for AI assistants
- [API_Documentation.md](API_Documentation.md) - Detailed API reference
- [PAYMENT_SETUP_GUIDE.md](PAYMENT_SETUP_GUIDE.md) - Payment integration guide

---

## Technology Credits

Built with production-grade open-source technologies:
- **FastMCP** - Model Context Protocol framework
- **FastAPI** - High-performance async web framework
- **OpenAI** - GPT models and embeddings
- **Stripe** - Payment processing infrastructure
- **PaddleOCR** - Multi-language OCR engine
