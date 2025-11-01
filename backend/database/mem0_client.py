"""
Mem0 Customer Conversation Memory Client (Cloud Version)

Uses Mem0 Platform (Cloud) hosted service at api.mem0.ai.
This is NOT the OSS (self-hosted) version.

Manages long-term and short-term memory for customer conversations.
Tracks customer preferences, conversation history, and context across sessions.

Cloud Features:
- Managed vector store and embeddings
- Automatic memory extraction from conversations
- Semantic search across memories
- Multi-user memory isolation
- Organization and project management

Requirements:
- MEM0_API_KEY: Required API key from Mem0 Platform (get it from https://app.mem0.ai)

Usage:
    from backend.database.mem0_client import Mem0Client

    client = Mem0Client()
    await client.connect()
    
    # Add memory from conversation
    result = await client.add_memory(
        user_id="customer_123",
        messages=[
            {"role": "user", "content": "I prefer high medical coverage"},
            {"role": "assistant", "content": "I'll remember that"}
        ]
    )
    
    # Get all memories
    memories = await client.get_all_memories("customer_123")
    
    # Search memories
    results = await client.search_memories("customer_123", "medical preferences")
"""

from typing import List, Dict, Any, Optional
import logging
from mem0 import AsyncMemoryClient

from backend.config import settings

logger = logging.getLogger(__name__)


class Mem0Client:
    """
    Mem0 client wrapper for customer conversation memory.

    Manages:
    - Short-term conversation context
    - Long-term customer preferences
    - Purchase history context
    - Personalization data
    """

    def __init__(self):
        """
        Initialize Mem0 Cloud client with API key.
        
        Raises:
            ValueError: If MEM0_API_KEY is not configured
        """
        if not settings.mem0_api_key:
            raise ValueError(
                "MEM0_API_KEY is required for Mem0 Cloud. "
                "Please set it in your .env file or environment variables."
            )
        
        self.api_key = settings.mem0_api_key
        self.client: Optional[AsyncMemoryClient] = None
        
        logger.debug("Mem0Client initialized with Cloud configuration (API key only)")

    async def connect(self):
        """
        Initialize Mem0 Platform (cloud) client connection.

        Uses Mem0 Platform hosted service at api.mem0.ai.
        Requires only MEM0_API_KEY from environment.
        """
        try:
            # Mem0 Platform (cloud) version - API key only
            # Hosted service with managed vector store and embeddings
            self.client = AsyncMemoryClient(api_key=self.api_key)
            
            logger.info("✓ Connected to Mem0 Platform (cloud)")
                
        except Exception as e:
            logger.error(f"Failed to connect to Mem0 Platform: {e}")
            raise

    async def disconnect(self):
        """Close Mem0 client connection."""
        if self.client:
            # Mem0 client doesn't require explicit close
            self.client = None
            logger.info("Disconnected from Mem0")

    # -------------------------------------------------------------------------
    # Memory Operations
    # -------------------------------------------------------------------------

    async def add_memory(
        self,
        user_id: str,
        messages: List[Dict[str, str]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add new memory for user from conversation messages.

        Args:
            user_id: User identifier
            messages: List of message dicts with 'role' and 'content' keys
            metadata: Optional metadata (e.g., {"type": "preference"})

        Returns:
            Dict with 'results' containing list of created memories with IDs

        Example:
            >>> result = await client.add_memory(
            ...     user_id="alice",
            ...     messages=[
            ...         {"role": "user", "content": "I prefer high medical coverage"},
            ...         {"role": "assistant", "content": "I'll remember that"}
            ...     ]
            ... )
            >>> # Returns: {"results": [{"id": "...", "memory": "...", "event": "ADD"}]}
        """
        if not self.client:
            await self.connect()

        try:
            result = await self.client.add(
                messages=messages,
                user_id=user_id,
                metadata=metadata
            )
            logger.info(f"Added {len(result.get('results', []))} memories for user {user_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to add memory for user {user_id}: {e}")
            raise

    async def get_all_memories(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all memories for user.

        Args:
            user_id: User identifier

        Returns:
            List of memory objects with id, memory, metadata, created_at

        Example:
            >>> memories = await client.get_all_memories("alice")
            >>> # Returns: [{"id": "...", "memory": "...", "created_at": "..."}]
        """
        if not self.client:
            await self.connect()

        try:
            # Mem0 v2 API requires filters parameter
            result = await self.client.get_all(
                filters={"user_id": user_id}
            )
            
            # Handle both list and dict responses
            if isinstance(result, list):
                memories = result
            else:
                memories = result.get('results', result)
                
            logger.info(f"Retrieved {len(memories)} memories for user {user_id}")
            return memories
        except Exception as e:
            logger.error(f"Failed to get memories for user {user_id}: {e}")
            raise

    async def search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search memories using semantic similarity.

        Args:
            user_id: User identifier
            query: Search query (e.g., "medical coverage preferences")
            limit: Maximum memories to return (default: 10)

        Returns:
            Most relevant memories with id, memory, score, metadata

        Example:
            >>> results = await client.search_memories(
            ...     user_id="alice",
            ...     query="food preferences",
            ...     limit=5
            ... )
            >>> # Returns: [{"id": "...", "memory": "...", "score": 0.95}]
        """
        if not self.client:
            await self.connect()

        try:
            # Mem0 v2 API requires filters parameter
            result = await self.client.search(
                query=query,
                filters={"user_id": user_id},
                limit=limit
            )
            
            # Handle both list and dict responses
            if isinstance(result, list):
                memories = result
            else:
                memories = result.get('results', result)
                
            logger.info(f"Found {len(memories)} memories for query '{query}' (user: {user_id})")
            return memories
        except Exception as e:
            logger.error(f"Failed to search memories for user {user_id}: {e}")
            raise

    async def update_memory(
        self,
        memory_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update existing memory.

        TODO: Implement memory updates
        TODO: Track revision history
        """
        pass

    async def delete_memory(self, memory_id: str) -> bool:
        """
        Delete memory by ID.

        Args:
            memory_id: Memory ID to delete

        Returns:
            True if deleted successfully

        Example:
            >>> success = await client.delete_memory("892db2ae-06d9-49e5-8b3e-585ef9b85b8e")
        """
        if not self.client:
            await self.connect()

        try:
            await self.client.delete(memory_id=memory_id)
            logger.info(f"Deleted memory {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            raise

    # -------------------------------------------------------------------------
    # Conversation Context (Block 2)
    # -------------------------------------------------------------------------

    async def add_conversation_turn(
        self,
        customer_id: str,
        session_id: str,
        user_message: str,
        assistant_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add conversation turn to memory.

        Args:
            customer_id: Customer ID
            session_id: Conversation session ID
            user_message: User's message
            assistant_response: Assistant's response
            metadata: Optional metadata (timestamp, intent, etc.)

        Returns:
            Memory ID for conversation turn

        TODO: Structure conversation memory
        TODO: Extract key information automatically
        TODO: Link to relevant policies/quotes
        """
        pass

    async def get_conversation_context(
        self,
        customer_id: str,
        session_id: str,
        last_n_turns: int = 10
    ) -> List[Dict]:
        """
        Retrieve recent conversation context.

        Args:
            customer_id: Customer ID
            session_id: Session ID
            last_n_turns: Number of recent turns to retrieve

        Returns:
            List of conversation turns with context

        TODO: Implement context retrieval
        TODO: Include relevant memories
        TODO: Format for LLM prompt injection
        """
        pass

    # -------------------------------------------------------------------------
    # Customer Preferences (Block 5)
    # -------------------------------------------------------------------------

    async def add_preference(
        self,
        customer_id: str,
        preference_type: str,
        preference_value: Any,
        confidence: float = 1.0
    ) -> str:
        """
        Add customer preference.

        Args:
            customer_id: Customer ID
            preference_type: Type (e.g., "coverage_preference", "budget_range")
            preference_value: Preference value
            confidence: Confidence score (0.0-1.0)

        Returns:
            Memory ID

        TODO: Implement preference storage
        TODO: Support preference updates
        TODO: Track preference changes over time
        """
        pass

    async def get_preferences(self, customer_id: str) -> Dict[str, Any]:
        """
        Get all customer preferences.

        Returns:
            Dictionary of preferences by type

        TODO: Implement preference aggregation
        TODO: Resolve conflicting preferences
        TODO: Return with confidence scores
        """
        pass

    async def infer_preferences(
        self,
        customer_id: str,
        conversation_history: List[Dict]
    ) -> Dict[str, Any]:
        """
        Infer preferences from conversation history.

        Uses LLM to analyze conversation and extract:
        - Budget preferences
        - Coverage priorities
        - Risk tolerance
        - Travel patterns

        TODO: Implement preference inference
        TODO: Use Claude to analyze conversations
        TODO: Store inferred preferences automatically
        """
        pass

    # -------------------------------------------------------------------------
    # Purchase History Context (Block 4)
    # -------------------------------------------------------------------------

    async def add_purchase_context(
        self,
        customer_id: str,
        purchase_data: Dict[str, Any]
    ) -> str:
        """
        Add purchase to customer memory.

        Args:
            customer_id: Customer ID
            purchase_data: Purchase details (policy, amount, date)

        Returns:
            Memory ID

        TODO: Structure purchase memory
        TODO: Link to policy details
        TODO: Extract relevant context for future recommendations
        """
        pass

    async def get_purchase_history(self, customer_id: str) -> List[Dict]:
        """
        Retrieve customer's purchase history from memory.

        TODO: Implement purchase history retrieval
        TODO: Include policy satisfaction indicators
        """
        pass

    # -------------------------------------------------------------------------
    # Session Management
    # -------------------------------------------------------------------------

    async def create_session(self, customer_id: str) -> str:
        """
        Create new conversation session.

        Returns:
            Session ID

        TODO: Generate unique session ID
        TODO: Initialize session context
        TODO: Load relevant customer memories
        """
        pass

    async def end_session(self, session_id: str):
        """
        End conversation session and consolidate memories.

        TODO: Extract key learnings from session
        TODO: Update customer preferences
        TODO: Archive session
        """
        pass

    # -------------------------------------------------------------------------
    # Memory Management
    # -------------------------------------------------------------------------

    async def clear_customer_memories(self, customer_id: str):
        """
        Clear all memories for customer (GDPR compliance).

        TODO: Implement memory clearing
        TODO: Add confirmation requirement
        TODO: Log for audit trail
        """
        pass

    async def get_memory_stats(self, customer_id: str) -> Dict[str, Any]:
        """
        Get statistics about customer memories.

        Returns:
        - Total memory count
        - Memory types breakdown
        - Last activity timestamp

        TODO: Implement stats collection
        """
        pass


# Global client instance (optional)
_mem0_client: Optional[Mem0Client] = None


async def get_mem0() -> Mem0Client:
    """
    Get or create global Mem0 client instance.

    Returns:
        Mem0Client: Configured client instance

    TODO: Implement connection pooling
    TODO: Add connection lifecycle management
    """
    global _mem0_client
    if _mem0_client is None:
        _mem0_client = Mem0Client()
        await _mem0_client.connect()
    return _mem0_client


# -----------------------------------------------------------------------------
# Migration Notes: OSS vs Cloud
# -----------------------------------------------------------------------------
"""
Mem0 Cloud vs OSS Differences:

1. INSTALLATION:
   - Cloud: Uses same package `mem0ai`, but different classes
   - OSS: Uses `Memory` or `AsyncMemory` classes
   - Cloud: Uses `MemoryClient` or `AsyncMemoryClient` classes

2. INITIALIZATION:
   OSS Version (OLD - Not used here):
   ```python
   from mem0 import AsyncMemory
   
   config = {
       "vector_store": {
           "provider": "qdrant",
           "config": {
               "host": "localhost",
               "port": 6333
           }
       },
       "llm": {
           "provider": "openai",
           "config": {
               "model": "gpt-4",
               "api_key": "sk-..."
           }
       },
       "embedder": {
           "provider": "openai",
           "config": {
               "model": "text-embedding-3-small"
           }
       }
   }
   
   client = AsyncMemory(config)
   ```
   
   Cloud Version (CURRENT - What we use):
   ```python
   from mem0 import AsyncMemoryClient
   
   # Simple initialization - just need API key
   client = AsyncMemoryClient(api_key="m0-...")
   ```

3. KEY DIFFERENCES:
   - Cloud: No need to configure vector stores, LLM, or embeddings
   - Cloud: Managed infrastructure and automatic scaling
   - Cloud: Built-in multi-tenancy with user_id isolation
   - Cloud: Hosted at api.mem0.ai
   - OSS: Requires local infrastructure (Qdrant, OpenAI API, etc.)
   - OSS: Self-hosted and self-managed

4. API COMPATIBILITY:
   - Both versions use similar API methods:
     * add() / add_memory()
     * get_all()
     * search()
     * delete()
   - Cloud version is simpler - no config object needed
   
5. ENVIRONMENT VARIABLES:
   Cloud Version (.env):
   ```
   MEM0_API_KEY=m0-xxx...
   ```
   
   OSS Version would need:
   ```
   QDRANT_HOST=localhost
   QDRANT_PORT=6333
   OPENAI_API_KEY=sk-xxx...
   ```

6. MIGRATION STEPS (if switching from OSS to Cloud):
   a. Get Mem0 Cloud API key from https://app.mem0.ai
   b. Update .env file with MEM0_API_KEY
   c. Change import from `Memory` to `MemoryClient`
   d. Remove vector_store, llm, embedder config
   e. Pass only api_key to constructor
   f. Remove local Qdrant/vector store infrastructure
"""
