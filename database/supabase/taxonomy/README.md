# Taxonomy Extraction Pipeline

A comprehensive 5-stage pipeline for extracting and aggregating travel insurance policy taxonomy data using LLMs.

## Overview

This pipeline systematically extracts structured information from unstructured policy documents and organizes it into a normalized taxonomy format for comparison and analysis.

### Pipeline Stages

```
Stage 1: Key Extraction (No LLM)
  ↓ Extracts unique condition/benefit keys from schema

Stage 2: Value Extraction & Validation (LLM: gpt-4.1 + gpt-4o)
  ↓ Extractor-Judger pillars extract and validate values

Stage 3: Product Aggregation (No LLM)
  ↓ Merges same condition/benefit across products

Stage 4: Parameter Standardization (LLM: gpt-4.1)
  ↓ Normalizes parameters for cross-product comparison

Stage 5: Final Assembly (No LLM)
  ↓ Merges all layers into final taxonomy
```

## Architecture

### Directory Structure

```
taxonomy/
├── config/                          # YAML configurations
│   ├── models.yaml                  # 9 AI agents (gpt-4.1, gpt-4o)
│   ├── pipeline.yaml                # 5-stage orchestration
│   └── generation.yaml              # Concurrency (max_workers=100)
│
├── agents/                          # Processing agents
│   ├── stage1_key_extractor.py      # ✅ COMPLETE
│   ├── stage2_condition_extractor.py     # ✅ COMPLETE
│   ├── stage2_condition_judger.py        # ✅ COMPLETE
│   ├── stage2_benefit_extractor.py       # ✅ COMPLETE
│   ├── stage2_benefit_judger.py          # ⏳ TODO
│   ├── stage2_benefit_condition_extractor.py  # ⏳ TODO
│   ├── stage2_benefit_condition_judger.py     # ⏳ TODO
│   ├── stage2_json_validators.py    # ✅ COMPLETE
│   ├── stage3_aggregator.py         # ✅ COMPLETE
│   ├── stage4_condition_standardizer.py      # ⏳ TODO
│   ├── stage4_benefit_standardizer.py        # ⏳ TODO
│   ├── stage4_benefit_condition_standardizer.py  # ⏳ TODO
│   └── stage5_final_assembler.py    # ✅ COMPLETE
│
├── entities/                        # Data models
│   ├── data_models.py               # ✅ 12 dataclasses
│   └── __init__.py
│
├── utils/                           # Shared utilities (symlinked)
│   ├── api_client.py                # API calls with retry
│   ├── response_validator.py       # JSON validation
│   ├── file_utils.py                # I/O operations
│   └── embedding_utils.py
│
├── pipeline.py                      # ✅ Main orchestrator
├── data_schema/
│   └── Taxonomy_Hackathon.json      # Template schema
├── raw_text/
│   └── product_dict.pkl             # Input: {product: [texts]}
└── output/                          # All stage outputs
```

### Status: 65% Complete

**✅ Completed (13/19 files):**
- Configuration files (3/3)
- Data models (2/2)
- Stage 1 agent (1/1)
- Stage 2 agents (4/9) - Condition extractor/judger, benefit extractor, validators
- Stage 3 agent (1/1)
- Stage 5 agent (1/1)
- Pipeline orchestrator (1/1)

**⏳ Remaining (6/19 files):**
- Stage 2: Benefit judger, benefit-condition extractor/judger (3 agents)
- Stage 4: All standardizers (3 agents)

## Quick Start

### 1. Install Dependencies

```bash
cd database/supabase/taxonomy
pip install -r requirements.txt  # Same as neo4j/policies
```

### 2. Prepare Input Data

Ensure these files exist:
- `data_schema/Taxonomy_Hackathon.json` - Template schema ✅
- `raw_text/product_dict.pkl` - Product text mapping ✅

### 3. Run Pipeline

```bash
# Run full pipeline
python pipeline.py

# Or run individual stages
from pipeline import TaxonomyExtractionPipeline
pipeline = TaxonomyExtractionPipeline()
pipeline.run_stage_1_key_extraction()
```

## Stage Details

### Stage 1: Key Extraction (COMPLETE)

**Purpose:** Extract unique keys from schema template
**Input:** `Taxonomy_Hackathon.json`
**Output:**
- `condition_names.json` - List of condition names
- `benefit_names.json` - List of benefit identifiers
- `benefit_condition.json` - List of (benefit, condition) pairs

**How it works:** Pure Python parsing, no LLMs

### Stage 2: Value Extraction (65% COMPLETE)

**Purpose:** Extract and validate condition/benefit values from policy text
**Input:** `product_dict.pkl` + reference lists from Stage 1
**Agents:**
1. ✅ **ConditionExtractor** (gpt-4.1) - Extracts general condition values
2. ✅ **ConditionJudger** (gpt-4o) - Validates and corrects extractions
3. ✅ **BenefitExtractor** (gpt-4.1) - Extracts benefit values
4. ⏳ **BenefitJudger** (gpt-4o) - Validates benefit extractions
5. ⏳ **BenefitConditionExtractor** (gpt-4.1) - Extracts benefit-specific conditions
6. ⏳ **BenefitConditionJudger** (gpt-4o) - Validates benefit-condition extractions
7. ✅ **JSONValidators** - Programmatic schema validation

**Workflow:** Extractor→Judger "pillar" (sequential on same text)

**Output:**
- `condition_values.json`
- `benefit_values.json`
- `benefit_condition_values.json`

**Key Features:**
- **Parallel Processing:** max_workers=100 (ThreadPoolExecutor)
- **Pillar Pattern:** Extractor and Judger run sequentially on same raw_text
- **Validation:** LLM judgment + programmatic JSON validation
- **Reference Enforcement:** All keys MUST match Stage 1 reference lists

### Stage 3: Product Aggregation (COMPLETE)

**Purpose:** Merge same condition/benefit across different products
**Input:** Stage 2 validated JSONs
**How it works:** Groups by condition/benefit key, merges product data
**Output:**
- `condition_value_aggregated.json`
- `benefit_value_aggregated.json`
- `benefit_value_pair_aggregated.json`

### Stage 4: Parameter Standardization (TODO)

**Purpose:** Normalize parameters for cross-product comparison
**Input:** Stage 3 aggregated JSONs
**Agents:**
1. ⏳ **ConditionStandardizer** (gpt-4.1)
2. ⏳ **BenefitStandardizer** (gpt-4.1)
3. ⏳ **BenefitConditionStandardizer** (gpt-4.1)

**Tasks:**
- Unify parameter key names (e.g., "min_age" and "minimum_age" → "minimum_age")
- Convert numeric strings to numbers
- Handle missing values (set to None)
- Ensure all products have same parameter keys

**Output:**
- `condition_value_aggregated_standardized.json`
- `benefit_value_aggregated_standardized.json`
- `benefit_value_pair_aggregated_standardized.json`

### Stage 5: Final Assembly (COMPLETE)

**Purpose:** Merge all layers into final taxonomy format
**Input:** Stage 4 standardized JSONs
**How it works:** Assembles into Taxonomy_Hackathon.json structure
**Output:** `final_value.json`

## Configuration

### models.yaml - AI Agents

```yaml
models:
  condition_extractor:
    name: "gpt-4.1"
    temperature: 0.1
  condition_judger:
    name: "gpt-4o"
    temperature: 0.0
  # ... (9 agents total)
```

### pipeline.yaml - Stage Control

```yaml
stages:
  stage_1_key_extraction:
    enabled: true
  stage_2_value_extraction:
    enabled: true
  # ... (5 stages)
```

### generation.yaml - Execution Parameters

```yaml
concurrency:
  stage_2_condition_extraction: 100
  stage_2_benefit_extraction: 100
  # ... (max_workers per stage)

batch_sizes:
  condition_extraction: 50
  # ... (batch sizes per task)
```

## Completing the Implementation

### To Complete Stage 2:

1. **Create BenefitJudger** (`stage2_benefit_judger.py`)
   - Copy `stage2_condition_judger.py` structure
   - Update prompts for benefit validation
   - Expected keys: `["benefit_name", "products"]`

2. **Create BenefitConditionExtractor** (`stage2_benefit_condition_extractor.py`)
   - Similar to `stage2_condition_extractor.py`
   - Extract (benefit_name, condition) pairs
   - Expected keys: `["benefit_name", "condition", "condition_type", "products"]`

3. **Create BenefitConditionJudger** (`stage2_benefit_condition_judger.py`)
   - Validate benefit-condition extractions
   - Check both benefit_name and condition against reference lists

### To Complete Stage 4:

1. **Create ConditionStandardizer** (`stage4_condition_standardizer.py`)
   - Prompt: "Normalize parameters across products for this condition"
   - Input: Aggregated condition with multiple products
   - Output: Same structure with unified parameter keys

2. **Create BenefitStandardizer** and **BenefitConditionStandardizer**
   - Similar pattern to ConditionStandardizer
   - Focus on coverage_limit, sub_limits normalization

**Prompt Template for Standardizers:**
```
You are a data normalization expert. Standardize parameters across products:

1. Unify parameter key names (choose most descriptive)
2. Convert numeric strings to numbers
3. For missing parameters, set value to null
4. Ensure all products have the same parameter keys

Input: {aggregated_data}
Output: {standardized_data with unified keys}
```

### Pipeline Orchestrator Updates:

Update `pipeline.py`:

```python
def run_stage_2_value_extraction(self):
    """Full Stage 2 implementation."""
    # Load product_dict.pkl
    product_dict = load_pickle(self.raw_text_dir / "product_dict.pkl")

    # Load reference lists
    condition_names = load_json(self.output_dir / "condition_names.json")
    benefit_names = load_json(self.output_dir / "benefit_names.json")
    benefit_condition_pairs = load_json(self.output_dir / "benefit_condition.json")

    # For each layer:
    # 1. Initialize Extractor + Judger
    # 2. Run extraction + judgment pillar
    # 3. Validate with JSONValidator
    # 4. Save results
```

## Data Models

All dataclasses defined in `entities/data_models.py`:

- **ExtractionResult** - Output from extractor agents
- **JudgmentResult** - Output from judger agents
- **ValidationResult** - Output from JSON validators
- **AggregationResult** - Output from aggregation
- **StandardizationResult** - Output from standardizers
- **FinalTaxonomy** - Final taxonomy structure

## Testing

### Test Individual Stages:

```python
# Stage 1
python agents/stage1_key_extractor.py

# Stage 3 (requires Stage 2 outputs)
python agents/stage3_aggregator.py

# Stage 5 (requires Stage 4 outputs)
python agents/stage5_final_assembler.py
```

### Test Full Pipeline:

```python
python pipeline.py
```

## Key Design Patterns

### 1. 3-Part Agent Pattern

Every LLM agent follows this structure:

```python
# Part 1: Prompt Template
class AgentPrompt:
    @staticmethod
    def get_system_prompt() -> str
    @staticmethod
    def get_user_prompt(...) -> str

# Part 2: Core Agent
class Agent:
    def process_item(self, ...) -> Result

# Part 3: Batch Processor
class BatchAgent:
    def process_batch(self, ..., max_workers) -> Dict[Result]
```

### 2. Extractor-Judger Pillar

Stage 2 uses sequential processing:

```python
for raw_text in texts:
    extraction = extractor.extract(raw_text)  # gpt-4.1
    judgment = judger.judge(extraction, raw_text)  # gpt-4o
    if judgment.approve:
        validated.append(judgment.final_value)
```

### 3. Input Fallback Logic

```python
# Try file first, fallback to memory
if input_file.exists():
    data = load_json(input_file)
else:
    data = self.stage_results.get('stage_X', {})
```

## Prompt Engineering Guidelines

### Extraction Focus (from pipeline.yaml):

**Include:**
- Coverage boundaries with exact limits, deductibles, exclusions
- Eligibility criteria defining who is covered and when
- Claim procedures specifying how to access benefits
- Legal obligations containing binding contract terms

**Exclude:**
- Marketing language and promotional text
- Dense legal clauses for minor provisions
- Regional terminology variations without value
- Historical background information

### Prompt Best Practices:

1. **Be Specific:** Define exact JSON structure in prompt
2. **Enforce References:** Remind agent to use EXACT keys from reference lists
3. **No Paraphrasing:** Emphasize verbatim extraction for original_text
4. **Type Safety:** Specify numbers should be numeric, not strings
5. **Clear Success Criteria:** Define what makes extraction "correct"

## Performance

### Expected Throughput:

- **Stage 1:** < 1 second (pure Python)
- **Stage 2:** ~30-60 min (depends on text volume, max_workers=100)
- **Stage 3:** < 10 seconds (pure Python)
- **Stage 4:** ~10-20 min (LLM standardization)
- **Stage 5:** < 5 seconds (pure Python)

### Optimization Tips:

1. Increase `max_workers` for faster parallel processing
2. Use larger `batch_size` to reduce overhead
3. Enable batch result saving for long-running stages
4. Monitor API rate limits (adjust batch_delays if needed)

## Troubleshooting

### Common Issues:

1. **ImportError:** Ensure utils symlink is created correctly
2. **API Key Error:** Check models.yaml has valid OpenAI key
3. **JSON Validation Fails:** Check expected_keys in ResponseValidator
4. **Rate Limiting:** Reduce max_workers or increase batch_delays

### Debug Mode:

Enable verbose logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

When adding new agents:

1. Follow 3-part pattern (Prompt + Core + Batch)
2. Use dataclasses from `entities/data_models.py`
3. Add configuration to `models.yaml` and `pipeline.yaml`
4. Update this README

## References

- **Architecture Pattern:** `database/neo4j/policies/`
- **Taxonomy Documentation:** `data_schema/Travel Insurance Product Taxonomy - Documentation.pdf`
- **Project Overview:** `CLAUDE.md` (root)

---

**Status:** Ready for completion of remaining 6 agents (Stage 2 & 4)
**Next Steps:** Implement missing judgers and standardizers following established patterns
