"""
Concept Graph Entity
Graph structure for managing insurance concepts with embedding-based deduplication.
"""

from typing import Dict, List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer


class ConceptGraph:
    """
    Graph structure for managing insurance concepts with semantic deduplication.

    The graph maintains:
    - Adjacency dictionary for concept relationships
    - Embedding vectors for all concepts
    - Concept mapping table for deduplication
    - Similarity-based duplicate detection

    Attributes:
        model: SentenceTransformer model for embeddings
        graph: Adjacency dictionary {concept: [neighbor_concepts]}
        concept_embeddings: Mapping of concept to embedding vector
        concept_mapping: Mapping of similar concepts to canonical concept
        similarity_threshold: Cosine similarity threshold for deduplication
    """

    def __init__(
        self,
        seed_concepts: List[str],
        model: SentenceTransformer,
        similarity_threshold: float
    ):
        """
        Initialize graph from seed concepts.

        Args:
            seed_concepts: List of seed concepts (externally deduplicated)
            model: SentenceTransformer model instance
            similarity_threshold: Similarity threshold for deduplication (0-1)
        """
        if model is None:
            raise ValueError("Model parameter cannot be None. Load model using embedding_utils.load_embedding_model()")

        self.model = model
        self.graph: Dict[str, List[str]] = {}
        self.concept_embeddings: Dict[str, np.ndarray] = {}
        self.concept_mapping: Dict[str, str] = {}
        self.similarity_threshold = similarity_threshold

        # Clean seed concepts
        cleaned_seeds = [concept.strip() for concept in seed_concepts if concept.strip()]

        print(f"Calculating embeddings for {len(cleaned_seeds)} seed concepts...")

        # Batch calculate embeddings
        if cleaned_seeds:
            seed_embeddings = self.model.encode(cleaned_seeds)

            # Build initial graph, embedding library, and mapping table
            for concept, embedding in zip(cleaned_seeds, seed_embeddings):
                self.graph[concept] = []
                self.concept_embeddings[concept] = embedding
                self.concept_mapping[concept] = concept  # Self-mapping

        print(f"Concept graph initialization complete. Seed concepts: {len(cleaned_seeds)}")

    @classmethod
    def from_graph_dict(
        cls,
        graph_dict: Dict[str, List[str]],
        concept_mapping: Dict[str, str],
        model: SentenceTransformer,
        similarity_threshold: float
    ) -> 'ConceptGraph':
        """
        Reconstruct ConceptGraph from saved dictionary.

        Args:
            graph_dict: Saved adjacency dictionary
            concept_mapping: Mapping of similar concepts
            model: SentenceTransformer model instance
            similarity_threshold: Similarity threshold for deduplication

        Returns:
            Reconstructed ConceptGraph instance
        """
        if model is None:
            raise ValueError("Model parameter cannot be None")

        # Create instance without initialization
        instance = cls.__new__(cls)
        instance.model = model
        instance.graph = graph_dict.copy()
        instance.concept_embeddings = {}
        instance.concept_mapping = concept_mapping
        instance.similarity_threshold = similarity_threshold

        # Recalculate embeddings for all concepts
        all_concepts = list(graph_dict.keys())
        if all_concepts:
            print(f"Recalculating embeddings for {len(all_concepts)} concepts...")
            all_embeddings = model.encode(all_concepts)

            for concept, embedding in zip(all_concepts, all_embeddings):
                instance.concept_embeddings[concept] = embedding

            print("ConceptGraph reconstruction complete")

        return instance

    def _get_target_concept(self, concept: str) -> Optional[str]:
        """
        Get canonical concept from mapping.

        Args:
            concept: Concept to look up

        Returns:
            Canonical concept if exists, None otherwise
        """
        return self.concept_mapping.get(concept)

    def _is_similar_to_existing(
        self,
        new_concept: str,
        new_embedding: np.ndarray
    ) -> Optional[str]:
        """
        Check if new concept is similar to existing ones.

        Args:
            new_concept: New concept string
            new_embedding: Embedding vector for new concept

        Returns:
            Similar existing concept if found, None otherwise
        """
        if not self.concept_embeddings:
            return None

        # Get existing concepts and embeddings
        existing_concepts = list(self.concept_embeddings.keys())
        existing_embeddings = np.array([
            self.concept_embeddings[concept]
            for concept in existing_concepts
        ])

        # Calculate cosine similarity
        similarities = self.model.similarity([new_embedding], existing_embeddings)[0]

        # Find most similar concept
        max_similarity_idx = np.argmax(similarities)
        max_similarity = similarities[max_similarity_idx]

        if max_similarity >= self.similarity_threshold:
            return existing_concepts[max_similarity_idx]

        return None

    def get_current_adjacency(self) -> Dict[str, List[str]]:
        """Get current adjacency dictionary (copy)."""
        return self.graph.copy()

    def calculate_metrics(self, expansion_results: Dict) -> Dict[str, float]:
        """
        Calculate expansion metrics.

        Args:
            expansion_results: Dictionary of expansion results

        Returns:
            Dictionary with connectivity_rate metric
        """
        # Collect all new concepts
        all_new_concepts = []
        for result in expansion_results.values():
            if result.status == "success" and result.new_concepts:
                all_new_concepts.extend(result.new_concepts)

        if not all_new_concepts:
            return {"connectivity_rate": 0.0}

        existing_concepts = set(self.graph.keys())

        # Calculate connectivity: new edges between old nodes / total existing edges
        old_total_edges = sum(len(neighbors) for neighbors in self.graph.values()) // 2

        # Count new edges between old nodes
        new_edges_between_old_nodes = 0
        for result in expansion_results.values():
            if result.status == "success" and result.new_concepts:
                center_concept = result.center_concept
                for new_concept in result.new_concepts:
                    if (new_concept in existing_concepts and
                        center_concept != new_concept and
                        new_concept not in self.graph.get(center_concept, [])):
                        new_edges_between_old_nodes += 1

        connectivity_rate = (
            new_edges_between_old_nodes / old_total_edges
            if old_total_edges > 0
            else float('inf')
        )

        return {"connectivity_rate": connectivity_rate}

    def update_graph(self, expansion_results: Dict) -> tuple:
        """
        Update graph structure with new expansion results.

        Uses concept mapping for efficient deduplication.

        Args:
            expansion_results: Dictionary of expansion results

        Returns:
            Tuple of (nodes_added, edges_added, embedding_duplicates, concept_add_rate)
        """
        nodes_added = 0
        edges_added = 0
        embedding_duplicates = 0

        # Collect all new concepts
        all_new_concepts = []
        concept_to_centers: Dict[str, List[str]] = {}  # Map concept to its center concepts

        for result in expansion_results.values():
            if result.status == "success" and result.new_concepts:
                center_concept = result.center_concept
                for new_concept in result.new_concepts:
                    if new_concept.strip():
                        cleaned_concept = new_concept.strip()
                        all_new_concepts.append(cleaned_concept)
                        if cleaned_concept not in concept_to_centers:
                            concept_to_centers[cleaned_concept] = []
                        concept_to_centers[cleaned_concept].append(center_concept)

        if not all_new_concepts:
            return nodes_added, edges_added, embedding_duplicates, 0.0

        num_all_new_concepts = len(all_new_concepts)
        print(f"Received {num_all_new_concepts} new concepts (not deduplicated)")

        # Use mapping to quickly filter known concepts
        concepts_need_embedding = []
        concept_targets: Dict[str, str] = {}  # concept -> target_concept mapping

        for concept in all_new_concepts:
            target = self._get_target_concept(concept)
            if target is not None:
                # Known concept, use mapping directly
                concept_targets[concept] = target
                if target != concept:
                    embedding_duplicates += 1
            else:
                # New concept that needs embedding calculation
                concepts_need_embedding.append(concept)

        # Calculate embeddings only for unknown concepts
        if concepts_need_embedding:
            unique_concepts = list(set(concepts_need_embedding))
            print(f"Performing embedding-based deduplication on {len(unique_concepts)} new concepts...")
            new_embeddings = self.model.encode(unique_concepts)

            # Process concepts one by one
            total_concepts = len(unique_concepts)
            for idx, (new_concept, new_embedding) in enumerate(zip(unique_concepts, new_embeddings), 1):
                # Print progress every 500 concepts
                if idx % 500 == 0 or idx == total_concepts:
                    print(f"  Processing progress: {idx}/{total_concepts} ({idx/total_concepts*100:.1f}%)")

                # Check if similar to existing concepts
                similar_concept = self._is_similar_to_existing(new_concept, new_embedding)

                if similar_concept:
                    # Found similar concept, create mapping
                    self.concept_mapping[new_concept] = similar_concept
                    concept_targets[new_concept] = similar_concept
                    embedding_duplicates += 1
                else:
                    # Brand new concept, add to graph
                    self.graph[new_concept] = []
                    self.concept_embeddings[new_concept] = new_embedding
                    self.concept_mapping[new_concept] = new_concept
                    concept_targets[new_concept] = new_concept
                    nodes_added += 1

        # Add edges (connecting to all relevant center concepts)
        for concept in all_new_concepts:
            target_concept = concept_targets[concept]

            for center_concept in concept_to_centers[concept]:
                # Ensure center concept exists in graph
                if center_concept in self.graph:
                    # Bidirectional connection
                    if target_concept not in self.graph[center_concept]:
                        self.graph[center_concept].append(target_concept)
                        edges_added += 1

                    if center_concept not in self.graph[target_concept]:
                        self.graph[target_concept].append(center_concept)
                        edges_added += 1

        print(f"Deduplication complete: Nodes added {nodes_added}, Edges added {edges_added//2}, Deduplicated concepts {embedding_duplicates}")

        # Undirected graph, so divide edge count by 2
        concept_add_rate = nodes_added / num_all_new_concepts
        return nodes_added, edges_added // 2, embedding_duplicates, concept_add_rate

    def get_graph_stats(self) -> Dict[str, int]:
        """
        Get graph statistics.

        Returns:
            Dictionary with node and edge counts
        """
        node_count = len(self.graph)
        edge_count = sum(len(neighbors) for neighbors in self.graph.values()) // 2
        return {"nodes": node_count, "edges": edge_count}

    def save_to_dict(self) -> Dict:
        """
        Export graph to dictionary format for serialization.

        Returns:
            Dictionary with graph, mapping, and metadata
        """
        return {
            "graph": self.graph,
            "concept_mapping": self.concept_mapping,
            "similarity_threshold": self.similarity_threshold,
            "stats": self.get_graph_stats()
        }
