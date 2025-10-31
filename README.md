# Conversational Insurance Ultra

> AI-powered conversational insurance platform transforming how customers discover, compare, and purchase travel insurance through natural language conversations on Claude/ChatGPT.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.108+-green.svg)](https://fastapi.tiangolo.com/)
[![FastMCP](https://img.shields.io/badge/FastMCP-0.1+-orange.svg)](https://github.com/jlowin/fastmcp)

---

## What We're Building

An AI-powered conversational insurance platform with **5 Revolutionary Blocks**:

### 🧠 Block 1: Policy Intelligence Engine
- Dual-layer intelligence: Normalized taxonomy + Original policy text
- Multi-database architecture (Postgres + Neo4j + Vector DB)
- Apples-to-apples policy comparisons
- 16+ language support with standardized terminology

### 💬 Block 2: Conversational FAQ & Recommendations
- Natural language Q&A with intelligent data source switching
- Context-aware conversations with Mem0 memory
- Handles complex multi-turn discussions
- Preserves customer preferences across sessions

### 📄 Block 3: Document Intelligence & Auto-Quotation
**Game Changer:** Upload flight bookings instead of filling forms
- OCR + AI extraction from travel documents
- Automatic data extraction: dates, destinations, travelers, trip value
- Cross-document validation
- Instant personalized quotations
- **Reduces quote time from 20 minutes → 2 minutes**

### 💳 Block 4: Seamless Purchase Execution
- Complete purchase within conversation
- Stripe payment integration
- Automatic policy generation and delivery
- Full conversation continuity

### 📊 Block 5: Data-Driven Recommendations
**MSIG's Competitive Moat:** Leverage proprietary claims data
- Evidence-based coverage suggestions
- Destination risk analysis from actual claims
- Demographic-specific recommendations
- Insights competitors can't match

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
│             (12 Conversational Tools)                       │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │ Block 1  │ Block 2  │ Block 3  │ Block 4  │ Block 5  │  │
│  │ Policy   │   FAQ    │ Document │ Purchase │Analytics │  │
│  │ Intel    │  & QA    │   OCR    │ Payment  │ Recom.   │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/REST
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Backend                            │
│              (Business Logic Layer)                         │
│  ┌─────────────┬─────────────┬──────────────┬───────────┐  │
│  │ API Routers │  Services   │    Models    │Dependencies│ │
│  │   (5 files) │ (13 files)  │  (5 files)   │           │  │
│  └─────────────┴─────────────┴──────────────┴───────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┬────────────┐
        ▼            ▼            ▼            ▼
   ┌────────┐  ┌────────┐  ┌─────────┐  ┌────────┐
   │Supabase│  │ Neo4j  │  │  Mem0   │  │ Stripe │
   │Postgres│  │ Graph  │  │Customer │  │Payment │
   │+Vector │  │   DB   │  │ Memory  │  │        │
   └────────┘  └────────┘  └─────────┘  └────────┘
```

---

## Tech Stack

### Core Framework
- **FastAPI** - High-performance async API framework
- **FastMCP** - Model Context Protocol server for Claude/ChatGPT integration
- **Python 3.11+** - Modern Python with type hints

### Databases
- **Supabase** - Postgres + pgvector for normalized policies and embeddings
- **Neo4j** - Graph database for policy relationships and claims analysis
- **Mem0** - Customer conversation memory and context management

### Document Processing
- **Tesseract OCR** - Open-source text extraction
- **EasyOCR** - Deep learning-based OCR
- **PyPDF** - PDF parsing and manipulation

### AI & ML
- **Anthropic Claude** - Primary LLM for conversations and analysis
- **OpenAI** - Embeddings for semantic search

### Payments
- **Stripe** - Payment processing and subscription management

---

## Project Structure

```
conversational-insurance-ultra/
├── mcp-server/                    # 🎯 FastMCP Server
│   ├── server.py                  # Main MCP entry point (12 tools)
│   ├── tools/                     # Individual MCP tool implementations
│   ├── prompts/                   # Prompt templates
│   └── client/                    # Backend API client
│       └── backend_client.py
│
├── backend/                       # 🔧 FastAPI Backend
│   ├── main.py                    # FastAPI application
│   ├── config.py                  # Pydantic settings
│   ├── dependencies.py            # Dependency injection
│   ├── api/                       # REST API routers (5 routers)
│   │   ├── policies.py            # Block 1: Policy Intelligence
│   │   ├── documents.py           # Block 3: Document upload
│   │   ├── quotations.py          # Block 3: Quote generation
│   │   ├── purchases.py           # Block 4: Payment flow
│   │   └── analytics.py           # Block 5: Recommendations
│   │
│   ├── services/                  # Business logic (13 services)
│   │   ├── policy_ingestion.py
│   │   ├── policy_normalization.py
│   │   ├── policy_comparison.py
│   │   ├── vector_search.py
│   │   ├── qa_engine.py
│   │   ├── document_processor.py
│   │   ├── travel_data_extractor.py
│   │   ├── quotation_generator.py
│   │   ├── purchase_service.py
│   │   ├── stripe_integration.py
│   │   ├── policy_generator.py
│   │   ├── claims_analyzer.py
│   │   └── recommendation_engine.py
│   │
│   ├── models/                    # Pydantic models (5 models)
│   │   ├── policy.py
│   │   ├── document.py
│   │   ├── quotation.py
│   │   ├── purchase.py
│   │   └── claim.py
│   │
│   └── database/                  # Database clients (4 clients)
│       ├── postgres_client.py     # Supabase Postgres
│       ├── neo4j_client.py        # Neo4j graph DB
│       ├── vector_client.py       # pgvector search
│       └── mem0_client.py         # Mem0 memory
│
├── libs/                          # 📚 Shared Libraries
│   ├── ocr/                       # OCR implementations
│   │   ├── tesseract_ocr.py
│   │   ├── easyocr_client.py
│   │   └── ocr_router.py
│   ├── storage/
│   │   └── supabase_storage.py    # Document storage
│   └── utils/
│       ├── logging.py
│       └── validation.py
│
├── database/                      # 🗄️ Database Setup & Data
│   ├── postgres/
│   │   ├── schema.sql             # Table definitions
│   │   └── seed_policies.py       # Load taxonomy JSON
│   ├── neo4j/
│   │   ├── schema.cypher          # Graph schema
│   │   ├── seed_graph.py          # Load claims data
│   │   └── claims/                # Claims data PDFs
│   ├── vector/
│   │   └── init_embeddings.py     # Generate embeddings
│   ├── policy_wordings/           # Source policy PDFs
│   └── supabase/taxonomy/         # Taxonomy JSON + docs
│
├── .env.example                   # Environment template
├── pyproject.toml                 # Project dependencies
├── requirements.txt               # Frozen dependencies
├── docker-compose.yml             # Local development services
└── README.md                      # This file
```

---

## Getting Started

### Prerequisites

- **Python 3.11+** installed
- **UV** package manager (recommended) or pip
- **Accounts & API Keys:**
  - Supabase account (database + storage)
  - Neo4j Aura account (or local Neo4j)
  - Mem0 API key
  - Anthropic API key (Claude)
  - Stripe account (test mode)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/williamhutech/conversational-insurance-ultra.git
   cd conversational-insurance-ultra
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   # Using UV (recommended)
   uv pip install -e .

   # Or using pip
   pip install -e .
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and database credentials
   ```

5. **Set up databases:**
   ```bash
   # Start local services (optional)
   docker-compose up -d neo4j redis

   # Initialize database schemas
   python -m database.postgres.seed_policies
   python -m database.neo4j.seed_graph
   python -m database.vector.init_embeddings
   ```

### Running the Application

**1. Start the FastAPI Backend:**
```bash
uvicorn backend.main:app --reload
```
Backend will be available at `http://localhost:8000`

**2. Start the MCP Server:**
```bash
python -m mcp-server.server
```

**3. Configure Claude Desktop / ChatGPT:**

Add to Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "insurance-ultra": {
      "command": "python",
      "args": ["-m", "mcp-server.server"],
      "cwd": "/path/to/conversational-insurance-ultra"
    }
  }
}
```

**4. Start Conversing!**
Open Claude Desktop and start asking about travel insurance!

---

## API Documentation

Once the backend is running, visit:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## Development

### Project Status

**Current Phase:** Architecture Setup (v0.1.0)

This repository contains the complete architecture scaffolding with:
- ✅ Directory structure
- ✅ Configuration management
- ✅ Database client interfaces
- ✅ Pydantic models
- ✅ FastAPI application skeleton
- ✅ FastMCP server skeleton
- ⏳ Business logic implementations (TODO)
- ⏳ API endpoint implementations (TODO)
- ⏳ Service layer implementations (TODO)

### Next Steps

1. **Implement Database Schemas**
   - Create Postgres tables for policies, quotations, purchases
   - Define Neo4j graph schema for policy relationships
   - Set up pgvector tables for embeddings

2. **Implement Core Services**
   - Policy comparison logic
   - OCR and data extraction
   - Quotation calculation engine
   - Stripe payment integration

3. **Implement MCP Tools**
   - Connect MCP tools to backend API
   - Add error handling and retries
   - Implement streaming responses

4. **Load Data**
   - Parse and load Taxonomy_Hackathon.json
   - Extract data from policy PDFs
   - Generate embeddings for vector search
   - Load claims data into Neo4j

### Running Tests

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=backend --cov=mcp-server
```

### Code Quality

```bash
# Format code
black .

# Lint code
ruff check .

# Type check
mypy backend/ mcp-server/
```

---

## Environment Variables

See `.env.example` for all required environment variables.

Key variables:
- `SUPABASE_URL`, `SUPABASE_KEY` - Supabase connection
- `NEO4J_URI`, `NEO4J_PASSWORD` - Neo4j connection
- `MEM0_API_KEY` - Mem0 customer memory
- `ANTHROPIC_API_KEY` - Claude API
- `STRIPE_SECRET_KEY` - Stripe payments

---

## Contributing

This is currently a private project for MSIG hackathon. Contribution guidelines will be added if open-sourced.

---

## License

Proprietary - MSIG Insurance

---

## Contact

**Project Lead:** William Hu
**Organization:** MSIG Insurance
**Repository:** https://github.com/williamhutech/conversational-insurance-ultra

---

## Acknowledgments

- **FastMCP** by Jlowin for MCP server framework
- **FastAPI** by Tiangolo for the amazing web framework
- **Anthropic** for Claude AI capabilities
- **MSIG Insurance** for claims data and domain expertise
