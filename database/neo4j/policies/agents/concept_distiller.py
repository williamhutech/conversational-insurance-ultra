"""
Concept Distiller Agent (Stage 7a)
Generates question-answer pairs for individual insurance concepts.
"""

import os
import time
import random
import pickle
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Union
from dataclasses import asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..utils.api_client import APIClient
from ..utils.response_validator import ResponseValidator
from ..entities.data_models import ConceptDistillationResult


class ConceptDistillerPrompt:
    """Prompt template for concept distillation (QA generation)."""

    @staticmethod
    def get_system_prompt() -> str:
        """Get system prompt for concept distillation."""
        return """You are an experienced insurance advisor with 15+ years of expertise in personal and commercial insurance products. Your task is to create high-quality educational content for training insurance agents and educating customers about insurance concepts.

Your generated questions must reflect real customer inquiries and require practical insurance knowledge - avoid simple definitional questions."""

    @staticmethod
    def get_user_prompt(concept: str, personality: str) -> str:
        """
        Get user prompt for generating QA pairs for a concept.

        Args:
            concept: The insurance concept to generate questions for
            personality: Customer persona description

        Returns:
            Formatted user prompt
        """
        return f"""**TARGET CONCEPT: {concept}**

**CUSTOMER PERSONA:** {personality}

Acting as this specific customer persona, generate exactly 3 diverse insurance-related questions about this concept, each with complete educational materials. Follow these requirements:

**QUESTION DESIGN PRINCIPLES:**
1. Questions should reflect this persona's specific situation, concerns, and knowledge level
2. Focus on practical insurance scenarios this persona would realistically encounter
3. Every detail mentioned must be RELEVANT to the insurance decision - avoid unnecessary information
4. Questions should require understanding of how {concept} applies to real insurance situations
5. **AVOID simple factual questions** - require practical application and decision-making

**KNOWLEDGE FACTS REQUIREMENTS:**
- Each fact must start with the concept name as the subject
- Focus on practical applications, coverage implications, claim scenarios
- Include regulatory or legal aspects when relevant

**OUTPUT FORMAT (strict JSON):**
{{
  "concept": "{concept}",
  "questions": [
    {{
      "question_id": 1,
      "question": "Insurance scenario question 1 from this persona's perspective...",
      "reasoning_guidance": "Step-by-step insurance thinking process 1...",
      "knowledge_facts": [
        "{concept} fact 1...",
        "{concept} fact 2...",
        "{concept} fact 3..."
      ],
      "final_answer": "Comprehensive insurance answer...",
      "best_to_know": "Information about the customer/context/product that would help answer this question better"
    }},
    {{
      "question_id": 2,
      "question": "Insurance scenario question 2 from this persona's perspective...",
      "reasoning_guidance": "Step-by-step insurance thinking process 2...",
      "knowledge_facts": [
        "{concept} fact 1...",
        "{concept} fact 2..."
      ],
      "final_answer": "Comprehensive insurance answer...",
      "best_to_know": "Information about the customer/context/product that would help answer this question better"
    }},
    {{
      "question_id": 3,
      "question": "Insurance scenario question 3 from this persona's perspective...",
      "reasoning_guidance": "Step-by-step insurance thinking process 3...",
      "knowledge_facts": [
        "{concept} fact 1...",
        "{concept} fact 2..."
      ],
      "final_answer": "Comprehensive insurance answer...",
      "best_to_know": "Information about the customer/context/product that would help answer this question better"
    }}
  ]
}}

Generate the educational content now from this customer's perspective."""


class ConceptDistiller:
    """
    Generate question-answer pairs for individual concepts.

    Creates 3 QA pairs per concept from the perspective of randomly
    selected customer personas, with complete educational materials.
    """

    def __init__(self, api_client: APIClient, personalities: List[str]):
        """
        Initialize concept distiller.

        Args:
            api_client: Configured API client
            personalities: List of customer personality descriptions
        """
        self.api_client = api_client
        self.personalities = personalities
        self.prompt = ConceptDistillerPrompt()

    def distill_concept(
        self,
        concept: str,
        concept_id: str
    ) -> ConceptDistillationResult:
        """
        Generate QA pairs for a single concept.

        Args:
            concept: The insurance concept to generate questions for
            concept_id: Unique identifier for tracking

        Returns:
            ConceptDistillationResult with generated questions
        """
        start_time = time.time()

        # Select random personality for this concept
        selected_personality = random.choice(self.personalities)

        # Create messages
        system_prompt = self.prompt.get_system_prompt()
        user_prompt = self.prompt.get_user_prompt(concept, selected_personality)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Call API
        api_result = self.api_client.call_api(messages, timeout=300)
        processing_time = time.time() - start_time

        if api_result["status"] != "success":
            return ConceptDistillationResult(
                status="api_error",
                concept_id=concept_id,
                concept_name=concept,
                error_details=api_result.get("error", "API call failed"),
                processing_time=processing_time
            )

        # Validate JSON response
        expected_keys = ["concept", "questions"]
        json_validation = ResponseValidator.validate_json_response(
            api_result["content"],
            expected_keys
        )

        if json_validation["is_valid_json"]:
            questions = json_validation["parsed_json"]["questions"]
            return ConceptDistillationResult(
                status="success",
                concept_id=concept_id,
                concept_name=concept,
                response=api_result["content"],
                processing_time=processing_time,
                json_validation=json_validation,
                generated_questions=questions
            )
        else:
            return ConceptDistillationResult(
                status="json_error",
                concept_id=concept_id,
                concept_name=concept,
                response=api_result["content"],
                error_details=f"JSON validation failed: {json_validation['error_type']}",
                processing_time=processing_time,
                json_validation=json_validation
            )


class BatchConceptDistiller:
    """
    Batch process multiple concepts for QA generation.

    Processes concepts in parallel, saves results in batches,
    and provides progress tracking and statistics.
    """

    def __init__(
        self,
        distiller: ConceptDistiller,
        output_dir: Union[str, Path]
    ):
        """
        Initialize batch distiller.

        Args:
            distiller: ConceptDistiller instance
            output_dir: Absolute path to directory for saving batch results (required)
        """
        self.distiller = distiller
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def distill_concept_graph(
        self,
        concept_graph_dict: Dict[str, List[str]],
        max_workers: int = 10,
        batch_size: int = 20,
        batch_delay: int = 0
    ) -> Dict[str, ConceptDistillationResult]:
        """
        Generate QA pairs for all concepts in the graph.

        Processes concepts in batches with configurable concurrency
        and delay between batches.

        Args:
            concept_graph_dict: Dictionary of concept -> neighbors
            max_workers: Number of concurrent workers
            batch_size: Number of concepts per batch
            batch_delay: Seconds to wait between batches

        Returns:
            Dictionary of concept_id -> ConceptDistillationResult
        """
        concept_list = list(concept_graph_dict.keys())
        total_concepts = len(concept_list)

        print(f"Starting batch processing: QA generation for {total_concepts} concepts")
        print(f"Batch size: {batch_size}, Max concurrency: {max_workers}")

        all_results = {}
        batch_num = 1

        # Process in batches
        for i in range(0, total_concepts, batch_size):
            batch_concepts = concept_list[i:i + batch_size]
            print(f"\nProcessing batch {batch_num}: Concepts {i+1}-{min(i+batch_size, total_concepts)} ({len(batch_concepts)} concepts)")

            batch_start_time = time.time()
            batch_results = self._process_batch(batch_concepts, max_workers, i)
            batch_end_time = time.time()

            # Save batch results
            self._save_batch_results(batch_results, batch_num, batch_start_time)

            all_results.update(batch_results)

            print(f"Batch {batch_num} complete, time taken: {batch_end_time - batch_start_time:.2f} seconds")

            batch_num += 1

            # Rest between batches
            if i + batch_size < total_concepts:
                time.sleep(batch_delay)

        print(f"\nAll batches processed! Total concepts processed: {total_concepts}")
        return all_results

    def _process_batch(
        self,
        batch_concepts: List[str],
        max_workers: int,
        start_index: int
    ) -> Dict[str, ConceptDistillationResult]:
        """
        Process a single batch of concepts in parallel.

        Args:
            batch_concepts: List of concepts to process
            max_workers: Number of concurrent workers
            start_index: Starting index for concept IDs

        Returns:
            Dictionary of concept_id -> results
        """
        batch_results = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit tasks
            future_to_concept = {}
            for idx, concept in enumerate(batch_concepts):
                concept_id = f"concept_{start_index + idx:06d}"
                future = executor.submit(
                    self.distiller.distill_concept,
                    concept,
                    concept_id
                )
                future_to_concept[future] = (concept_id, concept)

            # Collect results
            completed = 0
            for future in as_completed(future_to_concept):
                concept_id, concept = future_to_concept[future]
                try:
                    result = future.result()
                    batch_results[concept_id] = result

                    # Simple status display
                    status_symbol = "✓" if result.status == "success" else "✗"
                    completed += 1

                    if completed % 1000 == 0 or completed == len(batch_concepts):
                        success_count = sum(1 for r in batch_results.values() if r.status == "success")
                        print(f"  Completed: {completed}/{len(batch_concepts)} (Success: {success_count}) {status_symbol}")

                except Exception as e:
                    batch_results[concept_id] = ConceptDistillationResult(
                        status="exception",
                        concept_id=concept_id,
                        concept_name=concept,
                        error_details=str(e)
                    )
                    print(f"  Exception: {concept_id} - {str(e)}")

        return batch_results

    def _save_batch_results(
        self,
        batch_results: Dict[str, ConceptDistillationResult],
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
        filename = f"concept_distillation_batch_{batch_num:03d}_{timestamp}.pkl"
        filepath = self.output_dir / filename

        # Calculate statistics
        total_count = len(batch_results)
        success_count = sum(1 for r in batch_results.values() if r.status == "success")
        total_questions = sum(
            len(r.generated_questions) for r in batch_results.values()
            if r.status == "success" and r.generated_questions
        )

        # Convert dataclasses to dictionaries for serialization
        serializable_results = {
            k: (asdict(v) if isinstance(v, ConceptDistillationResult) else v)
            for k, v in batch_results.items()
        }

        save_data = {
            "metadata": {
                "batch_num": batch_num,
                "timestamp": timestamp,
                "start_time": start_time,
                "total_concepts": total_count,
                "successful_distillations": success_count,
                "total_questions_generated": total_questions
            },
            "results": serializable_results
        }

        # Save to file
        with open(filepath, 'wb') as f:
            pickle.dump(save_data, f)

        print(f"  Batch results saved to: {filename}")
        print(f"  Success: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
        print(f"  Total questions generated: {total_questions}")

        return filepath


def distill_concept_graph(
    concept_graph_dict: Dict[str, List[str]],
    personalities: List[str],
    api_client: APIClient,
    max_workers: int = 10,
    batch_size: int = 20,
    output_dir: str = "concept_distillation"
) -> Dict[str, ConceptDistillationResult]:
    """
    Convenience function to distill a concept graph.

    Args:
        concept_graph_dict: Dictionary of concept -> neighbors
        personalities: List of customer personality descriptions
        api_client: Configured API client
        max_workers: Number of concurrent workers
        batch_size: Number of concepts per batch
        output_dir: Directory for saving results

    Returns:
        Dictionary of concept_id -> ConceptDistillationResult
    """
    print(f"Preparing to distill concept graph: {len(concept_graph_dict)} concepts")
    print(f"Using {len(personalities)} different customer personas")

    # Initialize distiller
    distiller = ConceptDistiller(api_client, personalities)
    batch_distiller = BatchConceptDistiller(distiller, output_dir=output_dir)

    # Batch distill
    results = batch_distiller.distill_concept_graph(
        concept_graph_dict=concept_graph_dict,
        max_workers=max_workers,
        batch_size=batch_size,
        batch_delay=1
    )

    return results


def test_single_concept_distillation(
    concept: str,
    personalities: List[str],
    api_client: APIClient,
    verbose: bool = True
) -> ConceptDistillationResult:
    """
    Test distillation for a single concept.

    Args:
        concept: The concept to test
        personalities: List of customer personality descriptions
        api_client: Configured API client
        verbose: Whether to print detailed output

    Returns:
        ConceptDistillationResult
    """
    if verbose:
        print("=" * 80)
        print("Single Concept Distillation Test")
        print("=" * 80)
        print(f"Concept: {concept}")
        print(f"Available personalities: {len(personalities)}")
        print()

    distiller = ConceptDistiller(api_client, personalities)
    result = distiller.distill_concept(concept, "test_concept_001")

    if verbose:
        print(f"Status: {result.status}")
        print(f"Processing time: {result.processing_time:.2f}s")
        if result.status == "success" and result.generated_questions:
            print(f"Generated questions: {len(result.generated_questions)}")
            for i, q in enumerate(result.generated_questions, 1):
                print(f"\nQuestion {i}:")
                print(f"  {q.get('question', 'N/A')}")
        elif result.error_details:
            print(f"Error: {result.error_details}")

    return result
