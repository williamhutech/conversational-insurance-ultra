"""
LLM-Based Routing Service

Uses gpt-4o-mini to intelligently route policy data queries to appropriate
Supabase tables based on the query's semantic meaning.
"""

import json
import logging
from typing import Tuple, Optional, List, Dict, Any

from openai import AsyncOpenAI

from backend.config import settings
from backend.database.postgres_client import get_supabase

logger = logging.getLogger(__name__)


# Routing prompt template based on taxonomy documentation
ROUTING_PROMPT = """You are a travel insurance policy data router. Your task is to analyze queries and determine which database table(s) to search.

AVAILABLE TABLES:

1. **general_conditions** (Layer 1: Policy-Wide Rules)
   - Policy-wide eligibility requirements (age limits, trip origin requirements, health declarations, purchase timing)
   - Universal exclusions (pre-existing conditions, dangerous activities, prohibited destinations, war/terrorism, pandemic)
   - Examples: "age restrictions", "pre-existing medical conditions", "trip must start from Singapore", "dangerous sports exclusions"

2. **benefits** (Layer 2: Coverage & Benefits)
   - Available insurance coverages and what's covered
   - Coverage limits and amounts
   - Types of protection offered (medical, trip cancellation, baggage, liability)
   - Examples: "medical expenses coverage", "trip cancellation benefits", "baggage delay compensation", "coverage limits"

3. **benefit_conditions** (Layer 3: Benefit-Specific Requirements)
   - Specific requirements for claiming each benefit
   - Time limits for claims
   - Minimum thresholds and proof requirements
   - Benefit-specific exclusions
   - Examples: "how long before baggage is considered delayed", "claim documentation needed", "minimum delay for compensation"

ROUTING RULES:

- Query about **age/eligibility/trip requirements/general exclusions** → ["general_conditions"]
- Query about **coverage types/benefits/what's covered/limits** → ["benefits"]
- Query about **claiming/requirements/documentation/thresholds for specific benefits** → ["benefit_conditions"]
- Query **comparing/analyzing multiple aspects** → multiple tables (e.g., ["benefits", "benefit_conditions"])
- Query **very general/broad** → all three tables: ["general_conditions", "benefits", "benefit_conditions"]

IMPORTANT:
- Return ONLY a JSON object with a "tables" array containing 1-3 table names
- Table names must be EXACTLY: "general_conditions", "benefits", or "benefit_conditions"
- Do not include any other text or explanation

EXAMPLES:

Query: "What are the age restrictions for travel insurance?"
Response: {"tables": ["general_conditions"]}

Query: "What medical expenses are covered?"
Response: {"tables": ["benefits"]}

Query: "How long must my baggage be delayed to claim compensation?"
Response: {"tables": ["benefit_conditions"]}

Query: "Compare trip cancellation coverage across policies"
Response: {"tables": ["benefits", "benefit_conditions"]}

Query: "Tell me everything about travel insurance for seniors"
Response: {"tables": ["general_conditions", "benefits", "benefit_conditions"]}

NOW ROUTE THIS QUERY:

Query: {query}

Respond with JSON only:"""


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
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for routing service")

        self.openai = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base_url
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
