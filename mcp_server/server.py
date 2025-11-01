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
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Any, Dict, List
from fastmcp import FastMCP

from mcp_server.client.backend_client import BackendClient

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
    customer_id: str,
    document_type: str,
    file_path: str
) -> Dict[str, Any]:
    """
    Upload travel document for data extraction.

    Args:
        customer_id: Customer ID
        document_type: Type of document (flight_booking, hotel_booking, itinerary)
        file_path: Path to document file

    Returns:
        Document ID and upload status

    TODO: Implement file upload to Supabase storage
    TODO: Trigger OCR processing
    TODO: Return document metadata
    """
    logger.info(f"Uploading document for customer {customer_id}: {document_type}")
    return {"error": "Not implemented"}


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
    travel_plan_id: str | None = None,
    manual_travel_data: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """
    Generate personalized insurance quotations.

    Args:
        customer_id: Customer ID
        travel_plan_id: ID of extracted travel plan (from documents)
        manual_travel_data: Manual travel data if not using extracted plan

    Returns:
        List of quotations with recommendations

    TODO: Implement quotation generation
    TODO: Calculate premiums based on travel data
    TODO: Apply data-driven recommendations
    TODO: Return multiple policy options
    """
    logger.info(f"Generating quotation for customer {customer_id}")
    return {"error": "Not implemented"}


# =============================================================================
# BLOCK 4: Seamless Purchase Execution
# =============================================================================

@mcp.tool()
async def initiate_purchase(
    user_id: str,
    quote_id: str,
    amount: int,
    currency: str,
    product_name: str,
    customer_email: str | None = None
) -> Dict[str, Any]:
    """
    Initiate purchase process for an insurance policy.

    This tool creates a payment session and returns a checkout URL for the customer
    to complete their purchase. Use this when a customer is ready to buy a policy.

    Args:
        user_id: User/customer identifier
        quote_id: Quote identifier for the policy being purchased
        amount: Amount in cents (e.g., 15000 for $150.00 or SGD 150.00)
        currency: Currency code (e.g., "SGD", "USD")
        product_name: Product description (e.g., "Premium Travel Insurance - 7 Days Asia")
        customer_email: Optional customer email for pre-filling checkout form

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
    logger.info(f"Initiating purchase for user {user_id}, quote {quote_id}")

    try:
        result = await backend_client.initiate_payment(
            user_id=user_id,
            quote_id=quote_id,
            amount=amount,
            currency=currency,
            product_name=product_name,
            customer_email=customer_email
        )

        logger.info(f"Purchase initiated: {result.get('payment_intent_id')}")
        return result

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
# Server Entry Point
# =============================================================================

if __name__ == "__main__":
    # Run the MCP server with STDIO transport
    mcp.run(transport="stdio")
