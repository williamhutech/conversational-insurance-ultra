"""
Fact Extractor Agent (Stage 3)
Extracts verifiable facts from insurance policy texts.
"""

import json
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..utils.api_client import APIClient
from ..entities.data_models import FactExtractionResult


class FactPromptTemplate:
    """Prompt template for fact extraction with strategic information prioritization."""

    @staticmethod
    def get_system_prompt() -> str:
        """Get system prompt for fact extraction."""
        return """You are an expert insurance analyst specializing in extracting decision-critical facts from policy documents.

**STRATEGIC EXTRACTION FRAMEWORK**

PRIORITY 1 - CRITICAL COVERAGE FACTS (Extract ALL):
• Coverage boundaries: limits, caps, maximums, deductibles, copayments, waiting periods
• Eligibility criteria: age restrictions, pre-existing condition clauses, geographic limitations, qualifying events
• Claim procedures: filing requirements, documentation needed, time limits, approval processes
• Binding obligations: renewal terms, cancellation rights, premium adjustment triggers, dispute resolution

PRIORITY 2 - SUPPORTING FACTS (Extract if substantive):
• Definitions that affect coverage interpretation (e.g., "accident", "disability", "dependent")
• Exclusions and limitations that restrict benefits
• Benefit calculation formulas and payment schedules
• Insurer identification and contact obligations

EXPLICITLY EXCLUDE (Do NOT extract):
• Marketing language, promotional statements, or sales-oriented text
• Boilerplate legal clauses for minor administrative provisions
• Regional terminology variations without coverage impact
• Historical context, background information, or policy rationale
• Redundant restatements of the same coverage term

**EXTRACTION PRINCIPLES**:
- Extract only concrete, verifiable facts directly from the text
- Each fact must be a complete, standalone statement
- Preserve exact numbers, dates, monetary amounts, and percentages
- Include product/plan variant specificity in every fact
- Remove duplicates; prioritize by decision-impact (Critical → Supporting)
- Facts must be actionable for coverage comparison or claim assessment

Output must strictly follow JSON format requirements."""

    @staticmethod
    def get_extraction_prompt(text_content: str, product_name: str) -> str:
        """
        Get extraction prompt for fact extraction.

        Args:
            text_content: Text content to extract facts from
            product_name: Name of the insurance product

        Returns:
            Formatted extraction prompt
        """
        return f"""**TASK: Extract decision-critical facts from insurance policy**

**Product Name**: {product_name}

**APPLY STRATEGIC FILTERING**: Focus on coverage boundaries, eligibility, claims, and obligations. Exclude marketing language and minor legal boilerplate.

**Source Text:**
---
{text_content}
---

**REQUIREMENTS**:
1. Each fact MUST reference {product_name} explicitly
2. For plan variants/components, specify clearly (e.g., "The Gold Plan of {product_name} provides...")
3. Prioritize facts by decision-impact: Critical coverage terms first, supporting details second
4. Preserve exact numerical values, dates, and monetary amounts
5. Ensure facts are standalone and comparison-ready

**Output Format (strict JSON):**
```json
{{
  "facts": [
    "fact1",
    "fact2",
    "fact3",
    "..."
  ]
}}"""


class FactExtractor:
    """
    Extract factual statements from insurance policy texts.

    Processes product texts in parallel, extracts verifiable facts,
    and returns deduplicated facts organized by product.
    """

    def __init__(
        self,
        api_client: APIClient,
        max_workers: int = 100
    ):
        """
        Initialize fact extractor.

        Args:
            api_client: Configured API client
            max_workers: Number of concurrent API calls (default: 100)
        """
        self.api_client = api_client
        self.max_workers = max_workers
        self.prompt = FactPromptTemplate()

    def extract_from_single_text(
        self,
        text: str,
        product_name: str,
        index: int
    ) -> FactExtractionResult:
        """
        Extract facts from a single text.

        Args:
            text: Text content to process
            product_name: Name of the insurance product
            index: Text index for logging

        Returns:
            FactExtractionResult with extracted facts
        """
        if not text:
            return FactExtractionResult(
                status="error",
                product_name=product_name,
                text_index=index,
                error="Empty text"
            )

        # Create messages
        messages = [
            {
                "role": "system",
                "content": self.prompt.get_system_prompt()
            },
            {
                "role": "user",
                "content": self.prompt.get_extraction_prompt(text, product_name)
            }
        ]

        # Call API
        api_result = self.api_client.call_api(messages, timeout=120)

        if api_result["status"] == "success":
            try:
                # Parse JSON response
                response_content = api_result["content"]

                # Remove markdown code blocks if present
                if "```json" in response_content:
                    response_content = response_content.split("```json")[1].split("```")[0]
                elif "```" in response_content:
                    response_content = response_content.replace("```", "")

                response_json = json.loads(response_content.strip())
                facts = response_json.get("facts", [])

                print(f"{product_name} - Text {index + 1}: Extracted {len(facts)} facts")

                return FactExtractionResult(
                    status="success",
                    product_name=product_name,
                    text_index=index,
                    extracted_facts=facts
                )

            except Exception as e:
                print(f"Failed to parse {product_name} - Text {index + 1}: {str(e)}")
                return FactExtractionResult(
                    status="error",
                    product_name=product_name,
                    text_index=index,
                    error=f"JSON parsing failed: {str(e)}"
                )

        return FactExtractionResult(
            status="error",
            product_name=product_name,
            text_index=index,
            error=api_result.get("error", "API call failed")
        )

    def extract_facts(
        self,
        product_dict: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """
        Extract facts from all products in dictionary.

        Processes each text for each product in parallel, extracts facts,
        and returns deduplicated facts organized by product.

        Args:
            product_dict: Dictionary with product names as keys and text lists as values

        Returns:
            Dictionary with product names as keys and lists of unique facts as values
        """
        product_facts = {}

        # Process each product
        for product_name, text_list in product_dict.items():
            print(f"\nProcessing {product_name}: {len(text_list)} texts")

            all_facts = []

            # Process texts concurrently
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                futures = {
                    executor.submit(self.extract_from_single_text, text, product_name, i): i
                    for i, text in enumerate(text_list)
                }

                # Collect results as they complete
                for future in as_completed(futures):
                    result = future.result()
                    if result.status == "success" and result.extracted_facts:
                        all_facts.extend(result.extracted_facts)

            # Remove duplicates while preserving order
            seen = set()
            unique_facts = []
            for fact in all_facts:
                if fact not in seen:
                    seen.add(fact)
                    unique_facts.append(fact)

            product_facts[product_name] = unique_facts
            print(f"{product_name}: Extracted {len(unique_facts)} unique facts total")

        return product_facts

    def get_all_facts(self, product_facts: Dict[str, List[str]]) -> List[str]:
        """
        Get all unique facts from all products combined.

        Args:
            product_facts: Dictionary of product names to fact lists

        Returns:
            List of all unique facts across all products
        """
        all_facts = []
        for facts in product_facts.values():
            all_facts.extend(facts)

        # Return as-is (may contain duplicates across products)
        return all_facts
