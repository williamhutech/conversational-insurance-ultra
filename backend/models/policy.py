"""
Policy Data Models

Pydantic models for insurance policy data structures.
Used for API request/response validation and database operations.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator


# -----------------------------------------------------------------------------
# Policy Models (Block 1: Policy Intelligence)
# -----------------------------------------------------------------------------

class PolicyCondition(BaseModel):
    """Model for policy condition."""
    condition_id: str
    condition_type: str
    condition_exists: bool
    original_text: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class PolicyBenefit(BaseModel):
    """Model for policy benefit."""
    benefit_id: str
    benefit_name: str
    coverage_amount: Optional[float] = None
    coverage_currency: str = "SGD"
    description: Optional[str] = None
    conditions: List[str] = []  # List of condition IDs
    original_text: Optional[str] = None


class PolicyBase(BaseModel):
    """Base policy model with common fields."""
    policy_name: str
    product_type: str = "travel"
    provider: str = "MSIG"
    version: str = "1.0"
    effective_date: Optional[datetime] = None
    description: Optional[str] = None


class PolicyCreate(PolicyBase):
    """Model for creating a new policy."""
    benefits: List[PolicyBenefit]
    general_conditions: List[PolicyCondition]
    source_document_url: Optional[str] = None


class PolicyResponse(PolicyBase):
    """Model for policy API response."""
    policy_id: str
    benefits: List[PolicyBenefit]
    general_conditions: List[PolicyCondition]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PolicyComparison(BaseModel):
    """Model for policy comparison results."""
    comparison_id: str
    policy_ids: List[str]
    comparison_matrix: Dict[str, Any]  # benefit_name -> {policy_id -> value}
    recommendations: List[str]
    created_at: datetime


class PolicySearchQuery(BaseModel):
    """Model for policy search request."""
    query: str
    filters: Optional[Dict[str, Any]] = None
    limit: int = Field(default=10, ge=1, le=100)
    include_embeddings: bool = False


class PolicySearchResult(BaseModel):
    """Model for policy search result."""
    policy_id: str
    policy_name: str
    relevance_score: float
    matched_section: str
    highlights: List[str] = []


# TODO: Add models for:
# - PolicyExclusion
# - PolicyDocument
# - PolicyVersion
# - PolicyRating
