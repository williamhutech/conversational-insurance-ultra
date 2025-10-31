"""
Claim Data Models

Pydantic models for historical claims data analysis and recommendations.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Claim Models (Block 5: Data-Driven Recommendations)
# -----------------------------------------------------------------------------

class ClaimRecord(BaseModel):
    """Historical claim record."""
    claim_id: str
    policy_id: str
    customer_id: str

    # Claim details
    claim_type: str  # medical, baggage_loss, trip_cancellation, etc.
    claim_amount: float
    claim_currency: str = "SGD"
    settlement_amount: Optional[float] = None

    # Context
    destination: str
    incident_date: datetime
    claim_filed_date: datetime
    settlement_date: Optional[datetime] = None
    status: Literal["pending", "approved", "rejected", "settled"]

    # Additional information
    incident_description: Optional[str] = None
    medical_condition: Optional[str] = None
    activity_involved: Optional[str] = None


class DestinationRiskAnalysis(BaseModel):
    """Risk analysis for a specific destination."""
    destination: str
    risk_level: Literal["low", "medium", "high", "very_high"]
    risk_score: float = Field(..., ge=0.0, le=1.0)

    # Claim statistics
    total_claims: int
    average_claim_amount: float
    most_common_claim_types: List[Dict[str, Any]]  # [{type, count, percentage}]

    # Recommendations
    recommended_coverage_level: str
    critical_benefits: List[str]
    warnings: List[str] = []


class RiskFactor(BaseModel):
    """Individual risk factor."""
    factor_name: str
    factor_type: Literal["destination", "activity", "age", "duration", "season"]
    risk_contribution: float  # Impact on overall risk
    description: str
    mitigation_suggestion: Optional[str] = None


class RecommendationRequest(BaseModel):
    """Request for data-driven recommendations."""
    customer_id: str
    travel_plan: Dict[str, Any]  # Destinations, dates, travelers, activities
    current_quotation_id: Optional[str] = None


class Recommendation(BaseModel):
    """Individual recommendation."""
    recommendation_id: str
    recommendation_type: Literal["coverage_increase", "add_benefit", "warning", "general"]
    priority: Literal["critical", "high", "medium", "low"]

    # Content
    title: str
    description: str
    rationale: str  # Based on claims data
    supporting_data: Dict[str, Any]  # Statistics, examples

    # Actionable
    suggested_action: Optional[str] = None
    estimated_cost_impact: Optional[float] = None


class RecommendationResponse(BaseModel):
    """Complete recommendation response."""
    customer_id: str
    travel_plan_summary: Dict[str, Any]

    # Risk assessment
    overall_risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_factors: List[RiskFactor]

    # Destination analysis
    destination_analyses: List[DestinationRiskAnalysis]

    # Recommendations
    recommendations: List[Recommendation]
    recommended_policy_adjustments: List[Dict[str, Any]]

    # Generated at
    generated_at: datetime


class ClaimPatternAnalysis(BaseModel):
    """Analysis of claim patterns for insights."""
    pattern_id: str
    pattern_name: str
    pattern_description: str

    # Pattern details
    affected_demographics: List[str]
    common_scenarios: List[str]
    average_severity: float

    # Business insight
    prevention_tips: List[str]
    coverage_recommendations: List[str]


# TODO: Add models for:
# - ClaimPrediction
# - FraudDetection
# - SeasonalRiskAnalysis
# - ActivityRiskProfile
