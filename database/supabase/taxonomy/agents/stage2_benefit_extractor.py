"""
Stage 2: Benefit Value Extractor
Extracts benefit values from raw policy text using LLMs.
"""

import time
import sys
from pathlib import Path
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.api_client import APIClient
from utils.response_validator import ResponseValidator
from entities.data_models import ExtractionResult


class BenefitExtractorPrompt:
    """Prompt template for benefit value extraction."""

    @staticmethod
    def get_system_prompt() -> str:
        return """You are an expert insurance policy analyst extracting benefit information from travel insurance policies.

Your task is to extract ALL relevant benefits from policy text and return them as a JSON list.

**CRITICAL RULES:**
1. Extract ONLY factual benefit information from the provided text
2. Return a JSON list of benefit objects
3. Use EXACT product_name provided
4. Use ONLY benefit names from the provided reference list
5. Extract coverage_limit and sub_limits with numeric values
6. Set condition_exist to true if benefit is offered, false if not found in this text

**FOCUS ON:**
✓ Coverage limits and maximum payouts
✓ Sub-limits for specific scenarios
✓ Benefit-level parameters and conditions
✓ Specific inclusions and coverage scope

Return ONLY valid JSON list."""

    @staticmethod
    def get_user_prompt(benefit_names_list: List[str], product_name: str, raw_text: str) -> str:
        benefits_str = ', '.join(f'"{b}"' for b in benefit_names_list[:20])  # Show first 20
        total = len(benefit_names_list)

        return f"""**EXTRACTION TASK**

**Product Name:** {product_name}
**Reference Benefit Names ({total} total):** [{benefits_str}...]

**Policy Text:**
```
{raw_text}
```

**Required JSON Format:**
```json
[
  {{
    "benefit_name": "benefit_name_from_list",
    "parameters": [],
    "products": {{
      "{product_name}": {{
        "condition_exist": true,
        "parameters": {{
          "coverage_limit": 50000,
          "key1": "value1",
          "key2": 123
        }}
      }}
    }}
  }},
  {{
    "benefit_name": "another_benefit_name",
    "parameters": [],
    "products": {{
      "{product_name}": {{
        "condition_exist": true,
        "parameters": {{}}
      }}
    }}
  }}
]
```

**INSTRUCTIONS:**
1. Review ALL benefit names in the reference list
2. For each benefit found in the policy text, create a JSON object
3. Use EXACT benefit names from the reference list
4. Extract coverage_limit, sub_limits, and all relevant parameters
5. Only include benefits actually found in this text (condition_exist=true)
6. Use numeric types for numbers

Return ONLY a JSON list (even if empty [])."""


class BenefitExtractor:
    """Extracts all benefits from policy text in one call."""

    def __init__(self, api_client: APIClient, benefit_names: List[str]):
        self.api_client = api_client
        self.benefit_names = benefit_names
        self.prompt = BenefitExtractorPrompt()

    def extract_benefits(
        self,
        product_name: str,
        raw_text: str,
        text_index: int
    ) -> ExtractionResult:
        """
        Extract ALL benefits from raw text in one call.

        Args:
            product_name: Name of the insurance product
            raw_text: Policy text chunk to analyze
            text_index: Index of this text chunk

        Returns:
            ExtractionResult with extracted_data as a list of benefit objects
        """
        start_time = time.time()

        try:
            # Build messages with full benefit list
            messages = [
                {"role": "system", "content": self.prompt.get_system_prompt()},
                {"role": "user", "content": self.prompt.get_user_prompt(
                    self.benefit_names, product_name, raw_text
                )}
            ]

            # Call API
            api_result = self.api_client.call_api(messages, timeout=300)

            if api_result["status"] != "success":
                return ExtractionResult(
                    status="api_error",
                    layer_name="benefits",
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
                    layer_name="benefits",
                    product_name=product_name,
                    text_index=text_index,
                    raw_text=raw_text,
                    response=api_result["content"],
                    error_details=f"JSON validation failed: {json_validation['error_type']}",
                    processing_time=time.time() - start_time
                )

            parsed = json_validation["parsed_json"]

            # Validate each benefit in the list has required keys
            for idx, item in enumerate(parsed):
                if not isinstance(item, dict):
                    return ExtractionResult(
                        status="json_error",
                        layer_name="benefits",
                        product_name=product_name,
                        text_index=text_index,
                        raw_text=raw_text,
                        response=api_result["content"],
                        error_details=f"List item {idx} is not a dict",
                        processing_time=time.time() - start_time
                    )

                # Check required keys
                required_keys = ["benefit_name", "products"]
                missing = [k for k in required_keys if k not in item]
                if missing:
                    return ExtractionResult(
                        status="json_error",
                        layer_name="benefits",
                        product_name=product_name,
                        text_index=text_index,
                        raw_text=raw_text,
                        response=api_result["content"],
                        error_details=f"Item {idx} missing keys: {missing}",
                        processing_time=time.time() - start_time
                    )

                # Validate benefit name is in reference list
                if item["benefit_name"] not in self.benefit_names:
                    return ExtractionResult(
                        status="json_error",
                        layer_name="benefits",
                        product_name=product_name,
                        text_index=text_index,
                        raw_text=raw_text,
                        response=api_result["content"],
                        error_details=f"Benefit '{item['benefit_name']}' not in reference list",
                        processing_time=time.time() - start_time
                    )

            # Success - return list
            return ExtractionResult(
                status="success",
                layer_name="benefits",
                product_name=product_name,
                text_index=text_index,
                raw_text=raw_text,
                extracted_data=parsed,  # This is a list of benefit objects
                response=api_result["content"],
                processing_time=time.time() - start_time
            )

        except Exception as e:
            return ExtractionResult(
                status="exception",
                layer_name="benefits",
                product_name=product_name,
                text_index=text_index,
                raw_text=raw_text,
                error_details=f"Exception: {str(e)}",
                processing_time=time.time() - start_time
            )


class BatchBenefitExtractor:
    """Parallel batch processor for extracting all benefits from text chunks."""

    def __init__(self, extractor: BenefitExtractor, output_dir: Path):
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
        Extract ALL benefits from all product texts.

        Args:
            product_dict: Dict mapping product_name -> list of raw_text chunks
            max_workers: Maximum parallel workers
            batch_size: Number of items per batch

        Returns:
            Dictionary mapping result_id -> ExtractionResult (with list of benefits)
        """
        print(f"\n{'=' * 80}")
        print(f"Extracting All Benefits")
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
                    self.extractor.extract_benefits,  # Extract ALL benefits
                    product_name,
                    raw_text,
                    text_index
                )
                result_id = f"{product_name}_{text_index:04d}"
                future_to_task[future] = result_id

            # Collect results with progress tracking
            completed = 0
            successful = 0
            total_benefits = 0

            for future in as_completed(future_to_task):
                result_id = future_to_task[future]
                result = future.result()
                batch_results[result_id] = result

                if result.status == "success":
                    successful += 1
                    # Count benefits extracted
                    if isinstance(result.extracted_data, list):
                        total_benefits += len(result.extracted_data)

                completed += 1
                if completed % 10 == 0 or completed == len(batch_tasks):
                    print(f"  Progress: {completed}/{len(batch_tasks)} | "
                          f"Success: {successful} | Benefits found: {total_benefits}")

        return batch_results
