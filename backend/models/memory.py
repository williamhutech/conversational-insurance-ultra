"""
Memory Data Models

Pydantic models for memory management operations.
Supports conversation memory, user preferences, and context management.

Usage:
    from backend.models.memory import AddMemoryRequest, MemoryResult
"""

from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field


class MemoryMessage(BaseModel):
    """Single conversation message for memory storage."""
    role: Literal["user", "assistant", "system"] = Field(
        ...,
        description="Message role"
    )
    content: str = Field(
        ...,
        description="Message content"
    )


class AddMemoryRequest(BaseModel):
    """Request to add new memory for a user."""
    user_id: str = Field(
        ...,
        description="User identifier"
    )
    messages: List[MemoryMessage] = Field(
        ...,
        description="List of conversation messages to store as memory"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional metadata for categorization and filtering"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "alice_123",
                "messages": [
                    {
                        "role": "user",
                        "content": "I prefer travel insurance with high medical coverage"
                    },
                    {
                        "role": "assistant",
                        "content": "I'll remember your preference for high medical coverage"
                    }
                ],
                "metadata": {
                    "type": "preference",
                    "category": "insurance"
                }
            }
        }
    }


class AddMemoryResponse(BaseModel):
    """Response after adding memory."""
    results: List[Dict[str, Any]] = Field(
        ...,
        description="List of created memories with IDs"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "results": [
                    {
                        "id": "892db2ae-06d9-49e5-8b3e-585ef9b85b8e",
                        "memory": "User prefers high medical coverage for travel insurance",
                        "event": "ADD"
                    }
                ]
            }
        }
    }


class SearchMemoryRequest(BaseModel):
    """Request to search memories using semantic similarity."""
    user_id: str = Field(
        ...,
        description="User identifier"
    )
    query: str = Field(
        ...,
        description="Search query for semantic search"
    )
    limit: int = Field(
        10,
        ge=1,
        le=100,
        description="Maximum number of memories to return"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "alice_123",
                "query": "insurance preferences",
                "limit": 5
            }
        }
    }


class MemoryResult(BaseModel):
    """Single memory result with metadata."""
    id: str = Field(
        ...,
        description="Unique memory identifier"
    )
    memory: str = Field(
        ...,
        description="Memory content"
    )
    user_id: Optional[str] = Field(
        None,
        description="User identifier"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Memory metadata"
    )
    created_at: Optional[str] = Field(
        None,
        description="Memory creation timestamp (ISO format)"
    )
    score: Optional[float] = Field(
        None,
        description="Relevance score (for search results)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "892db2ae-06d9-49e5-8b3e-585ef9b85b8e",
                "memory": "User prefers high medical coverage for travel insurance",
                "user_id": "alice_123",
                "metadata": {
                    "type": "preference",
                    "category": "insurance"
                },
                "created_at": "2025-01-15T10:30:00Z",
                "score": 0.95
            }
        }
    }


class SearchMemoryResponse(BaseModel):
    """Response from memory search."""
    results: List[MemoryResult] = Field(
        default_factory=list,
        description="List of matching memories"
    )
    total: int = Field(
        0,
        description="Total number of results"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "results": [
                    {
                        "id": "892db2ae-06d9-49e5-8b3e-585ef9b85b8e",
                        "memory": "User prefers high medical coverage",
                        "score": 0.95
                    }
                ],
                "total": 1
            }
        }
    }


class GetMemoriesResponse(BaseModel):
    """Response when getting all user memories."""
    results: List[MemoryResult] = Field(
        default_factory=list,
        description="List of all user memories"
    )
    total: int = Field(
        0,
        description="Total number of memories"
    )


class DeleteMemoryResponse(BaseModel):
    """Response after deleting a memory."""
    success: bool = Field(
        ...,
        description="Whether deletion was successful"
    )
    memory_id: str = Field(
        ...,
        description="ID of deleted memory"
    )
    message: str = Field(
        default="Memory deleted successfully",
        description="Status message"
    )
