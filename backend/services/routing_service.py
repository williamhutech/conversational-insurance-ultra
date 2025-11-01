"""
LLM-Based Routing Service

Uses gpt-4o-mini to intelligently route policy data queries to appropriate
Supabase tables based on the query's semantic meaning.
"""
from dotenv import load_dotenv
import json, os
import logging
from typing import Tuple, Optional, List, Dict, Any

from openai import AsyncOpenAI

# Load environment variables from .env
load_dotenv()

from backend.database.supabase_client import get_supabase

logger = logging.getLogger(__name__)


# Routing prompt template based on taxonomy documentation
ROUTING_PROMPT = """Route this travel insurance query to the correct database table(s).

TABLES:
1. **general_conditions** - Policy eligibility, age limits, trip origin requirements, universal exclusions (pre-existing conditions, dangerous activities, prohibited destinations)
2. **benefits** - Coverage types, benefit amounts, coverage limits, what's covered
3. **benefit_conditions** - Claim requirements, time limits, minimum thresholds, proof requirements, benefit-specific exclusions

ROUTING LOGIC:
- Eligibility/age/trip requirements/general exclusions → ["general_conditions"]
- Coverage types/benefit amounts/limits → ["benefits"]
- Claim requirements/documentation/thresholds → ["benefit_conditions"]
- Broad comparison/analysis → Multiple tables
- Very general questions → All three tables

Return ONLY valid JSON: {{"tables": ["table_name1", "table_name2"]}}

Examples:
- "age restrictions" → {{"tables": ["general_conditions"]}}
- "medical coverage" → {{"tables": ["benefits"]}}
- "baggage delay claim" → {{"tables": ["benefit_conditions"]}}
- "trip cancellation comparison" → {{"tables": ["benefits", "benefit_conditions"]}}
- "everything about seniors" → {{"tables": ["general_conditions", "benefits", "benefit_conditions"]}}

Query: {query}
JSON:"""


class RoutingService:
    """
    LLM-based routing service for policy data queries.

    Uses gpt-4o-mini to determine which Supabase table(s) to search
    based on semantic analysis of the user's query.
    """

    def __init__(self):
        """Initialize routing service with OpenAI client."""
        self.openai: Optional[AsyncOpenAI] = None
        self.valid_tables = {"general_conditions", "benefits", "benefit_conditions"}

    async def connect(self):
        """Initialize OpenAI client."""
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY is required for routing service")

        self.openai = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE_URL")
        )
        logger.info("Routing service initialized with gpt-4o-mini")

    async def _call_routing_llm(self, query: str) -> Optional[List[str]]:
        """
        Call gpt-4o-mini to route the query.

        Args:
            query: User's search query

        Returns:
            List of table names or None if parsing fails
        """
        if not self.openai:
            await self.connect()

        try:
            # Call gpt-4o-mini with routing prompt
            response = await self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": ROUTING_PROMPT.format(query=query)
                    }
                ],
                temperature=0.0,  # Deterministic routing
                max_tokens=100,
                response_format={"type": "json_object"}
            )

            # Parse JSON response
            content = response.choices[0].message.content
            parsed = json.loads(content)

            # Extract tables array
            tables = parsed.get("tables", [])

            # Validate table names
            valid_tables = [t for t in tables if t in self.valid_tables]

            if not valid_tables:
                logger.warning(f"No valid tables in LLM response: {tables}")
                return None

            logger.info(f"Routing decision: {valid_tables}")
            return valid_tables

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Routing LLM call failed: {e}")
            return None

    async def route_query(
        self,
        query: str,
        top_k: int = 10,
        max_retries: int = 3
    ) -> Tuple[int, Optional[List[Dict[str, Any]]]]:
        """
        Route query to appropriate table(s) and execute search.

        Args:
            query: User's search query
            top_k: Number of results to return per table
            max_retries: Maximum routing attempts (default: 3)

        Returns:
            Tuple of (status_code, results):
            - (0, combined_results) on success
            - (1, None) on failure after max retries

        Status Codes:
            0: Success
            1: Failure (routing failed or no valid tables after retries)
        """
        logger.info(f"Routing query: '{query}' (top_k={top_k}, max_retries={max_retries})")

        # Attempt routing with retries
        tables_to_search = None
        for attempt in range(1, max_retries + 1):
            logger.debug(f"Routing attempt {attempt}/{max_retries}")

            tables_to_search = await self._call_routing_llm(query)

            if tables_to_search:
                break

            if attempt < max_retries:
                logger.warning(f"Routing attempt {attempt} failed, retrying...")

        # If routing failed after all retries
        if not tables_to_search:
            logger.error(f"Routing failed after {max_retries} attempts")
            return (1, None)

        # Get Supabase client
        try:
            supabase_client = await get_supabase()
        except Exception as e:
            logger.error(f"Failed to get Supabase client: {e}")
            return (1, None)

        # Execute searches on determined tables
        combined_results = []

        try:
            for table_name in tables_to_search:
                logger.info(f"Searching table: {table_name}")

                # Route to appropriate search function
                if table_name == "general_conditions":
                    results = await supabase_client.search_general_conditions(query, top_k)
                elif table_name == "benefits":
                    results = await supabase_client.search_benefits(query, top_k)
                elif table_name == "benefit_conditions":
                    results = await supabase_client.search_benefit_conditions(query, top_k)
                else:
                    logger.warning(f"Unknown table: {table_name}, skipping")
                    continue

                combined_results.extend(results)
                logger.info(f"Retrieved {len(results)} results from {table_name}")

            # Sort combined results by similarity score (if available)
            if combined_results and 'similarity_score' in combined_results[0]:
                combined_results.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)

            logger.info(f"Successfully retrieved {len(combined_results)} total results")
            return (0, combined_results)

        except Exception as e:
            logger.error(f"Search execution failed: {e}")
            return (1, None)


# Global service instance
_routing_service: Optional[RoutingService] = None


async def get_routing_service() -> RoutingService:
    """
    Get or create global routing service instance.

    Returns:
        Initialized RoutingService instance
    """
    global _routing_service

    if _routing_service is None:
        _routing_service = RoutingService()
        await _routing_service.connect()

    return _routing_service

# Write a testing script for the RoutingService class defined above.
if __name__ == "__main__":
    import asyncio

    async def test_routing_service():
        service = RoutingService()
        await service.connect()

        test_queries = [
            "What are the age restrictions for travel insurance?",
            "Explain the medical coverage benefits.",
            "How do I file a baggage delay claim?",
            "Compare trip cancellation policies.",
            "Tell me everything about senior travel insurance."
        ]

        for query in test_queries:
            status_code, results = await service.route_query(query, top_k=5)
            print(f"Query: {query}")
            print(f"Status Code: {status_code}")
            if results is not None:
                print(f"Results ({len(results)}): {results}")
            else:
                print("No results returned.")
            print("-" * 50)

    asyncio.run(test_routing_service())