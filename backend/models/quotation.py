"""
Quotation Data Models

Pydantic models for insurance quotation generation and management.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Quotation Models (Block 3: Auto-Quotation)
# -----------------------------------------------------------------------------

class QuotationRequest(BaseModel):
    """Model for quotation generation request."""
    customer_id: str
    travel_plan_id: Optional[str] = None  # From extracted documents

    # Travel details (if not from documents)
    destinations: List[str]
    departure_date: datetime
    return_date: datetime
    travelers: List[Dict[str, Any]]  # [{name, age, date_of_birth}]

    # Coverage preferences
    requested_benefits: List[str] = []  # Optional specific benefits
    budget_range: Optional[Dict[str, float]] = None  # {min, max}
    coverage_level: Literal["basic", "standard", "comprehensive"] = "standard"


class QuotationItem(BaseModel):
    """Individual policy quotation."""
    policy_id: str
    policy_name: str
    provider: str = "MSIG"

    # Pricing
    base_premium: float
    add_ons: List[Dict[str, Any]] = []  # [{name, price}]
    total_premium: float
    currency: str = "SGD"

    # Coverage summary
    key_benefits: List[str]
    coverage_highlights: Dict[str, Any]
    exclusions_summary: List[str] = []

    # Recommendation
    recommended: bool = False
    recommendation_reason: Optional[str] = None
    match_score: float = Field(..., ge=0.0, le=1.0)


class QuotationResponse(BaseModel):
    """Complete quotation response with multiple policy options."""
    quotation_id: str
    customer_id: str
    travel_plan_id: Optional[str] = None

    # Travel summary
    travel_summary: Dict[str, Any]

    # Quotations
    quotations: List[QuotationItem]
    recommended_policy_id: Optional[str] = None

    # Metadata
    generated_at: datetime
    expires_at: datetime  # Typically 30 days
    status: Literal["draft", "sent", "accepted", "expired"] = "draft"


class QuotationAcceptance(BaseModel):
    """Model for accepting a quotation and proceeding to purchase."""
    quotation_id: str
    selected_policy_id: str
    selected_add_ons: List[str] = []
    final_premium: float


# TODO: Add models for:
# - QuotationComparison
# - PremiumCalculation
# - RiskAssessment
# - DiscountApplication
