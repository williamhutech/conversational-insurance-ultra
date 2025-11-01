"""
Purchase Data Models

Pydantic models for purchase execution and payment processing.
"""

from datetime import datetime
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, EmailStr


# -----------------------------------------------------------------------------
# Purchase Models (Block 4: Purchase Execution)
# -----------------------------------------------------------------------------

class CustomerDetails(BaseModel):
    """Customer information for purchase."""
    customer_id: Optional[str] = None  # If existing customer
    email: EmailStr
    full_name: str
    phone_number: str
    date_of_birth: datetime
    address: Dict[str, str]  # {street, city, postal_code, country}
    identification: Dict[str, str]  # {type: "passport", number: "XXX"}


class PurchaseInitiation(BaseModel):
    """Model for initiating a purchase."""
    quotation_id: str
    selected_policy_id: str
    customer_details: CustomerDetails
    travelers: list[Dict[str, Any]]  # Traveler details
    travel_details: Dict[str, Any]


class PaymentIntent(BaseModel):
    """Stripe payment intent information."""
    intent_id: str
    amount: float
    currency: str = "SGD"
    status: Literal["requires_payment_method", "requires_confirmation", "processing", "succeeded", "canceled"]
    client_secret: str  # For frontend Stripe integration


class PurchaseResponse(BaseModel):
    """Response after purchase initiation."""
    purchase_id: str
    quotation_id: str
    policy_id: str
    customer_id: str

    # Payment information
    payment_intent: PaymentIntent
    total_amount: float
    currency: str = "SGD"

    # Status
    status: Literal["pending_payment", "processing", "completed", "failed", "refunded"]
    created_at: datetime


class PaymentConfirmation(BaseModel):
    """Model for confirming payment completion."""
    purchase_id: str
    payment_intent_id: str
    payment_method: Literal["card", "bank_transfer", "other"]


class PolicyDocument(BaseModel):
    """Generated policy document."""
    policy_document_id: str
    purchase_id: str
    policy_number: str
    customer_id: str

    # Document details
    document_url: str  # Download link
    document_type: Literal["pdf", "html"]
    generated_at: datetime

    # Policy details
    effective_date: datetime
    expiry_date: datetime
    coverage_summary: Dict[str, Any]


class PurchaseComplete(BaseModel):
    """Complete purchase information after successful payment."""
    purchase_id: str
    purchase_status: str
    payment_status: str

    # Policy information
    policy_number: str
    policy_document: PolicyDocument

    # Customer communication
    confirmation_email_sent: bool
    policy_sent_at: Optional[datetime] = None


# TODO: Add models for:
# - RefundRequest
# - PurchaseHistory
# - SubscriptionPurchase
# - GroupPurchase
