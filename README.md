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
- **DynamoDB** - Payment records and transaction history
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
│   │
│   ├── routers/                   # REST API routers
│   │   ├── block_4_purchase.py    # ✅ Block 4: Payment & Purchase
│   │   └── ...                    # (Other blocks TODO)
│   │
│   ├── services/                  # Business logic
│   │   ├── purchase_service.py    # ✅ Purchase orchestration
│   │   ├── stripe_integration.py  # ✅ Stripe API integration
│   │   ├── payment/               # ✅ Payment sub-services
│   │   │   ├── stripe_webhook.py  # Webhook event handler
│   │   │   └── payment_pages.py   # Success/cancel pages
│   │   └── ...                    # (Other services TODO)
│   │
│   ├── models/                    # Pydantic models
│   │   ├── payment.py             # ✅ Payment models
│   │   ├── policy.py
│   │   ├── document.py
│   │   ├── quotation.py
│   │   ├── purchase.py
│   │   └── claim.py
│   │
│   └── database/                  # Database clients
│       ├── dynamodb_client.py     # ✅ DynamoDB payment records
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
│   ├── dynamodb/                  # ✅ DynamoDB setup
│   │   └── init_payments_table.py # Create payments table
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
   # Start local services (Neo4j, Redis, DynamoDB)
   docker-compose up -d

   # Initialize database schemas
   python -m database.dynamodb.init_payments_table  # Create payments table
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

## Payment Integration

### Complete Payment Flow

The platform includes a full-featured payment system powered by Stripe and DynamoDB:

#### Architecture

```
Customer → MCP Tool → Backend API → Stripe Checkout → Payment Success → Policy Generation
                ↓                        ↓
             DynamoDB ← Webhook Handler ←
```

#### Components

1. **DynamoDB Payment Records** (`database/dynamodb/`)
   - Stores payment intent records with status tracking
   - Global Secondary Indexes for efficient queries by user, quote, and session
   - Local development with DynamoDB Local (Docker)

2. **Stripe Integration** (`backend/services/stripe_integration.py`)
   - Creates checkout sessions with 24-hour expiration
   - Manages payment intents and refunds
   - Retrieves payment status and session details

3. **Purchase Service** (`backend/services/purchase_service.py`)
   - Orchestrates complete purchase flow
   - Creates payment records → Stripe checkout → Policy generation
   - Handles payment cancellation and status tracking

4. **Webhook Handler** (`backend/services/payment/stripe_webhook.py`)
   - Listens to Stripe events (completed, failed, expired)
   - Updates DynamoDB payment status automatically
   - Signature verification for security

5. **Payment Pages** (`backend/services/payment/payment_pages.py`)
   - Beautiful success/cancel pages with responsive design
   - Auto-close for popup window flows
   - Session ID tracking for confirmation

6. **API Router** (`backend/routers/block_4_purchase.py`)
   - REST endpoints for payment operations
   - POST `/api/purchase/initiate` - Create payment
   - GET `/api/purchase/payment/{id}` - Check status
   - POST `/api/purchase/complete/{id}` - Generate policy
   - POST `/api/purchase/cancel/{id}` - Cancel payment

7. **MCP Tools** (`mcp-server/server.py`)
   - `initiate_purchase()` - Start payment flow
   - `check_payment_status()` - Poll payment status
   - `complete_purchase()` - Generate policy after payment
   - `cancel_payment()` - Cancel pending payment

### Setting Up Payments

#### 1. Configure Stripe

```bash
# Get your Stripe keys from https://dashboard.stripe.com/test/apikeys
# Add to .env:
STRIPE_SECRET_KEY="sk_test_..."
STRIPE_PUBLISHABLE_KEY="pk_test_..."
STRIPE_WEBHOOK_SECRET="whsec_..."  # From webhook endpoint setup
```

#### 2. Start DynamoDB Local

```bash
# Start DynamoDB and admin UI
docker-compose up -d dynamodb dynamodb-admin

# Create payments table
python -m database.dynamodb.init_payments_table

# View tables at: http://localhost:8010
```

#### 3. Configure Stripe Webhook

1. Go to Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `http://localhost:8000/webhook/stripe`
3. Select events: `checkout.session.completed`, `checkout.session.expired`, `payment_intent.payment_failed`
4. Copy webhook secret to `.env`

For local development, use Stripe CLI:
```bash
stripe listen --forward-to localhost:8000/webhook/stripe
```

#### 4. Test Payment Flow

```python
# In Claude Desktop, use MCP tools:

# 1. Initiate payment
result = await initiate_purchase(
    user_id="user_123",
    quote_id="quote_456",
    amount=15000,  # $150.00 in cents
    currency="SGD",
    product_name="Premium Travel Insurance - 7 Days Asia",
    customer_email="customer@example.com"
)
# Returns: {"checkout_url": "https://checkout.stripe.com/...", ...}

# 2. User completes payment at checkout_url

# 3. Check payment status (webhook updates automatically)
status = await check_payment_status(result['payment_intent_id'])
# Returns: {"payment_status": "completed", ...}

# 4. Generate policy
policy = await complete_purchase(result['payment_intent_id'])
# Returns: {"policy_id": "pol_abc123", "policy_number": "POL-2025-...", ...}
```

### Payment Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/purchase/initiate` | POST | Create payment and Stripe checkout session |
| `/api/purchase/payment/{id}` | GET | Get payment status and details |
| `/api/purchase/complete/{id}` | POST | Complete purchase and generate policy |
| `/api/purchase/cancel/{id}` | POST | Cancel pending payment |
| `/api/purchase/user/{user_id}/payments` | GET | Get user's payment history |
| `/api/purchase/quote/{quote_id}/payment` | GET | Get payment for specific quote |
| `/webhook/stripe` | POST | Stripe webhook event handler |
| `/success` | GET | Payment success page |
| `/cancel` | GET | Payment cancel page |

### Database Schema

**DynamoDB `lea-payments-local` Table:**
```
Primary Key: payment_intent_id (String)

Attributes:
- payment_intent_id: Unique identifier (pi_...)
- user_id: Customer identifier
- quote_id: Quote being purchased
- amount: Amount in cents
- currency: Currency code (SGD, USD)
- product_name: Product description
- payment_status: pending | completed | failed | expired | cancelled
- stripe_session_id: Stripe checkout session ID
- stripe_payment_intent: Stripe PaymentIntent ID
- created_at: ISO timestamp
- updated_at: ISO timestamp
- metadata: Additional data (JSON)
- failure_reason: Error message if failed

Global Secondary Indexes:
- user_id-index: Query payments by user
- quote_id-index: Query payments by quote
- stripe_session_id-index: Query by Stripe session
```

### Security Features

- ✅ Stripe webhook signature verification
- ✅ HTTPS-only in production
- ✅ Payment intent idempotency
- ✅ Session expiration (24 hours)
- ✅ Secure credential management via environment variables

---

## API Documentation

Once the backend is running, visit:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## Development

### Project Status

**Current Phase:** Architecture Setup + Payment Integration (v0.2.0)

This repository contains the complete architecture scaffolding with:
- ✅ Directory structure
- ✅ Configuration management
- ✅ Database client interfaces
- ✅ Pydantic models
- ✅ FastAPI application skeleton
- ✅ FastMCP server skeleton
- ✅ **Block 4: Complete payment integration (NEW)**
  - ✅ DynamoDB payment records
  - ✅ Stripe checkout integration
  - ✅ Webhook handler
  - ✅ Payment pages (success/cancel)
  - ✅ Purchase service orchestration
  - ✅ MCP payment tools
  - ✅ API payment endpoints
- ⏳ Blocks 1-3, 5: Business logic implementations (TODO)

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
