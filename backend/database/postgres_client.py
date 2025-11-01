"""
Supabase Postgres Client

Manages connections to Supabase Postgres database for normalized policy data,
quotations, purchases, and customer information.

Features:
- Connection pooling
- Query builder interface
- Transaction management
- Error handling and retries

Usage:
    from backend.database.postgres_client import SupabaseClient

    client = SupabaseClient()
    policies = await client.get_policies()
"""

from typing import List, Dict, Any, Optional
from supabase import create_client, Client
from openai import AsyncOpenAI
import logging

from backend.config import settings

logger = logging.getLogger(__name__)


class SupabaseClient:
    """
    Supabase client wrapper for Postgres operations.

    Provides high-level interface for database operations on:
    - Policies (normalized taxonomy data)
    - Quotations (generated quotes)
    - Purchases (completed transactions)
    - Customers (user information)
    """

    def __init__(self):
        """Initialize Supabase client with credentials from settings."""
        self.url = settings.supabase_url
        self.key = settings.supabase_service_key  # Use service key for backend
        self.client: Optional[Client] = None
        self.openai: Optional[AsyncOpenAI] = None

    async def connect(self):
        """
        Establish connection to Supabase and OpenAI.

        TODO: Implement connection pooling
        TODO: Add connection health check
        TODO: Handle connection timeouts
        """
        try:
            # Initialize Supabase client
            self.client = create_client(self.url, self.key)
            logger.info("Connected to Supabase")

            # Initialize OpenAI client for embeddings
            if settings.openai_api_key:
                self.openai = AsyncOpenAI(
                    api_key=settings.openai_api_key,
                    base_url=settings.openai_api_base_url
                )
                logger.info("Initialized OpenAI client for embeddings")
        except Exception as e:
            logger.error(f"Failed to connect to Supabase/OpenAI: {e}")
            raise

    async def disconnect(self):
        """
        Close connection to Supabase.

        TODO: Implement graceful shutdown
        TODO: Wait for pending queries
        """
        if self.client:
            # Supabase Python client doesn't require explicit close
            self.client = None
            logger.info("Disconnected from Supabase")

    # -------------------------------------------------------------------------
    # Policy Operations (Block 1)
    # -------------------------------------------------------------------------

    async def get_policies(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """
        Retrieve policies from database.

        Args:
            filters: Optional filters (e.g., {"product_type": "travel"})

        Returns:
            List of policy records

        TODO: Implement filtering logic
        TODO: Add pagination support
        TODO: Add sorting options
        """
        pass

    async def get_policy_by_id(self, policy_id: str) -> Optional[Dict]:
        """
        Retrieve single policy by ID.

        TODO: Implement policy lookup
        TODO: Add caching
        """
        pass

    async def search_policies(self, query: str) -> List[Dict]:
        """
        Search policies using full-text search.

        TODO: Implement full-text search
        TODO: Use policy_name, product_type, benefits
        """
        pass

    # -------------------------------------------------------------------------
    # Quotation Operations (Block 3)
    # -------------------------------------------------------------------------

    async def create_quotation(self, quotation_data: Dict[str, Any]) -> Dict:
        """
        Create new quotation record.

        TODO: Validate quotation data
        TODO: Generate quotation ID
        TODO: Store extracted travel data
        """
        pass

    async def get_quotation(self, quotation_id: str) -> Optional[Dict]:
        """
        Retrieve quotation by ID.

        TODO: Implement quotation lookup
        TODO: Include related policy data
        """
        pass

    async def update_quotation(self, quotation_id: str, updates: Dict[str, Any]) -> Dict:
        """
        Update existing quotation.

        TODO: Implement update logic
        TODO: Track revision history
        """
        pass

    # -------------------------------------------------------------------------
    # Purchase Operations (Block 4)
    # -------------------------------------------------------------------------

    async def create_purchase(self, purchase_data: Dict[str, Any]) -> Dict:
        """
        Create new purchase record.

        TODO: Link to quotation
        TODO: Store payment information
        TODO: Generate policy document
        """
        pass

    async def get_purchase(self, purchase_id: str) -> Optional[Dict]:
        """
        Retrieve purchase by ID.

        TODO: Implement purchase lookup
        TODO: Include policy and payment details
        """
        pass

    async def update_purchase_status(
        self, purchase_id: str, status: str, payment_info: Optional[Dict] = None
    ) -> Dict:
        """
        Update purchase payment status.

        TODO: Handle status transitions
        TODO: Store Stripe payment details
        """
        pass

    # -------------------------------------------------------------------------
    # Selection Operations (Quotation-Payment Mapping)
    # -------------------------------------------------------------------------

    async def get_selection_by_payment_id(
        self, payment_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get selection record with related quotation data by payment_id.
        
        This is used to find the Ancileo quote and offer information
        when completing a purchase after payment.
        
        Args:
            payment_id: Payment intent ID from Stripe
        
        Returns:
            Dictionary with selection and quotation data:
            - selection fields (selection_id, quote_id, insureds, main_contact, etc.)
            - quotation fields (quote_id is Ancileo quote ID, offer_id, etc.)
            - None if not found
        """
        if not self.client:
            await self.connect()
        
        try:
            # Query selections table
            response = self.client.table('selections')\
                .select('*')\
                .eq('payment_id', payment_id)\
                .limit(1)\
                .execute()
            
            if not response.data:
                logger.info(f"No selection found for payment_id: {payment_id}")
                return None
            
            selection = response.data[0]
            
            # Get related quotation data
            quote_id = selection.get('quote_id')
            if quote_id:
                quote = await self.get_quotation_with_offers(quote_id)
                if quote:
                    selection['quotes'] = quote
            
            logger.info(f"Found selection {selection['selection_id']} for payment {payment_id}")
            return selection
            
        except Exception as e:
            logger.error(f"Error getting selection by payment_id: {e}")
            raise

    async def create_selection(
        self, selection_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new selection record.
        
        Args:
            selection_data: Dictionary with:
                - user_id: User ID
                - quote_id: Quote ID (FK) - this is the Ancileo quote ID directly
                - insureds: JSONB with insured persons
                - main_contact: JSONB with main contact info
                - selected_offer_id: Selected offer ID
                - product_type: Product type (default: "travel-insurance")
                - quantity: Quantity (default: 1)
                - total_price: Total price
                - is_send_email: Whether to send email (default: true)
                - status: Status (default: "draft")
        
        Returns:
            Created selection record
        """
        if not self.client:
            await self.connect()
        
        try:
            # Set defaults
            selection_data.setdefault('status', 'draft')
            selection_data.setdefault('product_type', 'travel-insurance')
            selection_data.setdefault('quantity', 1)
            selection_data.setdefault('is_send_email', True)
            
            response = self.client.table('selections')\
                .insert(selection_data)\
                .execute()
            
            logger.info(f"Created selection: {response.data[0]['selection_id']}")
            return response.data[0]
            
        except Exception as e:
            logger.error(f"Error creating selection: {e}")
            raise

    async def update_selection_payment_id(
        self, selection_id: str, payment_id: str
    ) -> Dict[str, Any]:
        """
        Update selection with payment_id to link quotation to payment.
        
        Args:
            selection_id: Selection UUID
            payment_id: Payment intent ID
        
        Returns:
            Updated selection record
        """
        if not self.client:
            await self.connect()
        
        try:
            response = self.client.table('selections')\
                .update({
                    'payment_id': payment_id,
                    'status': 'pending_payment',
                    'updated_at': 'now()'
                })\
                .eq('selection_id', selection_id)\
                .execute()
            
            logger.info(f"Updated selection {selection_id} with payment_id {payment_id}")
            return response.data[0]
            
        except Exception as e:
            logger.error(f"Error updating selection payment_id: {e}")
            raise

    async def get_quotation_with_offers(
        self, quote_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get quotation with full Ancileo response and offers.
        
        Args:
            quote_id: Quote ID
        
        Returns:
            Quotation record with quotation_response parsed
        """
        if not self.client:
            await self.connect()
        
        try:
            response = self.client.table('quotes')\
                .select('*')\
                .eq('quote_id', quote_id)\
                .limit(1)\
                .execute()
            
            if not response.data:
                return None
            
            quote = response.data[0]
            
            # Parse quotation_response to extract offers
            quotation_response = quote.get('quotation_response', {})
            if isinstance(quotation_response, dict):
                offer_categories = quotation_response.get('offerCategories', [])
                if offer_categories:
                    quote['offers'] = offer_categories[0].get('offers', [])
                else:
                    quote['offers'] = []
            
            return quote
            
        except Exception as e:
            logger.error(f"Error getting quotation with offers: {e}")
            raise

    # -------------------------------------------------------------------------
    # Customer Operations
    # -------------------------------------------------------------------------

    async def create_customer(self, customer_data: Dict[str, Any]) -> Dict:
        """
        Create new customer record.

        TODO: Validate customer data
        TODO: Check for duplicates
        """
        pass

    async def get_customer(self, customer_id: str) -> Optional[Dict]:
        """
        Retrieve customer by ID.

        TODO: Implement customer lookup
        TODO: Include purchase history
        """
        pass

    async def get_customer_by_email(self, email: str) -> Optional[Dict]:
        """
        Retrieve customer by email address.

        TODO: Implement email lookup
        TODO: Handle case-insensitive search
        """
        pass

    # -------------------------------------------------------------------------
    # Vector Search Operations (Travel Insurance Taxonomy)
    # -------------------------------------------------------------------------

    async def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text using OpenAI.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector

        Raises:
            RuntimeError: If embedding generation fails
        """
        if not self.openai:
            raise RuntimeError("OpenAI client not initialized")

        try:
            response = await self.openai.embeddings.create(
                model=settings.default_embedding_model,
                input=text
            )
            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding with {len(embedding)} dimensions")
            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise RuntimeError(f"Embedding generation failed: {e}")

    async def search_general_conditions(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Search general_conditions table using vector similarity.

        Searches Layer 1: Policy-wide eligibility & exclusions.

        Args:
            query: Natural language search query
            top_k: Number of top results to return

        Returns:
            List of dicts with all columns + similarity_score, sorted by similarity

        Raises:
            RuntimeError: If search fails
        """
        if not self.client:
            await self.connect()

        logger.info(f"Searching general_conditions: '{query}' (top_k={top_k})")

        try:
            # Generate query embedding
            query_embedding = await self._generate_embedding(query)

            # Execute vector search
            # Use direct SQL query for flexibility with cosine distance operator
            response = self.client.rpc(
                'search_general_conditions_vector',
                {
                    'query_embedding': query_embedding,
                    'match_count': top_k
                }
            ).execute()

            if not response.data:
                logger.info("No results found in general_conditions")
                return []

            # Add table identifier to results
            results = []
            for row in response.data:
                result = dict(row)
                result['table'] = 'general_conditions'
                results.append(result)

            logger.info(f"Found {len(results)} results in general_conditions")
            return results

        except Exception as e:
            logger.error(f"Search failed on general_conditions: {e}")
            raise RuntimeError(f"Failed to search general_conditions: {e}")

    async def search_benefits(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Search benefits table using vector similarity.

        Searches Layer 2: Available coverages and benefits.

        Args:
            query: Natural language search query
            top_k: Number of top results to return

        Returns:
            List of dicts with all columns + similarity_score, sorted by similarity

        Raises:
            RuntimeError: If search fails
        """
        if not self.client:
            await self.connect()

        logger.info(f"Searching benefits: '{query}' (top_k={top_k})")

        try:
            # Generate query embedding
            query_embedding = await self._generate_embedding(query)

            # Execute vector search
            response = self.client.rpc(
                'search_benefits_vector',
                {
                    'query_embedding': query_embedding,
                    'match_count': top_k
                }
            ).execute()

            if not response.data:
                logger.info("No results found in benefits")
                return []

            # Add table identifier to results
            results = []
            for row in response.data:
                result = dict(row)
                result['table'] = 'benefits'
                results.append(result)

            logger.info(f"Found {len(results)} results in benefits")
            return results

        except Exception as e:
            logger.error(f"Search failed on benefits: {e}")
            raise RuntimeError(f"Failed to search benefits: {e}")

    async def search_benefit_conditions(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Search benefit_conditions table using vector similarity.

        Searches Layer 3: Benefit-specific requirements & exclusions.

        Args:
            query: Natural language search query
            top_k: Number of top results to return

        Returns:
            List of dicts with all columns + similarity_score, sorted by similarity

        Raises:
            RuntimeError: If search fails
        """
        if not self.client:
            await self.connect()

        logger.info(f"Searching benefit_conditions: '{query}' (top_k={top_k})")

        try:
            # Generate query embedding
            query_embedding = await self._generate_embedding(query)

            # Execute vector search
            response = self.client.rpc(
                'search_benefit_conditions_vector',
                {
                    'query_embedding': query_embedding,
                    'match_count': top_k
                }
            ).execute()

            if not response.data:
                logger.info("No results found in benefit_conditions")
                return []

            # Add table identifier to results
            results = []
            for row in response.data:
                result = dict(row)
                result['table'] = 'benefit_conditions'
                results.append(result)

            logger.info(f"Found {len(results)} results in benefit_conditions")
            return results

        except Exception as e:
            logger.error(f"Search failed on benefit_conditions: {e}")
            raise RuntimeError(f"Failed to search benefit_conditions: {e}")

    async def search_original_text(self, query: str, top_k: int = 10) -> List[str]:
        """
        Search original policy text using vector similarity.

        Searches chunked original policy documents to find semantically similar text.
        Returns only the text content as a list of strings.

        Args:
            query: Natural language search query
            top_k: Number of top text chunks to return

        Returns:
            List of text strings, sorted by similarity descending

        Raises:
            RuntimeError: If search fails
        """
        if not self.client:
            await self.connect()

        logger.info(f"Searching original_text: '{query}' (top_k={top_k})")

        try:
            # Generate query embedding
            query_embedding = await self._generate_embedding(query)

            # Execute vector search using the existing RPC function
            response = self.client.rpc(
                'search_similar_original_text',
                {
                    'query_embedding': query_embedding,
                    'match_count': top_k,
                    'filter_product': None  # Search across all products
                }
            ).execute()

            if not response.data:
                logger.info("No results found in original_text")
                return []

            # Extract just the text content from each result
            text_list = [row['text'] for row in response.data if 'text' in row]

            logger.info(f"Found {len(text_list)} text chunks in original_text")
            return text_list

        except Exception as e:
            logger.error(f"Search failed on original_text: {e}")
            raise RuntimeError(f"Failed to search original_text: {e}")


# Global client instance (optional)
_supabase_client: Optional[SupabaseClient] = None


async def get_supabase() -> SupabaseClient:
    """
    Get or create global Supabase client instance.

    Returns:
        SupabaseClient: Configured client instance

    TODO: Implement connection pooling
    TODO: Add connection lifecycle management
    """
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
        await _supabase_client.connect()
    return _supabase_client
