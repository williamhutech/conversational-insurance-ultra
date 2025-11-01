"""
Structured Policy Search API Router

REST API endpoint for intelligent policy data search with LLM-based routing.
Provides semantic search across travel insurance taxonomy tables.

Endpoints:
    POST /api/v1/structured-policy-search - Search policy data with intelligent routing
"""

import logging
from fastapi import APIRouter, HTTPException, status

from backend.services.routing_service import get_routing_service
from backend.models.structured_policy import StructuredPolicyRequest, StructuredPolicyResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/structured-policy-search",
    tags=["structured-policy"],
    responses={
        400: {"description": "Invalid request parameters"},
        500: {"description": "Internal server error"},
        503: {"description": "Service unavailable"}
    }
)


@router.post(
    "",
    response_model=StructuredPolicyResponse,
    summary="Search structured policy data",
    description="Search travel insurance policy data using intelligent LLM routing and vector similarity search."
)
async def search_structured_policy(request: StructuredPolicyRequest) -> StructuredPolicyResponse:
    """
    Search structured policy data with intelligent table routing.

    This endpoint uses gpt-4o-mini to analyze your query and automatically
    route it to the most relevant database table(s):

    - **Layer 1 (general_conditions)**: Policy-wide eligibility & exclusions
    - **Layer 2 (benefits)**: Available coverages and benefits
    - **Layer 3 (benefit_conditions)**: Benefit-specific requirements

    The system performs vector similarity search using OpenAI embeddings
    to find the most relevant policy data.

    Example requests:

    ```json
    {
        "query": "What are the age restrictions for travel insurance?",
        "top_k": 10
    }
    ```

    ```json
    {
        "query": "Compare medical coverage limits across policies",
        "top_k": 15
    }
    ```

    ```json
    {
        "query": "What documentation is needed to claim baggage delay?",
        "top_k": 5
    }
    ```

    Returns:
        Structured policy data with similarity scores, sorted by relevance

    Raises:
        HTTPException 400: If query is empty or top_k is invalid
        HTTPException 500: If routing or search fails
        HTTPException 503: If database or OpenAI service is unavailable
    """
    try:
        logger.info(f"API: Structured policy search - Query: '{request.query}' (top_k={request.top_k})")

        # Get routing service
        routing_service = await get_routing_service()

        # Route query and execute search
        status_code, results = await routing_service.route_query(
            query=request.query,
            top_k=request.top_k,
            max_retries=3
        )

        # Check if routing/search failed
        if status_code != 0 or results is None:
            logger.error(f"API: Routing failed for query: '{request.query}'")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to route and search query after multiple attempts. Please rephrase your question or try again."
            )

        # Extract unique tables searched
        tables_searched = list(set(result.get('table', 'unknown') for result in results))

        response = StructuredPolicyResponse(
            success=True,
            data=results,
            tables_searched=tables_searched,
            total_results=len(results),
            query=request.query
        )

        logger.info(f"API: Successfully returned {len(results)} results from {len(tables_searched)} table(s)")
        return response

    except ValueError as e:
        # Invalid query or parameters
        logger.warning(f"API: Invalid request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except ConnectionError as e:
        # Database or OpenAI connection failed
        logger.error(f"API: Service connection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unavailable: {str(e)}"
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        # Unexpected error
        logger.error(f"API: Unexpected error during structured policy search: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )
