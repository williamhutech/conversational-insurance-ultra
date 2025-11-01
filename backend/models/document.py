"""
Document Data Models

Pydantic models for document upload, OCR, and data extraction.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, HttpUrl


# -----------------------------------------------------------------------------
# Document Models (Block 3: Document Intelligence)
# -----------------------------------------------------------------------------

class DocumentUpload(BaseModel):
    """Model for document upload request."""
    customer_id: str
    document_type: Literal["flight_booking", "hotel_booking", "itinerary", "other"]
    filename: str
    file_size: int = Field(..., gt=0, le=10*1024*1024)  # Max 10MB
    mime_type: str


class DocumentMetadata(BaseModel):
    """Model for document metadata."""
    document_id: str
    customer_id: str
    document_type: str
    filename: str
    file_size: int
    mime_type: str
    storage_url: HttpUrl
    uploaded_at: datetime
    processed: bool = False
    processed_at: Optional[datetime] = None


class TravelDataExtraction(BaseModel):
    """Model for extracted travel data from documents."""
    document_id: str
    extraction_method: Literal["tesseract", "easyocr", "claude_vision"]
    confidence_score: float = Field(..., ge=0.0, le=1.0)

    # Extracted travel information
    destinations: List[str] = []
    departure_date: Optional[datetime] = None
    return_date: Optional[datetime] = None
    travelers: List[Dict[str, Any]] = []  # [{name, age, relationship}]
    trip_value: Optional[float] = None
    activities: List[str] = []

    # Additional data
    extracted_text: str
    raw_data: Dict[str, Any] = {}
    extracted_at: datetime


class TravelDataValidation(BaseModel):
    """Model for travel data validation results."""
    is_valid: bool
    validation_errors: List[str] = []
    warnings: List[str] = []
    suggestions: List[str] = []


class ExtractedTravelPlan(BaseModel):
    """Consolidated travel plan from multiple documents."""
    customer_id: str
    document_ids: List[str]

    # Consolidated information
    destinations: List[str]
    departure_date: datetime
    return_date: datetime
    duration_days: int
    travelers: List[Dict[str, Any]]
    total_trip_value: Optional[float] = None
    activities: List[str] = []

    # Validation
    validation_result: TravelDataValidation
    requires_manual_review: bool = False


# TODO: Add models for:
# - DocumentProcessingStatus
# - OCRResult
# - DocumentValidation
# - MultiDocumentAnalysis
