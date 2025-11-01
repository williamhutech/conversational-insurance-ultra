"""
Embedding service for original policy text using OpenAI text-embedding-3-large.
Uses 2000 dimensions to match taxonomy embedding configuration.
"""

import asyncio
import time
from typing import List, Optional
from openai import AsyncOpenAI

from .config import TaxonomyLoaderConfig


class OriginalTextEmbeddingService:
    """
    Embedding service for original policy text.
    Uses text-embedding-3-large (2000 dimensions) to match taxonomy configuration.
    """

    def __init__(self, config: TaxonomyLoaderConfig):
        """
        Initialize embedding service.

        Args:
            config: TaxonomyLoaderConfig with OpenAI API key
        """
        self.config = config
        self.client = AsyncOpenAI(api_key=config.openai_api_key)

        # Use model and dimensions from config (matching taxonomy)
        self.model = config.openai_embedding_model  # text-embedding-3-large
        self.dimensions = config.embedding_dimensions  # 2000
        self.max_tokens = 8191  # Maximum context length for text-embedding-3-* models

        # Rate limiting
        self.rpm_limit = config.openai_rpm_limit
        self.requests_made = 0
        self.window_start = time.time()

    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a single text chunk.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (config.embedding_dimensions) or None on failure
        """
        if not text or not text.strip():
            return None

        try:
            await self._wait_for_rate_limit()

            response = await self.client.embeddings.create(
                model=self.model,
                input=text.strip(),
                dimensions=self.dimensions
            )

            embedding = response.data[0].embedding
            return embedding

        except Exception as e:
            print(f"❌ Failed to generate embedding: {e}")
            return None

    async def generate_embeddings_batch(
        self,
        texts: List[str],
        verbose: bool = True
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts concurrently.

        Args:
            texts: List of texts to embed
            verbose: Enable progress logging

        Returns:
            List of embedding vectors (same length as input)
        """
        if verbose:
            print(f"⚡ Generating {len(texts)} embeddings with {self.model} ({self.dimensions}D)...")

        tasks = [self.generate_embedding(text) for text in texts]
        embeddings = await asyncio.gather(*tasks)

        if verbose:
            success_count = sum(1 for emb in embeddings if emb is not None)
            print(f"✓ Generated {success_count}/{len(embeddings)} embeddings")

        return embeddings

    async def _wait_for_rate_limit(self):
        """
        Implement rate limiting to avoid exceeding OpenAI API limits.
        Simple token bucket algorithm.
        """
        self.requests_made += 1

        elapsed = time.time() - self.window_start
        if elapsed < 60:  # Within the same minute
            if self.requests_made >= self.rpm_limit:
                sleep_time = 60 - elapsed
                if self.config.verbose:
                    print(f"⏳ Rate limit reached. Waiting {sleep_time:.1f}s...")
                await asyncio.sleep(sleep_time)
                self.requests_made = 0
                self.window_start = time.time()
        else:
            # New minute window
            self.requests_made = 1
            self.window_start = time.time()

    async def close(self):
        """Close the OpenAI client"""
        await self.client.close()


async def batch_generate_with_retry(
    service: OriginalTextEmbeddingService,
    texts: List[str],
    max_retries: int = 3,
    verbose: bool = True
) -> List[Optional[List[float]]]:
    """
    Generate embeddings with automatic retry logic.

    Args:
        service: OriginalTextEmbeddingService instance
        texts: List of texts to embed
        max_retries: Maximum number of retry attempts
        verbose: Enable progress logging

    Returns:
        List of embeddings (None for failed items)
    """
    embeddings = await service.generate_embeddings_batch(texts, verbose)

    # Retry failed embeddings
    for attempt in range(max_retries):
        failed_indices = [i for i, emb in enumerate(embeddings) if emb is None]

        if not failed_indices:
            break  # All succeeded

        if verbose and failed_indices:
            print(f"⚠️  Retrying {len(failed_indices)} failed embeddings (attempt {attempt + 1}/{max_retries})...")

        # Retry only failed items
        failed_texts = [texts[i] for i in failed_indices]
        retry_embeddings = await service.generate_embeddings_batch(failed_texts, verbose=False)

        # Update results
        for idx, emb in zip(failed_indices, retry_embeddings):
            embeddings[idx] = emb

        # Wait before next retry
        if failed_indices and attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)  # Exponential backoff

    return embeddings
