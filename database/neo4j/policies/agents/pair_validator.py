"""
Concept Pair Validator Agent (Stage 7b)
Validates concept pairs and generates QA for insurance-relevant relationships.
"""

import os
import time
import random
import pickle
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Union
from dataclasses import asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..utils.api_client import APIClient
from ..utils.response_validator import ResponseValidator
from ..entities.data_models import PairValidationResult


class ConceptPairValidatorPrompt:
    """Prompt template for concept pair validation."""

    @staticmethod
    def get_system_prompt() -> str:
        """Get system prompt for pair validation."""
        return """You are a senior insurance underwriter and product specialist with 20+ years of experience across life, health, property, and casualty insurance. Your task is to rigorously evaluate concept pairs and generate high-quality educational content. You must act as a **strict filter**, approving only pairs with a **direct, critical, and undeniable link** in insurance practice and customer advisory."""

    @staticmethod
    def get_user_prompt(concept_pairs: List[Tuple[str, str]], personality: str) -> str:
        """
        Get user prompt for validating concept pairs.

        Args:
            concept_pairs: List of concept pairs to evaluate
            personality: Customer persona description

        Returns:
            Formatted user prompt
        """
        pairs_text = ""
        for i, (concept_a, concept_b) in enumerate(concept_pairs, 1):
            pairs_text += f"{i}. {concept_a} <-> {concept_b}\n"

        # Use first pair for template placeholders
        first_pair = concept_pairs[0] if concept_pairs else ("concept_a", "concept_b")

        return f"""**CONCEPT PAIRS TO EVALUATE:**
{pairs_text}

**CUSTOMER PERSONA:** {personality}

For each pair, you must strictly evaluate the following two criteria. **BOTH must be strongly true** to proceed.

1.  **Direct Insurance Relevance**: Is there a **direct coverage, risk, underwriting, claims, or regulatory link** between the two concepts? The connection should not be a weak, coincidental, or indirect association. One concept must frequently and directly influence the consideration of the other in **critical insurance decisions**.

2.  **Essential Educational Value**: Does understanding this specific link teach a **crucial, non-obvious insurance reasoning skill**? The relationship should highlight a common customer confusion, a key coverage interaction, or a pivotal underwriting decision. It must be more than a simple factual association.

**EXAMPLE OF A PAIR TO REJECT:**
- `"Premium" <-> "Office Building"`: While premiums are paid at insurance offices, this is a basic locational fact and lacks educational depth.

Acting as the customer persona above, for each pair that meets the stringent criteria:
1. Generate 1 insurance scenario question covering BOTH concepts from this customer's perspective.
2. Every detail mentioned must be CRITICAL to the insurance decision - avoid redundant details.
3. Focus on decision-making situations where simultaneously considering the concept pairs is central.
4. The question should reflect this persona's specific concerns, knowledge level, and situation.
5. **AVOID simple definitional questions** - require insurance reasoning and application.

**OUTPUT FORMAT (strict JSON):**
{{
  "evaluated_pairs": [
    {{
      "concept_pair": ["{first_pair[0]}", "{first_pair[1]}"],
      "is_insurancely_relevant": true/false,
      "is_instructionally_meaningful": true/false,
      "question": {{
        "question": "Insurance scenario covering both concepts from this persona's perspective...",
        "reasoning_guidance": "Step-by-step insurance thinking process...",
        "knowledge_facts": [
          "{first_pair[0]} fact 1...",
          "{first_pair[1]} fact 1...",
          "{first_pair[0]} fact 2..."
        ],
        "final_answer": "Comprehensive answer addressing the customer's concerns...",
        "best_to_know": "Information about the customer/context/product that would help better answer this question"
      }}
    }}
  ]
}}

Generate the evaluation and content now from this customer's perspective."""


class ConceptPairValidator:
    """
    Validate concept pairs and generate QA for relevant relationships.

    Acts as a strict filter that only generates QA content for concept
    pairs with direct insurance relevance and educational value.
    """

    def __init__(self, api_client: APIClient, personalities: List[str]):
        """
        Initialize concept pair validator.

        Args:
            api_client: Configured API client
            personalities: List of customer personality descriptions
        """
        self.api_client = api_client
        self.personalities = personalities
        self.prompt = ConceptPairValidatorPrompt()

    def validate_concept_pair(
        self,
        concept_pair: Tuple[str, str],
        pair_id: str
    ) -> PairValidationResult:
        """
        Validate a single concept pair and generate QA if relevant.

        Args:
            concept_pair: Tuple of (concept1, concept2)
            pair_id: Unique identifier for tracking

        Returns:
            PairValidationResult with validation outcome and QA data
        """
        start_time = time.time()

        # Select random personality for this pair
        selected_personality = random.choice(self.personalities)

        # Create messages
        system_prompt = self.prompt.get_system_prompt()
        user_prompt = self.prompt.get_user_prompt([concept_pair], selected_personality)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Call API
        api_result = self.api_client.call_api(messages, timeout=300)
        processing_time = time.time() - start_time

        if api_result["status"] != "success":
            return PairValidationResult(
                status="api_error",
                pair_id=pair_id,
                concept_pair=concept_pair,
                error_details=api_result.get("error", "API call failed"),
                processing_time=processing_time
            )

        # Validate JSON response
        expected_keys = ["evaluated_pairs"]
        json_validation = ResponseValidator.validate_json_response(
            api_result["content"],
            expected_keys
        )

        if not json_validation["is_valid_json"]:
            return PairValidationResult(
                status="json_error",
                pair_id=pair_id,
                concept_pair=concept_pair,
                response=api_result["content"],
                error_details=f"JSON validation failed: {json_validation['error_type']}",
                processing_time=processing_time,
                json_validation=json_validation
            )

        try:
            parsed_json = json_validation["parsed_json"]
            evaluated_pairs = parsed_json.get("evaluated_pairs", [])

            if not evaluated_pairs:
                return PairValidationResult(
                    status="success",
                    pair_id=pair_id,
                    concept_pair=concept_pair,
                    is_clinically_relevant=False,
                    is_instructionally_meaningful=False,
                    qa_data=None,
                    processing_time=processing_time,
                    json_validation=json_validation
                )

            pair_result = evaluated_pairs[0]
            is_relevant = pair_result.get("is_insurancely_relevant", False)
            is_meaningful = pair_result.get("is_instructionally_meaningful", False)

            qa_data = None
            if is_relevant and is_meaningful and pair_result.get("question"):
                question_data = pair_result["question"]
                qa_data = {
                    "concept": list(concept_pair),
                    "question": question_data.get("question", ""),
                    "reasoning_guidance": question_data.get("reasoning_guidance", ""),
                    "knowledge_facts": question_data.get("knowledge_facts", []),
                    "final_answer": question_data.get("final_answer", ""),
                    "best_to_know": question_data.get("best_to_know", "")
                }

            return PairValidationResult(
                status="success",
                pair_id=pair_id,
                concept_pair=concept_pair,
                is_clinically_relevant=is_relevant,
                is_instructionally_meaningful=is_meaningful,
                qa_data=qa_data,
                response=api_result["content"],
                processing_time=processing_time,
                json_validation=json_validation
            )

        except Exception as e:
            return PairValidationResult(
                status="exception",
                pair_id=pair_id,
                concept_pair=concept_pair,
                error_details=str(e),
                processing_time=processing_time
            )


class BatchConceptPairValidator:
    """
    Batch process multiple concept pairs for validation.

    Extracts unique edges from concept graph, validates them,
    and generates QA content for relevant pairs.
    """

    def __init__(
        self,
        validator: ConceptPairValidator,
        output_dir: Union[str, Path]
    ):
        """
        Initialize batch pair validator.

        Args:
            validator: ConceptPairValidator instance
            output_dir: Absolute path to directory for saving batch results (required)
        """
        self.validator = validator
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def validate_concept_pair_graph(
        self,
        concept_graph_dict: Dict[str, List[str]],
        max_workers: int = 10,
        batch_size: int = 20,
        batch_delay: int = 0
    ) -> Dict[str, PairValidationResult]:
        """
        Extract unique edges from concept graph and validate them as pairs.

        Args:
            concept_graph_dict: Dictionary of concept -> neighbors
            max_workers: Number of concurrent workers
            batch_size: Number of pairs per batch
            batch_delay: Seconds to wait between batches

        Returns:
            Dictionary of pair_id -> PairValidationResult
        """
        # Extract unique edges from the graph
        unique_edges = self._extract_unique_edges(concept_graph_dict)
        total_pairs = len(unique_edges)

        print(f"Starting batch processing: Concept pair validation for {total_pairs} pairs")
        print(f"Batch size: {batch_size}, Max concurrency: {max_workers}")

        all_results = {}
        batch_num = 1

        # Process in batches
        for i in range(0, total_pairs, batch_size):
            batch_pairs = unique_edges[i:i + batch_size]
            print(f"\nProcessing batch {batch_num}: Pairs {i + 1}-{min(i + batch_size, total_pairs)} ({len(batch_pairs)} pairs)")

            batch_start_time = time.time()
            batch_results = self._process_batch(batch_pairs, max_workers, i)
            batch_end_time = time.time()

            # Save batch results
            self._save_batch_results(batch_results, batch_num, batch_start_time)

            all_results.update(batch_results)

            print(f"Batch {batch_num} complete, time taken: {batch_end_time - batch_start_time:.2f} seconds")

            batch_num += 1

            # Rest between batches
            if i + batch_size < total_pairs:
                time.sleep(batch_delay)

        print(f"\nAll batches processed! Total pairs processed: {total_pairs}")
        return all_results

    @staticmethod
    def _extract_unique_edges(graph_dict: Dict[str, List[str]]) -> List[Tuple[str, str]]:
        """
        Extract unique edge pairs from the graph.

        Only includes pairs where both concepts exist as keys in the graph.
        Treats (A,B) and (B,A) as the same undirected edge.

        Args:
            graph_dict: Dictionary of concept -> neighbors

        Returns:
            List of unique concept pairs
        """
        processed_pairs = set()
        unique_edges = []
        graph_keys = set(graph_dict.keys())

        for concept_a, neighbors in graph_dict.items():
            for concept_b in neighbors:
                # Only include pairs where BOTH concepts exist as keys
                if concept_b not in graph_keys:
                    continue

                # Sort to ensure (A,B) and (B,A) are treated as the same pair
                edge = tuple(sorted([concept_a, concept_b]))

                if edge not in processed_pairs:
                    processed_pairs.add(edge)
                    unique_edges.append(edge)

        print(f"Total directed edges: {sum(len(neighbors) for neighbors in graph_dict.values())}")
        print(f"Edges after deduplication: {len(unique_edges)}")

        return unique_edges

    def _process_batch(
        self,
        batch_pairs: List[Tuple[str, str]],
        max_workers: int,
        start_index: int
    ) -> Dict[str, PairValidationResult]:
        """
        Process a single batch of concept pairs in parallel.

        Args:
            batch_pairs: List of concept pairs to process
            max_workers: Number of concurrent workers
            start_index: Starting index for pair IDs

        Returns:
            Dictionary of pair_id -> results
        """
        batch_results = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit tasks
            future_to_pair = {}
            for idx, pair in enumerate(batch_pairs):
                pair_id = f"pair_{start_index + idx:06d}"
                future = executor.submit(
                    self.validator.validate_concept_pair,
                    pair,
                    pair_id
                )
                future_to_pair[future] = (pair_id, pair)

            # Collect results
            completed = 0
            for future in as_completed(future_to_pair):
                pair_id, pair = future_to_pair[future]
                try:
                    result = future.result()
                    batch_results[pair_id] = result

                    # Status display
                    status_symbol = "✓" if result.status == "success" else "✗"
                    completed += 1

                    if completed % 100 == 0 or completed == len(batch_pairs):
                        success_count = sum(1 for r in batch_results.values() if r.status == "success")
                        relevant_count = sum(
                            1 for r in batch_results.values()
                            if r.status == "success" and r.is_clinically_relevant
                        )
                        print(f"  Completed: {completed}/{len(batch_pairs)} | Success: {success_count} | Relevant: {relevant_count} {status_symbol}")

                except Exception as e:
                    batch_results[pair_id] = PairValidationResult(
                        status="exception",
                        pair_id=pair_id,
                        concept_pair=pair,
                        error_details=str(e)
                    )
                    print(f"  Exception: {pair_id} - {str(e)}")

        return batch_results

    def _save_batch_results(
        self,
        batch_results: Dict[str, PairValidationResult],
        batch_num: int,
        start_time: float
    ) -> str:
        """
        Save batch results to pickle file.

        Args:
            batch_results: Dictionary of results
            batch_num: Batch number
            start_time: Batch start timestamp

        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"concept_pair_validation_batch_{batch_num:03d}_{timestamp}.pkl"
        filepath = self.output_dir / filename

        # Calculate statistics
        total_count = len(batch_results)
        success_count = sum(1 for r in batch_results.values() if r.status == "success")
        relevant_count = sum(
            1 for r in batch_results.values()
            if r.status == "success" and r.is_clinically_relevant
        )
        qa_count = sum(
            1 for r in batch_results.values()
            if r.status == "success" and r.qa_data is not None
        )

        # Convert to serializable format
        serializable_results = {
            k: asdict(v) for k, v in batch_results.items()
        }

        save_data = {
            "metadata": {
                "batch_num": batch_num,
                "timestamp": timestamp,
                "start_time": start_time,
                "total_pairs": total_count,
                "successful_validations": success_count,
                "clinically_relevant_pairs": relevant_count,
                "qa_pairs_generated": qa_count
            },
            "results": serializable_results
        }

        # Save to file
        with open(filepath, 'wb') as f:
            pickle.dump(save_data, f)

        print(f"  Batch results saved to: {filename}")
        print(f"  Success: {success_count}/{total_count} ({success_count / total_count * 100:.1f}%)")
        print(f"  Clinically Relevant: {relevant_count}/{success_count if success_count > 0 else 1}")
        print(f"  QA Pairs Generated: {qa_count}")

        return filepath


def validate_concept_pair_graph(
    concept_graph_dict: Dict[str, List[str]],
    personalities: List[str],
    api_client: APIClient,
    max_workers: int = 10,
    batch_size: int = 20,
    output_dir: str = "concept_pair_validation"
) -> Dict[str, PairValidationResult]:
    """
    Convenience function to validate concept pairs from a concept graph.

    Args:
        concept_graph_dict: Dictionary of concept -> neighbors
        personalities: List of customer personality descriptions
        api_client: Configured API client
        max_workers: Number of concurrent workers
        batch_size: Number of pairs per batch
        output_dir: Directory for saving results

    Returns:
        Dictionary of pair_id -> PairValidationResult
    """
    print(f"Preparing to validate concept pairs from graph: {len(concept_graph_dict)} concepts")
    print(f"Using {len(personalities)} different customer personas")

    # Initialize validator
    validator = ConceptPairValidator(api_client, personalities)
    batch_validator = BatchConceptPairValidator(validator, output_dir=output_dir)

    # Batch validate
    results = batch_validator.validate_concept_pair_graph(
        concept_graph_dict=concept_graph_dict,
        max_workers=max_workers,
        batch_size=batch_size,
        batch_delay=1
    )

    return results


def test_single_pair_validation(
    concept_pair: Tuple[str, str],
    personalities: List[str],
    api_client: APIClient,
    verbose: bool = True
) -> PairValidationResult:
    """
    Test validation for a single concept pair.

    Args:
        concept_pair: Tuple of (concept1, concept2)
        personalities: List of customer personality descriptions
        api_client: Configured API client
        verbose: Whether to print detailed output

    Returns:
        PairValidationResult
    """
    if verbose:
        print("=" * 80)
        print("Single Concept Pair Validation Test")
        print("=" * 80)
        print(f"Concept Pair: {concept_pair[0]} <-> {concept_pair[1]}")
        print(f"Using {len(personalities)} customer personas")
        print()

    validator = ConceptPairValidator(api_client, personalities)
    result = validator.validate_concept_pair(concept_pair, "test_pair")

    if verbose:
        print(f"Processing status: {result.status}")
        print(f"Processing time: {result.processing_time:.2f}s")
        print(f"Insurance Relevant: {result.is_clinically_relevant}")
        print(f"Instructionally Meaningful: {result.is_instructionally_meaningful}")

        if result.status == "success" and result.qa_data:
            print("=" * 80)
            print("Generated QA Data:")
            print(f"Question: {result.qa_data['question']}")
            print(f"Knowledge facts: {len(result.qa_data['knowledge_facts'])} items")
            print(f"Answer: {result.qa_data['final_answer'][:100]}...")
        elif result.error_details:
            print(f"Error: {result.error_details}")

    return result
