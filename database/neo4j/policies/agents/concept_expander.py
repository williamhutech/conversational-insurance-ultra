"""
Concept Expander Agent (Stage 4)
Iteratively expands concept graph by generating related concepts.
"""

import os
import time
import pickle
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..utils.api_client import APIClient
from ..utils.response_validator import ResponseValidator
from ..entities.data_models import ConceptExpansionResult
from ..entities.concept_graph import ConceptGraph


class ExpansionPromptTemplate:
    """Prompt template for concept expansion."""

    @staticmethod
    def get_system_prompt() -> str:
        """Get system prompt for concept expansion."""
        return """You are an insurance translator bridging technical policy language with customer understanding.

Your task is to expand concept graphs by generating plain-language terms that customers actually use when thinking about insurance, while maintaining connections to precise technical concepts for compliance."""

    @staticmethod
    def get_expansion_prompt(center_concept: str, neighbors: List[str]) -> str:
        """
        Get expansion prompt for generating new concepts.

        Args:
            center_concept: The concept to expand
            neighbors: Existing neighbor concepts

        Returns:
            Formatted expansion prompt
        """
        neighbors_text = ", ".join(neighbors) if neighbors else "None"

        return f"""**Task: Generate customer-friendly concepts related to the center concept**

**Domain**: Insurance explained in everyday language
**Relationship requirement**: New concepts must help customers understand "{center_concept}" through familiar terms, real-world scenarios, or common questions

**Center concept**: {center_concept}
**Existing neighbor concepts**: {neighbors_text}

**Output format (strictly follow JSON format):**

{{
"center_concept": "{center_concept}",
"new_concepts": [
    "concept1",
    "concept2",
    "concept3",
    "..."
]
}}

If no new concepts can be generated:

{{
"center_concept": "{center_concept}",
"new_concepts": ["NO NEW CONCEPTS"]
}}

**Instructions**:

1. **Prioritize customer language**: Generate terms customers use when asking about "{center_concept}" (e.g., for "deductible" → "out-of-pocket cost", "what I pay first", "upfront payment")
2. **Include real-world scenarios**: Situations where "{center_concept}" matters (e.g., for "claim denial" → "rejected claim", "appeal process", "what happens if denied")
3. **Add common questions**: What customers ask about "{center_concept}" (e.g., for "premium" → "monthly cost", "how much do I pay", "price comparison")
4. **Bridge technical terms**: When generating industry terms, pair with plain equivalents (e.g., "copayment (fixed fee per visit)")
5. Avoid repeating existing neighbors: {neighbors_text}
6. Use simple, conversational phrases over jargon
7. Focus on concepts that help customers make coverage decisions or understand their rights
8. Ensure concepts remain semantically accurate to maintain compliance"""


class ConceptExpander:
    """
    Expand a single concept by generating related concepts.

    Uses LLM to generate new insurance concepts that are strongly
    related to a given center concept, avoiding duplicates with
    existing neighbors.
    """

    def __init__(self, api_client: APIClient):
        """
        Initialize concept expander.

        Args:
            api_client: Configured API client
        """
        self.api_client = api_client
        self.template = ExpansionPromptTemplate()
        self.validator = ResponseValidator()

    def expand_single_concept(
        self,
        center_concept: str,
        neighbors: List[str],
        concept_id: str
    ) -> ConceptExpansionResult:
        """
        Expand a single concept.

        Args:
            center_concept: The concept to expand
            neighbors: Existing neighbor concepts
            concept_id: Unique identifier for tracking

        Returns:
            ConceptExpansionResult with new concepts
        """
        start_time = time.time()

        # Create messages
        system_prompt = self.template.get_system_prompt()
        user_prompt = self.template.get_expansion_prompt(center_concept, neighbors)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Call API
        api_result = self.api_client.call_api(messages, timeout=120)
        processing_time = time.time() - start_time

        if api_result["status"] != "success":
            return ConceptExpansionResult(
                status="api_error",
                concept_id=concept_id,
                center_concept=center_concept,
                existing_neighbors=neighbors,
                error_details=api_result.get("error", "API call failed"),
                processing_time=processing_time
            )

        # Validate JSON response
        expected_keys = ["center_concept", "new_concepts"]
        json_validation = self.validator.validate_json_response(
            api_result["content"],
            expected_keys
        )

        if json_validation["is_valid_json"]:
            returned_center = json_validation["parsed_json"]["center_concept"]
            new_concepts = json_validation["parsed_json"]["new_concepts"]

            # Check for "NO NEW CONCEPTS" marker
            if len(new_concepts) == 1 and new_concepts[0].strip() == "NO NEW CONCEPTS":
                return ConceptExpansionResult(
                    status="success",
                    concept_id=concept_id,
                    center_concept=center_concept,
                    existing_neighbors=neighbors,
                    new_concepts=[],  # Empty list indicates no new concepts
                    processing_time=processing_time
                )

            # Process new concepts - strip whitespace
            new_concepts = [concept.strip() for concept in new_concepts if concept.strip()]

            return ConceptExpansionResult(
                status="success",
                concept_id=concept_id,
                center_concept=center_concept,
                existing_neighbors=neighbors,
                new_concepts=new_concepts,
                processing_time=processing_time
            )
        else:
            return ConceptExpansionResult(
                status="json_error",
                concept_id=concept_id,
                center_concept=center_concept,
                existing_neighbors=neighbors,
                error_details=f"JSON validation failed: {json_validation['error_type']}",
                processing_time=processing_time
            )


class BatchConceptExpander:
    """
    Batch process multiple concepts for expansion.

    Processes concepts in parallel, saves results, and provides
    progress tracking and statistics.
    """

    def __init__(
        self,
        expander: ConceptExpander,
        output_dir: str = "concept_expansion"
    ):
        """
        Initialize batch expander.

        Args:
            expander: ConceptExpander instance
            output_dir: Directory for saving results
        """
        self.expander = expander
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def expand_concepts_batch(
        self,
        adjacency_dict: Dict[str, List[str]],
        max_workers: int = 10
    ) -> Dict[str, ConceptExpansionResult]:
        """
        Expand all concepts in adjacency dictionary.

        Args:
            adjacency_dict: Dictionary of concept -> neighbors
            max_workers: Number of concurrent workers

        Returns:
            Dictionary of concept_id -> ConceptExpansionResult
        """
        concepts_to_expand = list(adjacency_dict.keys())
        total_concepts = len(concepts_to_expand)

        print(f"Starting batch concept expansion for {total_concepts} concepts")
        print(f"Max concurrency: {max_workers}")

        batch_start_time = time.time()
        batch_results = self._process_batch(concepts_to_expand, adjacency_dict, max_workers)
        batch_end_time = time.time()

        print(f"Processing complete, time taken: {batch_end_time - batch_start_time:.2f} seconds")
        return batch_results

    def _process_batch(
        self,
        batch_concepts: List[str],
        adjacency_dict: Dict[str, List[str]],
        max_workers: int
    ) -> Dict[str, ConceptExpansionResult]:
        """
        Process a batch of concepts in parallel.

        Args:
            batch_concepts: List of concepts to expand
            adjacency_dict: Dictionary of concept -> neighbors
            max_workers: Number of concurrent workers

        Returns:
            Dictionary of concept_id -> results
        """
        batch_results = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit tasks
            future_to_concept = {}
            for idx, concept in enumerate(batch_concepts):
                concept_id = f"concept_{idx:06d}"
                neighbors = adjacency_dict.get(concept, [])
                future = executor.submit(
                    self.expander.expand_single_concept,
                    concept,
                    neighbors,
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

                    # Progress display
                    status_symbol = "✓" if result.status == "success" else "✗"
                    completed += 1

                    if completed % 1000 == 0 or completed == len(batch_concepts):
                        success_count = sum(1 for r in batch_results.values() if r.status == "success")
                        print(f"  Completed: {completed}/{len(batch_concepts)} (Success: {success_count}) {status_symbol}")

                except Exception as e:
                    batch_results[concept_id] = ConceptExpansionResult(
                        status="exception",
                        concept_id=concept_id,
                        center_concept=concept,
                        existing_neighbors=adjacency_dict.get(concept, []),
                        error_details=str(e)
                    )
                    print(f"  Exception: {concept_id} - {str(e)}")

        return batch_results

    def save_results(
        self,
        batch_results: Dict[str, ConceptExpansionResult],
        start_time: float
    ) -> str:
        """
        Save batch results to file.

        Args:
            batch_results: Dictionary of results
            start_time: Batch start timestamp

        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"concept_expansion_results_{timestamp}.pkl"
        filepath = os.path.join(self.output_dir, filename)

        # Calculate statistics
        total_count = len(batch_results)
        success_count = sum(1 for r in batch_results.values() if r.status == "success")
        error_count = total_count - success_count

        # Count new concepts
        total_new_concepts = sum(
            len(r.new_concepts) for r in batch_results.values()
            if r.status == "success" and r.new_concepts
        )

        # Count skipped concepts (no new concepts)
        skipped_concepts = sum(
            1 for r in batch_results.values()
            if r.status == "success" and r.new_concepts is not None and len(r.new_concepts) == 0
        )

        # Prepare save data
        save_data = {
            "metadata": {
                "timestamp": timestamp,
                "start_time": start_time,
                "total_concepts": total_count,
                "successful_expansions": success_count,
                "failed_expansions": error_count,
                "success_rate": success_count / total_count if total_count > 0 else 0,
                "total_new_concepts": total_new_concepts,
                "skipped_concepts": skipped_concepts
            },
            "results": batch_results
        }

        # Save to file
        with open(filepath, 'wb') as f:
            pickle.dump(save_data, f)

        print(f"  Results saved to: {filename}")
        print(f"  Success: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
        print(f"  Total new concepts: {total_new_concepts}")
        print(f"  Skipped concepts: {skipped_concepts}")

        return filepath


def run_concept_expansion_iteration(
    api_client: APIClient,
    concept_graph: ConceptGraph,
    max_workers: int = 10
) -> Dict:
    """
    Run a single concept expansion iteration.

    Args:
        api_client: Configured API client
        concept_graph: ConceptGraph instance to expand
        max_workers: Number of concurrent workers

    Returns:
        Dictionary with iteration results and statistics
    """
    # Initialize expander
    expander = ConceptExpander(api_client)
    batch_expander = BatchConceptExpander(expander)

    # Get current adjacency dictionary
    current_adjacency = concept_graph.get_current_adjacency()

    # Batch expand concepts
    expansion_results = batch_expander.expand_concepts_batch(
        adjacency_dict=current_adjacency,
        max_workers=max_workers
    )

    # Calculate metrics
    metrics = concept_graph.calculate_metrics(expansion_results)

    # Update graph with embedding-based deduplication
    nodes_added, edges_added, embedding_duplicates, concept_add_rate = concept_graph.update_graph(expansion_results)

    # Get updated graph statistics
    graph_stats = concept_graph.get_graph_stats()

    # Count skipped concepts
    skipped_count = sum(
        1 for r in expansion_results.values()
        if r.status == "success" and r.new_concepts is not None and len(r.new_concepts) == 0
    )

    # Print results
    print(f"\n=== Iteration Complete ===")
    print(f"Concept Add Rate: {concept_add_rate:.3f}")
    print(f"Concept Connectivity Rate: {metrics['connectivity_rate']:.3f}")
    print(f"Nodes at end of iteration: {graph_stats['nodes']}")
    print(f"Edges at end of iteration: {graph_stats['edges']}")
    print(f"Nodes added this round: {nodes_added}")
    print(f"Edges added this round: {edges_added}")
    print(f"Skipped concepts: {skipped_count}")

    return {
        "concept_add_rate": concept_add_rate,
        "connectivity_rate": metrics['connectivity_rate'],
        "graph_stats": graph_stats,
        "nodes_added": nodes_added,
        "edges_added": edges_added,
        "embedding_duplicates": embedding_duplicates,
        "skipped_count": skipped_count,
        "expansion_results": expansion_results
    }


def run_multiple_iterations(
    api_client: APIClient,
    concept_graph: ConceptGraph,
    max_iterations: int = 10,
    max_workers: int = 10,
    concept_add_threshold: float = 0.05,
    connectivity_threshold: float = 0.2
) -> Tuple[List[Dict], Dict[int, Dict]]:
    """
    Run multiple concept expansion iterations until convergence.

    Args:
        api_client: Configured API client
        concept_graph: ConceptGraph instance
        max_iterations: Maximum number of iterations
        max_workers: Number of concurrent workers
        concept_add_threshold: Stop if concept add rate < threshold
        connectivity_threshold: Stop if connectivity rate < threshold

    Returns:
        Tuple of (iteration_results, iteration_snapshots)
        - iteration_results: List of iteration metrics
        - iteration_snapshots: Dict mapping iteration number (1-indexed) to graph adjacency dict
    """
    iteration_results = []
    iteration_snapshots = {}  # Store graph snapshots after each iteration

    for iteration in range(max_iterations):
        print(f"\n{'='*60}")
        print(f"ITERATION {iteration + 1}/{max_iterations}")
        print(f"{'='*60}")

        # Run iteration
        result = run_concept_expansion_iteration(
            api_client=api_client,
            concept_graph=concept_graph,
            max_workers=max_workers
        )

        iteration_results.append(result)

        # Capture graph snapshot after this iteration (1-indexed)
        iteration_snapshots[iteration + 1] = concept_graph.get_current_adjacency()

        # Check convergence
        concept_add_rate = result['concept_add_rate']
        connectivity_rate = result['connectivity_rate']

        if (concept_add_rate < concept_add_threshold) or (connectivity_rate < connectivity_threshold):
            print(f"\nStopping: Convergence criteria met")
            print(f"  Concept add rate ({concept_add_rate:.3f}) < {concept_add_threshold}")
            print(f"  OR Connectivity rate ({connectivity_rate:.3f}) < {connectivity_threshold}")
            break

    print(f"\n{'='*60}")
    print(f"EXPANSION COMPLETE: {len(iteration_results)} iterations")
    print(f"{'='*60}")

    return iteration_results, iteration_snapshots
