"""
Block 4: Purchase Execution Router

FastAPI routes for insurance policy purchase and payment processing.
Provides endpoints for initiating payments, checking status, and managing purchases.

Routes:
    POST /api/purchase/initiate - Initiate a new payment for a quote
    GET /api/purchase/payment/{payment_intent_id} - Get payment status
    POST /api/purchase/cancel/{payment_intent_id} - Cancel a pending payment
    POST /api/purchase/complete/{payment_intent_id} - Complete purchase after payment
    GET /api/purchase/user/{user_id}/payments - Get user's payment history
    GET /api/purchase/quote/{quote_id}/payment - Get payment for a quote

Webhook Routes (mounted separately in main.py):
    POST /webhook/stripe - Stripe payment webhook handler
    GET /success - Payment success page
    GET /cancel - Payment cancel page

Usage:
    from backend.routers import purchase_router
    app.include_router(purchase_router, prefix="/api")
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field

from backend.services.purchase_service import get_purchase_service, PurchaseService
from backend.models.payment import (
    PaymentInitiation,
    StripeCheckoutResponse,
    PaymentConfirmation
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/purchase",
    tags=["Block 4: Purchase Execution"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)


# =============================================================================
# Request/Response Models
# =============================================================================

class InitiatePaymentRequest(BaseModel):
    """Request to initiate a payment for a quote."""
    user_id: str = Field(..., description="User identifier")
    quote_id: str = Field(..., description="Quote identifier to purchase")
    amount: int = Field(..., gt=0, description="Amount in cents (e.g., 15000 = $150.00)")
    currency: str = Field(default="SGD", description="Currency code")
    product_name: str = Field(..., description="Product description")
    customer_email: Optional[str] = Field(None, description="Customer email for Stripe checkout")
    metadata: Optional[Dict[str, str]] = Field(default_factory=dict, description="Additional metadata")


class PaymentStatusResponse(BaseModel):
    """Payment status response."""
    payment_intent_id: str
    payment_status: str
    stripe_session_id: Optional[str]
    amount: int
    currency: str
    product_name: str
    user_id: str
    quote_id: str
    created_at: str
    updated_at: str
    stripe_payment_intent: Optional[str]
    failure_reason: Optional[str]


class CompletePurchaseResponse(BaseModel):
    """Purchase completion response."""
    policy_id: str
    policy_number: str
    status: str
    payment_intent_id: str
    quote_id: str
    user_id: str
    amount: int
    currency: str
    product_name: str
    policy_document_url: Optional[str]
    created_at: str


class CancelPaymentResponse(BaseModel):
    """Payment cancellation response."""
    payment_intent_id: str
    status: str
    message: str


# =============================================================================
# Payment Endpoints
# =============================================================================

@router.post(
    "/initiate",
    response_model=StripeCheckoutResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate Payment",
    description="""
    Initiate a payment for an insurance policy quote.

    This endpoint:
    1. Creates a payment record in DynamoDB with status "pending"
    2. Generates a Stripe checkout session
    3. Returns the checkout URL for the user to complete payment

    The user should be redirected to the checkout_url to complete payment.
    Payment status will be updated via Stripe webhook when payment completes.
    """
)
async def initiate_payment(
    request: InitiatePaymentRequest,
    purchase_service: PurchaseService = Depends(get_purchase_service)
) -> StripeCheckoutResponse:
    """
    Initiate payment for a quote.

    Args:
        request: Payment initiation request
        purchase_service: Injected purchase service

    Returns:
        StripeCheckoutResponse with checkout URL

    Raises:
        HTTPException: If payment initiation fails
    """
    try:
        logger.info(f"Initiating payment for user {request.user_id}, quote {request.quote_id}")

        result = await purchase_service.initiate_payment(
            user_id=request.user_id,
            quote_id=request.quote_id,
            amount=request.amount,
            currency=request.currency,
            product_name=request.product_name,
            customer_email=request.customer_email,
            metadata=request.metadata
        )

        logger.info(f"Payment initiated: {result.payment_intent_id}")
        return result

    except Exception as e:
        logger.error(f"Error initiating payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate payment: {str(e)}"
        )


@router.get(
    "/payment/{payment_intent_id}",
    response_model=PaymentStatusResponse,
    summary="Get Payment Status",
    description="""
    Get the current status of a payment.

    Returns the payment record with current status:
    - pending: Payment initiated, awaiting completion
    - completed: Payment successful
    - failed: Payment failed
    - expired: Checkout session expired
    - cancelled: Payment cancelled
    """
)
async def get_payment_status(
    payment_intent_id: str,
    purchase_service: PurchaseService = Depends(get_purchase_service)
) -> PaymentStatusResponse:
    """
    Get payment status.

    Args:
        payment_intent_id: Payment intent identifier
        purchase_service: Injected purchase service

    Returns:
        Payment status details

    Raises:
        HTTPException: If payment not found
    """
    try:
        logger.info(f"Getting payment status: {payment_intent_id}")

        status_data = await purchase_service.check_payment_status(payment_intent_id)
        return PaymentStatusResponse(**status_data)

    except ValueError as e:
        logger.error(f"Payment not found: {payment_intent_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting payment status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get payment status: {str(e)}"
        )


@router.post(
    "/cancel/{payment_intent_id}",
    response_model=CancelPaymentResponse,
    summary="Cancel Payment",
    description="""
    Cancel a pending payment.

    Only pending payments can be cancelled. Completed payments must use refund instead.
    This will cancel the Stripe payment intent and update the payment record.
    """
)
async def cancel_payment(
    payment_intent_id: str,
    reason: Optional[str] = None,
    purchase_service: PurchaseService = Depends(get_purchase_service)
) -> CancelPaymentResponse:
    """
    Cancel a pending payment.

    Args:
        payment_intent_id: Payment intent identifier
        reason: Optional cancellation reason
        purchase_service: Injected purchase service

    Returns:
        Cancellation confirmation

    Raises:
        HTTPException: If cancellation fails
    """
    try:
        logger.info(f"Cancelling payment: {payment_intent_id}")

        success = await purchase_service.cancel_payment(
            payment_intent_id=payment_intent_id,
            reason=reason
        )

        if success:
            return CancelPaymentResponse(
                payment_intent_id=payment_intent_id,
                status="cancelled",
                message="Payment cancelled successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel payment"
            )

    except ValueError as e:
        logger.error(f"Invalid cancellation: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error cancelling payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel payment: {str(e)}"
        )


@router.post(
    "/complete/{payment_intent_id}",
    response_model=CompletePurchaseResponse,
    summary="Complete Purchase",
    description="""
    Complete the purchase after successful payment.

    This endpoint is typically called after payment is confirmed (via webhook).
    It generates the policy document and returns policy details.

    Note: Payment must be in "completed" status to complete purchase.
    """
)
async def complete_purchase(
    payment_intent_id: str,
    purchase_service: PurchaseService = Depends(get_purchase_service)
) -> CompletePurchaseResponse:
    """
    Complete purchase after payment.

    Args:
        payment_intent_id: Payment intent identifier
        purchase_service: Injected purchase service

    Returns:
        Policy details and confirmation

    Raises:
        HTTPException: If completion fails or payment not completed
    """
    try:
        logger.info(f"Completing purchase for payment: {payment_intent_id}")

        result = await purchase_service.complete_purchase_after_payment(payment_intent_id)
        return CompletePurchaseResponse(**result)

    except ValueError as e:
        logger.error(f"Invalid completion: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error completing purchase: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete purchase: {str(e)}"
        )


@router.get(
    "/user/{user_id}/payments",
    response_model=List[PaymentStatusResponse],
    summary="Get User Payments",
    description="""
    Get all payments for a user.

    Returns a list of payment records sorted by creation date (newest first).
    Useful for displaying payment history to users.
    """
)
async def get_user_payments(
    user_id: str,
    limit: int = 50,
    purchase_service: PurchaseService = Depends(get_purchase_service)
) -> List[PaymentStatusResponse]:
    """
    Get user's payment history.

    Args:
        user_id: User identifier
        limit: Maximum number of payments to return (default: 50)
        purchase_service: Injected purchase service

    Returns:
        List of payment records

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        logger.info(f"Getting payments for user: {user_id}")

        payments = await purchase_service.get_user_payments(user_id, limit=limit)
        return [PaymentStatusResponse(**p) for p in payments]

    except Exception as e:
        logger.error(f"Error getting user payments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user payments: {str(e)}"
        )


@router.get(
    "/quote/{quote_id}/payment",
    response_model=Optional[PaymentStatusResponse],
    summary="Get Quote Payment",
    description="""
    Get the payment record for a specific quote.

    Returns the most recent payment for the quote, or null if no payment exists.
    """
)
async def get_quote_payment(
    quote_id: str,
    purchase_service: PurchaseService = Depends(get_purchase_service)
) -> Optional[PaymentStatusResponse]:
    """
    Get payment for a quote.

    Args:
        quote_id: Quote identifier
        purchase_service: Injected purchase service

    Returns:
        Payment record if exists, None otherwise

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        logger.info(f"Getting payment for quote: {quote_id}")

        payment = await purchase_service.get_quote_payment(quote_id)

        if payment:
            return PaymentStatusResponse(**payment)
        return None

    except Exception as e:
        logger.error(f"Error getting quote payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get quote payment: {str(e)}"
        )


# =============================================================================
# Health Check
# =============================================================================

@router.get(
    "/health",
    summary="Health Check",
    description="Check if the purchase service is healthy"
)
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.

    Returns:
        Service health status
    """
    return {
        "service": "purchase",
        "status": "healthy",
        "block": "Block 4: Purchase Execution"
    }


# TODO: Add endpoint for refunds
# TODO: Add endpoint for payment history with filters
# TODO: Add endpoint for payment analytics
# TODO: Add authentication/authorization
# TODO: Add rate limiting
# TODO: Add request validation middleware
