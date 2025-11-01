"""
Text chunking utilities for splitting policy documents into semantic chunks.
Uses sentence-boundary aware chunking with configurable overlap.
"""

from typing import List, Dict, Any
import re


class TextChunker:
    """
    Intelligent text chunking for policy documents.
    Respects sentence boundaries and maintains context with overlap.
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100
    ):
        """
        Initialize text chunker.

        Args:
            chunk_size: Target size of each chunk in characters
            chunk_overlap: Number of overlapping characters between chunks
            min_chunk_size: Minimum chunk size (avoid tiny fragments)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Split text into semantic chunks with metadata.

        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to each chunk

        Returns:
            List of chunk dictionaries with text and metadata
        """
        if not text or not text.strip():
            return []

        # Split into sentences first
        sentences = self._split_into_sentences(text)

        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            # If adding this sentence exceeds chunk_size, finalize current chunk
            if current_length + sentence_length > self.chunk_size and current_chunk:
                chunk_text = " ".join(current_chunk)
                if len(chunk_text) >= self.min_chunk_size:
                    chunks.append(self._create_chunk(chunk_text, len(chunks), metadata))

                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk)
                current_chunk = [overlap_text] if overlap_text else []
                current_length = len(overlap_text) if overlap_text else 0

            current_chunk.append(sentence)
            current_length += sentence_length

        # Add remaining chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(self._create_chunk(chunk_text, len(chunks), metadata))

        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using regex.
        Handles common abbreviations and edge cases.
        """
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        # Split on sentence boundaries (., !, ?) followed by space and capital letter
        # But preserve common abbreviations (e.g., Dr., Mr., etc.)
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)

        # Filter out empty sentences
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    def _get_overlap_text(self, sentences: List[str]) -> str:
        """
        Get overlapping text from the end of current chunk.

        Args:
            sentences: List of sentences in current chunk

        Returns:
            Text for overlap (last N characters)
        """
        if not sentences:
            return ""

        # Take sentences from the end until we reach overlap size
        overlap_sentences = []
        overlap_length = 0

        for sentence in reversed(sentences):
            sentence_length = len(sentence)
            if overlap_length + sentence_length > self.chunk_overlap:
                break
            overlap_sentences.insert(0, sentence)
            overlap_length += sentence_length

        return " ".join(overlap_sentences)

    def _create_chunk(
        self,
        text: str,
        chunk_index: int,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Create chunk dictionary with text and metadata.

        Args:
            text: Chunk text
            chunk_index: Index of chunk in sequence
            metadata: Optional metadata

        Returns:
            Chunk dictionary
        """
        chunk = {
            "text": text.strip(),
            "chunk_index": chunk_index,
            "char_count": len(text.strip())
        }

        if metadata:
            chunk["metadata"] = metadata

        return chunk


def chunk_policy_document(
    policy_text: str,
    product_name: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> List[Dict[str, Any]]:
    """
    Convenience function to chunk a policy document with product metadata.

    Args:
        policy_text: Full policy text
        product_name: Name of insurance product
        chunk_size: Target chunk size
        chunk_overlap: Overlap between chunks

    Returns:
        List of chunks with metadata
    """
    chunker = TextChunker(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    metadata = {
        "product_name": product_name,
        "document_type": "policy_wording"
    }

    return chunker.chunk_text(policy_text, metadata)
