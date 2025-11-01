"""
FastMCP Server for Conversational Insurance Ultra

Main MCP server entry point that exposes all 12 tools for Claude/ChatGPT integration.

Features:
- 12 MCP tools across 5 functional blocks
- Backend API integration
- Session management via Mem0
- Streaming responses for long operations

Run with:
    python -m mcp-server.server

Or configure in Claude Desktop / ChatGPT:
    {
      "mcpServers": {
        "insurance-ultra": {
          "command": "python",
          "args": ["-m", "mcp-server.server"]
        }
      }
    }
"""

import logging
import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Any, Dict, List
from fastmcp import FastMCP
from libs.ocr.fast_ocr import fast_text_extract

from mcp_server.client.backend_client import BackendClient
from mcp_server.utils import normalize_country_code

# TODO: Import remaining tools when implemented
# from mcp_server.tools import (
#     compare_policies,
#     explain_coverage,
#     answer_question,
#     search_policies,
#     upload_document,
#     extract_travel_data,
#     generate_quotation,
#     get_recommendations,
#     analyze_destination_risk,
#     manage_conversation_memory,
# )

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize backend client
backend_client = BackendClient()


# Application lifecycle management
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict]:
    """
    Application lifecycle management for FastMCP server.

    Handles:
    - Backend client initialization and connectivity verification
    - Resource cleanup on shutdown
    """
    logger.info("Starting Insurance Ultra MCP Server v0.1.0")

    # Startup: Verify backend connectivity
    try:
        response = await backend_client.client.get("/health")
        health_data = response.json()
        logger.info(f"Backend health check: {health_data}")
    except Exception as e:
        logger.error(f"Backend connection failed: {e}")
        logger.warning("Server starting without backend connectivity")

    try:
        yield {}  # Server runs here
    finally:
        # Shutdown: Clean up resources
        logger.info("Shutting down Insurance Ultra MCP Server")
        await backend_client.close()
        logger.info("Backend client closed successfully")


# Initialize FastMCP server with lifespan
mcp = FastMCP(
    name="insurance-ultra-mcp",
    instructions="AI-powered conversational insurance platform MCP server",
    version="0.1.0",
    lifespan=app_lifespan
)


# =============================================================================
# BLOCK 1: Policy Intelligence Engine
# =============================================================================

@mcp.tool()
async def compare_policies(policy_ids: List[str], comparison_criteria: List[str]) -> Dict[str, Any]:
    """
    Compare multiple insurance policies across specified criteria.

    Args:
        policy_ids: List of policy IDs to compare
        comparison_criteria: Criteria to compare (e.g., ["medical_coverage", "baggage_loss", "price"])

    Returns:
        Comparison matrix with recommendations

    TODO: Implement policy comparison logic
    TODO: Call backend API /api/v1/policies/compare
    TODO: Format results for conversational display
    """
    logger.info(f"Comparing policies: {policy_ids}")
    return {
        "error": "Not implemented",
        "message": "Policy comparison tool is under development"
    }


@mcp.tool()
async def explain_coverage(
    policy_id: str,
    coverage_question: str,
    use_original_text: bool = False
) -> Dict[str, Any]:
    """
    Explain specific coverage details from a policy.

    Args:
        policy_id: Policy identifier
        coverage_question: Natural language question about coverage
        use_original_text: If True, use original policy text; if False, use normalized data

    Returns:
        Detailed explanation with sources

    TODO: Implement coverage explanation
    TODO: Route to normalized vs original text based on flag
    TODO: Include policy document references
    """
    logger.info(f"Explaining coverage for policy {policy_id}: {coverage_question}")
    return {"error": "Not implemented"}


@mcp.tool()
async def search_policies(
    query: str,
    filters: Dict[str, Any] | None = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Search for policies using natural language query.

    Args:
        query: Search query (e.g., "policies with high medical coverage")
        filters: Optional filters (product_type, price_range, etc.)
        limit: Maximum results

    Returns:
        List of matching policies with relevance scores

    TODO: Implement semantic search
    TODO: Use vector store for similarity search
    TODO: Combine with metadata filtering
    """
    logger.info(f"Searching policies: {query}")
    return []


# =============================================================================
# BLOCK 2: Conversational FAQ & Recommendations
# =============================================================================

@mcp.tool()
async def answer_question(
    customer_id: str,
    question: str,
    session_id: str | None = None,
    policy_context: List[str] | None = None
) -> Dict[str, Any]:
    """
    Answer insurance-related questions using FAQ database and policy knowledge.

    Args:
        customer_id: Customer identifier
        question: Customer's question
        session_id: Optional session ID for context
        policy_context: Optional policy IDs for context

    Returns:
        Answer with sources and confidence score

    TODO: Implement Q&A engine
    TODO: Search FAQ embeddings
    TODO: Use conversation memory from Mem0
    TODO: Provide source citations
    """
    logger.info(f"Answering question for customer {customer_id}: {question}")
    return {"error": "Not implemented"}


# =============================================================================
# BLOCK 3: Document Intelligence & Auto-Quotation
# =============================================================================


@mcp.tool()
async def upload_document(
    file_path: str,
    customer_id: str | None = None,
    document_type: str | None = None,
    lang: str = "auto",
    enable_text_cleanup: bool = True,
    use_angle_cls: bool = True
) -> Dict[str, Any]:
    """
    Upload and parse travel document for data extraction using Fast OCR.
    
    This tool handles both document upload (optional) and OCR text extraction.
    If customer_id and document_type are provided, the document will be saved to storage.
    OCR extraction is always performed to extract text content.
    
    Args:
        file_path: Path to the document file to upload and parse
        customer_id: Optional customer ID for saving document to storage
        document_type: Optional document type (flight_booking, hotel_booking, itinerary, other)
        lang: Language for OCR (default: "auto" for auto-detection)
        enable_text_cleanup: Whether to clean up extracted text (default: True)
        use_angle_cls: Whether to use angle classification for rotated images (default: True)
    
    Returns:
        Dictionary with:
        - document_id: Document ID if saved to storage (optional)
        - text: Extracted text content from OCR
        - file_info: File metadata (name, type, pages, size, etc.)
        - metadata: Additional OCR metadata
        - storage_url: URL if document was saved to storage (optional)
    
    Examples:
        # Simple OCR without saving
        upload_document(file_path="path/to/document.pdf")
        
        # Upload and OCR with customer tracking
        upload_document(
            file_path="itinerary.pdf",
            customer_id="user_123",
            document_type="itinerary"
        )
    """
    logger.info(f"Uploading and parsing document: {file_path}")
    
    if not file_path:
        error_message = "file_path is required"
        logger.error(error_message)
        return {"error": error_message}

    # Step 1: Extract text using Fast OCR
    try:
        result = fast_text_extract(
            file=file_path,
            lang=lang,
            enable_text_cleanup=enable_text_cleanup,
            use_angle_cls=use_angle_cls
        )
        
        metadata = result.get('metadata', {}) or {}
        
        logger.info(f"Successfully extracted {result.get('page_count', 0)} pages from {file_path}")
        
        response = {
            "text": result.get('text', ''),
            "file_info": {
                "name": result.get('file_name'),
                "type": result.get('file_type'),
                "language": result.get('language'),
                "pages": result.get('page_count'),
                "size_mb": result.get('file_size_mb'),
                "confidence": result.get('confidence'),
            },
            "metadata": metadata,
        }
        
        # Step 2: Optionally save to storage if customer_id provided
        if customer_id and document_type:
            try:
                # TODO: Implement file upload to Supabase storage
                # For now, just log that we would save it
                logger.info(
                    f"Document would be saved for customer {customer_id}, "
                    f"type: {document_type}"
                )
                # When implemented, add:
                # document_id = await backend_client.upload_document(...)
                # response["document_id"] = document_id
                # response["storage_url"] = storage_url
                
            except Exception as storage_error:
                logger.warning(f"Failed to save document to storage: {storage_error}")
                # Continue even if storage fails - OCR extraction is still successful
        
        return response
        
    except Exception as exc:
        error_message = f"OCR extraction failed: {exc}"
        logger.exception(error_message)
        return {"error": error_message}


@mcp.tool()
async def extract_travel_data(document_ids: List[str]) -> Dict[str, Any]:
    """
    Extract and consolidate travel data from uploaded documents.

    Args:
        document_ids: List of document IDs to process

    Returns:
        Extracted travel plan with validation results

    TODO: Implement OCR + data extraction
    TODO: Cross-validate data across documents
    TODO: Return consolidated travel plan
    """
    logger.info(f"Extracting travel data from documents: {document_ids}")
    return {"error": "Not implemented"}


@mcp.tool()
async def generate_quotation(
    customer_id: str,
    trip_type: str,  # "RT" or "ST"
    departure_date: str,  # YYYY-MM-DD
    return_date: str | None = None,  # YYYY-MM-DD (required for RT)
    departure_country: str = "SG",
    arrival_country: str = "CN",
    adults_count: int = 1,
    children_count: int = 0,
    market: str = "SG",
    language_code: str = "en",
    channel: str = "white-label"
) -> Dict[str, Any]:
    """
    Generate personalized insurance quotations via Ancileo API.

    Args:
        customer_id: Customer ID
        trip_type: "RT" (Round Trip) or "ST" (Single Trip)
        departure_date: Departure date in YYYY-MM-DD format
        return_date: Return date in YYYY-MM-DD format (required for RT, optional for ST)
        departure_country: Country name or ISO code (e.g., "Greece" or "GR", default: "SG")
        arrival_country: Country name or ISO code (e.g., "Japan" or "JP", default: "CN")
        adults_count: Number of adults (default: 1)
        children_count: Number of children (default: 0)
        market: Market code (default: "SG")
        language_code: Language preference (default: "en")
        channel: Distribution channel (default: "white-label")

    Returns:
        Dictionary with:
        - quotation_id: Quotation ID (this is the Ancileo quote ID directly)
        - offers: List of available offers with pricing
        - trip_summary: Travel details
        - created_at: Creation timestamp

    Error Handling:
        Returns error dict with user-friendly message if API call fails or country not supported
    """
    logger.info(f"Generating quotation for customer {customer_id}: {trip_type} {departure_date}")
    
    try:
        # Normalize country codes (handles both names and ISO codes)
        norm_departure = normalize_country_code(departure_country)
        norm_arrival = normalize_country_code(arrival_country)
        
        # Validate country codes
        if not norm_departure:
            return {
                "error": {
                    "error_code": "unsupported_departure_country",
                    "message": f"Unsupported departure country: {departure_country}",
                    "user_message": f"I don't recognize '{departure_country}' as a supported departure country. Please provide a valid country name or ISO code (e.g., 'Singapore', 'SG', 'Greece', 'GR')."
                }
            }
        
        if not norm_arrival:
            return {
                "error": {
                    "error_code": "unsupported_arrival_country",
                    "message": f"Unsupported arrival country: {arrival_country}",
                    "user_message": f"I don't recognize '{arrival_country}' as a supported destination country. Please provide a valid country name or ISO code (e.g., 'Japan', 'JP', 'Greece', 'GR')."
                }
            }
        
        logger.info(f"Normalized countries: {departure_country} → {norm_departure}, {arrival_country} → {norm_arrival}")
        
        # Call backend API to generate quotation with normalized codes
        result = await backend_client.generate_quotation(
            customer_id=customer_id,
            trip_type=trip_type,
            departure_date=departure_date,
            return_date=return_date,
            departure_country=norm_departure,
            arrival_country=norm_arrival,
            adults_count=adults_count,
            children_count=children_count,
            market=market,
            language_code=language_code,
            channel=channel
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error generating quotation: {e}", exc_info=True)
        error_message = str(e)
        
        # Check if it's an HTTP error with status code
        if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
            if e.response.status_code == 400:
                return {
                    "error": {
                        "error_code": "validation_error",
                        "message": error_message,
                        "user_message": f"I need more information to generate a quotation: {error_message}"
                    }
                }
            elif e.response.status_code == 404:
                return {
                    "error": {
                        "error_code": "not_found",
                        "message": error_message,
                        "user_message": "The requested resource was not found. Please try again."
                    }
                }
        
        return {
            "error": {
                "error_code": "quotation_generation_failed",
                "message": error_message,
                "user_message": "I encountered an issue generating the quotation. Please try again or contact support."
            }
        }


# =============================================================================
# BLOCK 4: Seamless Purchase Execution
# =============================================================================

@mcp.tool()
async def initiate_purchase(
    user_id: str,
    quote_id: str,
    selected_offer_id: str,
    amount: int,
    currency: str,
    product_name: str,
    customer_email: str | None = None,
    insureds: Dict[str, Any] | None = None,
    main_contact: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """
    Initiate purchase process for an insurance policy.

    This tool creates a payment session and returns a checkout URL for the customer
    to complete their purchase. Use this when a customer is ready to buy a policy.

    Args:
        user_id: User/customer identifier
        quote_id: Quote identifier for the policy being purchased
        selected_offer_id: Selected offer ID from quotation (Ancileo offer.id)
        amount: Amount in cents (e.g., 15000 for $150.00 or SGD 150.00)
        currency: Currency code (e.g., "SGD", "USD")
        product_name: Product description (e.g., "Premium Travel Insurance - 7 Days Asia")
        customer_email: Optional customer email for pre-filling checkout form
        insureds: Optional insured persons info (JSONB). If not provided, can be added later before purchase
        main_contact: Optional main contact info (JSONB). If not provided, can be added later before purchase

    Returns:
        Dictionary with:
        - payment_intent_id: Unique payment identifier for tracking
        - checkout_url: Stripe checkout URL to redirect the customer
        - session_id: Stripe session ID
        - amount: Payment amount in cents
        - currency: Payment currency
        - expires_at: Checkout session expiration time (24 hours from creation)

    Error Handling:
        If this returns an error, handle it conversationally:
        - "duplicate_payment": Quote already has a pending/completed payment
          → Offer to check existing payment status or create a new quote
        - "quote_not_found": Quote doesn't exist or expired
          → Offer to create a new quote
        - "service_unavailable": Payment system temporarily down
          → Offer to save quote for later using save_quote_for_later()

        Example error response:
        {
            "error": {
                "error_code": "duplicate_payment",
                "message": "This quote already has a pending payment",
                "suggested_action": "check_existing_payment",
                "user_message": "It looks like you've already started a payment...",
                "can_retry": false
            }
        }

    Example:
        >>> result = await initiate_purchase(
        ...     user_id="user_123",
        ...     quote_id="quote_456",
        ...     amount=15000,
        ...     currency="SGD",
        ...     product_name="Premium Travel Insurance - 7 Days Asia",
        ...     customer_email="customer@example.com"
        ... )
        >>> if "error" in result:
        ...     # Handle error conversationally using error.user_message
        ...     print(result["error"]["user_message"])
        ... else:
        ...     print(f"Redirect user to: {result['checkout_url']}")

    Note:
        - The checkout session expires after 24 hours
        - Payment status will be updated via webhook when customer completes payment
        - Use check_payment_status() to poll payment status if needed
        - Always check for "error" key in response before proceeding
    """
    logger.info(f"Initiating purchase for user {user_id}, quote {quote_id}, offer {selected_offer_id}")

    try:
        # Step 1: Initiate payment via backend API
        result = await backend_client.initiate_payment(
            user_id=user_id,
            quote_id=quote_id,
            amount=amount,
            currency=currency,
            product_name=product_name,
            customer_email=customer_email
        )

        payment_intent_id = result.get('payment_intent_id')
        logger.info(f"Purchase initiated: {payment_intent_id}")

        # Step 2: Create selection record via backend API
        try:
            selection_result = await backend_client.create_selection(
                user_id=user_id,
                quote_id=quote_id,
                selected_offer_id=selected_offer_id,
                payment_id=payment_intent_id,
                insureds=insureds,
                main_contact=main_contact,
                total_price=float(amount) / 100.0
            )
            logger.info(f"Created selection {selection_result.get('selection_id')} for payment {payment_intent_id}")
        except Exception as e:
            logger.warning(f"Failed to create selection record: {e}. Payment will still work but Ancileo purchase may fail.")
            # Don't fail the payment initiation if selection creation fails

        # Return widget-enabled response for OpenAI Apps SDK
        # Format amount as currency string (e.g., "150.00" from 15000 cents)
        formatted_amount = f"{amount / 100:.2f}"

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"✅ Payment initiated for {product_name}! Total: {currency} {formatted_amount}\n\nClick 'Pay via Stripe' in the card below to complete your purchase securely."
                }
            ],
            "_meta": {
                "openai/outputTemplate": f"{os.getenv('WIDGET_BASE_URL', 'http://localhost:8085/widgets')}/payment-widget.html"
            },
            "widgetState": {
                "payment_intent_id": result["payment_intent_id"],
                "checkout_url": result["checkout_url"],
                "product_name": product_name,
                "amount": formatted_amount,
                "currency": currency,
                "status": "pending"
            }
        }

    except Exception as e:
        logger.error(f"Error initiating purchase: {e}")
        error_message = str(e)

        # Return conversational error response
        return {
            "error": {
                "error_code": "payment_initiation_failed",
                "message": error_message,
                "user_message": f"I encountered an issue starting your payment: {error_message}. Would you like me to save this quote and send you a payment link to complete it later?",
                "suggested_action": "save_quote_for_later",
                "can_retry": True
            }
        }


@mcp.tool()
async def check_payment_status(payment_intent_id: str) -> Dict[str, Any]:
    """
    Check the current status of a payment.

    Use this tool to poll the payment status or verify if a customer has completed
    their payment. Payment status is automatically updated via webhooks, so you
    typically just need to check this endpoint.

    Args:
        payment_intent_id: Payment intent identifier returned from initiate_purchase

    Returns:
        Dictionary with:
        - payment_intent_id: Payment identifier
        - payment_status: Current status (pending/completed/failed/expired/cancelled)
        - stripe_session_id: Stripe session ID if available
        - amount: Payment amount in cents
        - currency: Payment currency
        - product_name: Product description
        - user_id: User identifier
        - quote_id: Quote identifier
        - created_at: Payment creation timestamp
        - updated_at: Last update timestamp
        - stripe_payment_intent: Stripe payment intent ID if completed
        - failure_reason: Failure reason if payment failed

    Conversational Handling by Status:
        - "completed": Great! Proceed to complete_purchase() to generate policy
        - "pending": Customer hasn't completed payment yet. Offer to:
          → Send payment link reminder
          → Check if they need help
        - "failed": Payment failed. Check failure_reason and offer:
          → Try different payment method
          → Save quote for later
          → Contact support if issue persists
        - "expired": Payment session expired (>24h). Offer to:
          → Create new payment session
          → Save quote for later
        - "cancelled": Payment was cancelled. Ask if they want to:
          → Start a new payment
          → Get a new quote

    Example:
        >>> status = await check_payment_status("pi_abc123...")
        >>> if status['payment_status'] == 'completed':
        ...     print("Payment successful! Let me generate your policy...")
        ...     policy = await complete_purchase(status['payment_intent_id'])
        ... elif status['payment_status'] == 'failed':
        ...     print(f"Payment failed: {status.get('failure_reason')}")
        ...     print("Would you like to try a different payment method?")
        ... elif status['payment_status'] == 'pending':
        ...     print("I see your payment is still pending. Would you like me to send you a reminder?")
    """
    logger.info(f"Checking payment status: {payment_intent_id}")

    try:
        result = await backend_client.get_payment_status(payment_intent_id)
        logger.info(f"Payment status: {result.get('payment_status')}")
        return result

    except Exception as e:
        logger.error(f"Error checking payment status: {e}")
        error_message = str(e)

        return {
            "error": {
                "error_code": "payment_not_found",
                "message": error_message,
                "user_message": f"I couldn't find that payment record. It may not exist or there was a technical issue. Would you like to start a new purchase?",
                "suggested_action": "create_new_payment",
                "can_retry": False
            }
        }


@mcp.tool()
async def complete_purchase(payment_intent_id: str) -> Dict[str, Any]:
    """
    Complete the purchase and generate policy after successful payment.

    This tool should be called after verifying that payment status is "completed".
    It generates the policy document and returns policy details.

    Args:
        payment_intent_id: Payment intent identifier

    Returns:
        Dictionary with:
        - policy_id: Generated policy identifier
        - policy_number: Human-readable policy number
        - status: Purchase completion status
        - payment_intent_id: Payment identifier
        - quote_id: Quote identifier
        - user_id: User identifier
        - amount: Payment amount
        - currency: Payment currency
        - product_name: Product name
        - policy_document_url: URL to download policy PDF (when implemented)
        - created_at: Policy creation timestamp

    Conversational Handling:
        ALWAYS check payment status first before calling this tool!

        Success flow:
        1. Check payment status
        2. If status == "completed", call this tool
        3. Congratulate customer and provide policy details

        Error scenarios:
        - Payment not completed: "Your payment hasn't been processed yet. Let me check the status..."
        - Payment failed: "Unfortunately your payment didn't go through. Would you like to try again?"
        - Payment not found: "I couldn't find that payment. Let me help you start a new purchase."

    Example:
        >>> # First check payment is completed
        >>> status = await check_payment_status("pi_abc123...")
        >>> if status['payment_status'] == 'completed':
        ...     policy = await complete_purchase("pi_abc123...")
        ...     print(f"Congratulations! Your policy {policy['policy_number']} is now active!")
        ...     print(f"Policy ID: {policy['policy_id']}")
        ... else:
        ...     print(f"Payment status is {status['payment_status']}. Cannot complete purchase yet.")

    Note:
        - Payment must be in "completed" status
        - Policy document generation is currently in development
        - Customer will receive confirmation email (when implemented)
    """
    logger.info(f"Completing purchase for payment: {payment_intent_id}")

    try:
        result = await backend_client.complete_purchase(payment_intent_id)
        logger.info(f"Purchase completed: {result.get('policy_id')}")
        return result

    except Exception as e:
        logger.error(f"Error completing purchase: {e}")
        error_message = str(e)

        # Check if it's a "payment not completed" error
        if "not completed" in error_message.lower():
            return {
                "error": {
                    "error_code": "payment_not_completed",
                    "message": error_message,
                    "user_message": "Your payment hasn't been completed yet. Let me check the current status for you.",
                    "suggested_action": "check_payment_status",
                    "can_retry": True
                }
            }
        else:
            return {
                "error": {
                    "error_code": "purchase_completion_failed",
                    "message": error_message,
                    "user_message": f"I encountered an issue completing your purchase: {error_message}. Please contact support for assistance.",
                    "suggested_action": "contact_support",
                    "can_retry": False
                }
            }


@mcp.tool()
async def cancel_payment(payment_intent_id: str, reason: str | None = None) -> Dict[str, Any]:
    """
    Cancel a pending payment.

    Use this when a customer wants to cancel their purchase before completing payment.
    Only pending payments can be cancelled. Completed payments must be refunded instead.

    Args:
        payment_intent_id: Payment intent identifier
        reason: Optional cancellation reason

    Returns:
        Dictionary with:
        - payment_intent_id: Payment identifier
        - status: Cancellation status
        - message: Confirmation message

    Example:
        >>> result = await cancel_payment("pi_abc123...", reason="Customer changed mind")
        >>> print(result['message'])

    Note:
        - Cannot cancel completed payments (use refund instead)
        - Cancellation is immediate and cannot be undone
    """
    logger.info(f"Cancelling payment: {payment_intent_id}")

    try:
        result = await backend_client.cancel_payment(payment_intent_id, reason)
        logger.info(f"Payment cancelled: {payment_intent_id}")
        return result

    except Exception as e:
        logger.error(f"Error cancelling payment: {e}")
        return {
            "error": str(e),
            "message": "Failed to cancel payment. It may already be completed."
        }


@mcp.tool()
async def save_quote_for_later(
    quote_id: str,
    user_id: str,
    customer_email: str,
    product_name: str,
    amount: int,
    currency: str,
    policy_id: str | None = None,
    notes: str | None = None
) -> Dict[str, Any]:
    """
    Save a quote and generate a payment link for later completion.

    Use this when:
    - A customer wants to think about it or compare options
    - Payment fails and the customer wants to complete it later
    - Customer needs to get approval before purchasing
    - Customer prefers to pay on a different device or at a different time

    This creates a payment link that's valid for 7 days. The customer can complete
    the payment anytime within that period without needing to get a new quote.

    Args:
        quote_id: Quote identifier (e.g., "quote_abc123")
        user_id: User/customer identifier
        customer_email: Customer's email address
        product_name: Product description (e.g., "Premium Travel Insurance - 7 Days Asia")
        amount: Amount in cents (e.g., 15000 for $150.00)
        currency: Currency code (e.g., "SGD", "USD")
        policy_id: Optional policy ID if already selected
        notes: Optional notes about the quote

    Returns:
        Dictionary with:
        - quote_id: Quote identifier
        - payment_link_id: Unique payment link identifier
        - payment_link_url: URL for customer to complete payment
        - expires_at: Link expiration timestamp (7 days from now)
        - message: Confirmation message for the customer

    Example conversation:
        Customer: "I'd like to think about it and pay later"
        AI: "No problem! Let me save this quote for you..."
        >>> result = await save_quote_for_later(
        ...     quote_id="quote_123",
        ...     user_id="user_456",
        ...     customer_email="customer@example.com",
        ...     product_name="Premium Travel Insurance",
        ...     amount=15000,
        ...     currency="SGD"
        ... )
        AI: "I've saved your quote! I'll send you a payment link to {email}.
             The link is valid for 7 days. You can complete your purchase anytime
             using this link: {payment_link_url}"

    Note:
        - Payment link expires after 7 days
        - Customer can use the link multiple times if payment fails
        - Quote is saved and can be retrieved using get_payment_link()
    """
    logger.info(f"Saving quote {quote_id} for user {user_id}")

    try:
        result = await backend_client.save_quote_for_later(
            quote_id=quote_id,
            user_id=user_id,
            customer_email=customer_email,
            product_name=product_name,
            amount=amount,
            currency=currency,
            policy_id=policy_id,
            notes=notes
        )

        logger.info(f"Quote saved: {quote_id}, link: {result.get('payment_link_id')}")
        return result

    except Exception as e:
        logger.error(f"Error saving quote: {e}")
        return {
            "error": str(e),
            "message": "Failed to save quote. Please try again or contact support."
        }


@mcp.tool()
async def send_payment_link(
    quote_id: str,
    customer_email: str,
    customer_name: str | None = None
) -> Dict[str, Any]:
    """
    Send a payment link to customer via email.

    Use this when:
    - Customer wants the payment link sent to their email
    - Following up on a saved quote
    - Customer requests a reminder about their pending quote
    - Resending a payment link after it was previously sent

    This sends an email with the payment link to the customer's email address.
    The link must already exist (created via save_quote_for_later).

    Args:
        quote_id: Quote identifier that has a saved payment link
        customer_email: Email address to send the link to
        customer_name: Optional customer name for personalized email

    Returns:
        Dictionary with:
        - success: Boolean indicating if email was sent
        - message: Confirmation message
        - quote_id: Quote identifier
        - email_sent_to: Email address where link was sent

    Example conversation:
        Customer: "Can you send me the payment link?"
        AI: "Of course! Let me send that to your email..."
        >>> result = await send_payment_link(
        ...     quote_id="quote_123",
        ...     customer_email="customer@example.com",
        ...     customer_name="John Doe"
        ... )
        AI: "I've sent the payment link to {email}. Please check your inbox
             (and spam folder just in case). The link is valid for 7 days."

    Note:
        - Quote must have been saved first using save_quote_for_later()
        - Email sending functionality is currently in development (placeholder)
        - Customer can request resend if they don't receive the email
    """
    logger.info(f"Sending payment link for quote {quote_id} to {customer_email}")

    try:
        result = await backend_client.send_payment_link(
            quote_id=quote_id,
            customer_email=customer_email,
            customer_name=customer_name
        )

        logger.info(f"Payment link sent for quote {quote_id}")
        return result

    except Exception as e:
        logger.error(f"Error sending payment link: {e}")
        return {
            "error": str(e),
            "message": "Failed to send payment link. Please try again."
        }


@mcp.tool()
async def get_payment_link(quote_id: str) -> Dict[str, Any]:
    """
    Get or generate a payment link for a quote.

    Use this when:
    - Customer asks for their payment link
    - You need to retrieve a previously created payment link
    - Customer lost their payment link and needs it again
    - Checking if a payment link exists for a quote

    This retrieves the payment link for a saved quote. If the quote doesn't have
    a payment link yet, it generates one.

    Args:
        quote_id: Quote identifier

    Returns:
        Dictionary with:
        - quote_id: Quote identifier
        - payment_link_id: Payment link identifier
        - payment_link_url: URL for customer to complete payment
        - expires_at: Link expiration timestamp
        - is_active: Boolean indicating if link is still valid

    Example conversation:
        Customer: "I lost the payment link you sent earlier"
        AI: "No worries! Let me retrieve that for you..."
        >>> result = await get_payment_link("quote_123")
        AI: "Here's your payment link: {payment_link_url}
             This link is valid until {expires_at}. Let me know if you have
             any questions about completing your purchase!"

    Note:
        - Returns existing link if one exists
        - Payment links are valid for 7 days from creation
        - Check is_active to verify link hasn't expired
    """
    logger.info(f"Retrieving payment link for quote {quote_id}")

    try:
        result = await backend_client.get_payment_link(quote_id)
        logger.info(f"Payment link retrieved for quote {quote_id}")
        return result

    except Exception as e:
        logger.error(f"Error retrieving payment link: {e}")
        return {
            "error": str(e),
            "message": "Failed to retrieve payment link. The quote may not exist."
        }


# =============================================================================
# BLOCK 5: Data-Driven Recommendations
# =============================================================================

@mcp.tool()
async def get_recommendations(
    customer_id: str,
    travel_plan: Dict[str, Any],
    current_quotation_id: str | None = None
) -> Dict[str, Any]:
    """
    Get data-driven recommendations based on claims analysis.

    Args:
        customer_id: Customer ID
        travel_plan: Travel details (destinations, dates, activities)
        current_quotation_id: Optional current quotation for comparison

    Returns:
        Recommendations with supporting claims data

    TODO: Implement recommendation engine
    TODO: Analyze historical claims data
    TODO: Identify risk factors
    TODO: Suggest coverage improvements
    """
    logger.info(f"Generating recommendations for customer {customer_id}")
    return {"error": "Not implemented"}


@mcp.tool()
async def analyze_destination_risk(destination: str) -> Dict[str, Any]:
    """
    Analyze risk levels for specific destination based on claims history.

    Args:
        destination: Destination name or country

    Returns:
        Risk analysis with statistics and recommendations

    TODO: Implement destination risk analysis
    TODO: Query Neo4j for claims patterns
    TODO: Calculate risk scores
    TODO: Provide actionable insights
    """
    logger.info(f"Analyzing destination risk: {destination}")
    return {"error": "Not implemented"}


# =============================================================================
# Memory Management Tool
# =============================================================================

@mcp.tool()
async def manage_conversation_memory(
    user_id: str,
    action: str,
    messages: list | None = None,
    query: str | None = None,
    memory_id: str | None = None,
    limit: int = 10,
    metadata: dict | None = None
) -> Dict[str, Any]:
    """
    Manage user conversation memory using Mem0.

    Simple memory management - LLM decides what to store and when to retrieve.
    This tool provides 4 basic operations: add, search, get_all, and delete.

    Args:
        user_id: User identifier (required)
        action: Memory operation - "add", "search", "get_all", or "delete"
        messages: For "add" - List of conversation messages with 'role' and 'content' keys
        query: For "search" - Search query for semantic memory search
        memory_id: For "delete" - Memory ID to delete
        limit: For "search" - Maximum number of memories to return (default: 10)
        metadata: For "add" - Optional metadata for categorization

    Returns:
        Operation result with memories or confirmation

    Examples:
        Store a conversation:
        >>> await manage_conversation_memory(
        ...     user_id="alice_123",
        ...     action="add",
        ...     messages=[
        ...         {"role": "user", "content": "I prefer high medical coverage"},
        ...         {"role": "assistant", "content": "I'll remember that preference"}
        ...     ],
        ...     metadata={"type": "preference"}
        ... )

        Search for relevant memories:
        >>> await manage_conversation_memory(
        ...     user_id="alice_123",
        ...     action="search",
        ...     query="insurance preferences",
        ...     limit=5
        ... )

        Get all memories:
        >>> await manage_conversation_memory(
        ...     user_id="alice_123",
        ...     action="get_all"
        ... )

        Delete a memory:
        >>> await manage_conversation_memory(
        ...     user_id="alice_123",
        ...     action="delete",
        ...     memory_id="892db2ae-06d9-49e5-8b3e-585ef9b85b8e"
        ... )

    Note:
        - LLM autonomously decides what conversations to store
        - Mem0 automatically extracts key information from messages
        - Semantic search uses AI to find relevant memories by meaning
        - All operations are specific to the user_id
    """
    logger.info(f"Managing memory for user {user_id}: action={action}")

    try:
        if action == "add":
            if not messages:
                return {
                    "error": "Missing required parameter",
                    "message": "'messages' parameter is required for 'add' action"
                }

            result = await backend_client.add_memory(
                user_id=user_id,
                messages=messages,
                metadata=metadata
            )
            logger.info(f"Added memories for user {user_id}")
            return result

        elif action == "search":
            if not query:
                return {
                    "error": "Missing required parameter",
                    "message": "'query' parameter is required for 'search' action"
                }

            results = await backend_client.search_memories(
                user_id=user_id,
                query=query,
                limit=limit
            )
            logger.info(f"Found {len(results)} memories for user {user_id}")
            return {
                "results": results,
                "total": len(results)
            }

        elif action == "get_all":
            results = await backend_client.get_all_memories(user_id=user_id)
            logger.info(f"Retrieved {len(results)} memories for user {user_id}")
            return {
                "results": results,
                "total": len(results)
            }

        elif action == "delete":
            if not memory_id:
                return {
                    "error": "Missing required parameter",
                    "message": "'memory_id' parameter is required for 'delete' action"
                }

            result = await backend_client.delete_memory(memory_id=memory_id)
            logger.info(f"Deleted memory {memory_id}")
            return result

        else:
            return {
                "error": "Invalid action",
                "message": f"Unknown action '{action}'. Valid actions: add, search, get_all, delete"
            }

    except Exception as e:
        logger.error(f"Memory operation failed for user {user_id}: {e}")
        return {
            "error": str(e),
            "message": f"Failed to {action} memory. Please try again."
        }


# =============================================================================
# Neo4j Concept Search Tool
# =============================================================================

@mcp.tool()
async def search_neo4j_concept(query: str, top_k: int = 15) -> str:
    """
    Search insurance concept knowledge graph for term definitions and contextual understanding.

    DATA SOURCE: Neo4j knowledge graph with insurance concepts, terminology, and relationships
    OUTPUT: Detailed concept definitions with contextual information and cross-references

    QUERY CLASSIFICATION - WHEN TO USE THIS TOOL:

    ✓ EXPLANATION QUERIES (PRIMARY) - "What exactly is covered under medical expenses?"
      → Use FIRST for conceptual understanding and terminology clarification
      → Provides foundational knowledge before diving into specific policy details

    ✓ SCENARIO ANALYSIS (PRIMARY) - "What happens if I break my leg skiing in Japan?"
      → Use FIRST to understand relevant concepts (medical coverage, adventure sports, geographical coverage)
      → Combine with get_structured_policy_data for complete scenario modeling

    ✗ COMPARISON QUERIES - "Which plan has better medical coverage?"
      → NOT recommended - use get_structured_policy_data instead

    ✗ ELIGIBILITY QUERIES - "Am I covered for pre-existing conditions?"
      → NOT recommended - use get_structured_policy_data + get_original_text_data instead

    PROCESSING: Semantic search via MemOS TreeTextMemory with OpenAI embeddings
    FILTERS: Excludes short concept nodes (<100 chars) for quality results

    Args:
        query: Conceptual question about insurance terms, coverage types, or scenarios
        top_k: Number of concept nodes to return (1-50, default: 15)

    Returns:
        Concatenated concept definitions and explanations from knowledge graph

    Examples:
        "What does 'pre-existing condition' mean in travel insurance?"
        "Explain adventure sports coverage and exclusions"
        "What are the types of trip cancellation reasons?"
    """
    logger.info(f"Searching Neo4j concepts: '{query}' (top_k={top_k})")

    try:
        # Call backend API
        result = await backend_client.search_neo4j_concept(
            query=query,
            top_k=top_k
        )

        logger.info(f"Found {result.get('count', 0)} concept results")

        # Return the formatted string directly
        return result.get('results', 'No results found.')

    except Exception as e:
        logger.error(f"Neo4j concept search failed: {e}")
        error_message = str(e)

        # Return user-friendly error message
        return f"Error searching concepts: {error_message}. Please try again or contact support if the issue persists."


# =============================================================================
# Structured Policy Data Search Tool
# =============================================================================

@mcp.tool()
async def get_structured_policy_data(query: str, top_k: int = 10) -> str:
    """
    Search normalized taxonomic policy data with AI-powered intelligent routing across 3 layers.

    DATA SOURCE: Normalized taxonomy in Supabase (general_conditions, benefits, benefit_conditions)
    PROCESSING: gpt-4o-mini routes query → Vector search with OpenAI embeddings → Structured JSON
    OUTPUT: Side-by-side feature matrices with quantified parameters, coverage limits, and conditions

    QUERY CLASSIFICATION - WHEN TO USE THIS TOOL:

    ✓ COMPARISON QUERIES (PRIMARY) - "Which plan has better medical coverage?"
      → Use FIRST for structured analysis and side-by-side comparisons
      → Enables quantified differentiation (e.g., $500k vs $1M coverage)
      → Fallback: get_original_text_data if structured data insufficient

    ✓ EXPLANATION QUERIES (SECONDARY) - "What exactly is covered under medical expenses?"
      → Use AFTER search_neo4j_concept for specific policy details
      → Provides normalized, comparable policy parameters

    ✓ ELIGIBILITY QUERIES (PRIMARY) - "Am I covered for pre-existing conditions?"
      → Use TOGETHER WITH get_original_text_data for comprehensive assessment
      → Provides normalized rules AND original conditions

    ✓ SCENARIO ANALYSIS (SECONDARY) - "What happens if I break my leg skiing in Japan?"
      → Use WITH search_neo4j_concept for complete scenario modeling
      → Provides specific benefit conditions and exclusions across multiple coverages

    3-LAYER TAXONOMY:
    • Layer 1 (general_conditions): Age limits, trip requirements, universal exclusions
    • Layer 2 (benefits): Coverage types, limits, sub-limits across all products
    • Layer 3 (benefit_conditions): Claim requirements, thresholds, documentation needs

    Args:
        query: Specific policy question requiring structured, comparable data
        top_k: Results per table (1-50, default: 10)

    Returns:
        JSON with success, tables_searched, total_results, data array (includes similarity scores)

    Examples:
        "Compare trip cancellation coverage limits across all policies"
        "What are the age restrictions for each product?"
        "Which benefits require 6+ hours delay to claim?"
    """
    logger.info(f"Searching structured policy data: '{query}' (top_k={top_k})")

    try:
        # Call backend API
        result = await backend_client.search_structured_policy(
            query=query,
            top_k=top_k
        )

        logger.info(f"Found {result.get('total_results', 0)} structured policy results")

        # Format as JSON string for Claude/ChatGPT
        import json
        return json.dumps(result, indent=2, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Structured policy search failed: {e}")
        error_message = str(e)

        # Return user-friendly error in JSON format
        error_response = {
            "success": False,
            "error": error_message,
            "message": "Failed to search policy data. The routing service may have failed after multiple attempts, or the database may be unavailable. Please rephrase your question or try again."
        }
        return json.dumps(error_response, indent=2)


# =============================================================================
# Original Policy Text Search Tool
# =============================================================================

@mcp.tool()
async def get_original_text_data(query: str, top_k: int = 10) -> str:
    """
    Search chunked original policy documents for exact wording and legal language references.

    DATA SOURCE: Original policy text chunks (16+ languages) with embeddings in Supabase
    PROCESSING: Vector similarity search with OpenAI embeddings maintaining legal precision
    OUTPUT: Exact policy language passages with "---" separators, preserving original formatting

    QUERY CLASSIFICATION - WHEN TO USE THIS TOOL:

    ✓ COMPARISON QUERIES (FALLBACK) - "Which plan has better medical coverage?"
      → Use ONLY IF get_structured_policy_data returns insufficient data
      → Provides original wording when normalized data is unclear

    ✓ EXPLANATION QUERIES (TERTIARY) - "What exactly is covered under medical expenses?"
      → Use LAST after search_neo4j_concept → get_structured_policy_data
      → Provides exact legal wording and detailed policy language references

    ✓ ELIGIBILITY QUERIES (PRIMARY) - "Am I covered for pre-existing conditions?"
      → Use TOGETHER WITH get_structured_policy_data for comprehensive assessment
      → Provides original conditions text for legal precision and qualifying clauses

    ✗ SCENARIO ANALYSIS - "What happens if I break my leg skiing in Japan?"
      → NOT recommended - use search_neo4j_concept + get_structured_policy_data instead
      → Original text lacks the structured cross-benefit analysis needed for scenarios

    CHARACTERISTICS:
    • Chunk size: 500-2000 characters per passage
    • Multilingual: Preserves original policy language (English, Chinese, Malay, etc.)
    • Unstructured: Raw policy text, not normalized for comparison
    • Legal precision: Exact terms and conditions as written in source documents

    Args:
        query: Question requiring exact policy wording or legal language
        top_k: Number of text chunks (1-50, default: 10)

    Returns:
        Concatenated passages with "---" separators, ranked by semantic similarity

    Examples:
        "What is the exact definition of pre-existing condition in the policy?"
        "Show me the original exclusion text for dangerous activities"
        "What does the policy document say about trip cancellation refunds?"
    """
    logger.info(f"Searching original policy text: '{query}' (top_k={top_k})")

    try:
        # Import here to avoid circular dependencies
        from backend.database.postgres_client import get_supabase

        # Get Supabase client and search
        supabase_client = await get_supabase()
        text_chunks = await supabase_client.search_original_text(query, top_k)

        if not text_chunks:
            logger.info("No original text results found")
            return "No matching text found for your query. Try rephrasing or using different keywords."

        logger.info(f"Found {len(text_chunks)} original text chunks")

        # Concatenate text chunks with separators for readability
        formatted_text = "\n\n---\n\n".join(text_chunks)

        # Add header with context
        result = f"Found {len(text_chunks)} relevant policy text passage(s):\n\n{formatted_text}"

        return result

    except RuntimeError as e:
        # Search-specific error
        logger.error(f"Original text search failed: {e}")
        error_message = str(e)
        return f"Error: Failed to search original policy text. {error_message}\n\nThis may be due to:\n- Database connection issue\n- Missing embeddings in the database\n- Invalid query format\n\nPlease try again or contact support."

    except ConnectionError as e:
        # Database connection error
        logger.error(f"Database connection failed: {e}")
        return f"Error: Could not connect to the policy database. Please try again later.\n\nDetails: {str(e)}"

    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error in original text search: {e}", exc_info=True)
        error_message = str(e)
        return f"Error: An unexpected error occurred while searching policy text.\n\nDetails: {error_message}\n\nPlease try rephrasing your query or contact support if the issue persists."


# =============================================================================
# Server Entry Point
# =============================================================================

if __name__ == "__main__":
    # Run the MCP server with STDIO transport
    mcp.run(transport="stdio")