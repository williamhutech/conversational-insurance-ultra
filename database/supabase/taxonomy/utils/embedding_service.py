"""
Dual Embedding Service for Travel Insurance Taxonomy.
Generates separate embeddings for normalized parameters and original policy text
using OpenAI's text-embedding-3-large model (3072 dimensions).
"""

import asyncio
import time
from typing import List, Optional, Dict, Any, Tuple
from openai import AsyncOpenAI
import json

from .config import TaxonomyLoaderConfig
from .models import format_parameters_for_embedding, format_coverage_limit


class EmbeddingService:
    """
    Service for generating dual embeddings with rate limiting and retry logic.

    Generates two types of embeddings:
    1. Normalized: Structured parameters formatted as human-readable text
    2. Original: Raw policy text for legal precision
    """

    def __init__(self, config: TaxonomyLoaderConfig):
        self.config = config
        self.client = AsyncOpenAI(api_key=config.openai_api_key)
        self.model = config.openai_embedding_model
        self.dimensions = config.embedding_dimensions

        # Rate limiting
        self.rpm_limit = config.openai_rpm_limit
        self.requests_made = 0
        self.window_start = time.time()

    async def _wait_for_rate_limit(self):
        """Implement rate limiting to avoid exceeding OpenAI API limits"""
        self.requests_made += 1

        # Check if we're exceeding the rate limit
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

    async def _generate_embedding(
        self,
        text: str,
        retry_count: int = 0
    ) -> Optional[List[float]]:
        """
        Generate embedding for a single text with retry logic.

        Args:
            text: Text to embed
            retry_count: Current retry attempt

        Returns:
            List of floats (embedding vector) or None on failure
        """
        if not text or not text.strip():
            return None

        try:
            await self._wait_for_rate_limit()

            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.dimensions
            )

            embedding = response.data[0].embedding
            return embedding

        except Exception as e:
            if retry_count < self.config.openai_retry_attempts:
                delay = self.config.openai_retry_delay * (2 ** retry_count)
                if self.config.verbose:
                    print(f"⚠️  Embedding failed, retrying in {delay}s... ({retry_count + 1}/{self.config.openai_retry_attempts})")
                await asyncio.sleep(delay)
                return await self._generate_embedding(text, retry_count + 1)
            else:
                print(f"❌ Failed to generate embedding after {self.config.openai_retry_attempts} attempts: {e}")
                return None

    async def generate_dual_embeddings_for_condition(
        self,
        condition_name: str,
        condition_type: str,
        parameters: Dict[str, Any],
        original_text: Optional[str]
    ) -> Tuple[Optional[List[float]], Optional[List[float]]]:
        """
        Generate dual embeddings for a general condition.

        Args:
            condition_name: Name of the condition
            condition_type: Type (exclusion/eligibility)
            parameters: Structured parameters
            original_text: Original policy text

        Returns:
            Tuple of (normalized_embedding, original_embedding)
        """
        # Normalized embedding: structured parameters as text
        normalized_text = self._format_condition_for_embedding(
            condition_name, condition_type, parameters
        )

        # Original embedding: policy text
        original_text_clean = original_text if original_text and original_text.strip() else None

        # Generate both embeddings concurrently
        normalized_emb, original_emb = await asyncio.gather(
            self._generate_embedding(normalized_text),
            self._generate_embedding(original_text_clean) if original_text_clean else asyncio.sleep(0, result=None)
        )

        return normalized_emb, original_emb

    async def generate_dual_embeddings_for_benefit(
        self,
        benefit_name: str,
        coverage_limit: Optional[Any],
        sub_limits: Dict[str, Any],
        parameters: Dict[str, Any],
        original_text: Optional[str]
    ) -> Tuple[Optional[List[float]], Optional[List[float]]]:
        """
        Generate dual embeddings for a benefit.

        Args:
            benefit_name: Name of the benefit
            coverage_limit: Coverage limit (numeric, dict, or None)
            sub_limits: Nested sub-limits
            parameters: Additional parameters
            original_text: Original policy text

        Returns:
            Tuple of (normalized_embedding, original_embedding)
        """
        # Normalized embedding: benefit details as text
        normalized_text = self._format_benefit_for_embedding(
            benefit_name, coverage_limit, sub_limits, parameters
        )

        # Original embedding: policy text
        original_text_clean = original_text if original_text and original_text.strip() else None

        # Generate both embeddings concurrently
        normalized_emb, original_emb = await asyncio.gather(
            self._generate_embedding(normalized_text),
            self._generate_embedding(original_text_clean) if original_text_clean else asyncio.sleep(0, result=None)
        )

        return normalized_emb, original_emb

    async def generate_dual_embeddings_for_benefit_condition(
        self,
        benefit_name: str,
        condition_name: str,
        condition_type: Optional[str],
        parameters: Dict[str, Any],
        original_text: Optional[str]
    ) -> Tuple[Optional[List[float]], Optional[List[float]]]:
        """
        Generate dual embeddings for a benefit-specific condition.

        Args:
            benefit_name: Parent benefit name
            condition_name: Name of the condition
            condition_type: Type (benefit_eligibility/benefit_exclusion)
            parameters: Structured parameters
            original_text: Original policy text

        Returns:
            Tuple of (normalized_embedding, original_embedding)
        """
        # Normalized embedding: benefit + condition details
        normalized_text = self._format_benefit_condition_for_embedding(
            benefit_name, condition_name, condition_type, parameters
        )

        # Original embedding: policy text
        original_text_clean = original_text if original_text and original_text.strip() else None

        # Generate both embeddings concurrently
        normalized_emb, original_emb = await asyncio.gather(
            self._generate_embedding(normalized_text),
            self._generate_embedding(original_text_clean) if original_text_clean else asyncio.sleep(0, result=None)
        )

        return normalized_emb, original_emb

    # ========================================================================
    # TEXT FORMATTING FOR EMBEDDINGS
    # ========================================================================

    def _format_condition_for_embedding(
        self,
        condition_name: str,
        condition_type: str,
        parameters: Dict[str, Any]
    ) -> str:
        """Format general condition as human-readable text for embedding"""
        parts = [
            f"Condition: {condition_name.replace('_', ' ').title()}",
            f"Type: {condition_type}",
        ]

        if parameters:
            params_text = format_parameters_for_embedding(parameters)
            parts.append(f"Parameters: {params_text}")

        return "\n".join(parts)

    def _format_benefit_for_embedding(
        self,
        benefit_name: str,
        coverage_limit: Optional[Any],
        sub_limits: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> str:
        """Format benefit as human-readable text for embedding"""
        parts = [
            f"Benefit: {benefit_name.replace('_', ' ').title()}",
        ]

        # Coverage limit
        if coverage_limit is not None:
            coverage_text = format_coverage_limit(coverage_limit)
            parts.append(coverage_text)

        # Sub-limits
        if sub_limits:
            sub_limits_text = self._format_sub_limits(sub_limits)
            if sub_limits_text:
                parts.append(f"Sub-limits: {sub_limits_text}")

        # Additional parameters
        if parameters:
            params_text = format_parameters_for_embedding(parameters)
            parts.append(f"Parameters: {params_text}")

        return "\n".join(parts)

    def _format_benefit_condition_for_embedding(
        self,
        benefit_name: str,
        condition_name: str,
        condition_type: Optional[str],
        parameters: Dict[str, Any]
    ) -> str:
        """Format benefit-specific condition as human-readable text for embedding"""
        parts = [
            f"Benefit: {benefit_name.replace('_', ' ').title()}",
            f"Condition: {condition_name.replace('_', ' ').title()}",
        ]

        if condition_type:
            parts.append(f"Type: {condition_type}")

        if parameters:
            params_text = format_parameters_for_embedding(parameters)
            parts.append(f"Parameters: {params_text}")

        return "\n".join(parts)

    def _format_sub_limits(self, sub_limits: Dict[str, Any], depth: int = 0) -> str:
        """Recursively format nested sub-limits"""
        if not sub_limits:
            return ""

        parts = []
        indent = "  " * depth

        for key, value in sub_limits.items():
            if isinstance(value, dict):
                nested = self._format_sub_limits(value, depth + 1)
                parts.append(f"{indent}{key}: {{{nested}}}")
            elif isinstance(value, (int, float)):
                parts.append(f"{indent}{key}: ${value:,.0f}")
            else:
                parts.append(f"{indent}{key}: {value}")

        return "; ".join(parts)

    async def close(self):
        """Close the OpenAI client"""
        await self.client.close()


# ============================================================================
# BATCH PROCESSING UTILITIES
# ============================================================================

async def generate_embeddings_batch(
    service: EmbeddingService,
    items: List[Dict[str, Any]],
    item_type: str,  # 'condition', 'benefit', or 'benefit_condition'
    verbose: bool = True
) -> List[Tuple[Optional[List[float]], Optional[List[float]]]]:
    """
    Generate dual embeddings for a batch of items.

    Args:
        service: EmbeddingService instance
        items: List of items (dicts with relevant fields)
        item_type: Type of item to process
        verbose: Enable progress logging

    Returns:
        List of (normalized_embedding, original_embedding) tuples
    """
    tasks = []

    for item in items:
        if item_type == "condition":
            task = service.generate_dual_embeddings_for_condition(
                condition_name=item["condition_name"],
                condition_type=item["condition_type"],
                parameters=item["parameters"],
                original_text=item.get("original_text")
            )
        elif item_type == "benefit":
            task = service.generate_dual_embeddings_for_benefit(
                benefit_name=item["benefit_name"],
                coverage_limit=item.get("coverage_limit"),
                sub_limits=item.get("sub_limits", {}),
                parameters=item.get("parameters", {}),
                original_text=item.get("original_text")
            )
        elif item_type == "benefit_condition":
            task = service.generate_dual_embeddings_for_benefit_condition(
                benefit_name=item["benefit_name"],
                condition_name=item["condition_name"],
                condition_type=item.get("condition_type"),
                parameters=item["parameters"],
                original_text=item.get("original_text")
            )
        else:
            raise ValueError(f"Unknown item_type: {item_type}")

        tasks.append(task)

    if verbose:
        print(f"⚡ Generating embeddings for {len(tasks)} {item_type}s...")

    results = await asyncio.gather(*tasks)

    if verbose:
        success_count = sum(1 for norm, orig in results if norm is not None)
        print(f"✓ Generated {success_count}/{len(results)} normalized embeddings")
        orig_count = sum(1 for norm, orig in results if orig is not None)
        print(f"✓ Generated {orig_count}/{len(results)} original embeddings")

    return results
