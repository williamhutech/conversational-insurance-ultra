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

    def __init__(self, base_url: str = "http://localhost:8085"):
        """
        Initialize backend client.

        Args:
            base_url: Backend API base URL (default: http://localhost:8085)

        TODO: Load base_url from environment variable
        TODO: Add authentication token handling
        """
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
        travel_plan_id: Optional[str] = None,
        manual_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate quotation.

        TODO: Implement POST /api/v1/quotations/generate
        """
        pass

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
