# Supabase Taxonomy Data Loader

**Complete ETL Pipeline for Loading Travel Insurance Taxonomy into Supabase with Dual Vector Embeddings**

## Overview

This module provides a production-ready ETL pipeline that:
- Loads travel insurance taxonomy JSON into Supabase PostgreSQL
- Generates **dual vector embeddings** (normalized + original text) using OpenAI text-embedding-3-large (3072 dims)
- Creates a **read-optimized denormalized schema** for AI Agentic vector search
- Supports 4 AI query types: Comparison, Explanation, Eligibility, Scenario Analysis

## Quick Start

### 1. Environment Setup

```bash
# Required variables
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_KEY="your-service-role-key"
export OPENAI_API_KEY="sk-your-openai-api-key"
```

### 2. Create Database Schema

```bash
# Run schema.sql in Supabase SQL Editor or via psql
psql -h your-project.supabase.co -U postgres -f schema.sql
```

### 3. Run Loader

```bash
python -m database.supabase.taxonomy.utils.loader
```

## Files

- **`schema.sql`** (300 lines) - Complete PostgreSQL schema with vector indexes
- **`config.py`** - Environment configuration management
- **`models.py`** - Pydantic models for type safety
- **`embedding_service.py`** - Dual embedding generation with rate limiting
- **`loader.py`** - Main ETL pipeline orchestrator
- **`__init__.py`** - Module exports

## Database Schema

### Tables (Denormalized for Speed)

```sql
products                     -- 3 products
general_conditions           -- Layer 1: ~150 records
benefits                     -- Layer 2: ~183 records
benefit_conditions           -- Layer 3: ~417 records
```

### Dual Embeddings Per Table

```sql
normalized_embedding vector(3072)  -- For comparison queries
original_embedding vector(3072)    -- For explanation queries
```

### Indexes

- **12 Vector indexes** (IVFFlat for cosine similarity)
- **6 JSONB indexes** (GIN for structured queries)
- **4 Composite B-tree indexes** (for eligibility queries)

## Usage

### Validate Environment

```python
from database.supabase.taxonomy.utils import validate_environment
validate_environment()
```

### Load Data

```python
import asyncio
from database.supabase.taxonomy.utils import TaxonomyLoader, load_config

async def main():
    config = load_config()
    loader = TaxonomyLoader(config)
    stats = await loader.load_taxonomy()
    print(f"✅ Loaded {stats['benefits']} benefits!")

asyncio.run(main())
```

### Query Examples

```sql
-- Comparison: Side-by-side product features
SELECT product_name, benefit_name, coverage_limit
FROM benefits
WHERE benefit_name LIKE '%medical%';

-- Explanation: Vector search on original text
SELECT * FROM explain_coverage(
    (SELECT original_embedding FROM benefits LIMIT 1),
    5
);

-- Eligibility: Rule-based assessment
SELECT * FROM eligibility_view
WHERE condition_name LIKE '%pre_existing%';

-- Scenario: Multi-benefit coverage
SELECT * FROM scenario_view
WHERE benefit_name = 'medical_expenses_overseas';
```

## Performance

- **Loading Time**: 5-10 minutes (rate limited)
- **Query Latency**: 30-200ms depending on query type
- **Cost**: ~$0.04 for OpenAI embeddings (1500 API calls)
- **Storage**: ~18MB for vector data

## Configuration Options

```python
from database.supabase.taxonomy.utils import TaxonomyLoaderConfig

config = TaxonomyLoaderConfig(
    supabase_url="...",
    supabase_service_key="...",
    openai_api_key="...",
    batch_size=10,                    # Records per batch
    openai_rpm_limit=3000,            # Rate limit
    generate_embeddings=True,         # Set False for dry-run
    verbose=True,                     # Detailed logging
)
```

## Troubleshooting

### Import Errors
```python
# Ensure correct Python path
import sys
sys.path.append('/path/to/conversational-finance')
```

### Rate Limiting
```python
# Reduce rate limit if hitting API errors
config = TaxonomyLoaderConfig(openai_rpm_limit=1000)
```

### Database Connection
```bash
# Test Supabase connection
python -c "from supabase import create_client; client = create_client('URL', 'KEY'); print('✓ Connected')"
```

## Cost Breakdown

**OpenAI Embeddings**:
- 750 records × 2 embeddings = 1500 API calls
- ~200 tokens avg per call = 300K tokens
- $0.13/1M tokens = **$0.04 total**

**Supabase Storage**:
- 750 rows × 2 vectors × 3072 dims × 4 bytes = **18MB**
- Free tier: Up to 500MB included

## Next Steps

1. ✅ Schema created and data loaded
2. ⏳ Integrate with FastAPI backend (`backend/services/policy_service.py`)
3. ⏳ Expose via MCP tools (`mcp-server/tools/`)
4. ⏳ Implement query handlers for 4 AI query types
5. ⏳ Load original policy PDFs for dual-layer intelligence

## Support

- Check logs for detailed error messages
- Run `validate_environment()` to verify configuration
- Review Supabase dashboard for schema issues
- Check OpenAI API usage and rate limits

---

**Part of Conversational Finance** - AI-powered insurance platform using Claude/ChatGPT with MCP
