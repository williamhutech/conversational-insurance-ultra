"""
Neo4j Concept Search Client

Uses MemOS TreeTextMemory for concept-based semantic search in Neo4j.
Integrates with OpenAI for embeddings and LLM processing.
"""

import json
import logging
import os
import tempfile
from typing import List, Optional

from dotenv import load_dotenv
from memos.configs.memory import TreeTextMemoryConfig
from memos.memories.textual.tree import TreeTextMemory

# Load environment variables from .env
load_dotenv()

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
        Initialize TreeTextMemory with configuration from environment variables.

        Raises:
            ValueError: If required configuration is missing
            ConnectionError: If Neo4j or OpenAI connection fails
        """
        logger.info("Initializing Neo4j concept client with MemOS TreeTextMemory")

        # Load environment variables
        openai_api_key = os.getenv("OPENAI_API_KEY")
        openai_api_base_url = os.getenv("OPENAI_API_BASE_URL", "https://api.openai.com/v1")
        neo4j_policy_uri = os.getenv("NEO4J_POLICY_URI")
        neo4j_policy_username = os.getenv("NEO4J_POLICY_USERNAME", "neo4j")
        neo4j_policy_password = os.getenv("NEO4J_POLICY_PASSWORD")
        neo4j_policy_database = os.getenv("NEO4J_POLICY_DATABASE", "neo4j")
        default_embedding_model = os.getenv("DEFAULT_EMBEDDING_MODEL", "text-embedding-3-small")

        # Validate required settings
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for concept search")
        if not neo4j_policy_password:
            raise ValueError("NEO4J_POLICY_PASSWORD is required for concept search")
        if not neo4j_policy_uri:
            raise ValueError("NEO4J_POLICY_URI is required for concept search")

        # Build MemOS configuration dictionary
        config_dict = {
            "extractor_llm": {
                "backend": "openai",
                "config": {
                    "model_name_or_path": "gpt-4o-mini",
                    "api_key": openai_api_key,
                    "api_base": openai_api_base_url,
                    "temperature": 0.5,
                    "remove_think_prefix": True,
                    "max_tokens": 8192
                }
            },
            "dispatcher_llm": {
                "backend": "openai",
                "config": {
                    "model_name_or_path": "gpt-4o-mini",
                    "api_key": openai_api_key,
                    "api_base": openai_api_base_url,
                    "temperature": 0.5,
                    "remove_think_prefix": True,
                    "max_tokens": 8192
                }
            },
            "embedder": {
                "backend": "sentence_transformer",
                "config": {
                    "model_name_or_path": "sentence-transformers/all-mpnet-base-v2"
                }
            },
            "graph_db": {
                "backend": "neo4j",
                "config": {
                    "uri": neo4j_policy_uri,
                    "user": neo4j_policy_username,
                    "password": neo4j_policy_password,
                    "db_name": neo4j_policy_database,
                    "auto_create": False,  # Set to False for Neo4j Aura (cloud) - database must exist
                    "embedding_dimension": 768  # sentence-transformers/all-mpnet-base-v2 dimension
                }
            }
        }

        try:
            # Write config to temporary JSON file (required by TreeTextMemoryConfig)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
                temp_config_path = f.name

            try:
                # Create TreeTextMemoryConfig from JSON file
                self._config = TreeTextMemoryConfig.from_json_file(temp_config_path)

                # Initialize TreeTextMemory
                self.tree_memory = TreeTextMemory(self._config)

                print(f"Successfully initialized Neo4j concept client (database: {neo4j_policy_database})")
            finally:
                # Clean up temporary config file
                if os.path.exists(temp_config_path):
                    os.unlink(temp_config_path)

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

        print("All Memories:")

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

