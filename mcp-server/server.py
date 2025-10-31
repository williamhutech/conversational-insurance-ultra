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

# Initialize FastMCP server
mcp = FastMCP(
    name="insurance-ultra-mcp",
    version="0.1.0",
    description="AI-powered conversational insurance platform MCP server"
)

# Initialize backend client
backend_client = BackendClient()


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

    Example:
        >>> result = await initiate_purchase(
        ...     user_id="user_123",
        ...     quote_id="quote_456",
        ...     amount=15000,
        ...     currency="SGD",
        ...     product_name="Premium Travel Insurance - 7 Days Asia",
        ...     customer_email="customer@example.com"
        ... )
        >>> print(f"Redirect user to: {result['checkout_url']}")

    Note:
        - The checkout session expires after 24 hours
        - Payment status will be updated via webhook when customer completes payment
        - Use check_payment_status() to poll payment status if needed
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
        return {
            "error": str(e),
            "message": "Failed to initiate purchase. Please try again or contact support."
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

    Example:
        >>> status = await check_payment_status("pi_abc123...")
        >>> if status['payment_status'] == 'completed':
        ...     print("Payment successful! Generating policy...")
        ... elif status['payment_status'] == 'pending':
        ...     print("Waiting for customer to complete payment...")
    """
    logger.info(f"Checking payment status: {payment_intent_id}")

    try:
        result = await backend_client.get_payment_status(payment_intent_id)
        logger.info(f"Payment status: {result.get('payment_status')}")
        return result

    except Exception as e:
        logger.error(f"Error checking payment status: {e}")
        return {
            "error": str(e),
            "message": "Failed to retrieve payment status. Please try again."
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

    Example:
        >>> # First check payment is completed
        >>> status = await check_payment_status("pi_abc123...")
        >>> if status['payment_status'] == 'completed':
        ...     policy = await complete_purchase("pi_abc123...")
        ...     print(f"Policy generated: {policy['policy_number']}")

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
        return {
            "error": str(e),
            "message": "Failed to complete purchase. Payment may not be completed yet."
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
    customer_id: str,
    action: str,
    data: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """
    Manage customer conversation memory.

    Args:
        customer_id: Customer ID
        action: Action to perform (add_memory, get_memories, search_memories)
        data: Action-specific data

    Returns:
        Memory operation result

    TODO: Implement Mem0 integration
    TODO: Support different memory operations
    TODO: Maintain conversation context
    """
    logger.info(f"Managing memory for customer {customer_id}: {action}")
    return {"error": "Not implemented"}


# =============================================================================
# Server Lifecycle
# =============================================================================

@mcp.startup()
async def startup():
    """Initialize MCP server and connections."""
    logger.info("Starting Insurance Ultra MCP Server")
    # TODO: Initialize backend API client
    # TODO: Verify backend connectivity
    # TODO: Load configuration


@mcp.shutdown()
async def shutdown():
    """Clean up resources on shutdown."""
    logger.info("Shutting down Insurance Ultra MCP Server")
    # TODO: Close connections
    # TODO: Save session state


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
