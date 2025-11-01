"""
Standardized Error Response Models

Provides consistent error formatting for AI-driven conversational interfaces.
Error responses include actionable suggestions for recovery.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class ErrorCode(str, Enum):
    """Standard error codes for payment operations."""

    # Payment errors
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_DECLINED = "payment_declined"
    CARD_DECLINED = "card_declined"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    CARD_EXPIRED = "card_expired"
    INVALID_CARD = "invalid_card"

    # Quote/validation errors
    QUOTE_NOT_FOUND = "quote_not_found"
    QUOTE_EXPIRED = "quote_expired"
    DUPLICATE_PAYMENT = "duplicate_payment"
    INVALID_AMOUNT = "invalid_amount"

    # Session errors
    SESSION_EXPIRED = "session_expired"
    SESSION_NOT_FOUND = "session_not_found"

    # System errors
    SERVICE_UNAVAILABLE = "service_unavailable"
    DATABASE_ERROR = "database_error"
    INVALID_REQUEST = "invalid_request"
    UNKNOWN_ERROR = "unknown_error"


class SuggestedAction(str, Enum):
    """Suggested actions for error recovery."""

    RETRY_PAYMENT = "retry_payment"
    USE_DIFFERENT_CARD = "use_different_card"
    CHECK_CARD_DETAILS = "check_card_details"
    CONTACT_BANK = "contact_bank"
    SAVE_QUOTE_FOR_LATER = "save_quote_for_later"
    REQUEST_NEW_QUOTE = "request_new_quote"
    CONTACT_SUPPORT = "contact_support"
    WAIT_AND_RETRY = "wait_and_retry"


class ConversationalError(BaseModel):
    """
    Standardized error response for conversational AI interfaces.

    Designed to be easily parsed by AI agents for natural error handling.
    """

    error_code: ErrorCode = Field(
        ...,
        description="Machine-readable error code"
    )

    message: str = Field(
        ...,
        description="Human-readable error message for the user"
    )

    suggested_action: SuggestedAction = Field(
        ...,
        description="Primary suggested action for recovery"
    )

    alternative_actions: List[SuggestedAction] = Field(
        default_factory=list,
        description="Alternative actions the user can take"
    )

    user_message: str = Field(
        ...,
        description="Conversational message for AI to relay to user"
    )

    technical_details: Optional[str] = Field(
        None,
        description="Technical details for debugging (not shown to user)"
    )

    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for AI decision-making"
    )

    can_retry: bool = Field(
        True,
        description="Whether the operation can be retried"
    )

    requires_user_action: bool = Field(
        True,
        description="Whether user action is required to proceed"
    )


class PaymentErrorResponse(BaseModel):
    """Payment-specific error response with checkout details."""

    error: ConversationalError
    payment_intent_id: Optional[str] = None
    quote_id: Optional[str] = None
    amount: Optional[int] = None
    currency: Optional[str] = None


# Predefined error templates for common scenarios
ERROR_TEMPLATES = {
    "duplicate_payment": ConversationalError(
        error_code=ErrorCode.DUPLICATE_PAYMENT,
        message="This quote already has a pending or completed payment.",
        suggested_action=SuggestedAction.CONTACT_SUPPORT,
        alternative_actions=[SuggestedAction.REQUEST_NEW_QUOTE],
        user_message="It looks like you've already started a payment for this quote. Would you like me to check the status of your existing payment, or help you create a new quote?",
        can_retry=False,
        requires_user_action=True
    ),

    "card_declined": ConversationalError(
        error_code=ErrorCode.CARD_DECLINED,
        message="Your card was declined by your bank.",
        suggested_action=SuggestedAction.USE_DIFFERENT_CARD,
        alternative_actions=[
            SuggestedAction.CONTACT_BANK,
            SuggestedAction.SAVE_QUOTE_FOR_LATER
        ],
        user_message="Your payment was declined. This could be due to insufficient funds, incorrect card details, or your bank's security settings. Would you like to try a different payment method, or I can save this quote and send you a payment link to complete later?",
        can_retry=True,
        requires_user_action=True
    ),

    "session_expired": ConversationalError(
        error_code=ErrorCode.SESSION_EXPIRED,
        message="The payment session has expired (24 hours).",
        suggested_action=SuggestedAction.REQUEST_NEW_QUOTE,
        alternative_actions=[SuggestedAction.CONTACT_SUPPORT],
        user_message="Your payment session has expired. Don't worry! I can help you create a fresh quote with the same coverage. Would you like me to generate a new quote for you?",
        can_retry=False,
        requires_user_action=True
    ),

    "quote_not_found": ConversationalError(
        error_code=ErrorCode.QUOTE_NOT_FOUND,
        message="The specified quote was not found.",
        suggested_action=SuggestedAction.REQUEST_NEW_QUOTE,
        alternative_actions=[SuggestedAction.CONTACT_SUPPORT],
        user_message="I couldn't find that quote in our system. It may have expired or been removed. Would you like me to help you create a new quote?",
        can_retry=False,
        requires_user_action=True
    ),

    "service_unavailable": ConversationalError(
        error_code=ErrorCode.SERVICE_UNAVAILABLE,
        message="Payment service is temporarily unavailable.",
        suggested_action=SuggestedAction.SAVE_QUOTE_FOR_LATER,
        alternative_actions=[
            SuggestedAction.WAIT_AND_RETRY,
            SuggestedAction.CONTACT_SUPPORT
        ],
        user_message="Our payment system is experiencing temporary issues. I can save your quote and send you a payment link via email to complete when the system is back up. Would you like me to do that?",
        can_retry=True,
        requires_user_action=True
    )
}


def create_payment_error(
    error_type: str,
    payment_intent_id: Optional[str] = None,
    quote_id: Optional[str] = None,
    amount: Optional[int] = None,
    currency: Optional[str] = None,
    technical_details: Optional[str] = None,
    **context
) -> PaymentErrorResponse:
    """
    Create a standardized payment error response.

    Args:
        error_type: Key from ERROR_TEMPLATES or custom error
        payment_intent_id: Payment identifier if available
        quote_id: Quote identifier if available
        amount: Payment amount if available
        currency: Payment currency if available
        technical_details: Technical error details for debugging
        **context: Additional context for the error

    Returns:
        PaymentErrorResponse with conversational error
    """
    error_template = ERROR_TEMPLATES.get(error_type)

    if not error_template:
        # Create generic error
        error_template = ConversationalError(
            error_code=ErrorCode.UNKNOWN_ERROR,
            message=f"An error occurred: {error_type}",
            suggested_action=SuggestedAction.CONTACT_SUPPORT,
            alternative_actions=[SuggestedAction.WAIT_AND_RETRY],
            user_message="I encountered an unexpected issue. Please try again, or I can connect you with our support team.",
            can_retry=True,
            requires_user_action=True
        )

    # Add technical details and context
    error = error_template.model_copy(deep=True)
    error.technical_details = technical_details
    error.context = context

    return PaymentErrorResponse(
        error=error,
        payment_intent_id=payment_intent_id,
        quote_id=quote_id,
        amount=amount,
        currency=currency
    )
