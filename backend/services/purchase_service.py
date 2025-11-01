"""
Purchase Service

Orchestrates the complete purchase flow including payment processing.
Coordinates between DynamoDB payment records, Stripe checkout sessions,
and policy generation after successful payment.

Usage:
    from backend.services.purchase_service import PurchaseService

    service = PurchaseService()
    checkout_result = await service.initiate_payment(user_id, quote_id, ...)
    status = await service.check_payment_status(payment_intent_id)
    policy = await service.complete_purchase_after_payment(payment_intent_id)
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from backend.database.dynamodb_client import DynamoDBClient
from backend.database.supabase_client import SupabaseClient
from backend.services.stripe_integration import StripeService
from backend.services.ancileo_client import AncileoClient
from backend.models.payment import (
    PaymentRecord,
    PaymentInitiation,
    PaymentConfirmation,
    StripeCheckoutResponse
)
from backend.config import settings

logger = logging.getLogger(__name__)


class PurchaseService:
    """
    Service for managing insurance policy purchases and payments.

    Orchestrates:
    - Payment record creation in DynamoDB
    - Stripe checkout session generation
    - Payment status tracking
    - Policy generation after successful payment

    Flow:
    1. User requests to purchase a quote
    2. Create payment record in DynamoDB (status: pending)
    3. Create Stripe checkout session
    4. Return checkout URL to user
    5. User completes payment (Stripe webhook updates DynamoDB)
    6. Complete purchase and generate policy document
    """

    def __init__(self):
        """Initialize purchase service with database and payment clients."""
        self.dynamodb_client = DynamoDBClient()
        self.stripe_service = StripeService()
        self.supabase_client = SupabaseClient()
        self.ancileo_client = AncileoClient()

    async def initiate_payment(
        self,
        user_id: str,
        quote_id: str,
        amount: int,
        currency: str,
        product_name: str,
        customer_email: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> StripeCheckoutResponse:
        """
        Initiate payment process for an insurance policy purchase.

        This is the main entry point for starting a purchase. It:
        1. Generates a unique payment intent ID
        2. Creates a payment record in DynamoDB with status "pending"
        3. Creates a Stripe checkout session
        4. Returns the checkout URL for the user to complete payment

        Args:
            user_id: User identifier
            quote_id: Quote identifier to purchase
            amount: Amount in cents (e.g., 15000 = $150.00)
            currency: Currency code (e.g., "SGD")
            product_name: Product description (e.g., "Premium Travel Insurance")
            customer_email: Optional email for pre-filling Stripe checkout
            metadata: Additional metadata to attach to payment

        Returns:
            StripeCheckoutResponse with:
            - payment_intent_id: Unique payment identifier
            - checkout_url: Stripe checkout URL for user
            - session_id: Stripe session identifier
            - expires_at: Session expiration time

        Raises:
            Exception: If payment creation or Stripe session creation fails

        TODO: Add validation for quote_id existence
        TODO: Add duplicate payment detection
        TODO: Add payment amount limits
        """
        try:
            # Step 0: Check for duplicate payment (quote already has pending/completed payment)
            existing_payment = await self.dynamodb_client.get_payment_by_quote(quote_id)
            if existing_payment:
                existing_status = existing_payment.get("payment_status")
                if existing_status in ["completed", "pending"]:
                    logger.warning(f"Quote {quote_id} already has {existing_status} payment")
                    raise ValueError(
                        f"This quote already has a {existing_status} payment. "
                        f"Payment ID: {existing_payment['payment_intent_id']}"
                    )

            # Generate unique payment intent ID
            payment_intent_id = f"pi_{uuid.uuid4().hex}"

            logger.info(f"Initiating payment for user {user_id}, quote {quote_id}")

            # Step 1: Create payment record in DynamoDB
            payment_record = await self.dynamodb_client.create_payment(
                payment_intent_id=payment_intent_id,
                user_id=user_id,
                quote_id=quote_id,
                amount=amount,
                currency=currency,
                product_name=product_name
            )

            logger.info(f"Created payment record: {payment_intent_id}")

            # Step 2: Create Stripe checkout session
            stripe_session = await self.stripe_service.create_checkout_session(
                payment_intent_id=payment_intent_id,
                amount=amount,
                product_name=product_name,
                customer_email=customer_email,
                metadata={
                    "user_id": user_id,
                    "quote_id": quote_id,
                    **(metadata or {})
                }
            )

            # Step 3: Update payment record with Stripe session ID
            await self.dynamodb_client.update_payment_status(
                payment_intent_id=payment_intent_id,
                status="pending",
                stripe_session_id=stripe_session["session_id"]
            )

            logger.info(
                f"Created Stripe checkout session {stripe_session['session_id']} "
                f"for payment {payment_intent_id}"
            )

            # Return checkout details
            return StripeCheckoutResponse(
                payment_intent_id=payment_intent_id,
                checkout_url=stripe_session["checkout_url"],
                session_id=stripe_session["session_id"],
                amount=amount,
                currency=currency,
                expires_at=stripe_session["expires_at"]
            )

        except Exception as e:
            logger.error(f"Error initiating payment: {e}")
            # If we created a payment record, mark it as failed
            if 'payment_intent_id' in locals():
                try:
                    await self.dynamodb_client.update_payment_status(
                        payment_intent_id=payment_intent_id,
                        status="failed"
                    )
                    # Update with failure reason
                    await self.dynamodb_client.update_payment(
                        payment_intent_id=payment_intent_id,
                        updates={"failure_reason": str(e)}
                    )
                except Exception as cleanup_error:
                    logger.error(f"Error during payment cleanup: {cleanup_error}")
            raise

    async def check_payment_status(
        self,
        payment_intent_id: str
    ) -> Dict[str, Any]:
        """
        Check the current status of a payment.

        Queries DynamoDB for the payment record and returns its status.
        Use this to poll payment status or verify completion.

        Args:
            payment_intent_id: Payment intent identifier

        Returns:
            Dictionary with:
            - payment_intent_id: Payment identifier
            - payment_status: Current status (pending/completed/failed/expired)
            - stripe_session_id: Stripe session ID if available
            - amount: Payment amount
            - currency: Payment currency
            - created_at: Payment creation time
            - updated_at: Last update time
            - stripe_payment_intent: Stripe payment intent ID if completed

        Raises:
            ValueError: If payment not found

        TODO: Add caching to reduce DynamoDB queries
        TODO: Add webhook event history
        """
        try:
            payment = await self.dynamodb_client.get_payment(payment_intent_id)

            if not payment:
                raise ValueError(f"Payment not found: {payment_intent_id}")

            logger.info(f"Payment {payment_intent_id} status: {payment['payment_status']}")

            return {
                "payment_intent_id": payment["payment_intent_id"],
                "payment_status": payment["payment_status"],
                "stripe_session_id": payment.get("stripe_session_id"),
                "amount": payment["amount"],
                "currency": payment["currency"],
                "product_name": payment["product_name"],
                "user_id": payment["user_id"],
                "quote_id": payment["quote_id"],
                "created_at": payment["created_at"],
                "updated_at": payment["updated_at"],
                "stripe_payment_intent": payment.get("stripe_payment_intent"),
                "failure_reason": payment.get("failure_reason")
            }

        except Exception as e:
            logger.error(f"Error checking payment status: {e}")
            raise

    async def complete_purchase_after_payment(
        self,
        payment_intent_id: str
    ) -> Dict[str, Any]:
        """
        Complete the purchase after successful payment.

        This is called after payment is confirmed (typically via webhook).
        If Ancileo mapping exists, calls Ancileo Purchase API to complete the purchase.
        Generates the policy document and updates records.

        Args:
            payment_intent_id: Payment intent identifier

        Returns:
            Dictionary with:
            - policy_id: Generated policy identifier
            - policy_number: Human-readable policy number
            - status: Purchase completion status
            - ancileo_purchase_id: Ancileo purchase ID if Ancileo API was called
            - policy_document_url: URL to policy PDF

        Raises:
            ValueError: If payment not found or not completed
        """
        try:
            # Step 1: Verify payment is completed
            payment = await self.dynamodb_client.get_payment(payment_intent_id)

            if not payment:
                raise ValueError(f"Payment not found: {payment_intent_id}")

            if payment["payment_status"] != "completed":
                raise ValueError(
                    f"Payment not completed: {payment_intent_id} "
                    f"(status: {payment['payment_status']})"
                )

            logger.info(f"Completing purchase for payment {payment_intent_id}")

            # Step 2: Get selection with Ancileo mapping from Supabase
            await self.supabase_client.connect()
            selection = await self.supabase_client.get_selection_by_payment_id(payment_intent_id)

            ancileo_purchase_id = None
            purchased_offers = None

            # Step 3: If selection exists, call Ancileo Purchase API
            # Note: quote_id in selection is now the Ancileo quote ID directly
            if selection and selection.get('quote_id'):
                try:
                    ancileo_result = await self._complete_ancileo_purchase(
                        payment_intent_id=payment_intent_id,
                        selection=selection,
                        payment=payment
                    )
                    ancileo_purchase_id = ancileo_result.get('id')
                    purchased_offers = ancileo_result.get('purchasedOffers', [])
                    logger.info(f"Ancileo Purchase completed: {ancileo_purchase_id}")
                except Exception as e:
                    logger.error(f"Ancileo Purchase API failed: {e}")
                    # Continue without Ancileo - generate internal policy anyway
                    # This allows graceful degradation

            # Step 4: Generate policy document
            policy_id = f"pol_{uuid.uuid4().hex[:12]}"
            policy_number = f"POL-{datetime.now().year}-{uuid.uuid4().hex[:8].upper()}"

            # Step 5: Create policy record in Supabase (if selection exists)
            if selection:
                try:
                    policy_data = {
                        'selection_id': selection['selection_id'],
                        'user_id': payment['user_id'],
                        'quote_id': payment['quote_id'],
                        'payment_id': payment_intent_id,
                        'external_purchase_id': ancileo_purchase_id or '',
                        'purchased_offer_id': selection.get('selected_offer_id') or '',
                        'product_code': selection.get('selected_product_code') or '',
                        'cover_start_date': None,  # TODO: Extract from purchase response
                        'cover_end_date': None,  # TODO: Extract from purchase response
                        'premium_amount': payment['amount'] / 100.0,  # Convert cents to currency
                        'currency': payment['currency'],
                        'purchase_response': purchased_offers if purchased_offers else None,
                        'status': 'active'
                    }
                    
                    # TODO: Store policy in Supabase policies table
                    # await self.supabase_client.create_policy(policy_data)
                    logger.info(f"Policy data prepared for storage: {policy_id}")
                    
                except Exception as e:
                    logger.warning(f"Failed to store policy in Supabase: {e}")

            logger.info(f"Generated policy {policy_id} for payment {payment_intent_id}")

            return {
                "policy_id": policy_id,
                "policy_number": policy_number,
                "status": "completed",
                "payment_intent_id": payment_intent_id,
                "quote_id": payment["quote_id"],
                "user_id": payment["user_id"],
                "amount": payment["amount"],
                "currency": payment["currency"],
                "product_name": payment["product_name"],
                "ancileo_purchase_id": ancileo_purchase_id,
                "purchased_offers": purchased_offers,
                "policy_document_url": None,  # TODO: Generate PDF
                "created_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error completing purchase: {e}")
            raise

    async def _complete_ancileo_purchase(
        self,
        payment_intent_id: str,
        selection: Dict[str, Any],
        payment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Private method: Call Ancileo Purchase API to complete purchase.
        
        Args:
            payment_intent_id: Payment intent ID
            selection: Selection record from Supabase (with quotation data)
            payment: Payment record from DynamoDB
        
        Returns:
            Ancileo Purchase API response
        
        Raises:
            ValueError: If required data is missing
            httpx.HTTPStatusError: If Ancileo API fails
        """
        # Extract Ancileo info from selection
        # Note: quote_id is now the Ancileo quote ID directly
        ancileo_quote_id = selection.get('quote_id')  # quote_id is the Ancileo quote ID
        selected_offer_id = selection.get('selected_offer_id')
        product_type = selection.get('product_type', 'travel-insurance')
        quantity = selection.get('quantity', 1)
        total_price = selection.get('total_price')
        is_send_email = selection.get('is_send_email', True)
        
        insureds = selection.get('insureds')
        main_contact = selection.get('main_contact')
        
        # Get quotation data (includes market, language_code, channel)
        quotes_data = selection.get('quotes')
        if isinstance(quotes_data, dict):
            market = quotes_data.get('market', 'SG')
            language_code = quotes_data.get('language_code', 'en')
            channel = quotes_data.get('channel', 'white-label')
            # Get selected offer details from quotation
            quotation_response = quotes_data.get('quotation_response', {})
            if isinstance(quotation_response, dict):
                offer_categories = quotation_response.get('offerCategories', [])
                if offer_categories:
                    offers = offer_categories[0].get('offers', [])
                    selected_offer = next(
                        (o for o in offers if o.get('id') == selected_offer_id),
                        None
                    )
                    if selected_offer:
                        product_code = selected_offer.get('productCode')
                        unit_price = float(selected_offer.get('unitPrice', 0))
                        currency = selected_offer.get('currency', 'SGD')
                    else:
                        # Fallback to selection data
                        product_code = selection.get('selected_product_code')
                        unit_price = float(total_price) if total_price else payment['amount'] / 100.0
                        currency = payment['currency']
                else:
                    product_code = selection.get('selected_product_code')
                    unit_price = float(total_price) if total_price else payment['amount'] / 100.0
                    currency = payment['currency']
            else:
                product_code = selection.get('selected_product_code')
                unit_price = float(total_price) if total_price else payment['amount'] / 100.0
                currency = payment['currency']
        else:
            market = 'SG'
            language_code = 'en'
            channel = 'white-label'
            product_code = selection.get('selected_product_code')
            unit_price = float(total_price) if total_price else payment['amount'] / 100.0
            currency = payment['currency']
        
        # Validate required fields
        if not ancileo_quote_id:
            raise ValueError("quote_id (Ancileo quote ID) is required in selection")
        if not selected_offer_id:
            raise ValueError("selected_offer_id is required in selection")
        if not insureds:
            raise ValueError("insureds is required in selection")
        if not main_contact:
            raise ValueError("main_contact is required in selection")
        
        # Build purchase_offers array
        purchase_offers = [{
            "productType": product_type,
            "offerId": selected_offer_id,
            "productCode": product_code or '',
            "unitPrice": unit_price,
            "currency": currency,
            "quantity": quantity,
            "totalPrice": float(total_price) if total_price else (unit_price * quantity),
            "isSendEmail": is_send_email
        }]
        
        # Ensure insureds is a list
        if not isinstance(insureds, list):
            insureds = [insureds] if insureds else []
        
        # Call Ancileo Purchase API
        logger.info(
            f"Calling Ancileo Purchase API: quote_id={ancileo_quote_id}, "
            f"offer_id={selected_offer_id}"
        )
        
        result = await self.ancileo_client.complete_purchase(
            quote_id=ancileo_quote_id,
            purchase_offers=purchase_offers,
            insureds=insureds,
            main_contact=main_contact,
            market=market,
            language_code=language_code,
            channel=channel
        )
        
        return result

    async def get_user_payments(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get all payments for a specific user.

        Args:
            user_id: User identifier
            limit: Maximum number of payments to return

        Returns:
            List of payment records

        Raises:
            Exception: If database query fails
        """
        try:
            payments = await self.dynamodb_client.get_user_payments(user_id, limit=limit)
            logger.info(f"Retrieved {len(payments)} payments for user {user_id}")
            return payments

        except Exception as e:
            logger.error(f"Error getting user payments: {e}")
            raise

    async def cancel_payment(
        self,
        payment_intent_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """
        Cancel a pending payment.

        Updates payment status to "cancelled" and cancels Stripe payment intent
        if it exists.

        Args:
            payment_intent_id: Payment intent identifier
            reason: Optional cancellation reason

        Returns:
            True if cancelled successfully

        Raises:
            ValueError: If payment not found or already completed

        TODO: Add refund support for completed payments
        """
        try:
            payment = await self.dynamodb_client.get_payment(payment_intent_id)

            if not payment:
                raise ValueError(f"Payment not found: {payment_intent_id}")

            if payment["payment_status"] == "completed":
                raise ValueError(
                    f"Cannot cancel completed payment: {payment_intent_id}. "
                    "Use refund instead."
                )

            logger.info(f"Cancelling payment {payment_intent_id}")

            # Cancel Stripe payment intent if exists
            stripe_payment_intent = payment.get("stripe_payment_intent")
            if stripe_payment_intent:
                await self.stripe_service.cancel_payment_intent(stripe_payment_intent)

            # Update DynamoDB status
            await self.dynamodb_client.update_payment_status(
                payment_intent_id=payment_intent_id,
                status="cancelled"
            )

            # Add cancellation reason
            if reason:
                await self.dynamodb_client.update_payment(
                    payment_intent_id=payment_intent_id,
                    updates={"failure_reason": reason}
                )

            logger.info(f"Cancelled payment {payment_intent_id}")
            return True

        except Exception as e:
            logger.error(f"Error cancelling payment: {e}")
            raise

    async def get_user_payments(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get all payments for a user.

        Args:
            user_id: User identifier
            limit: Maximum number of payments to return

        Returns:
            List of payment records sorted by creation date (newest first)

        TODO: Add pagination support
        TODO: Add filtering by status
        """
        try:
            payments = await self.dynamodb_client.get_user_payments(
                user_id=user_id,
                limit=limit
            )

            logger.info(f"Retrieved {len(payments)} payments for user {user_id}")
            return payments

        except Exception as e:
            logger.error(f"Error getting user payments: {e}")
            raise

    async def get_quote_payment(
        self,
        quote_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get payment record for a specific quote.

        Args:
            quote_id: Quote identifier

        Returns:
            Payment record if exists, None otherwise

        TODO: Handle multiple payments for same quote
        """
        try:
            payment = await self.dynamodb_client.get_payment_by_quote(quote_id)
            return payment

        except Exception as e:
            logger.error(f"Error getting quote payment: {e}")
            raise


# Global service instance (optional)
_purchase_service: Optional[PurchaseService] = None


def get_purchase_service() -> PurchaseService:
    """
    Get or create global purchase service instance.

    Returns:
        PurchaseService: Configured service instance
    """
    global _purchase_service
    if _purchase_service is None:
        _purchase_service = PurchaseService()
    return _purchase_service
