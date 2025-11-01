"""
Payment Data Models

Pydantic models for payment records and Stripe integration.
Used for DynamoDB storage and API request/response validation.
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Payment Models
# -----------------------------------------------------------------------------

class PaymentBase(BaseModel):
    """Base payment model with common fields."""
    user_id: str = Field(..., description="Customer identifier")
    quote_id: str = Field(..., description="Insurance quote identifier")
    amount: int = Field(..., gt=0, description="Payment amount in cents")
    currency: str = Field(default="SGD", description="Currency code")
    product_name: str = Field(..., description="Product description")


class PaymentCreate(PaymentBase):
    """Model for creating a new payment record."""
    payment_intent_id: str = Field(..., description="Unique payment identifier")
    stripe_session_id: Optional[str] = Field(None, description="Stripe checkout session ID")


class PaymentRecord(PaymentBase):
    """Complete payment record from DynamoDB."""
    payment_intent_id: str
    payment_status: Literal["pending", "completed", "failed", "expired"]
    stripe_session_id: Optional[str] = None
    stripe_payment_intent: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    webhook_processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaymentStatusUpdate(BaseModel):
    """Model for updating payment status."""
    payment_intent_id: str
    payment_status: Literal["pending", "completed", "failed", "expired"]
    stripe_payment_intent: Optional[str] = None
    stripe_session_id: Optional[str] = None


class PaymentQuery(BaseModel):
    """Model for querying payments."""
    payment_intent_id: Optional[str] = None
    user_id: Optional[str] = None
    quote_id: Optional[str] = None
    stripe_session_id: Optional[str] = None
    payment_status: Optional[Literal["pending", "completed", "failed", "expired"]] = None


# -----------------------------------------------------------------------------
# Stripe Integration Models
# -----------------------------------------------------------------------------

class StripeCheckoutRequest(BaseModel):
    """Request to create Stripe checkout session."""
    payment_intent_id: str
    quote_id: str
    user_id: str
    amount: int = Field(..., gt=0, description="Amount in cents")
    currency: str = "SGD"
    product_name: str
    customer_email: Optional[str] = None
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class StripeCheckoutResponse(BaseModel):
    """Response from Stripe checkout session creation."""
    session_id: str
    checkout_url: str
    payment_intent_id: str
    expires_at: datetime


class StripeWebhookEvent(BaseModel):
    """Stripe webhook event structure."""
    event_type: str
    event_id: str
    session_id: Optional[str] = None
    payment_intent_id: Optional[str] = None
    client_reference_id: Optional[str] = None
    status: Optional[str] = None


# -----------------------------------------------------------------------------
# Payment Flow Models
# -----------------------------------------------------------------------------

class PaymentInitiation(BaseModel):
    """Model for initiating payment flow."""
    quote_id: str
    user_id: str
    amount: int
    currency: str = "SGD"
    product_name: str
    customer_email: Optional[str] = None


class PaymentInitiationResponse(BaseModel):
    """Response after initiating payment."""
    payment_intent_id: str
    checkout_url: str
    session_id: str
    expires_at: datetime
    payment_status: str = "pending"


class PaymentConfirmation(BaseModel):
    """Payment confirmation details."""
    payment_intent_id: str
    payment_status: Literal["completed", "failed", "expired"]
    stripe_payment_intent: Optional[str] = None
    amount: int
    currency: str
    completed_at: Optional[datetime] = None


class PaymentHistory(BaseModel):
    """Payment history for a user."""
    user_id: str
    payments: list[PaymentRecord]
    total_payments: int
    total_amount: int


# TODO: Add models for:
# - PaymentRefund
# - PaymentDispute
# - PaymentAnalytics
# - BulkPaymentOperation
