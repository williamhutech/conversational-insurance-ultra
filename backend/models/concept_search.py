"""
Concept Search Models

Pydantic models for Neo4j concept search requests and responses.
"""

from pydantic import BaseModel, Field


class ConceptSearchRequest(BaseModel):
    """
    Request model for concept search.

    Attributes:
        query: Natural language search query
        top_k: Number of top results to return (default: 15)
    """
    query: str = Field(..., description="Natural language search query", min_length=1)
    top_k: int = Field(default=15, description="Number of top results to return", ge=1, le=50)


class ConceptSearchResponse(BaseModel):
    """
    Response model for concept search.

    Attributes:
        results: Concatenated string of filtered node memories
        count: Number of results returned
        query: Original search query
    """
    results: str = Field(..., description="Concatenated string of node memories")
    count: int = Field(..., description="Number of concept nodes returned", ge=0)
    query: str = Field(..., description="Original search query")
