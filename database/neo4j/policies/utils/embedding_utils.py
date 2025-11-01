"""
Embedding Utilities
Functions for loading embedding models and computing semantic similarities.
"""

import random
from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer


def load_embedding_model(
    model_name: str = "sentence-transformers/all-mpnet-base-v2",
    device: str = "cuda",
    trust_remote_code: bool = True
) -> SentenceTransformer:
    """
    Load a sentence transformer embedding model.

    Args:
        model_name: Hugging Face model identifier
        device: Device to load model on ("cuda", "mps", or "cpu")
        trust_remote_code: Whether to trust remote code from Hugging Face

    Returns:
        Loaded SentenceTransformer model
    """
    print(f"Loading embedding model: {model_name}")
    print(f"Device: {device}")

    model = SentenceTransformer(
        model_name,
        trust_remote_code=trust_remote_code,
        device=device
    )

    print("Model loaded successfully")
    return model


def generate_embeddings_batch(
    texts: Union[str, List[str]],
    model: SentenceTransformer,
    batch_size: int = 50,
    show_progress: bool = True,
    convert_to_list: bool = True
) -> Union[List, np.ndarray]:
    """
    Generate embeddings for texts in batches.

    Args:
        texts: Single text string or list of texts
        model: Loaded SentenceTransformer model
        batch_size: Batch size for encoding
        show_progress: Whether to print progress messages
        convert_to_list: Whether to convert embeddings to Python lists

    Returns:
        List of embeddings (if convert_to_list=True) or numpy array
    """
    # Handle single text
    if isinstance(texts, str):
        embedding = model.encode(texts, convert_to_tensor=False)
        return embedding.tolist() if convert_to_list else embedding

    # Batch processing for multiple texts
    all_embeddings = []
    total = len(texts)

    for i in range(0, total, batch_size):
        batch_end = min(i + batch_size, total)
        batch_texts = texts[i:batch_end]

        if show_progress:
            batch_num = i // batch_size + 1
            total_batches = (total - 1) // batch_size + 1
            print(f"  Embedding batch {batch_num}/{total_batches} ({len(batch_texts)} texts)")

        # Batch encode
        batch_embeddings = model.encode(
            batch_texts,
            convert_to_tensor=False,
            show_progress_bar=False
        )

        # Convert and store
        if convert_to_list:
            for emb in batch_embeddings:
                all_embeddings.append(emb.tolist())
        else:
            all_embeddings.append(batch_embeddings)

    if convert_to_list:
        return all_embeddings
    else:
        return np.vstack(all_embeddings)


def compute_similarity_matrix(
    embeddings1: np.ndarray,
    embeddings2: np.ndarray,
    model: SentenceTransformer
) -> np.ndarray:
    """
    Compute cosine similarity matrix between two sets of embeddings.

    Args:
        embeddings1: First set of embeddings (N x D)
        embeddings2: Second set of embeddings (M x D)
        model: SentenceTransformer model (for similarity computation)

    Returns:
        Similarity matrix (N x M)
    """
    similarities = model.similarity(embeddings1, embeddings2)
    return similarities.cpu().numpy() if hasattr(similarities, 'cpu') else similarities


def deduplicate_concepts_by_similarity(
    concepts: List[str],
    model: SentenceTransformer,
    similarity_threshold: float = 0.95,
    verbose: bool = True
) -> List[str]:
    """
    Deduplicate concepts based on embedding similarity.
    For pairs exceeding the threshold, randomly removes one.

    Args:
        concepts: List of concept strings
        model: Loaded SentenceTransformer model
        similarity_threshold: Cosine similarity threshold (0-1)
        verbose: Whether to print deduplication details

    Returns:
        Filtered list of concepts
    """
    if not concepts:
        return []

    if verbose:
        print(f"Deduplicating {len(concepts)} concepts with threshold {similarity_threshold}")

    # Generate embeddings
    embeddings = model.encode(concepts)

    # Compute similarity matrix
    similarities = model.similarity(embeddings, embeddings)
    similarities = similarities.cpu().numpy() if hasattr(similarities, 'cpu') else similarities

    # Find duplicates
    to_remove = set()
    n = len(concepts)

    for i in range(n):
        for j in range(i + 1, n):
            if similarities[i][j] > similarity_threshold:
                # Randomly choose one to remove
                remove_idx = random.choice([i, j])
                to_remove.add(remove_idx)

                if verbose:
                    print(f"Similar pair: '{concepts[i]}' vs '{concepts[j]}' (similarity: {similarities[i][j]:.4f})")
                    print(f"  -> Removing: '{concepts[remove_idx]}'")

    # Filter concepts
    filtered_concepts = [
        concept for i, concept in enumerate(concepts)
        if i not in to_remove
    ]

    if verbose:
        print(f"\nDeduplication result: {len(concepts)} -> {len(filtered_concepts)} concepts")
        print(f"Removed {len(to_remove)} similar concepts")

    return filtered_concepts


def find_most_similar(
    query_embedding: np.ndarray,
    candidate_embeddings: np.ndarray,
    candidates: List[str],
    top_k: int = 5
) -> List[tuple]:
    """
    Find top-k most similar candidates to a query embedding.

    Args:
        query_embedding: Query embedding vector
        candidate_embeddings: Matrix of candidate embeddings (N x D)
        candidates: List of candidate strings
        top_k: Number of top results to return

    Returns:
        List of (candidate, similarity_score) tuples
    """
    # Compute similarities
    similarities = np.dot(
        query_embedding.reshape(1, -1),
        candidate_embeddings.T
    ).flatten()

    # Get top-k indices
    top_indices = np.argsort(similarities)[::-1][:top_k]

    # Return (candidate, score) tuples
    results = [
        (candidates[idx], float(similarities[idx]))
        for idx in top_indices
    ]

    return results


def is_similar_to_any(
    new_embedding: np.ndarray,
    existing_embeddings: np.ndarray,
    existing_concepts: List[str],
    similarity_threshold: float = 0.8
) -> tuple:
    """
    Check if a new embedding is similar to any existing embeddings.

    Args:
        new_embedding: New embedding vector to check
        existing_embeddings: Matrix of existing embeddings (N x D)
        existing_concepts: List of concept strings corresponding to embeddings
        similarity_threshold: Similarity threshold for matching

    Returns:
        (is_similar: bool, matched_concept: str or None, max_similarity: float)
    """
    if existing_embeddings.size == 0:
        return False, None, 0.0

    # Compute similarities
    similarities = np.dot(
        new_embedding.reshape(1, -1),
        existing_embeddings.T
    ).flatten()

    # Find maximum similarity
    max_idx = np.argmax(similarities)
    max_similarity = float(similarities[max_idx])

    if max_similarity >= similarity_threshold:
        return True, existing_concepts[max_idx], max_similarity
    else:
        return False, None, max_similarity
