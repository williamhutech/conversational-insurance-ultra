"""
Stage 4: Benefit-Specific Condition Parameter Standardizer
Normalizes benefit-specific condition parameters across products for cross-product comparison using LLMs.
"""

import time
import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.api_client import APIClient
from utils.response_validator import ResponseValidator
from entities.data_models import StandardizationResult


class BenefitConditionStandardizerPrompt:
    """Prompt template for benefit-condition parameter standardization."""

    @staticmethod
    def get_system_prompt() -> str:
        return """You are an expert parameter standardizer. Your task: unify and normalize benefit-specific condition parameters across products.

**INPUT FORMAT (Benefit-Specific Conditions):**
{
  "benefit_name": "parent_benefit",
  "condition": "specific_condition_name",
  "condition_type": "benefit_eligibility | benefit_exclusion",
  "parameters": [],  // condition-level parameters
  "products": {
    "product_name": {
      "condition_exist": true/false,
      "original_text": "extracted policy wording",
      "parameters": {
        "time_limit": "90 days",
        "minimum_amount": "$500"
        // other specific parameters
      }
    }
  }
}

**STANDARDIZATION PROCESS:**
1. **Analyze all products** - Identify all parameter patterns (time limits, amounts, requirements)
2. **Extract missing parameters** - If original_text contains values not in parameters, extract them
3. **Unify key names** - Standardize naming (e.g., "notice_days"/"minimum_notice" → "notice_period_days")
4. **Normalize values** - Convert to appropriate types, standardize units (days, amounts, etc.)
5. **Ensure completeness** - All products have identical parameter keys (use null for missing)

**ADVANCED CAPABILITIES:**
- CREATE new parameters from original_text if requirements mentioned but not parameterized
- EXTRACT time periods, amounts, percentages from policy text
- STANDARDIZE units (e.g., "14 days"/"2 weeks" → {"days": 14, "weeks": 2})
- UNIFY amount naming (e.g., "min_claim"/"minimum_amount" → "minimum_claim_amount")

**PRESERVE UNCHANGED:** benefit_name, condition, condition_type, condition-level parameters, condition_exist, original_text

**EXAMPLE:**
Input: {"benefit_name": "trip_cancellation", "condition": "notice_period", "condition_type": "benefit_eligibility", "parameters": [], "products": {"A": {"condition_exist": true, "original_text": "Notify 14 days in advance, min claim $500", "parameters": {"notice_days": "14"}}, "B": {"condition_exist": true, "original_text": "Minimum 7 days notice, claim above $1000", "parameters": {"minimum_notice": 7, "min_claim": 1000}}}}

Output: {"benefit_name": "trip_cancellation", "condition": "notice_period", "condition_type": "benefit_eligibility", "parameters": [], "products": {"A": {"condition_exist": true, "original_text": "Notify 14 days in advance, min claim $500", "parameters": {"notice_period_days": 14, "minimum_claim_amount": 500}}, "B": {"condition_exist": true, "original_text": "Minimum 7 days notice, claim above $1000", "parameters": {"notice_period_days": 7, "minimum_claim_amount": 1000}}}}

Return ONLY valid JSON with complete structure."""

    @staticmethod
    def get_user_prompt(aggregated_benefit_condition: Dict[str, Any]) -> str:
        bc_json = json.dumps(aggregated_benefit_condition, indent=2, ensure_ascii=False)
        return f"""Standardize this benefit-condition across all products:

```json
{bc_json}
```

**Required actions:**
1. Extract ALL parameters from original_text (time limits, amounts, requirements not yet captured)
2. Unify parameter key names across products (choose most descriptive, e.g., "notice_period_days")
3. Convert strings to appropriate types (numbers for amounts/days, etc.)
4. Ensure ALL products have identical parameter keys (null for missing)

**Key principle:** The original_text is the source of truth. Extract all requirements and conditions mentioned.

Return complete standardized JSON."""


class BenefitConditionStandardizer:
    """Single-item benefit-condition parameter standardizer."""

    def __init__(self, api_client: APIClient):
        self.api_client = api_client
        self.prompt = BenefitConditionStandardizerPrompt()

    def standardize_benefit_condition(
        self,
        aggregated_bc: Dict[str, Any],
        bc_id: str
    ) -> StandardizationResult:
        start_time = time.time()

        try:
            messages = [
                {"role": "system", "content": self.prompt.get_system_prompt()},
                {"role": "user", "content": self.prompt.get_user_prompt(aggregated_bc)}
            ]

            api_result = self.api_client.call_api(messages, timeout=300)

            if api_result["status"] != "success":
                return StandardizationResult(
                    status="api_error",
                    layer_name="benefit_specific_conditions",
                    key_identifier=bc_id,
                    original_data=aggregated_bc,
                    error_details=api_result.get("error", "Unknown API error"),
                    processing_time=time.time() - start_time
                )

            validation = ResponseValidator.validate_json_response(
                api_result["content"],
                expected_keys=["benefit_name", "condition", "condition_type", "parameters", "products"]
            )

            if not validation["is_valid_json"]:
                return StandardizationResult(
                    status="json_error",
                    layer_name="benefit_specific_conditions",
                    key_identifier=bc_id,
                    original_data=aggregated_bc,
                    response=api_result["content"],
                    error_details=f"Invalid JSON: {validation.get('error_type', 'Unknown')}",
                    processing_time=time.time() - start_time
                )

            return StandardizationResult(
                status="success",
                layer_name="benefit_specific_conditions",
                key_identifier=bc_id,
                standardized_data=validation["parsed_json"],
                original_data=aggregated_bc,
                response=api_result["content"],
                json_validation=validation,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            return StandardizationResult(
                status="exception",
                layer_name="benefit_specific_conditions",
                key_identifier=bc_id,
                original_data=aggregated_bc,
                error_details=f"Exception: {str(e)}",
                processing_time=time.time() - start_time
            )


class BatchBenefitConditionStandardizer:
    """Parallel batch processor for benefit-condition standardization."""

    def __init__(self, standardizer: BenefitConditionStandardizer, output_dir: Path):
        self.standardizer = standardizer
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def standardize_all_benefit_conditions(
        self,
        aggregated_bcs: List[Dict[str, Any]],
        max_workers: int = 100,
        batch_size: int = 20
    ) -> List[Dict[str, Any]]:
        print(f"\n{'=' * 80}")
        print(f"Standardizing Benefit-Specific Conditions")
        print(f"{'=' * 80}")
        print(f"Total benefit-conditions: {len(aggregated_bcs)}")

        all_standardized = []

        for batch_start in range(0, len(aggregated_bcs), batch_size):
            batch_end = min(batch_start + batch_size, len(aggregated_bcs))
            batch_bcs = aggregated_bcs[batch_start:batch_end]
            batch_num = (batch_start // batch_size) + 1

            print(f"\nBatch {batch_num} ({len(batch_bcs)} items)")

            batch_results = self._process_batch(batch_bcs, max_workers, batch_start)
            all_standardized.extend(batch_results)

        return all_standardized

    def _process_batch(
        self,
        batch_bcs: List[Dict[str, Any]],
        max_workers: int,
        start_idx: int
    ) -> List[Dict[str, Any]]:
        batch_results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {}
            for idx, bc in enumerate(batch_bcs, start_idx):
                bc_id = f"{bc.get('benefit_name', 'unknown')}_{bc.get('condition', 'unknown')}"
                future = executor.submit(
                    self.standardizer.standardize_benefit_condition,
                    bc,
                    bc_id
                )
                future_to_idx[future] = idx

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
                    results_dict[idx] = result.original_data
                    print(f"  Warning: Failed to standardize {result.key_identifier}")

                completed += 1
                if completed % 10 == 0 or completed == len(batch_bcs):
                    print(f"  Progress: {completed}/{len(batch_bcs)} | Success: {successful}")

            for idx in sorted(results_dict.keys()):
                batch_results.append(results_dict[idx])

        return batch_results
