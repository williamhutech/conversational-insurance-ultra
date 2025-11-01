"""
Stage 2: General Condition Value Extractor
Extracts condition values from raw policy text using LLMs.

Focuses on:
- Coverage boundaries with exact limits, deductibles, and exclusions
- Eligibility criteria defining who is covered and when
- Claim procedures specifying how to access benefits
- Legal obligations containing binding contract terms
"""

import time
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.api_client import APIClient
from utils.response_validator import ResponseValidator
from entities.data_models import ExtractionResult


# ============================================================================
# Part 1: Prompt Template
# ============================================================================

class ConditionExtractorPrompt:
    """Prompt template for general condition value extraction."""

    @staticmethod
    def get_system_prompt() -> str:
        """Define agent role and behavior."""
        return """You are an expert insurance policy analyst specializing in extracting structured data from travel insurance policy documents.

Your task is to extract ALL relevant general conditions from policy text and return them as a JSON list.

**CRITICAL RULES:**
1. Extract ONLY factual information explicitly stated in the provided text
2. Return a JSON list of condition objects
3. Use EXACT product_name provided
4. Use ONLY condition names from the provided reference list
5. Extract original_text verbatim (no paraphrasing)
6. Convert numbers to numeric types (not strings)
7. Set condition_exist to true if condition is mentioned, false if not found in this text

**FOCUS ON:**
✓ Coverage boundaries with exact limits, deductibles, and exclusions
✓ Eligibility criteria defining who is covered and when
✓ Claim procedures specifying how to access benefits
✓ Legal obligations containing binding contract terms

**AVOID:**
✗ Marketing language and promotional text
✗ Dense legal clauses for minor provisions
✗ Regional terminology variations without value
✗ Historical background information

Return ONLY valid JSON list."""

    @staticmethod
    def get_user_prompt(
        condition_names_list: List[str],
        product_name: str,
        raw_text: str
    ) -> str:
        """Generate user prompt with extraction task."""
        conditions_str = ', '.join(f'"{c}"' for c in condition_names_list[:20])  # Show first 20
        total = len(condition_names_list)

        return f"""**EXTRACTION TASK**

**Product Name:** {product_name}
**Reference Condition Names ({total} total):** [{conditions_str}...]

**Policy Text:**
```
{raw_text}
```

**Required JSON Format:**
```json
[
  {{
    "condition": "condition_name_from_list",
    "condition_type": "eligibility",
    "products": {{
      "{product_name}": {{
        "condition_exist": true,
        "original_text": "verbatim text from policy",
        "parameters": {{
          "key1": "value1",
          "key2": 123
        }}
      }}
    }}
  }},
  {{
    "condition": "another_condition_name",
    "condition_type": "exclusion",
    "products": {{
      "{product_name}": {{
        "condition_exist": true,
        "original_text": "verbatim text",
        "parameters": {{}}
      }}
    }}
  }}
]
```

**INSTRUCTIONS:**
1. Review ALL condition names in the reference list
2. For each condition found in the policy text, create a JSON object
3. Use EXACT condition names from the reference list
4. Determine condition_type: "eligibility" or "exclusion"
5. Extract original_text verbatim and all relevant parameters
6. Only include conditions actually found in this text (condition_exist=true)
7. Use numeric types for numbers

Return ONLY a JSON list (even if empty [])."""


# ============================================================================
# Part 2: Core Extractor Agent
# ============================================================================

class ConditionExtractor:
    """Extracts all conditions from policy text in one call."""

    def __init__(self, api_client: APIClient, condition_names: List[str]):
        """
        Initialize condition extractor.

        Args:
            api_client: API client for LLM calls
            condition_names: List of valid condition names from Stage 1
        """
        self.api_client = api_client
        self.condition_names = condition_names
        self.prompt = ConditionExtractorPrompt()

    def extract_conditions(
        self,
        product_name: str,
        raw_text: str,
        text_index: int
    ) -> ExtractionResult:
        """
        Extract ALL conditions from raw text in one call.

        Args:
            product_name: Name of the insurance product
            raw_text: Policy text chunk to analyze
            text_index: Index of this text chunk

        Returns:
            ExtractionResult with extracted_data as a list of condition objects
        """
        start_time = time.time()

        try:
            # Build messages with full condition list
            messages = [
                {"role": "system", "content": self.prompt.get_system_prompt()},
                {"role": "user", "content": self.prompt.get_user_prompt(
                    self.condition_names, product_name, raw_text
                )}
            ]

            # Call API
            api_result = self.api_client.call_api(messages, timeout=300)

            if api_result["status"] != "success":
                return ExtractionResult(
                    status="api_error",
                    layer_name="general_conditions",
                    product_name=product_name,
                    text_index=text_index,
                    raw_text=raw_text,
                    error_details=api_result.get("error", "Unknown API error"),
                    processing_time=time.time() - start_time
                )

            # Validate JSON response - expect a list using ResponseValidator
            json_validation = ResponseValidator.extract_json_array(api_result["content"])

            if not json_validation["is_valid_json"]:
                return ExtractionResult(
                    status="json_error",
                    layer_name="general_conditions",
                    product_name=product_name,
                    text_index=text_index,
                    raw_text=raw_text,
                    response=api_result["content"],
                    error_details=f"JSON validation failed: {json_validation['error_type']}",
                    processing_time=time.time() - start_time
                )

            parsed = json_validation["parsed_json"]

            # Validate each condition in the list has required keys
            for idx, item in enumerate(parsed):
                if not isinstance(item, dict):
                    return ExtractionResult(
                        status="json_error",
                        layer_name="general_conditions",
                        product_name=product_name,
                        text_index=text_index,
                        raw_text=raw_text,
                        response=api_result["content"],
                        error_details=f"List item {idx} is not a dict",
                        processing_time=time.time() - start_time
                    )

                # Check required keys
                required_keys = ["condition", "condition_type", "products"]
                missing = [k for k in required_keys if k not in item]
                if missing:
                    return ExtractionResult(
                        status="json_error",
                        layer_name="general_conditions",
                        product_name=product_name,
                        text_index=text_index,
                        raw_text=raw_text,
                        response=api_result["content"],
                        error_details=f"Item {idx} missing keys: {missing}",
                        processing_time=time.time() - start_time
                    )

                # Validate condition name is in reference list
                if item["condition"] not in self.condition_names:
                    return ExtractionResult(
                        status="json_error",
                        layer_name="general_conditions",
                        product_name=product_name,
                        text_index=text_index,
                        raw_text=raw_text,
                        response=api_result["content"],
                        error_details=f"Condition '{item['condition']}' not in reference list",
                        processing_time=time.time() - start_time
                    )

            # Success - return list
            return ExtractionResult(
                status="success",
                layer_name="general_conditions",
                product_name=product_name,
                text_index=text_index,
                raw_text=raw_text,
                extracted_data=parsed,  # This is a list of condition objects
                response=api_result["content"],
                processing_time=time.time() - start_time
            )

        except Exception as e:
            return ExtractionResult(
                status="exception",
                layer_name="general_conditions",
                product_name=product_name,
                text_index=text_index,
                raw_text=raw_text,
                error_details=f"Exception: {str(e)}",
                processing_time=time.time() - start_time
            )


# ============================================================================
# Part 3: Batch Processor
# ============================================================================

class BatchConditionExtractor:
    """Parallel batch processor for extracting all conditions from text chunks."""

    def __init__(
        self,
        extractor: ConditionExtractor,
        output_dir: Path
    ):
        """
        Initialize batch processor.

        Args:
            extractor: ConditionExtractor instance
            output_dir: Directory for saving batch results
        """
        self.extractor = extractor
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_from_product_dict(
        self,
        product_dict: Dict[str, List[str]],
        max_workers: int = 100,
        batch_size: int = 50
    ) -> Dict[str, ExtractionResult]:
        """
        Extract ALL conditions from all product texts.

        Args:
            product_dict: Dict mapping product_name -> list of raw_text chunks
            max_workers: Maximum parallel workers
            batch_size: Number of items per batch

        Returns:
            Dictionary mapping result_id -> ExtractionResult (with list of conditions)
        """
        print(f"\n{'=' * 80}")
        print(f"Extracting All General Conditions")
        print(f"{'=' * 80}")

        # Build task list: (product_name, text_index, raw_text)
        tasks = []
        for product_name, text_list in product_dict.items():
            for text_index, raw_text in enumerate(text_list):
                tasks.append((product_name, text_index, raw_text))

        total_tasks = len(tasks)
        print(f"Total text chunks to process: {total_tasks}")
        print(f"Max workers: {max_workers}")
        print(f"Batch size: {batch_size}")

        all_results = {}

        # Process in batches
        for batch_start in range(0, total_tasks, batch_size):
            batch_end = min(batch_start + batch_size, total_tasks)
            batch_tasks = tasks[batch_start:batch_end]
            batch_num = (batch_start // batch_size) + 1
            total_batches = (total_tasks + batch_size - 1) // batch_size

            print(f"\nBatch {batch_num}/{total_batches} ({len(batch_tasks)} items)")

            batch_results = self._process_batch(
                batch_tasks,
                max_workers,
                batch_start
            )

            all_results.update(batch_results)

        return all_results

    def _process_batch(
        self,
        batch_tasks: List[tuple],
        max_workers: int,
        start_idx: int
    ) -> Dict[str, ExtractionResult]:
        """Process a single batch in parallel."""
        batch_results = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_task = {}
            for idx, (product_name, text_index, raw_text) in enumerate(batch_tasks, start_idx):
                future = executor.submit(
                    self.extractor.extract_conditions,  # Extract ALL conditions
                    product_name,
                    raw_text,
                    text_index
                )
                result_id = f"{product_name}_{text_index:04d}"
                future_to_task[future] = result_id

            # Collect results with progress tracking
            completed = 0
            successful = 0
            total_conditions = 0

            for future in as_completed(future_to_task):
                result_id = future_to_task[future]
                result = future.result()
                batch_results[result_id] = result

                if result.status == "success":
                    successful += 1
                    # Count conditions extracted
                    if isinstance(result.extracted_data, list):
                        total_conditions += len(result.extracted_data)

                completed += 1
                if completed % 10 == 0 or completed == len(batch_tasks):
                    print(f"  Progress: {completed}/{len(batch_tasks)} | "
                          f"Success: {successful} | Conditions found: {total_conditions}")

        return batch_results
