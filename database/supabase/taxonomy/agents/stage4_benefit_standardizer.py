"""
Stage 4: Benefit Parameter Standardizer
Normalizes benefit parameters (coverage_limit, sub_limits) across products for cross-product comparison using LLMs.
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


class BenefitStandardizerPrompt:
    """Prompt template for benefit parameter standardization."""

    @staticmethod
    def get_system_prompt() -> str:
        return """You are an expert parameter standardizer. Your task: unify and normalize benefit parameters across products.

**INPUT FORMAT (Benefits):**
{
  "benefit_name": "benefit_identifier",
  "parameters": [],  // benefit-level parameters if applicable
  "products": {
    "product_name": {
      "benefit_exist": true/false,
      "parameters": {
        "coverage_limit": "amount",
        "sub_limits": {}
      }
    }
  }
}

**STANDARDIZATION PROCESS:**
1. **Analyze all products** - Identify coverage patterns and sub-limit structures
2. **Extract missing parameters** - If benefit details exist but aren't parameterized, extract them
3. **Unify coverage limits** - Standardize "limit"/"max_coverage"/"coverage" → "coverage_limit"
4. **Normalize sub_limits** - Ensure consistent sub-limit key names across products
5. **Ensure completeness** - All products have "coverage_limit" and "sub_limits" (null/{} if missing)

**ADVANCED CAPABILITIES:**
- CREATE sub_limits from text if specific limits mentioned (e.g., "outpatient $5000" → {"outpatient": 5000})
- STANDARDIZE currency amounts to numbers (e.g., "$500,000" → 500000)
- UNIFY sub-limit naming (e.g., "out_patient"/"outpatient care" → "outpatient")

**PRESERVE UNCHANGED:** benefit_name, benefit-level parameters, benefit_exist

**EXAMPLE:**
Input: {"benefit_name": "overseas_medical", "parameters": ["coverage_limit"], "products": {"A": {"benefit_exist": true, "parameters": {"limit": "$500,000", "outpatient": "5000"}}, "B": {"benefit_exist": true, "parameters": {"max_coverage": 1000000, "sub_limit_outpatient_care": 10000}}}}

Output: {"benefit_name": "overseas_medical", "parameters": ["coverage_limit"], "products": {"A": {"benefit_exist": true, "parameters": {"coverage_limit": 500000, "sub_limits": {"outpatient": 5000}}}, "B": {"benefit_exist": true, "parameters": {"coverage_limit": 1000000, "sub_limits": {"outpatient": 10000}}}}}

Return ONLY valid JSON with complete structure."""

    @staticmethod
    def get_user_prompt(aggregated_benefit: Dict[str, Any]) -> str:
        benefit_json = json.dumps(aggregated_benefit, indent=2, ensure_ascii=False)
        return f"""Standardize this benefit across all products:

```json
{benefit_json}
```

**Required actions:**
1. Unify coverage limit naming → "coverage_limit" (convert currency strings to numbers)
2. Structure all sub-limits under "sub_limits" object with consistent key names
3. Extract any missing coverage/limit details from available data

**Key principle:** Maintain benefit structure while ensuring cross-product parameter consistency.

Return complete standardized JSON."""


class BenefitStandardizer:
    """Single-item benefit parameter standardizer."""

    def __init__(self, api_client: APIClient):
        self.api_client = api_client
        self.prompt = BenefitStandardizerPrompt()

    def standardize_benefit(
        self,
        aggregated_benefit: Dict[str, Any],
        benefit_id: str
    ) -> StandardizationResult:
        start_time = time.time()

        try:
            messages = [
                {"role": "system", "content": self.prompt.get_system_prompt()},
                {"role": "user", "content": self.prompt.get_user_prompt(aggregated_benefit)}
            ]

            api_result = self.api_client.call_api(messages, timeout=300)

            if api_result["status"] != "success":
                return StandardizationResult(
                    status="api_error",
                    layer_name="benefits",
                    key_identifier=benefit_id,
                    original_data=aggregated_benefit,
                    error_details=api_result.get("error", "Unknown API error"),
                    processing_time=time.time() - start_time
                )

            validation = ResponseValidator.validate_json_response(
                api_result["content"],
                expected_keys=["benefit_name", "parameters", "products"]
            )

            if not validation["is_valid_json"]:
                return StandardizationResult(
                    status="json_error",
                    layer_name="benefits",
                    key_identifier=benefit_id,
                    original_data=aggregated_benefit,
                    response=api_result["content"],
                    error_details=f"Invalid JSON: {validation.get('error_type', 'Unknown')}",
                    processing_time=time.time() - start_time
                )

            return StandardizationResult(
                status="success",
                layer_name="benefits",
                key_identifier=benefit_id,
                standardized_data=validation["parsed_json"],
                original_data=aggregated_benefit,
                response=api_result["content"],
                json_validation=validation,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            return StandardizationResult(
                status="exception",
                layer_name="benefits",
                key_identifier=benefit_id,
                original_data=aggregated_benefit,
                error_details=f"Exception: {str(e)}",
                processing_time=time.time() - start_time
            )


class BatchBenefitStandardizer:
    """Parallel batch processor for benefit standardization."""

    def __init__(self, standardizer: BenefitStandardizer, output_dir: Path):
        self.standardizer = standardizer
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def standardize_all_benefits(
        self,
        aggregated_benefits: List[Dict[str, Any]],
        max_workers: int = 100,
        batch_size: int = 20
    ) -> List[Dict[str, Any]]:
        print(f"\n{'=' * 80}")
        print(f"Standardizing Benefits")
        print(f"{'=' * 80}")
        print(f"Total benefits: {len(aggregated_benefits)}")

        all_standardized = []

        for batch_start in range(0, len(aggregated_benefits), batch_size):
            batch_end = min(batch_start + batch_size, len(aggregated_benefits))
            batch_benefits = aggregated_benefits[batch_start:batch_end]
            batch_num = (batch_start // batch_size) + 1

            print(f"\nBatch {batch_num} ({len(batch_benefits)} items)")

            batch_results = self._process_batch(batch_benefits, max_workers, batch_start)
            all_standardized.extend(batch_results)

        return all_standardized

    def _process_batch(
        self,
        batch_benefits: List[Dict[str, Any]],
        max_workers: int,
        start_idx: int
    ) -> List[Dict[str, Any]]:
        batch_results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {}
            for idx, benefit in enumerate(batch_benefits, start_idx):
                benefit_id = benefit.get("benefit_name", f"unknown_{idx}")
                future = executor.submit(
                    self.standardizer.standardize_benefit,
                    benefit,
                    benefit_id
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
                    print(f"  Warning: Failed to standardize benefit {result.key_identifier}")

                completed += 1
                if completed % 10 == 0 or completed == len(batch_benefits):
                    print(f"  Progress: {completed}/{len(batch_benefits)} | Success: {successful}")

            for idx in sorted(results_dict.keys()):
                batch_results.append(results_dict[idx])

        return batch_results
