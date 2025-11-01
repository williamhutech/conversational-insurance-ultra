"""
Concept Extractor Agent (Stage 2)
Extracts insurance-related concept terms from policy texts.
"""

import json
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..utils.api_client import APIClient
from ..entities.data_models import ConceptExtractionResult


class ConceptPromptTemplate:
    """Prompt template for concept extraction."""

    @staticmethod
    def get_system_prompt() -> str:
        """Get system prompt for concept extraction."""
        return """You are an experienced insurance specialist, skilled in identifying and extracting insurance concept terms from policy texts.

Your task is to extract all relevant concept terms from insurance policy texts.

Extraction principles:
- Only extract insurance-related concepts, terms, and nouns
- Only concept terms, not complete definitions or explanations
- Prefer single core terms (e.g., "retroactive date", "premium", "sublimit")
- Use phrases only when they represent standard insurance terminology that cannot be meaningfully separated (e.g., "business interruption", "professional indemnity")
- Avoid descriptive combinations (e.g., "high deductible" → "deductible")
- Avoid overly vague terms (e.g., "insurance problem", "policy issue")
- Include but not limited to coverage types, limits, exclusions, perils, conditions, clauses, legal concepts, and all other related concepts
- Remove duplicate concepts
- Sort by importance

Please ensure the output format strictly follows JSON format requirements."""

    @staticmethod
    def get_extraction_prompt(text_content: str) -> str:
        """
        Get extraction prompt for concept extraction.

        Args:
            text_content: Text content to extract concepts from

        Returns:
            Formatted extraction prompt
        """
        return f"""**Task: Extract concept terms from insurance policy text**

**Please extract all relevant insurance concept terms from the following text:**

---
{text_content}
---

**Output format (strictly follow JSON format):**
```json
{{
"concepts": [
    "concept1",
    "concept2",
    "concept3",
    "..."
]
}}"""


class ConceptExtractor:
    """
    Extract insurance concept terms from text documents.

    Processes texts in parallel, extracts insurance-specific concepts,
    and returns deduplicated, sorted list of concept terms.
    """

    def __init__(
        self,
        api_client: APIClient,
        max_workers: int = 100
    ):
        """
        Initialize concept extractor.

        Args:
            api_client: Configured API client
            max_workers: Number of concurrent API calls (default: 100)
        """
        self.api_client = api_client
        self.max_workers = max_workers
        self.prompt = ConceptPromptTemplate()

    def extract_from_single_text(
        self,
        text: str,
        index: int
    ) -> ConceptExtractionResult:
        """
        Extract concepts from a single text.

        Args:
            text: Text content to process
            index: Text index for logging

        Returns:
            ConceptExtractionResult with extracted concepts
        """
        if not text:
            return ConceptExtractionResult(
                status="error",
                text_id=str(index),
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
                "content": self.prompt.get_extraction_prompt(text)
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
                concepts = response_json.get("concepts", [])

                print(f"Text {index + 1}: Extracted {len(concepts)} concepts")

                return ConceptExtractionResult(
                    status="success",
                    text_id=str(index),
                    extracted_concepts=concepts
                )

            except Exception as e:
                print(f"Failed to parse text {index + 1}: {str(e)}")
                return ConceptExtractionResult(
                    status="error",
                    text_id=str(index),
                    error=f"JSON parsing failed: {str(e)}"
                )

        return ConceptExtractionResult(
            status="error",
            text_id=str(index),
            error=api_result.get("error", "API call failed")
        )

    def generate_seed_concepts(
        self,
        text_list: List[str]
    ) -> List[str]:
        """
        Generate seed concepts from list of texts.

        Processes all texts in parallel, extracts concepts, removes
        duplicates, and returns sorted list of unique concepts.

        Args:
            text_list: List of text strings to extract concepts from

        Returns:
            List of unique seed concepts (sorted)
        """
        print(f"Processing {len(text_list)} texts with {self.max_workers} workers...")

        seed_concepts = []

        # Process texts concurrently
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(self.extract_from_single_text, text, i): i
                for i, text in enumerate(text_list)
            }

            # Collect results as they complete
            for future in as_completed(futures):
                result = future.result()
                if result.status == "success" and result.extracted_concepts:
                    seed_concepts.extend(result.extracted_concepts)

        # Remove duplicates and sort
        unique_concepts = sorted(list(set(seed_concepts)))
        print(f"Total: Generated {len(unique_concepts)} unique seed concepts")

        return unique_concepts

    def generate_from_json_files(
        self,
        raw_text_dir: str
    ) -> List[str]:
        """
        Generate seed concepts from all JSON files in directory.

        Convenience method that loads JSON files, concatenates texts,
        and extracts concepts.

        Args:
            raw_text_dir: Directory containing JSON text files

        Returns:
            List of unique seed concepts
        """
        from pathlib import Path
        from ..utils.file_utils import load_json

        # Load all texts from JSON files
        all_texts = []
        json_files = list(Path(raw_text_dir).glob("*.json"))

        print(f"Loading texts from {len(json_files)} JSON files...")

        for json_file in json_files:
            texts = load_json(json_file)
            if isinstance(texts, list):
                all_texts.extend(texts)

        print(f"Loaded {len(all_texts)} texts total")

        # Generate seed concepts
        return self.generate_seed_concepts(all_texts)
