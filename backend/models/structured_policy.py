"""
Structured Policy Search Models

Pydantic models for intelligent policy data search with LLM routing.
"""

from typing import List, Dict, Any
from pydantic import BaseModel, Field


class StructuredPolicyRequest(BaseModel):
    """
    Request model for structured policy data search.

    Attributes:
        query: Natural language search query
        top_k: Number of top results to return per table
    """
    query: str = Field(..., description="Natural language search query", min_length=1)
    top_k: int = Field(default=10, description="Number of top results per table", ge=1, le=50)


class StructuredPolicyResponse(BaseModel):
    """
    Response model for structured policy data search.

    Attributes:
        success: Whether the search was successful
        data: List of search results from one or more tables
        tables_searched: Names of tables that were searched
        total_results: Total number of results returned
        query: Original search query
    """
    success: bool = Field(..., description="Search success status")
    data: List[Dict[str, Any]] = Field(default_factory=list, description="Search results")
    tables_searched: List[str] = Field(default_factory=list, description="Tables that were searched")
    total_results: int = Field(default=0, description="Total number of results", ge=0)
    query: str = Field(..., description="Original search query")
