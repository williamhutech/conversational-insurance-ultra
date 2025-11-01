"""
Stage 2: Benefit Value Judger
Validates and corrects benefit extractions from the Extractor agent.

Runs in a pillar with BenefitExtractor - processes the same raw_text sequentially.
"""

import time
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.api_client import APIClient
from utils.response_validator import ResponseValidator
from entities.data_models import ExtractionResult, JudgmentResult


# ============================================================================
# Part 1: Prompt Template
# ============================================================================

class BenefitJudgerPrompt:
    """Prompt template for benefit extraction judgment."""

    @staticmethod
    def get_system_prompt() -> str:
        """Define agent role and behavior."""
        return """You are a senior insurance policy analyst responsible for quality assurance of extracted benefit data.

Your task is to validate benefit extractions LIST and either approve them or provide corrections for EACH ITEM.

**VALIDATION CRITERIA:**
1. **Correctness:** Extracted data accurately reflects the policy text
2. **Relevance:** Information is relevant to the specified benefit
3. **Format:** JSON structure exactly matches requirements
4. **Completeness:** coverage_limit and sub_limits are properly extracted
5. **Precision:** Numeric values stored as numbers (not strings)
6. **Structure:** Parameters follow the benefit schema

**YOUR RESPONSE MUST BE VALID JSON:**
```json
{
  "validations": [
    {
      "item_index": 0,
      "benefit_name": "exact_benefit_name",
      "approve": true,
      "final_value": {
        "benefit_name": "exact_benefit_name",
        "parameters": [],
        "products": {
          "exact_product_name": {
            "condition_exist": true,
            "parameters": {"coverage_limit": "amount", "sub_limits": {}}
          }
        }
      }
    }
  ]
}
```

For each item: If approve=true, final_value MUST be identical to the original extraction.
If approve=false, final_value MUST contain your corrected version."""

    @staticmethod
    def get_user_prompt(
        extracted_data_list: List[Dict[str, Any]],
        product_name: str,
        raw_text: str,
        benefit_names: List[str]
    ) -> str:
        """Generate user prompt for judgment task."""
        import json
        extracted_json = json.dumps(extracted_data_list, indent=2)
        benefits_str = ', '.join(f'"{b}"' for b in benefit_names[:20])
        total = len(benefit_names)

        return f"""**JUDGMENT TASK**

**Product Name:** {product_name}

**Original Policy Text:**
```
{raw_text}
```

**Extracted Data to Validate ({len(extracted_data_list)} items):**
```json
{extracted_json}
```

**Reference Benefit List ({total} total):**
[{benefits_str}...]

**VALIDATION CHECKLIST (for EACH item):**
1. Does the extraction accurately represent benefit information in the policy text?
2. Is the benefit_name EXACTLY from the reference list?
3. Is the product_name EXACTLY "{product_name}"?
4. Is coverage_limit present and properly formatted?
5. Are sub_limits correctly structured?
6. Are numeric values stored as numbers (not strings)?
7. Does the JSON structure match requirements?
8. Is condition_exist correctly set (true if benefit offered, false if not)?

**YOUR RESPONSE:**
Return a JSON object with a "validations" array containing one entry per extracted item:
```json
{{
  "validations": [
    {{
      "item_index": 0,
      "benefit_name": "benefit_name_from_extraction",
      "approve": true,
      "final_value": <original extraction unchanged if approved, corrected version if not>
    }},
    ...
  ]
}}
```

Return ONLY valid JSON, no additional text."""


# ============================================================================
# Part 2: Core Judger Agent
# ============================================================================

class BenefitJudger:
    """Judges list of benefit extractions."""

    def __init__(
        self,
        api_client: APIClient,
        benefit_names: List[str]
    ):
        """
        Initialize benefit judger.

        Args:
            api_client: API client for LLM calls
            benefit_names: List of valid benefit names (reference)
        """
        self.api_client = api_client
        self.benefit_names = benefit_names
        self.prompt = BenefitJudgerPrompt()

    def judge_extractions(
        self,
        extraction_result: ExtractionResult
    ) -> JudgmentResult:
        """
        Judge a list of benefit extraction results.

        Args:
            extraction_result: Result from BenefitExtractor (contains list in extracted_data)

        Returns:
            JudgmentResult with validations list in final_value
        """
        start_time = time.time()

        # If extraction failed, return failure judgment
        if extraction_result.status != "success":
            return JudgmentResult(
                status="error",
                layer_name="benefits",
                product_name=extraction_result.product_name,
                text_index=extraction_result.text_index,
                approve=False,
                error_details=f"Cannot judge failed extraction: {extraction_result.error_details}",
                processing_time=time.time() - start_time
            )

        try:
            # Extract list from extraction_result
            extracted_data_list = extraction_result.extracted_data
            if not isinstance(extracted_data_list, list):
                return JudgmentResult(
                    status="error",
                    layer_name="benefits",
                    product_name=extraction_result.product_name,
                    text_index=extraction_result.text_index,
                    approve=False,
                    error_details="Expected extracted_data to be a list",
                    processing_time=time.time() - start_time
                )

            # Build messages
            messages = [
                {"role": "system", "content": self.prompt.get_system_prompt()},
                {"role": "user", "content": self.prompt.get_user_prompt(
                    extracted_data_list,
                    extraction_result.product_name,
                    extraction_result.raw_text,
                    self.benefit_names
                )}
            ]

            # Call API
            api_result = self.api_client.call_api(messages, timeout=300)

            if api_result["status"] != "success":
                return JudgmentResult(
                    status="api_error",
                    layer_name="benefits",
                    product_name=extraction_result.product_name,
                    text_index=extraction_result.text_index,
                    approve=False,
                    original_extraction=extraction_result.extracted_data,
                    error_details=api_result.get("error", "Unknown API error"),
                    processing_time=time.time() - start_time
                )

            # Validate JSON response - expect "validations" key
            validation = ResponseValidator.validate_json_response(
                api_result["content"],
                expected_keys=["validations"]
            )

            if not validation["is_valid_json"]:
                return JudgmentResult(
                    status="json_error",
                    layer_name="benefits",
                    product_name=extraction_result.product_name,
                    text_index=extraction_result.text_index,
                    approve=False,
                    original_extraction=extraction_result.extracted_data,
                    response=api_result["content"],
                    error_details=f"Invalid JSON: {validation.get('error_type', 'Unknown')}",
                    processing_time=time.time() - start_time
                )

            parsed_judgment = validation["parsed_json"]

            # Check if all items approved
            validations = parsed_judgment.get("validations", [])
            all_approved = all(v.get("approve", False) for v in validations)

            # Success
            return JudgmentResult(
                status="success",
                layer_name="benefits",
                product_name=extraction_result.product_name,
                text_index=extraction_result.text_index,
                approve=all_approved,
                final_value=parsed_judgment,  # Contains {"validations": [...]}
                original_extraction=extraction_result.extracted_data,
                response=api_result["content"],
                json_validation=validation,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            return JudgmentResult(
                status="exception",
                layer_name="benefits",
                product_name=extraction_result.product_name,
                text_index=extraction_result.text_index,
                approve=False,
                original_extraction=extraction_result.extracted_data,
                error_details=f"Exception: {str(e)}",
                processing_time=time.time() - start_time
            )


# ============================================================================
# Part 3: Batch Processor (Pillar with Extractor)
# ============================================================================

class BatchBenefitJudger:
    """Parallel batch processor for benefit judgment."""

    def __init__(
        self,
        judger: BenefitJudger,
        output_dir: Path
    ):
        """
        Initialize batch processor.

        Args:
            judger: BenefitJudger instance
            output_dir: Directory for saving batch results
        """
        self.judger = judger
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def judge_extractions(
        self,
        extraction_results: Dict[str, ExtractionResult],
        max_workers: int = 100,
        batch_size: int = 50
    ) -> Dict[str, JudgmentResult]:
        """
        Judge all extraction results in parallel.

        Args:
            extraction_results: Dict of ExtractionResults from extractor (each contains a list)
            max_workers: Maximum parallel workers
            batch_size: Number of items per batch

        Returns:
            Dictionary mapping result_id -> JudgmentResult
        """
        print(f"\n{'=' * 80}")
        print(f"Judging All Benefit Extractions")
        print(f"{'=' * 80}")
        print(f"Total extraction results to judge: {len(extraction_results)}")
        print(f"Max workers: {max_workers}")

        all_judgments = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all judgment tasks
            future_to_id = {}
            for result_id, extraction_result in extraction_results.items():
                future = executor.submit(
                    self.judger.judge_extractions,
                    extraction_result
                )
                future_to_id[future] = result_id

            # Collect results with progress tracking
            completed = 0
            approved = 0
            total_items_judged = 0

            for future in as_completed(future_to_id):
                result_id = future_to_id[future]
                judgment = future.result()
                all_judgments[result_id] = judgment

                if judgment.status == "success" and judgment.approve:
                    approved += 1
                    # Count individual items judged
                    if judgment.final_value and "validations" in judgment.final_value:
                        total_items_judged += len(judgment.final_value["validations"])

                completed += 1
                if completed % 10 == 0 or completed == len(extraction_results):
                    approval_rate = (approved / completed * 100) if completed > 0 else 0
                    print(f"  Progress: {completed}/{len(extraction_results)} | "
                          f"Approved: {approved} ({approval_rate:.1f}%) | "
                          f"Items judged: {total_items_judged}")

        return all_judgments
