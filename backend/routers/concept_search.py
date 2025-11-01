"""
Concept Search API Router

REST API endpoint for Neo4j concept search using MemOS.
Provides semantic search capabilities over insurance concepts.

Endpoints:
    POST /api/v1/concept-search - Search insurance concepts by natural language query
"""

import logging
from fastapi import APIRouter, HTTPException, status

from backend.database.neo4j_concept_client import get_neo4j_concept_client
from backend.models.concept_search import ConceptSearchRequest, ConceptSearchResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/concept-search",
    tags=["concept-search"],
    responses={
        400: {"description": "Invalid request parameters"},
        500: {"description": "Internal server error"},
        503: {"description": "Neo4j service unavailable"}
    }
)


@router.post(
    "",
    response_model=ConceptSearchResponse,
    summary="Search Neo4j concepts",
    description="Search insurance concepts in Neo4j using semantic similarity with MemOS TreeTextMemory."
)
async def search_concepts(request: ConceptSearchRequest) -> ConceptSearchResponse:
    """
    Search insurance concepts using natural language queries.

    Uses MemOS TreeTextMemory with OpenAI embeddings to find semantically
    similar insurance concepts stored in Neo4j. Results are filtered to
    exclude short concept nodes (< 100 characters).

    Example request:
        ```json
        {
            "query": "I want to travel to China, please recommend insurance for me",
            "top_k": 15
        }
        ```

    Returns:
        ConceptSearchResponse with concatenated concept memories

    Raises:
        HTTPException 400: If query is empty or top_k is invalid
        HTTPException 503: If Neo4j connection fails
        HTTPException 500: If search operation fails
    """
    try:
        logger.info(f"API: Searching concepts with query: '{request.query}' (top_k={request.top_k})")

        # Get Neo4j concept client
        client = await get_neo4j_concept_client()

        # Execute search
        filtered_results = await client.search_concepts(
            query=request.query,
            top_k=request.top_k
        )

        # Format results into single concatenated string
        results_text = "\n\n".join(filtered_results) if filtered_results else "No results found."

        response = ConceptSearchResponse(
            results=results_text,
            count=len(filtered_results),
            query=request.query
        )

        logger.info(f"API: Successfully found {len(filtered_results)} concepts")
        return response

    except ValueError as e:
        # Invalid query or parameters
        logger.warning(f"API: Invalid request parameters: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except ConnectionError as e:
        # Neo4j connection failed
        logger.error(f"API: Neo4j connection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Neo4j service unavailable: {str(e)}"
        )

    except RuntimeError as e:
        # Search operation failed
        logger.error(f"API: Concept search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search concepts: {str(e)}"
        )

    except Exception as e:
        # Unexpected error
        logger.error(f"API: Unexpected error during concept search: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )
