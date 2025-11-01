"""
Backend API Client for MCP Server

HTTP client for communicating with the FastAPI backend from MCP tools.
Handles API requests, authentication, and error handling.

Usage:
    from mcp_server.client.backend_client import BackendClient

    client = BackendClient()
    policies = await client.get_policies()
"""

import httpx
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class BackendClient:
    """
    HTTP client for backend API communication.

    Handles all MCP → Backend API calls with:
    - Automatic retries
    - Error handling
    - Response validation
    """

    def __init__(self, base_url: str | None = None):
        """
        Initialize backend client.

        Args:
            base_url: Backend API base URL (default: from environment or http://localhost:8000)

        TODO: Add authentication token handling
        """
        import os

        # Get backend URL from environment or use default
        if base_url is None:
            backend_host = os.getenv("BACKEND_HOST", "localhost")
            backend_port = os.getenv("BACKEND_PORT", "8000")
            base_url = f"http://{backend_host}:{backend_port}"
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            headers={"Content-Type": "application/json"}
        )

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    # -------------------------------------------------------------------------
    # Block 1: Policy Intelligence
    # -------------------------------------------------------------------------

    async def compare_policies(
        self,
        policy_ids: List[str],
        criteria: List[str]
    ) -> Dict[str, Any]:
        """
        Compare policies via backend API.

        TODO: Implement POST /api/v1/policies/compare
        """
        pass

    async def get_policy(self, policy_id: str) -> Dict[str, Any]:
        """
        Get single policy details.

        TODO: Implement GET /api/v1/policies/{policy_id}
        """
        pass

    async def search_policies(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search policies.

        TODO: Implement POST /api/v1/policies/search
        """
        pass

    # -------------------------------------------------------------------------
    # Block 3: Document Processing
    # -------------------------------------------------------------------------

    async def upload_document(
        self,
        customer_id: str,
        document_type: str,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """
        Upload document to backend.

        TODO: Implement POST /api/v1/documents/upload
        TODO: Handle multipart/form-data
        """
        pass

    async def extract_travel_data(
        self,
        document_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Extract travel data from documents.

        TODO: Implement POST /api/v1/documents/extract
        """
        pass

    async def generate_quotation(
        self,
        customer_id: str,
        trip_type: str,
        departure_date: str,
        return_date: Optional[str] = None,
        departure_country: str = "SG",
        arrival_country: str = "CN",
        adults_count: int = 1,
        children_count: int = 0,
        market: str = "SG",
        language_code: str = "en",
        channel: str = "white-label"
    ) -> Dict[str, Any]:
        """
        Generate quotation via backend API.

        Args:
            customer_id: Customer ID
            trip_type: "RT" or "ST"
            departure_date: Departure date (YYYY-MM-DD)
            return_date: Return date (YYYY-MM-DD, optional for ST)
            departure_country: Departure country ISO code
            arrival_country: Arrival country ISO code
            adults_count: Number of adults
            children_count: Number of children
            market: Market code
            language_code: Language code
            channel: Distribution channel

        Returns:
            Quotation response with offers

        Raises:
            httpx.HTTPError: If request fails
        """
        try:
            response = await self.client.post(
                "/api/quotation/generate",
                json={
                    "customer_id": customer_id,
                    "trip_type": trip_type,
                    "departure_date": departure_date,
                    "return_date": return_date,
                    "departure_country": departure_country,
                    "arrival_country": arrival_country,
                    "adults_count": adults_count,
                    "children_count": children_count,
                    "market": market,
                    "language_code": language_code,
                    "channel": channel
                }
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"HTTP Error generating quotation: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            raise

    async def create_selection(
        self,
        user_id: str,
        quote_id: str,
        selected_offer_id: str,
        payment_id: Optional[str] = None,
        insureds: Optional[list[Dict[str, Any]]] = None,
        main_contact: Optional[Dict[str, Any]] = None,
        total_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Create selection record via backend API.

        Args:
            user_id: User ID
            quote_id: Quote ID
            selected_offer_id: Selected offer ID from quotation
            payment_id: Payment intent ID (if payment initiated)
            insureds: Optional list of insured persons
            main_contact: Optional main contact info
            total_price: Total price

        Returns:
            Selection response

        Raises:
            httpx.HTTPError: If request fails
        """
        try:
            response = await self.client.post(
                "/api/quotation/selection/create",
                json={
                    "user_id": user_id,
                    "quote_id": quote_id,
                    "selected_offer_id": selected_offer_id,
                    "payment_id": payment_id,
                    "insureds": insureds,
                    "main_contact": main_contact,
                    "total_price": total_price
                }
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"HTTP Error creating selection: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            raise

    # -------------------------------------------------------------------------
    # Block 4: Purchase & Payment
    # -------------------------------------------------------------------------

    async def initiate_payment(
        self,
        user_id: str,
        quote_id: str,
        amount: int,
        currency: str,
        product_name: str,
        customer_email: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Initiate payment for a quote.

        Args:
            user_id: User identifier
            quote_id: Quote identifier
            amount: Amount in cents
            currency: Currency code (e.g., "SGD")
            product_name: Product description
            customer_email: Optional customer email
            metadata: Optional metadata

        Returns:
            Payment initiation response with checkout URL

        Raises:
            httpx.HTTPError: If request fails
        """
        try:
            response = await self.client.post(
                "/api/purchase/initiate",
                json={
                    "user_id": user_id,
                    "quote_id": quote_id,
                    "amount": amount,
                    "currency": currency,
                    "product_name": product_name,
                    "customer_email": customer_email,
                    "metadata": metadata or {}
                }
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"HTTP Error initiating payment: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            else:
                logger.error(f"No response object available - likely connection error")
            raise

    async def get_payment_status(self, payment_intent_id: str) -> Dict[str, Any]:
        """
        Get payment status.

        Args:
            payment_intent_id: Payment intent identifier

        Returns:
            Payment status details

        Raises:
            httpx.HTTPError: If request fails
        """
        try:
            response = await self.client.get(
                f"/api/purchase/payment/{payment_intent_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error getting payment status: {e}")
            raise

    async def complete_purchase(self, payment_intent_id: str) -> Dict[str, Any]:
        """
        Complete purchase after successful payment.

        Args:
            payment_intent_id: Payment intent identifier

        Returns:
            Policy details and confirmation

        Raises:
            httpx.HTTPError: If request fails
        """
        try:
            response = await self.client.post(
                f"/api/purchase/complete/{payment_intent_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error completing purchase: {e}")
            raise

    async def cancel_payment(
        self,
        payment_intent_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel a pending payment.

        Args:
            payment_intent_id: Payment intent identifier
            reason: Optional cancellation reason

        Returns:
            Cancellation confirmation

        Raises:
            httpx.HTTPError: If request fails
        """
        try:
            response = await self.client.post(
                f"/api/purchase/cancel/{payment_intent_id}",
                params={"reason": reason} if reason else None
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error cancelling payment: {e}")
            raise

    async def get_user_payments(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get payment history for a user.

        Args:
            user_id: User identifier
            limit: Maximum results

        Returns:
            List of payment records

        Raises:
            httpx.HTTPError: If request fails
        """
        try:
            response = await self.client.get(
                f"/api/purchase/user/{user_id}/payments",
                params={"limit": limit}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error getting user payments: {e}")
            raise

    async def get_quote_payment(self, quote_id: str) -> Optional[Dict[str, Any]]:
        """
        Get payment for a specific quote.

        Args:
            quote_id: Quote identifier

        Returns:
            Payment record if exists, None otherwise

        Raises:
            httpx.HTTPError: If request fails
        """
        try:
            response = await self.client.get(
                f"/api/purchase/quote/{quote_id}/payment"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error getting quote payment: {e}")
            raise

    async def save_quote_for_later(
        self,
        quote_id: str,
        user_id: str,
        customer_email: str,
        product_name: str,
        amount: int,
        currency: str,
        policy_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save quote and generate payment link for later.

        Args:
            quote_id: Quote identifier
            user_id: User identifier
            customer_email: Customer email
            product_name: Product name
            amount: Amount in cents
            currency: Currency code
            policy_id: Optional policy ID
            notes: Optional notes

        Returns:
            Payment link details

        Raises:
            httpx.HTTPError: If request fails
        """
        try:
            response = await self.client.post(
                "/api/purchase/save-quote",
                json={
                    "quote_id": quote_id,
                    "user_id": user_id,
                    "customer_email": customer_email,
                    "product_name": product_name,
                    "amount": amount,
                    "currency": currency,
                    "policy_id": policy_id,
                    "notes": notes
                }
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error saving quote: {e}")
            raise

    async def send_payment_link(
        self,
        quote_id: str,
        customer_email: str,
        customer_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send payment link via email.

        Args:
            quote_id: Quote identifier
            customer_email: Customer email
            customer_name: Optional customer name

        Returns:
            Send confirmation

        Raises:
            httpx.HTTPError: If request fails
        """
        try:
            response = await self.client.post(
                f"/api/purchase/send-payment-link/{quote_id}",
                json={
                    "quote_id": quote_id,
                    "customer_email": customer_email,
                    "customer_name": customer_name
                }
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error sending payment link: {e}")
            raise

    async def get_payment_link(self, quote_id: str) -> Dict[str, Any]:
        """
        Get payment link for quote.

        Args:
            quote_id: Quote identifier

        Returns:
            Payment link details

        Raises:
            httpx.HTTPError: If request fails
        """
        try:
            response = await self.client.get(
                f"/api/purchase/payment-link/{quote_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error getting payment link: {e}")
            raise

    # -------------------------------------------------------------------------
    # Block 5: Analytics & Recommendations
    # -------------------------------------------------------------------------

    async def get_recommendations(
        self,
        customer_id: str,
        travel_plan: Dict[str, Any],
        quotation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get recommendations.

        TODO: Implement POST /api/v1/analytics/recommendations
        """
        pass

    async def analyze_destination_risk(
        self,
        destination: str
    ) -> Dict[str, Any]:
        """
        Analyze destination risk.

        TODO: Implement GET /api/v1/analytics/destination-risk/{destination}
        """
        pass

    # -------------------------------------------------------------------------
    # Memory Management
    # -------------------------------------------------------------------------

    async def add_memory(
        self,
        user_id: str,
        messages: List[Dict[str, str]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add memory for user from conversation messages.

        Args:
            user_id: User identifier
            messages: List of messages with 'role' and 'content'
            metadata: Optional metadata

        Returns:
            Memory creation response with IDs

        Raises:
            httpx.HTTPError: If request fails
        """
        try:
            response = await self.client.post(
                "/api/v1/memory/add",
                json={
                    "user_id": user_id,
                    "messages": messages,
                    "metadata": metadata
                }
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error adding memory: {e}")
            raise

    async def search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search user memories using semantic similarity.

        Args:
            user_id: User identifier
            query: Search query
            limit: Maximum results

        Returns:
            List of matching memories with scores

        Raises:
            httpx.HTTPError: If request fails
        """
        try:
            response = await self.client.post(
                "/api/v1/memory/search",
                json={
                    "user_id": user_id,
                    "query": query,
                    "limit": limit
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get('results', [])

        except httpx.HTTPError as e:
            logger.error(f"Error searching memories: {e}")
            raise

    async def get_all_memories(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all memories for a user.

        Args:
            user_id: User identifier

        Returns:
            List of all user memories

        Raises:
            httpx.HTTPError: If request fails
        """
        try:
            response = await self.client.get(
                f"/api/v1/memory/{user_id}"
            )
            response.raise_for_status()
            result = response.json()
            return result.get('results', [])

        except httpx.HTTPError as e:
            logger.error(f"Error getting memories: {e}")
            raise

    async def delete_memory(
        self,
        memory_id: str
    ) -> Dict[str, Any]:
        """
        Delete a specific memory by ID.

        Args:
            memory_id: Memory identifier to delete

        Returns:
            Deletion confirmation

        Raises:
            httpx.HTTPError: If request fails
        """
        try:
            response = await self.client.delete(
                f"/api/v1/memory/{memory_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error deleting memory: {e}")
            raise

    # -------------------------------------------------------------------------
    # Neo4j Concept Search
    # -------------------------------------------------------------------------

    async def search_neo4j_concept(
        self,
        query: str,
        top_k: int = 15
    ) -> Dict[str, Any]:
        """
        Search Neo4j insurance concepts using semantic similarity.

        Uses MemOS TreeTextMemory for intelligent concept retrieval
        from the Neo4j knowledge graph.

        Args:
            query: Natural language search query
            top_k: Number of top results to return (1-50)

        Returns:
            Dict with 'results' (concatenated string), 'count', and 'query'

        Raises:
            httpx.HTTPError: If request fails
        """
        try:
            response = await self.client.post(
                "/api/v1/concept-search",
                json={
                    "query": query,
                    "top_k": top_k
                }
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error searching Neo4j concepts: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            raise

    # -------------------------------------------------------------------------
    # Structured Policy Search
    # -------------------------------------------------------------------------

    async def search_structured_policy(
        self,
        query: str,
        top_k: int = 10
    ) -> Dict[str, Any]:
        """
        Search structured policy data with intelligent routing.

        Uses LLM-based routing to determine which Supabase table(s) to search
        (general_conditions, benefits, benefit_conditions) and performs
        vector similarity search.

        Args:
            query: Natural language search query
            top_k: Number of top results to return per table (1-50)

        Returns:
            Dict with 'success', 'data', 'tables_searched', 'total_results', 'query'

        Raises:
            httpx.HTTPError: If request fails
        """
        try:
            response = await self.client.post(
                "/api/v1/structured-policy-search",
                json={
                    "query": query,
                    "top_k": top_k
                }
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error searching structured policy data: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            raise


# Global client instance
_backend_client: Optional[BackendClient] = None


def get_backend_client() -> BackendClient:
    """
    Get or create global backend client.

    TODO: Implement connection pooling
    TODO: Add configuration management
    """
    global _backend_client
    if _backend_client is None:
        _backend_client = BackendClient()
    return _backend_client
