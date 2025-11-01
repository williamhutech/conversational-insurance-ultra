"""
Pydantic models for Travel Insurance Taxonomy data validation.
Ensures type safety during JSON parsing and database loading.
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from datetime import datetime


# ============================================================================
# PRODUCT-LEVEL MODELS
# ============================================================================

class ProductConditionData(BaseModel):
    """Represents product-specific condition data (Layer 1 & 3)"""
    condition_exist: bool
    original_text: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class ProductBenefitData(BaseModel):
    """Represents product-specific benefit data (Layer 2)"""
    benefit_exist: Optional[bool] = None
    condition_exist: Optional[bool] = None  # Some data uses this instead of benefit_exist
    coverage_limit: Optional[Union[int, float, Dict[str, Any]]] = None
    sub_limits: Dict[str, Any] = Field(default_factory=dict)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    original_text: Optional[str] = None

    @model_validator(mode="after")
    def normalize_benefit_exist(self):
        """Normalize benefit_exist from condition_exist if needed"""
        # If benefit_exist is None but condition_exist is set, use condition_exist
        if self.benefit_exist is None and self.condition_exist is not None:
            self.benefit_exist = self.condition_exist
        # If benefit_exist is still None, default to False
        if self.benefit_exist is None:
            self.benefit_exist = False
        return self

    model_config = ConfigDict(extra="allow")


# ============================================================================
# LAYER 1: GENERAL CONDITIONS
# ============================================================================

class GeneralCondition(BaseModel):
    """Layer 1: General eligibility and exclusion conditions"""
    condition: str
    condition_type: Optional[str] = None  # 'exclusion' or 'eligibility', or None
    products: Dict[str, ProductConditionData]

    @field_validator("condition_type")
    @classmethod
    def validate_condition_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        valid_types = {"exclusion", "eligibility"}
        if v not in valid_types:
            raise ValueError(f"condition_type must be one of {valid_types}, got {v}")
        return v

    model_config = ConfigDict(extra="forbid")


# ============================================================================
# LAYER 2: BENEFITS
# ============================================================================

class Benefit(BaseModel):
    """Layer 2: Policy benefits with coverage limits"""
    benefit_name: str
    parameters: List[str] = Field(default_factory=list)
    products: Dict[str, ProductBenefitData]

    model_config = ConfigDict(extra="forbid")


# ============================================================================
# LAYER 3: BENEFIT-SPECIFIC CONDITIONS
# ============================================================================

class BenefitCondition(BaseModel):
    """Layer 3: Benefit-specific eligibility and exclusion conditions"""
    benefit_name: str
    condition: str
    condition_type: Optional[str] = None  # 'benefit_eligibility' or 'benefit_exclusion'
    parameters: List[str] = Field(default_factory=list)
    products: Dict[str, ProductConditionData]

    @field_validator("condition_type")
    @classmethod
    def validate_benefit_condition_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        valid_types = {"benefit_eligibility", "benefit_exclusion"}
        if v not in valid_types:
            raise ValueError(f"condition_type must be one of {valid_types}, got {v}")
        return v

    model_config = ConfigDict(extra="forbid")


# ============================================================================
# ROOT TAXONOMY MODEL
# ============================================================================

class TaxonomyMetadata(BaseModel):
    """Metadata about the taxonomy extraction"""
    created_at: str
    pipeline: str
    version: str
    layers: Dict[str, int] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class TravelInsuranceTaxonomy(BaseModel):
    """Root model for the entire taxonomy JSON"""
    taxonomy_name: str
    products: List[str]
    layers: Dict[str, List[Union[GeneralCondition, Benefit, BenefitCondition]]]
    metadata: Optional[TaxonomyMetadata] = None

    @field_validator("layers", mode="before")
    @classmethod
    def validate_layers(cls, v: Dict) -> Dict:
        """Validate and parse nested layer data (runs before Pydantic parsing)"""
        # In Pydantic v2 with mode="before", v is the raw dict data
        # We just return it as-is and let Pydantic's type system handle the parsing
        return v

    model_config = ConfigDict(extra="forbid")


# ============================================================================
# DATABASE MODELS (for insertion)
# ============================================================================

class ProductDB(BaseModel):
    """Database model for products table"""
    id: Optional[int] = None
    product_name: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class GeneralConditionDB(BaseModel):
    """Database model for general_conditions table"""
    id: Optional[int] = None
    product_id: int
    product_name: str
    condition_name: str
    condition_type: str
    condition_exist: bool
    original_text: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    normalized_embedding: Optional[List[float]] = None
    original_embedding: Optional[List[float]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BenefitDB(BaseModel):
    """Database model for benefits table"""
    id: Optional[int] = None
    product_id: int
    product_name: str
    benefit_name: str
    benefit_exist: bool
    coverage_limit: Optional[Dict[str, Any]] = None
    sub_limits: Dict[str, Any] = Field(default_factory=dict)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    original_text: Optional[str] = None
    normalized_embedding: Optional[List[float]] = None
    original_embedding: Optional[List[float]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BenefitConditionDB(BaseModel):
    """Database model for benefit_conditions table"""
    id: Optional[int] = None
    product_id: int
    product_name: str
    benefit_name: str
    condition_name: str
    condition_type: Optional[str] = None
    condition_exist: bool
    original_text: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    normalized_embedding: Optional[List[float]] = None
    original_embedding: Optional[List[float]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_parameters_for_embedding(params: Dict[str, Any]) -> str:
    """
    Convert structured parameters to human-readable text for embedding.

    Example:
        {"exclude_hiv": true, "age_min": 18} ->
        "exclude_hiv: true; age_min: 18"
    """
    if not params:
        return ""

    formatted_parts = []
    for key, value in params.items():
        if isinstance(value, dict):
            # Nested dict - format recursively
            nested = format_parameters_for_embedding(value)
            formatted_parts.append(f"{key}: {{{nested}}}")
        elif isinstance(value, list):
            # List - join with commas
            formatted_parts.append(f"{key}: [{', '.join(map(str, value))}]")
        elif value is not None:
            formatted_parts.append(f"{key}: {value}")

    return "; ".join(formatted_parts)


def format_coverage_limit(coverage: Optional[Union[int, float, Dict[str, Any]]]) -> str:
    """
    Convert coverage limit to human-readable text.

    Example:
        50000 -> "Coverage limit: $50,000"
        {"Standard": 30000, "Elite": 50000} -> "Coverage limits: Standard: $30,000; Elite: $50,000"
    """
    if coverage is None:
        return "No coverage limit specified"

    if isinstance(coverage, (int, float)):
        return f"Coverage limit: ${coverage:,.0f}"

    if isinstance(coverage, dict):
        parts = [f"{plan}: ${amount:,.0f}" for plan, amount in coverage.items()]
        return f"Coverage limits: {'; '.join(parts)}"

    return str(coverage)
