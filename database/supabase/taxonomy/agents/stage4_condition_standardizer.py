"""
Stage 4: General Condition Parameter Standardizer
Normalizes parameters across products for cross-product comparison using LLMs.

Takes aggregated conditions with multiple products and ensures:
- Unified parameter key names
- Numeric values stored as numbers
- All products have the same parameter keys
- Missing values represented as null
"""

import time
import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.api_client import APIClient
from utils.response_validator import ResponseValidator
from entities.data_models import StandardizationResult


# ============================================================================
# Part 1: Prompt Template
# ============================================================================

class ConditionStandardizerPrompt:
    """Prompt template for condition parameter standardization."""

    @staticmethod
    def get_system_prompt() -> str:
        """Define agent role and behavior."""
        return """You are an expert parameter standardizer. Your task: unify and normalize condition parameters across products.

**INPUT FORMAT (General Conditions):**
{
  "condition": "condition_name",
  "condition_type": "eligibility | exclusion",
  "products": {
    "product_name": {
      "condition_exist": true/false,
      "original_text": "extracted policy wording",
      "parameters": {"key": "value"}  // e.g., age limits, time periods
    }
  }
}

**STANDARDIZATION PROCESS:**
1. **Analyze all products** - Identify all parameter concepts across products
2. **Extract missing parameters** - If original_text contains values not in parameters, extract them
3. **Unify key names** - Choose most descriptive name (e.g., "min_age"/"minimum_age" → "minimum_age")
4. **Normalize values** - Convert strings to numbers ("18" → 18), standardize units
5. **Ensure completeness** - All products must have identical parameter keys (use null for missing)

**ADVANCED CAPABILITIES:**
- CREATE new parameters from original_text if details are mentioned but not in parameters
- INFER parameter values from policy text when needed
- STANDARDIZE units (e.g., "3 months", "90 days" → {"months": 3, "days": 90})

**PRESERVE UNCHANGED:** condition, condition_type, condition_exist, original_text

**EXAMPLE:**
Input: {"condition": "age_eligibility", "condition_type": "eligibility", "products": {"A": {"condition_exist": true, "original_text": "Age 18-70, must be Singapore resident", "parameters": {"min_age": "18"}}, "B": {"condition_exist": true, "original_text": "Maximum 75 years old", "parameters": {"maximum_age": 70}}}}

Output: {"condition": "age_eligibility", "condition_type": "eligibility", "products": {"A": {"condition_exist": true, "original_text": "Age 18-70, must be Singapore resident", "parameters": {"minimum_age": 18, "maximum_age": 70, "residency_requirement": "Singapore"}}, "B": {"condition_exist": true, "original_text": "Maximum 75 years old", "parameters": {"minimum_age": null, "maximum_age": 75, "residency_requirement": null}}}}

Return ONLY valid JSON with complete structure."""

    @staticmethod
    def get_user_prompt(aggregated_condition: Dict[str, Any]) -> str:
        """Generate user prompt with standardization task."""
        condition_json = json.dumps(aggregated_condition, indent=2, ensure_ascii=False)

        return f"""Standardize this condition across all products:

```json
{condition_json}
```

**Required actions:**
1. Extract ALL parameters from original_text (including those not yet in parameters)
2. Unify parameter key names across products (choose most descriptive)
3. Convert strings to appropriate types (numbers, booleans, etc.)
4. Ensure ALL products have identical parameter keys (null for missing)

**Key principle:** The original_text is the source of truth. If it mentions parameters not captured, add them.

Return complete standardized JSON."""


# ============================================================================
# Part 2: Core Standardizer Agent
# ============================================================================

class ConditionStandardizer:
    """Single-item condition parameter standardizer."""

    def __init__(self, api_client: APIClient):
        """
        Initialize condition standardizer.

        Args:
            api_client: API client for LLM calls
        """
        self.api_client = api_client
        self.prompt = ConditionStandardizerPrompt()

    def standardize_condition(
        self,
        aggregated_condition: Dict[str, Any],
        condition_id: str
    ) -> StandardizationResult:
        """
        Standardize parameters for an aggregated condition.

        Args:
            aggregated_condition: Aggregated condition with multiple products
            condition_id: Identifier for this condition

        Returns:
            StandardizationResult with standardized data
        """
        start_time = time.time()

        try:
            # Build messages
            messages = [
                {"role": "system", "content": self.prompt.get_system_prompt()},
                {"role": "user", "content": self.prompt.get_user_prompt(aggregated_condition)}
            ]

            # Call API
            api_result = self.api_client.call_api(messages, timeout=300)

            if api_result["status"] != "success":
                return StandardizationResult(
                    status="api_error",
                    layer_name="general_conditions",
                    key_identifier=condition_id,
                    original_data=aggregated_condition,
                    error_details=api_result.get("error", "Unknown API error"),
                    processing_time=time.time() - start_time
                )

            # Validate JSON response
            validation = ResponseValidator.validate_json_response(
                api_result["content"],
                expected_keys=["condition", "condition_type", "products"]
            )

            if not validation["is_valid_json"]:
                return StandardizationResult(
                    status="json_error",
                    layer_name="general_conditions",
                    key_identifier=condition_id,
                    original_data=aggregated_condition,
                    response=api_result["content"],
                    error_details=f"Invalid JSON: {validation.get('error_type', 'Unknown')}",
                    processing_time=time.time() - start_time
                )

            # Success
            return StandardizationResult(
                status="success",
                layer_name="general_conditions",
                key_identifier=condition_id,
                standardized_data=validation["parsed_json"],
                original_data=aggregated_condition,
                response=api_result["content"],
                json_validation=validation,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            return StandardizationResult(
                status="exception",
                layer_name="general_conditions",
                key_identifier=condition_id,
                original_data=aggregated_condition,
                error_details=f"Exception: {str(e)}",
                processing_time=time.time() - start_time
            )


# ============================================================================
# Part 3: Batch Processor
# ============================================================================

class BatchConditionStandardizer:
    """Parallel batch processor for condition standardization."""

    def __init__(
        self,
        standardizer: ConditionStandardizer,
        output_dir: Path
    ):
        """
        Initialize batch processor.

        Args:
            standardizer: ConditionStandardizer instance
            output_dir: Directory for saving batch results
        """
        self.standardizer = standardizer
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def standardize_all_conditions(
        self,
        aggregated_conditions: List[Dict[str, Any]],
        max_workers: int = 100,
        batch_size: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Standardize all aggregated conditions in parallel.

        Args:
            aggregated_conditions: List of aggregated condition dicts
            max_workers: Maximum parallel workers
            batch_size: Number of items per batch

        Returns:
            List of standardized condition dicts
        """
        print(f"\n{'=' * 80}")
        print(f"Standardizing General Conditions")
        print(f"{'=' * 80}")
        print(f"Total conditions: {len(aggregated_conditions)}")
        print(f"Max workers: {max_workers}")
        print(f"Batch size: {batch_size}")

        all_standardized = []

        # Process in batches
        for batch_start in range(0, len(aggregated_conditions), batch_size):
            batch_end = min(batch_start + batch_size, len(aggregated_conditions))
            batch_conditions = aggregated_conditions[batch_start:batch_end]
            batch_num = (batch_start // batch_size) + 1
            total_batches = (len(aggregated_conditions) + batch_size - 1) // batch_size

            print(f"\nBatch {batch_num}/{total_batches} ({len(batch_conditions)} items)")

            batch_results = self._process_batch(
                batch_conditions,
                max_workers,
                batch_start
            )

            all_standardized.extend(batch_results)

        return all_standardized

    def _process_batch(
        self,
        batch_conditions: List[Dict[str, Any]],
        max_workers: int,
        start_idx: int
    ) -> List[Dict[str, Any]]:
        """Process a single batch in parallel."""
        batch_results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_idx = {}
            for idx, condition in enumerate(batch_conditions, start_idx):
                condition_id = condition.get("condition", f"unknown_{idx}")
                future = executor.submit(
                    self.standardizer.standardize_condition,
                    condition,
                    condition_id
                )
                future_to_idx[future] = idx

            # Collect results with progress tracking
            completed = 0
            successful = 0
            results_dict = {}

            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                result = future.result()

                if result.status == "success":
                    results_dict[idx] = result.standardized_data
                    successful += 1
                else:
                    # Keep original if standardization failed
                    results_dict[idx] = result.original_data
                    print(f"  Warning: Failed to standardize condition {result.key_identifier}")

                completed += 1
                if completed % 10 == 0 or completed == len(batch_conditions):
                    print(f"  Progress: {completed}/{len(batch_conditions)} | Success: {successful}")

            # Return results in original order
            for idx in sorted(results_dict.keys()):
                batch_results.append(results_dict[idx])

        return batch_results
