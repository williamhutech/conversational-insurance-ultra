"""
Stripe Webhook Handler Service

Receives and processes Stripe webhook events for payment status updates.
Integrated with DynamoDB for payment record management.

Usage:
    # Can be run standalone or mounted in main FastAPI app
    uvicorn backend.services.payment.stripe_webhook:app --port 8086
"""

import json
import logging
from typing import Dict, Any
from datetime import datetime

import stripe
import boto3
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from backend.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stripe-webhook")

# Initialize DynamoDB client
if settings.dynamodb_endpoint:
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=settings.aws_region,
        endpoint_url=settings.dynamodb_endpoint
    )
else:
    dynamodb = boto3.resource('dynamodb', region_name=settings.aws_region)

payments_table = dynamodb.Table(settings.dynamodb_payments_table)

# Initialize FastAPI app
app = FastAPI(
    title="Stripe Webhook Service",
    version="1.0.0",
    description="Handles Stripe webhook events for insurance payments"
)


@app.get("/health")
async def health():
    """Health check endpoint for monitoring."""
    return {
        "status": "ok",
        "service": "stripe-webhook",
        "table": settings.dynamodb_payments_table
    }


@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """
    Stripe webhook endpoint.

    Processes Stripe events and updates payment status in DynamoDB.

    Events Handled:
    - checkout.session.completed: Payment successful
    - checkout.session.expired: Session expired without payment
    - payment_intent.payment_failed: Payment failed

    Args:
        request: FastAPI request with Stripe event payload

    Returns:
        JSONResponse with status

    Raises:
        HTTPException: If signature verification fails or payload invalid
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    logger.info(f"Webhook secret configured: {bool(settings.stripe_webhook_secret)}")

    if not settings.stripe_webhook_secret:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    try:
        # Verify webhook signature
        if len(settings.stripe_webhook_secret) < 20 or not sig_header:
            logger.warning("Using webhook without signature verification (local testing)")
            event = json.loads(payload.decode('utf-8'))
        else:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except Exception as e:
        if 'signature' in str(e).lower():
            logger.error(f"Invalid signature: {e}")
            raise HTTPException(status_code=400, detail="Invalid signature")
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    event_type = event["type"]
    event_data = event["data"]["object"]

    logger.info(f"Received Stripe event: {event_type}")

    # Route events to appropriate handlers
    if event_type == "checkout.session.completed":
        await handle_payment_success(event_data)
    elif event_type == "checkout.session.expired":
        await handle_payment_expired(event_data)
    elif event_type == "payment_intent.payment_failed":
        await handle_payment_failed(event_data)
    else:
        logger.info(f"Unhandled event type: {event_type}")

    return JSONResponse({"status": "success", "event_type": event_type})


async def handle_payment_success(session_data: Dict[str, Any]):
    """
    Handle successful payment completion.

    Updates payment status to 'completed' in DynamoDB.

    Args:
        session_data: Stripe checkout session data
    """
    session_id = session_data.get("id")
    client_reference_id = session_data.get("client_reference_id")
    payment_intent_id = session_data.get("payment_intent")

    logger.info(f"Payment successful for session: {session_id}")

    if not client_reference_id:
        logger.warning(f"No client_reference_id found for session {session_id}")
        return

    try:
        response = payments_table.get_item(Key={"payment_intent_id": client_reference_id})
        payment_record = response.get("Item")

        if not payment_record:
            logger.warning(f"Payment record not found for payment_intent_id: {client_reference_id}")
            return

        # Update payment status
        payment_record["payment_status"] = "completed"
        payment_record["stripe_payment_intent"] = payment_intent_id
        payment_record["stripe_session_id"] = session_id
        payment_record["updated_at"] = datetime.utcnow().isoformat()
        payment_record["webhook_processed_at"] = datetime.utcnow().isoformat()

        payments_table.put_item(Item=payment_record)

        logger.info(f"Updated payment status to completed for {client_reference_id}")

    except Exception as e:
        logger.error(f"Failed to update payment record: {e}")
        raise


async def handle_payment_expired(session_data: Dict[str, Any]):
    """
    Handle expired payment session.

    Updates payment status to 'expired' in DynamoDB.

    Args:
        session_data: Stripe checkout session data
    """
    session_id = session_data.get("id")
    client_reference_id = session_data.get("client_reference_id")

    logger.info(f"Payment session expired: {session_id}")

    if not client_reference_id:
        logger.warning(f"No client_reference_id found for expired session {session_id}")
        return

    try:
        response = payments_table.get_item(Key={"payment_intent_id": client_reference_id})
        payment_record = response.get("Item")

        if not payment_record:
            logger.warning(f"Payment record not found for payment_intent_id: {client_reference_id}")
            return

        # Update payment status
        payment_record["payment_status"] = "expired"
        payment_record["updated_at"] = datetime.utcnow().isoformat()
        payment_record["webhook_processed_at"] = datetime.utcnow().isoformat()

        payments_table.put_item(Item=payment_record)

        logger.info(f"Updated payment status to expired for {client_reference_id}")

    except Exception as e:
        logger.error(f"Failed to update expired payment record: {e}")
        raise


async def handle_payment_failed(payment_intent_data: Dict[str, Any]):
    """
    Handle failed payment attempt.

    Updates payment status to 'failed' in DynamoDB.

    Args:
        payment_intent_data: Stripe payment intent data
    """
    payment_intent_id = payment_intent_data.get("id")

    logger.info(f"Payment failed for intent: {payment_intent_id}")

    try:
        # Find payment record by stripe_payment_intent
        response = payments_table.scan(
            FilterExpression="stripe_payment_intent = :intent_id",
            ExpressionAttributeValues={":intent_id": payment_intent_id}
        )

        items = response.get("Items", [])
        if not items:
            logger.warning(f"Payment record not found for intent: {payment_intent_id}")
            return

        payment_record = items[0]

        # Update payment status
        payment_record["payment_status"] = "failed"
        payment_record["updated_at"] = datetime.utcnow().isoformat()
        payment_record["webhook_processed_at"] = datetime.utcnow().isoformat()

        payments_table.put_item(Item=payment_record)

        logger.info(f"Updated payment status to failed for {payment_record['payment_intent_id']}")

    except Exception as e:
        logger.error(f"Failed to update failed payment record: {e}")
        raise


# TODO: Add support for refunds
# TODO: Add support for disputed payments
# TODO: Add retry logic for DynamoDB failures
# TODO: Add metrics/monitoring
