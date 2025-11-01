"""
Pydantic models for original policy text storage.
Defines schema for text chunks and embeddings in Supabase.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import uuid


class TextChunk(BaseModel):
    """Raw text chunk before database insertion"""

    text: str = Field(..., min_length=1, description="Text content of the chunk")
    chunk_index: int = Field(..., ge=0, description="Index of chunk in document")
    product_name: str = Field(..., description="Insurance product name")
    char_count: int = Field(..., ge=0, description="Character count of chunk")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Ensure text is not empty after stripping"""
        if not v.strip():
            raise ValueError("Text cannot be empty")
        return v.strip()


class OriginalTextRecord(BaseModel):
    """
    Database record for original_text table.
    Matches Supabase schema with pgvector support.
    """

    text_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier (UUID)"
    )
    product_name: str = Field(..., description="Insurance product name")
    text: str = Field(..., description="Text content")
    chunk_index: int = Field(..., ge=0, description="Chunk sequence number")
    char_count: int = Field(..., ge=0, description="Character count")
    original_embedding: Optional[List[float]] = Field(
        default=None,
        description="Embedding vector from text-embedding-3-large (2000 dimensions)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (JSONB)"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp"
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class OriginalTextStats(BaseModel):
    """Statistics for text loading operation"""

    total_chunks: int = Field(default=0, description="Total chunks processed")
    chunks_inserted: int = Field(default=0, description="Chunks successfully inserted")
    embeddings_generated: int = Field(default=0, description="Embeddings generated")
    products_processed: int = Field(default=0, description="Number of products processed")
    total_characters: int = Field(default=0, description="Total characters processed")
    errors: int = Field(default=0, description="Number of errors encountered")

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary"""
        return {
            "total_chunks": self.total_chunks,
            "chunks_inserted": self.chunks_inserted,
            "embeddings_generated": self.embeddings_generated,
            "products_processed": self.products_processed,
            "total_characters": self.total_characters,
            "errors": self.errors
        }


class ProductDocument(BaseModel):
    """
    Represents a single policy document from product_dict.pkl.
    """

    product_name: str = Field(..., description="Product name (from dict key)")
    raw_content: List[str] = Field(..., description="List of text sections from dict value")

    @property
    def full_text(self) -> str:
        """Concatenate all sections into full text"""
        return "\n\n".join(self.raw_content)

    @property
    def total_length(self) -> int:
        """Total character count"""
        return len(self.full_text)
