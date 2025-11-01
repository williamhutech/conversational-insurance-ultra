"""
Stripe Integration Service

Handles Stripe API operations for payment processing.
Creates checkout sessions, retrieves payment status, and manages payment intents.

Usage:
    from backend.services.stripe_integration import StripeService

    service = StripeService()
    session = await service.create_checkout_session(...)
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

import stripe
from backend.config import settings

logger = logging.getLogger(__name__)

# Initialize Stripe with API key
stripe.api_key = settings.stripe_secret_key


class StripeService:
    """
    Stripe service for payment processing.

    Provides methods for:
    - Creating checkout sessions
    - Retrieving session details
    - Managing payment intents
    - Checking payment status
    """

    def __init__(self):
        """Initialize Stripe service."""
        self.currency = settings.stripe_currency
        self.success_url = settings.payment_success_url
        self.cancel_url = settings.payment_cancel_url

    async def create_checkout_session(
        self,
        payment_intent_id: str,
        amount: int,
        product_name: str,
        customer_email: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create Stripe checkout session for insurance payment.

        Args:
            payment_intent_id: Unique payment identifier (used as client_reference_id)
            amount: Amount in cents
            product_name: Product description
            customer_email: Customer email for pre-filling
            metadata: Additional metadata to attach

        Returns:
            Dictionary with:
            - session_id: Stripe checkout session ID
            - checkout_url: URL for customer to complete payment
            - expires_at: Session expiration time

        Raises:
            stripe.error.StripeError: If session creation fails

        TODO: Add support for multiple line items
        TODO: Add support for coupons/discounts
        TODO: Add support for subscription payments
        """
        try:
            # Prepare session parameters
            session_params = {
                'payment_method_types': ['card'],
                'line_items': [
                    {
                        'price_data': {
                            'currency': self.currency.lower(),
                            'unit_amount': amount,
                            'product_data': {
                                'name': product_name,
                                'description': f'Travel Insurance Policy - {product_name}',
                            },
                        },
                        'quantity': 1,
                    }
                ],
                'mode': 'payment',
                'success_url': f'{self.success_url}?session_id={{CHECKOUT_SESSION_ID}}',
                'cancel_url': self.cancel_url,
                'client_reference_id': payment_intent_id,  # Link to our payment record
                'expires_at': int((datetime.now() + timedelta(hours=24)).timestamp()),
            }

            # Add customer email if provided
            if customer_email:
                session_params['customer_email'] = customer_email

            # Add metadata
            if metadata:
                session_params['metadata'] = metadata

            # Create session
            session = stripe.checkout.Session.create(**session_params)

            logger.info(f"Created Stripe checkout session: {session.id}")

            return {
                'session_id': session.id,
                'checkout_url': session.url,
                'payment_intent_id': payment_intent_id,
                'expires_at': datetime.fromtimestamp(session.expires_at),
                'amount': amount,
                'currency': self.currency
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating checkout session: {e}")
            raise

    async def get_checkout_session(self, session_id: str) -> Dict[str, Any]:
        """
        Retrieve checkout session details.

        Args:
            session_id: Stripe checkout session ID

        Returns:
            Session details including payment status

        TODO: Add caching for frequently accessed sessions
        """
        try:
            session = stripe.checkout.Session.retrieve(session_id)

            return {
                'session_id': session.id,
                'payment_status': session.payment_status,
                'status': session.status,
                'client_reference_id': session.client_reference_id,
                'payment_intent': session.payment_intent,
                'customer_email': session.customer_email,
                'amount_total': session.amount_total,
                'currency': session.currency,
                'created': datetime.fromtimestamp(session.created),
                'expires_at': datetime.fromtimestamp(session.expires_at) if session.expires_at else None
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error retrieving session {session_id}: {e}")
            raise

    async def get_payment_intent(self, payment_intent_id: str) -> Dict[str, Any]:
        """
        Retrieve payment intent details.

        Args:
            payment_intent_id: Stripe payment intent ID

        Returns:
            Payment intent details

        TODO: Add support for payment method details
        """
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            return {
                'id': intent.id,
                'status': intent.status,
                'amount': intent.amount,
                'currency': intent.currency,
                'payment_method': intent.payment_method,
                'created': datetime.fromtimestamp(intent.created),
                'client_secret': intent.client_secret
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error retrieving payment intent {payment_intent_id}: {e}")
            raise

    async def cancel_payment_intent(self, payment_intent_id: str) -> bool:
        """
        Cancel a payment intent.

        Args:
            payment_intent_id: Stripe payment intent ID

        Returns:
            True if cancelled successfully

        TODO: Add reason for cancellation
        """
        try:
            intent = stripe.PaymentIntent.cancel(payment_intent_id)
            logger.info(f"Cancelled payment intent: {payment_intent_id}")
            return intent.status == 'canceled'
        except stripe.error.StripeError as e:
            logger.error(f"Error cancelling payment intent: {e}")
            return False

    async def create_refund(
        self,
        payment_intent_id: str,
        amount: Optional[int] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a refund for a payment.

        Args:
            payment_intent_id: Stripe payment intent ID
            amount: Amount to refund in cents (None for full refund)
            reason: Reason for refund

        Returns:
            Refund details

        TODO: Implement refund processing
        TODO: Update payment record in DynamoDB
        """
        try:
            refund_params = {'payment_intent': payment_intent_id}

            if amount:
                refund_params['amount'] = amount

            if reason:
                refund_params['reason'] = reason

            refund = stripe.Refund.create(**refund_params)

            logger.info(f"Created refund {refund.id} for payment {payment_intent_id}")

            return {
                'refund_id': refund.id,
                'status': refund.status,
                'amount': refund.amount,
                'currency': refund.currency,
                'created': datetime.fromtimestamp(refund.created)
            }
        except stripe.error.StripeError as e:
            logger.error(f"Error creating refund: {e}")
            raise

    async def list_payment_methods(self, customer_id: str) -> list[Dict[str, Any]]:
        """
        List payment methods for a customer.

        Args:
            customer_id: Stripe customer ID

        Returns:
            List of payment methods

        TODO: Implement payment method listing
        """
        try:
            methods = stripe.PaymentMethod.list(customer=customer_id, type='card')
            return [
                {
                    'id': method.id,
                    'type': method.type,
                    'card': method.card if hasattr(method, 'card') else None
                }
                for method in methods.data
            ]
        except stripe.error.StripeError as e:
            logger.error(f"Error listing payment methods: {e}")
            raise


# Global service instance (optional)
_stripe_service: Optional[StripeService] = None


def get_stripe_service() -> StripeService:
    """
    Get or create global Stripe service instance.

    Returns:
        StripeService: Configured service instance
    """
    global _stripe_service
    if _stripe_service is None:
        _stripe_service = StripeService()
    return _stripe_service
