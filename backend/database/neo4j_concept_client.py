"""
Neo4j Concept Search Client

Uses MemOS TreeTextMemory for concept-based semantic search in Neo4j.
Integrates with OpenAI for embeddings and LLM processing.
"""

import logging
from typing import List, Optional

from memos.configs.memory import TreeTextMemoryConfig
from memos.memories.textual.tree import TreeTextMemory

from backend.config import settings

logger = logging.getLogger(__name__)


class Neo4jConceptClient:
    """
    Neo4j concept search client using MemOS TreeTextMemory.

    Provides semantic search capabilities over insurance concepts stored in Neo4j,
    using OpenAI embeddings and GPT models for intelligent retrieval.
    """

    def __init__(self):
        """Initialize the Neo4j concept client with MemOS configuration."""
        self.tree_memory: Optional[TreeTextMemory] = None
        self._config: Optional[TreeTextMemoryConfig] = None

    async def connect(self):
        """
        Initialize TreeTextMemory with configuration from settings.

        Raises:
            ValueError: If required configuration is missing
            ConnectionError: If Neo4j or OpenAI connection fails
        """
        logger.info("Initializing Neo4j concept client with MemOS TreeTextMemory")

        # Validate required settings
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for concept search")
        if not settings.neo4j_password:
            raise ValueError("NEO4J_PASSWORD is required for concept search")

        # Build MemOS configuration dictionary
        config_dict = {
            "extractor_llm": {
                "backend": "openai",
                "config": {
                    "model_name_or_path": "gpt-4o-mini",
                    "api_key": settings.openai_api_key,
                    "api_base": settings.openai_api_base_url,
                    "temperature": 0.5,
                    "remove_think_prefix": True,
                    "max_tokens": 8192
                }
            },
            "dispatcher_llm": {
                "backend": "openai",
                "config": {
                    "model_name_or_path": "gpt-4o-mini",
                    "api_key": settings.openai_api_key,
                    "api_base": settings.openai_api_base_url,
                    "temperature": 0.5,
                    "remove_think_prefix": True,
                    "max_tokens": 8192
                }
            },
            "embedder": {
                "backend": "openai",
                "config": {
                    "model": settings.default_embedding_model,
                    "api_key": settings.openai_api_key,
                    "api_base": settings.openai_api_base_url
                }
            },
            "graph_db": {
                "backend": "neo4j",
                "config": {
                    "uri": settings.neo4j_uri,
                    "user": settings.neo4j_user,
                    "password": settings.neo4j_password,
                    "db_name": settings.neo4j_database,
                    "auto_create": True,
                    "embedding_dimension": 1536  # OpenAI text-embedding-3-small dimension
                }
            }
        }

        try:
            # Create TreeTextMemoryConfig from dictionary
            self._config = TreeTextMemoryConfig.from_dict(config_dict)

            # Initialize TreeTextMemory
            self.tree_memory = TreeTextMemory(self._config)

            logger.info(f"Successfully initialized Neo4j concept client (database: {settings.neo4j_database})")

        except Exception as e:
            logger.error(f"Failed to initialize Neo4j concept client: {e}")
            raise ConnectionError(f"Could not connect to Neo4j concept database: {e}")

    async def search_concepts(self, query: str, top_k: int = 15) -> List[str]:
        """
        Search for insurance concepts using semantic similarity.

        Args:
            query: Natural language search query
            top_k: Number of top results to retrieve (default: 15)

        Returns:
            List of concept memory strings (filtered to exclude short nodes < 100 chars)

        Raises:
            RuntimeError: If client is not connected
            ValueError: If query is empty or top_k is invalid
        """
        if not self.tree_memory:
            await self.connect()

        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        if top_k < 1 or top_k > 50:
            raise ValueError("top_k must be between 1 and 50")

        logger.info(f"Searching concepts with query: '{query}' (top_k={top_k})")

        try:
            # Execute search using TreeTextMemory
            results = self.tree_memory.search(query, top_k=top_k)

            # Filter out short pure concept nodes (< 100 characters)
            # These are typically just labels without meaningful content
            filtered_results = [
                node.memory for node in results
                if hasattr(node, 'memory') and len(node.memory) > 100
            ]

            logger.info(f"Found {len(results)} total results, {len(filtered_results)} after filtering")

            return filtered_results

        except Exception as e:
            logger.error(f"Concept search failed: {e}")
            raise RuntimeError(f"Failed to search concepts: {e}")

    async def close(self):
        """Close the Neo4j connection."""
        if self.tree_memory:
            logger.info("Closing Neo4j concept client")
            # TreeTextMemory doesn't have explicit close, but we'll clear the reference
            self.tree_memory = None
            self._config = None


# Global client instance
_client_instance: Optional[Neo4jConceptClient] = None


async def get_neo4j_concept_client() -> Neo4jConceptClient:
    """
    Get or create the global Neo4j concept client instance.

    Returns:
        Initialized Neo4jConceptClient instance
    """
    global _client_instance

    if _client_instance is None:
        _client_instance = Neo4jConceptClient()
        await _client_instance.connect()

    return _client_instance
