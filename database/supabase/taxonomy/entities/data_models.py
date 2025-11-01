"""
Data Models
Dataclasses for representing entities throughout the taxonomy extraction pipeline.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


# ============================================================================
# Stage 1: Key Extraction Models
# ============================================================================

@dataclass
class KeyExtractionResult:
    """Result from unique key extraction (Stage 1)."""
    status: str  # "success" or "error"
    layer_name: str  # "general_conditions", "benefits", or "benefit_specific_conditions"
    unique_keys: Optional[List[Any]] = None  # List of str for simple keys, List[tuple] for pairs
    count: int = 0
    error: Optional[str] = None


# ============================================================================
# Stage 2: Value Extraction Models
# ============================================================================

@dataclass
class ExtractionResult:
    """Result from value extraction by Extractor agents."""
    status: str  # "success", "api_error", "json_error", or "exception"
    layer_name: str  # "general_conditions", "benefits", or "benefit_specific_conditions"
    product_name: str
    text_index: int  # Index of raw_text chunk in product_dict
    raw_text: str  # The actual text chunk processed
    extracted_data: Optional[Any] = None  # The extracted JSON structure (can be Dict or List)
    response: Optional[str] = None  # Raw API response
    error_details: Optional[str] = None
    processing_time: Optional[float] = None


@dataclass
class JudgmentResult:
    """Result from Judger agent validation."""
    status: str  # "success", "api_error", "json_error", or "exception"
    layer_name: str  # "general_conditions", "benefits", or "benefit_specific_conditions"
    product_name: str
    text_index: int
    approve: bool = False  # True if extraction is valid
    final_value: Optional[Any] = None  # Approved or corrected JSON (can be Dict or List)
    original_extraction: Optional[Any] = None  # The extraction being judged (can be Dict or List)
    response: Optional[str] = None  # Raw API response
    error_details: Optional[str] = None
    processing_time: Optional[float] = None
    json_validation: Optional[Dict[str, Any]] = None  # Validation metadata


@dataclass
class ValidationResult:
    """Result from programmatic JSON validation."""
    is_valid: bool
    layer_name: str
    data: Dict[str, Any]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ============================================================================
# Stage 3: Aggregation Models
# ============================================================================

@dataclass
class AggregationResult:
    """Result from product aggregation (Stage 3)."""
    status: str  # "success" or "error"
    layer_name: str
    key_identifier: str  # condition_name, benefit_name, or (benefit_name, condition) tuple
    aggregated_data: Optional[Dict[str, Any]] = None  # Merged product data
    product_count: int = 0  # Number of products aggregated
    error: Optional[str] = None


# ============================================================================
# Stage 4: Standardization Models
# ============================================================================

@dataclass
class StandardizationResult:
    """Result from parameter standardization (Stage 4)."""
    status: str  # "success", "api_error", "json_error", or "exception"
    layer_name: str
    key_identifier: str  # The condition/benefit being standardized
    standardized_data: Optional[Dict[str, Any]] = None  # Standardized JSON structure
    original_data: Optional[Dict[str, Any]] = None  # Original aggregated data
    response: Optional[str] = None  # Raw API response
    error_details: Optional[str] = None
    processing_time: Optional[float] = None
    json_validation: Optional[Dict[str, Any]] = None


# ============================================================================
# Stage 5: Final Assembly Models
# ============================================================================

@dataclass
class FinalTaxonomy:
    """Complete taxonomy structure (Stage 5)."""
    taxonomy_name: str
    products: List[str]
    layers: Dict[str, List[Dict[str, Any]]]  # layer_name -> list of items
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "taxonomy_name": self.taxonomy_name,
            "products": self.products,
            "layers": self.layers,
            "metadata": self.metadata
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get taxonomy statistics."""
        return {
            "product_count": len(self.products),
            "layer_1_count": len(self.layers.get("layer_1_general_conditions", [])),
            "layer_2_count": len(self.layers.get("layer_2_benefits", [])),
            "layer_3_count": len(self.layers.get("layer_3_benefit_specific_conditions", [])),
            "total_items": sum(len(items) for items in self.layers.values()),
            "metadata": self.metadata
        }


# ============================================================================
# Pipeline Metadata Models
# ============================================================================

@dataclass
class StageMetadata:
    """Metadata for a pipeline stage execution."""
    stage_name: str
    stage_number: int
    started_at: str
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    status: str = "running"  # "running", "completed", "failed"
    input_files: Dict[str, str] = field(default_factory=dict)
    output_files: Dict[str, str] = field(default_factory=dict)
    statistics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "stage_name": self.stage_name,
            "stage_number": self.stage_number,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "status": self.status,
            "input_files": self.input_files,
            "output_files": self.output_files,
            "statistics": self.statistics,
            "errors": self.errors
        }


@dataclass
class PipelineMetadata:
    """Overall pipeline execution metadata."""
    pipeline_name: str = "Taxonomy Extraction Pipeline"
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    total_duration_seconds: Optional[float] = None
    status: str = "running"  # "running", "completed", "failed"
    stages: List[StageMetadata] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pipeline_name": self.pipeline_name,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_duration_seconds": self.total_duration_seconds,
            "status": self.status,
            "stages": [stage.to_dict() for stage in self.stages]
        }


# ============================================================================
# Helper Models for Batch Processing
# ============================================================================

@dataclass
class BatchProcessingResult:
    """Result from batch processing with progress tracking."""
    batch_number: int
    total_batches: int
    items_processed: int
    successful: int
    failed: int
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def get_success_rate(self) -> float:
        """Calculate success rate."""
        if self.items_processed == 0:
            return 0.0
        return self.successful / self.items_processed

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "batch_number": self.batch_number,
            "total_batches": self.total_batches,
            "items_processed": self.items_processed,
            "successful": self.successful,
            "failed": self.failed,
            "success_rate": self.get_success_rate(),
            "timestamp": self.timestamp,
            "errors": self.errors
        }
