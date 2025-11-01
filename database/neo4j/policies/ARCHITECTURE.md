# Neo4j Knowledge Graph Generation - Modular Architecture

## Overview

This document describes the modularized architecture for generating an insurance knowledge graph from PDF documents. The original monolithic `neo4j_gen.py` (4891 lines) has been refactored into a clean, maintainable structure.

## Directory Structure

```
database/neo4j/policies/
├── config/                    # YAML configuration files
│   ├── models.yaml            # AI model configurations
│   ├── pipeline.yaml          # Stage orchestration
│   ├── neo4j.yaml            # Database connection settings
│   └── generation.yaml        # Generation parameters
│
├── utils/                     # Shared utilities (100% complete)
│   ├── api_client.py          # OpenAI API client with retry logic
│   ├── response_validator.py # JSON repair and validation
│   ├── embedding_utils.py     # Embedding generation & similarity
│   ├── file_utils.py          # File I/O operations
│   └── neo4j_utils.py         # Neo4j helper functions
│
├── entities/                  # Data models (100% complete)
│   ├── concept_graph.py       # ConceptGraph class
│   └── data_models.py         # All dataclasses (Product, QA, Personality, etc.)
│
├── services/                  # Core services (100% complete)
│   ├── ocr_service.py         # PDF → Markdown → JSON pipeline
│   └── neo4j_service.py       # Neo4j import & management
│
├── agents/                    # Pipeline stage agents (11% complete - 1/9)
│   ├── product_extractor.py   # ✅ Stage 1: Extract product names
│   ├── concept_extractor.py   # Stage 2: Generate seed concepts
│   ├── fact_extractor.py      # Stage 3: Extract policy facts
│   ├── concept_expander.py    # Stage 4: Iterative graph expansion
│   ├── personality_generator.py # Stage 5: Generate customer personas
│   ├── fact_integrator.py     # Stage 6: Integrate facts into graphs
│   ├── concept_distiller.py   # Stage 7a: Single-concept QA generation
│   ├── pair_validator.py      # Stage 7b: Concept-pair QA validation
│   └── qa_converter.py        # Stage 7c: QA collection merging
│
├── pipeline.py                # Main orchestrator
├── pdf_convert/              # Output directory for markdown files
└── neo4j_gen.py              # Original file (preserved for reference)
```

## The 9-Stage Pipeline

### Stage 0: OCR (Pre-processing)
- **Service:** `services/ocr_service.py`
- **Input:** PDFs in `database/policy_wordings/`
- **Output:** JSON files in `raw_text/`
- **What it does:** Converts PDFs to markdown using DeepSeek-OCR, then extracts text to JSON

### Stage 1: Product Extraction
- **Agent:** `agents/product_extractor.py` ✅
- **Input:** JSON files from Stage 0
- **Output:** `extracted_insurance_products.json`
- **What it does:** Identifies insurance product names from OCR text

### Stage 2: Concept Extraction
- **Agent:** `agents/concept_extractor.py`
- **Input:** All text from JSON files
- **Output:** `seed_concepts.json`
- **What it does:** Extracts insurance domain concepts (e.g., "deductible", "premium")

### Stage 3: Fact Extraction
- **Agent:** `agents/fact_extractor.py`
- **Input:** Product dictionary from Stage 1
- **Output:** `seed_facts.json`
- **What it does:** Extracts verifiable facts about each product

### Stage 4: Concept Graph Expansion
- **Agent:** `agents/concept_expander.py`
- **Input:** Seed concepts from Stage 2
- **Output:** `concept_graph_4omini_3_iter.pkl`, `concept_graph_4omini_1_iter.pkl`
- **What it does:** Iteratively expands concept graph with embedding-based deduplication

### Stage 5: Personality Generation
- **Agent:** `agents/personality_generator.py`
- **Input:** Configuration (number of personalities to generate)
- **Output:** `generated_personalities_Insurance.json`
- **What it does:** Generates diverse customer personas for QA generation

### Stage 6: Fact-Graph Integration
- **Agent:** `agents/fact_integrator.py`
- **Input:** Concept graphs + facts from Stages 3 & 4
- **Output:** `*_with_products_and_facts.pkl`
- **What it does:** Connects facts to semantically similar concepts

### Stage 7a: Concept Distillation
- **Agent:** `agents/concept_distiller.py`
- **Input:** Concept graph + personalities
- **Output:** `concept_distillation/` (pickle batches)
- **What it does:** Generates 3 QA pairs per concept using personas

### Stage 7b: Concept-Pair Validation
- **Agent:** `agents/pair_validator.py`
- **Input:** Concept graph edges + personalities
- **Output:** `concept_pair_validation/` (pickle batches)
- **What it does:** Generates QA pairs for important concept relationships

### Stage 7c: QA Collection Conversion
- **Agent:** `agents/qa_converter.py`
- **Input:** Results from Stages 7a & 7b
- **Output:** `final_qa_collection_insurance_example.json`
- **What it does:** Merges, validates, and converts QA collections

### Stage 8: MemOS Assembly
- **Function:** In `pipeline.py`
- **Input:** Concepts + QA collection
- **Output:** `insurance_textual_memory_graph.json`
- **What it does:** Assembles nodes and edges for Neo4j import

### Stage 9: Neo4j Import
- **Service:** `services/neo4j_service.py` ✅
- **Input:** Graph JSON from Stage 8
- **Output:** Populated Neo4j database
- **What it does:** Creates schema, imports nodes/edges, creates indexes

## Configuration System

All hardcoded values are externalized to YAML files:

### `config/models.yaml`
- API URL and key
- Model names for each stage
- Embedding model configuration

### `config/pipeline.yaml`
- Enable/disable stages
- Input/output paths
- Convergence criteria

### `config/neo4j.yaml`
- Connection settings
- Batch sizes
- Schema definitions

### `config/generation.yaml`
- Concurrency settings (max_workers)
- Batch sizes
- Generation parameters

## Key Design Patterns

### 1. Dependency Injection
All agents receive dependencies via constructors:
```python
agent = ProductExtractor(
    api_client=api_client,
    sample_size=config['sample_size']
)
```

### 2. Prompt Template Classes
Each agent has a dedicated prompt class:
```python
class ProductExtractorPrompt:
    @staticmethod
    def get_system_prompt() -> str:
        return "You are an insurance product identification specialist..."

    @staticmethod
    def get_user_prompt(sample_texts: List[str]) -> str:
        # Format prompt with inputs
        return f"Based on these text samples..."
```

### 3. Result Dataclasses
All agent results use typed dataclasses (in `entities/data_models.py`):
```python
@dataclass
class ProductExtractionResult:
    status: str
    file_name: str
    product_names: Optional[List[str]] = None
    error: Optional[str] = None
```

### 4. Batch Processing
Agents process data in configurable batches:
```python
def process_batch(self, items: List, batch_size: int = 20):
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        # Process batch...
```

## Agent Implementation Template

For the remaining agents (2-9), follow this template:

```python
"""
{AgentName} Agent (Stage {N})
{Description of what this agent does}
"""

from typing import Dict, List
from ..utils.api_client import APIClient
from ..utils.response_validator import ResponseValidator
from ..entities.data_models import {RelevantDataclass}


class {AgentName}Prompt:
    """Prompt template for {agent purpose}."""

    @staticmethod
    def get_system_prompt() -> str:
        return "System prompt defining agent role..."

    @staticmethod
    def get_user_prompt(**kwargs) -> str:
        return f"User prompt with {kwargs}..."


class {AgentName}:
    """
    {Detailed description}
    """

    def __init__(self, api_client: APIClient, **config):
        self.api_client = api_client
        self.prompt = {AgentName}Prompt()
        self.validator = ResponseValidator()
        # Store config parameters

    def process_single(self, item: Any) -> {ResultDataclass}:
        """Process a single item."""
        # 1. Create messages
        messages = [
            {"role": "system", "content": self.prompt.get_system_prompt()},
            {"role": "user", "content": self.prompt.get_user_prompt(**item)}
        ]

        # 2. Call API
        result = self.api_client.call_api(messages)

        # 3. Validate response
        if result["status"] == "success":
            validation = self.validator.validate_json_response(
                result["content"],
                expected_keys=["key1", "key2"]
            )
            if validation["is_valid_json"]:
                # Return success result
                return {ResultDataclass}(status="success", ...)

        return {ResultDataclass}(status="error", ...)

    def process_batch(self, items: List, batch_size: int = 20) -> List:
        """Process items in batches with concurrency."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self.process_single, item): item
                      for item in items}

            for future in as_completed(futures):
                result = future.result()
                results.append(result)

        return results
```

## Usage Example

```python
import yaml
from pathlib import Path
from utils.api_client import APIClient
from agents.product_extractor import ProductExtractor

# Load configuration
with open('config/models.yaml') as f:
    models_config = yaml.safe_load(f)

# Initialize API client
api_client = APIClient(
    api_url=models_config['api']['url'],
    api_key=models_config['api']['key'],
    model_name=models_config['models']['insurance_name_extractor']['name']
)

# Initialize agent
agent = ProductExtractor(api_client=api_client)

# Run extraction
products = agent.extract_products_from_directory(
    raw_text_dir=Path("raw_text"),
    output_file=Path("extracted_insurance_products.json")
)

print(f"Extracted {len(products)} products")
```

## Testing Strategy

1. **Unit Tests:** Test each agent independently with mock API responses
2. **Integration Tests:** Test agent chains (e.g., Stage 1 → Stage 2 → Stage 3)
3. **End-to-End Test:** Run full pipeline with small test dataset
4. **Smoke Test:** Verify OCR service with 1 PDF

## Migration Notes

### From Original `neo4j_gen.py`

The original monolithic file has been split as follows:

| Original Code (Lines) | New Location |
|----------------------|--------------|
| 69-139: APIClient | `utils/api_client.py` |
| 143-225: InsuranceProductExtractor | `agents/product_extractor.py` |
| 234-366: Seed concepts generation | `agents/concept_extractor.py` |
| 385-526: Fact extraction | `agents/fact_extractor.py` |
| 542-1390: ConceptGraph | `entities/concept_graph.py` |
| 794-895: ResponseValidator | `utils/response_validator.py` |
| 966-1152: Concept expansion | `agents/concept_expander.py` |
| 1392-1403: load_embedding_model | `utils/embedding_utils.py` |
| 1621-1796: Personality generation | `agents/personality_generator.py` |
| 1824-1980: Fact-graph integration | `agents/fact_integrator.py` |
| 2031-2281: Concept distillation | `agents/concept_distiller.py` |
| 2597-2914: Pair validation | `agents/pair_validator.py` |
| 3188-3601: QA conversion | `agents/qa_converter.py` |
| 4084-4409: MemOS assembly | `pipeline.py` (Stage 8) |
| 4519-4891: Neo4j import | `services/neo4j_service.py` |

### Backward Compatibility

The original `neo4j_gen.py` is preserved for reference. All functionality is maintained in the modular structure.

## Performance Optimizations

1. **Parallel Processing:** ThreadPoolExecutor for concurrent API calls
2. **Batch Operations:** Configurable batch sizes for all operations
3. **Streaming JSON:** ijson for memory-efficient large file processing
4. **Connection Pooling:** HTTP adapter with connection pooling
5. **Embedding Caching:** Pre-computed embeddings stored in ConceptGraph

## Common Issues & Solutions

### Import Errors
```python
# If you get "ModuleNotFoundError"
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
```

### OCR Module Not Found
```python
# Ensure libs/ocr/precise_ocr is in Python path
REPO_ROOT = Path(__file__).resolve().parents[4]
OCR_PATH = REPO_ROOT / "libs" / "ocr" / "precise_ocr"
sys.path.insert(0, str(OCR_PATH))
```

### Neo4j Connection Issues
- Verify URI format: `bolt://localhost:7687`
- Check database name matches configuration
- Ensure Neo4j is running: `docker ps` or system service

## Next Steps

To complete the implementation:

1. **Create Remaining Agents (2-9):** Follow the template above
2. **Create `pipeline.py`:** Orchestrator that runs all 9 stages sequentially
3. **Add `__init__.py` Files:** Make directories proper Python packages
4. **Test OCR Service:** Convert one PDF to validate Stage 0
5. **End-to-End Test:** Run complete pipeline with test data

## Maintenance

- **Configuration Changes:** Edit YAML files, not code
- **Model Updates:** Change model names in `config/models.yaml`
- **Adding Stages:** Create new agent following template, add to `pipeline.py`
- **Performance Tuning:** Adjust batch sizes and concurrency in `config/generation.yaml`
