"""
Fact Integrator Agent (Stage 6)
Integrates facts into concept graphs using embedding-based similarity.
"""

import time
import numpy as np
from typing import Dict, List
from sentence_transformers import SentenceTransformer


class FactGraphIntegrator:
    """
    Integrate facts into concept graphs based on semantic similarity.

    Uses pre-computed embeddings to efficiently connect facts to the
    top-k most similar concepts in both main and sub-concept graphs.
    """

    def __init__(self, embedding_model_name: str, device: str = 'cuda'):
        """
        Initialize fact-graph integrator with embedding model.

        Args:
            embedding_model_name: Name of the sentence transformer model
            device: Device to use ('cuda', 'mps', or 'cpu')
        """
        import torch

        self.device = device if torch.cuda.is_available() else 'mps'
        
        print(f"Initialize model, use device: {self.device}")

        self.model = SentenceTransformer(
            embedding_model_name,
            trust_remote_code=True,
            device=self.device
        )

        print("Model initialization completed")

    def add_products_to_graphs(
        self,
        concept_dict: Dict[str, List[str]],
        sub_concept_dict: Dict[str, List[str]],
        insurance_product_names: List[str]
    ) -> tuple:
        """
        Add insurance products as nodes to both concept graphs.

        Args:
            concept_dict: Main concept graph dictionary
            sub_concept_dict: Sub-concept graph dictionary
            insurance_product_names: List of product names to add

        Returns:
            Tuple of (updated concept_dict, updated sub_concept_dict)
        """
        for product in insurance_product_names:
            if product not in concept_dict:
                concept_dict[product] = []
            if product not in sub_concept_dict:
                sub_concept_dict[product] = []

        print(f"Added {len(insurance_product_names)} products to graphs")
        return concept_dict, sub_concept_dict

    def integrate_facts_with_graphs(
        self,
        seed_facts: List[str],
        concept_dict: Dict[str, List[str]],
        sub_concept_dict: Dict[str, List[str]],
        top_k: int = 5,
        batch_size: int = 32
    ) -> tuple:
        """
        Efficiently integrate facts into concept graphs using pre-computed embeddings.

        Connects each fact to the top-k most similar concepts in both graphs
        using cosine similarity of embeddings.

        Args:
            seed_facts: List of fact strings
            concept_dict: Main concept graph dictionary
            sub_concept_dict: Sub-concept graph dictionary
            top_k: Number of top similar nodes to connect (default: 5)
            batch_size: Batch size for encoding (default: 32)

        Returns:
            Tuple of (updated concept_dict, updated sub_concept_dict)
        """
        print("Pre-computing node embeddings...")
        start_time = time.time()

        # Get all unique nodes from both dictionaries
        all_concept_nodes = list(concept_dict.keys())
        all_sub_nodes = list(sub_concept_dict.keys())

        # Pre-compute embeddings for all existing nodes (one-time cost)
        concept_embeddings = self.model.encode(
            all_concept_nodes,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True
        )

        sub_embeddings = self.model.encode(
            all_sub_nodes,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True
        )

        print(f"Node embeddings computed in {time.time() - start_time:.2f} seconds")

        # Encode all facts in batches
        print("Encoding facts...")
        fact_embeddings = self.model.encode(
            seed_facts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True
        )

        print(f"Processing {len(seed_facts)} facts...")

        # Compute all similarities at once using matrix multiplication
        if len(all_concept_nodes) > 0:
            concept_similarities = np.dot(fact_embeddings, concept_embeddings.T)
        else:
            concept_similarities = np.array([])

        if len(all_sub_nodes) > 0:
            sub_similarities = np.dot(fact_embeddings, sub_embeddings.T)
        else:
            sub_similarities = np.array([])

        # Process each fact with pre-computed similarities
        for idx, fact in enumerate(seed_facts):
            if (idx + 1) % 100 == 0:
                print(f"Processed {idx + 1}/{len(seed_facts)} facts")

            # Get top-k similar nodes from pre-computed similarities
            top_concept_nodes = []
            if len(all_concept_nodes) > 0:
                top_concept_indices = np.argsort(concept_similarities[idx])[-top_k:][::-1]
                top_concept_nodes = [
                    all_concept_nodes[i]
                    for i in top_concept_indices[:min(top_k, len(all_concept_nodes))]
                ]

            top_sub_nodes = []
            if len(all_sub_nodes) > 0:
                top_sub_indices = np.argsort(sub_similarities[idx])[-top_k:][::-1]
                top_sub_nodes = [
                    all_sub_nodes[i]
                    for i in top_sub_indices[:min(top_k, len(all_sub_nodes))]
                ]

            # Add fact as a new node with connections to top similar nodes
            if fact not in concept_dict:
                concept_dict[fact] = top_concept_nodes
            else:
                concept_dict[fact].extend(top_concept_nodes)
                concept_dict[fact] = list(set(concept_dict[fact]))  # Remove duplicates

            if fact not in sub_concept_dict:
                sub_concept_dict[fact] = top_sub_nodes
            else:
                sub_concept_dict[fact].extend(top_sub_nodes)
                sub_concept_dict[fact] = list(set(sub_concept_dict[fact]))  # Remove duplicates

            # Update connected nodes to include the fact (bidirectional connection)
            for node in top_concept_nodes:
                if node in concept_dict:
                    if fact not in concept_dict[node]:
                        concept_dict[node].append(fact)

            for node in top_sub_nodes:
                if node in sub_concept_dict:
                    if fact not in sub_concept_dict[node]:
                        sub_concept_dict[node].append(fact)

        print(f"Completed integrating {len(seed_facts)} facts into graphs in {time.time() - start_time:.2f} seconds")
        return concept_dict, sub_concept_dict

    def save_graphs(
        self,
        concept_dict: Dict[str, List[str]],
        sub_concept_dict: Dict[str, List[str]],
        concept_path: str,
        sub_concept_path: str
    ):
        """
        Save concept graphs to pickle files.

        Args:
            concept_dict: Main concept graph dictionary
            sub_concept_dict: Sub-concept graph dictionary
            concept_path: Path to save concept_dict
            sub_concept_path: Path to save sub_concept_dict
        """
        import pickle

        with open(concept_path, 'wb') as f:
            pickle.dump(concept_dict, f)
        print(f"Saved concept graph to {concept_path}")

        with open(sub_concept_path, 'wb') as f:
            pickle.dump(sub_concept_dict, f)
        print(f"Saved sub-concept graph to {sub_concept_path}")
