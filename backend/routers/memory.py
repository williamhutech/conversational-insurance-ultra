"""
Memory API Router

REST API endpoints for memory management.
Handles conversation memory, user preferences, and context management.

Endpoints:
    POST   /api/v1/memory/add           - Add new memory
    POST   /api/v1/memory/search        - Search memories
    GET    /api/v1/memory/{user_id}     - Get all memories for user
    DELETE /api/v1/memory/{memory_id}   - Delete specific memory
    GET    /api/v1/memory/{user_id}/count - Get memory count for user
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from backend.dependencies import get_memory_service
from backend.services.memory_service import MemoryService
from backend.models.memory import (
    AddMemoryRequest,
    AddMemoryResponse,
    SearchMemoryRequest,
    SearchMemoryResponse,
    GetMemoriesResponse,
    DeleteMemoryResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/memory",
    tags=["memory"],
    responses={
        404: {"description": "Memory not found"},
        500: {"description": "Internal server error"}
    }
)


@router.post(
    "/add",
    response_model=AddMemoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add new memory",
    description="Store conversation messages as user memory. Mem0 automatically extracts and stores relevant information."
)
async def add_memory(
    request: AddMemoryRequest,
    service: MemoryService = Depends(get_memory_service)
) -> AddMemoryResponse:
    """
    Add new memory for a user from conversation messages.

    The LLM decides what conversations to store. Mem0 will automatically:
    - Extract key information from messages
    - Deduplicate similar memories
    - Store with timestamps

    Example request:
        ```json
        {
            "user_id": "alice_123",
            "messages": [
                {
                    "role": "user",
                    "content": "I prefer travel insurance with high medical coverage"
                },
                {
                    "role": "assistant",
                    "content": "I'll remember your preference"
                }
            ],
            "metadata": {
                "type": "preference"
            }
        }
        ```
    """
    try:
        logger.info(f"API: Adding memory for user {request.user_id}")
        return await service.add_memory(request)
    except Exception as e:
        logger.error(f"API: Failed to add memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add memory: {str(e)}"
        )


@router.post(
    "/search",
    response_model=SearchMemoryResponse,
    summary="Search memories",
    description="Semantic search for relevant memories using natural language query."
)
async def search_memories(
    request: SearchMemoryRequest,
    service: MemoryService = Depends(get_memory_service)
) -> SearchMemoryResponse:
    """
    Search user memories using semantic similarity.

    Uses AI-powered semantic search to find relevant memories
    based on the meaning of the query, not just keywords.

    Example request:
        ```json
        {
            "user_id": "alice_123",
            "query": "insurance preferences",
            "limit": 5
        }
        ```

    Returns memories ranked by relevance score.
    """
    try:
        logger.info(f"API: Searching memories for user {request.user_id}")
        return await service.search_memories(request)
    except Exception as e:
        logger.error(f"API: Failed to search memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search memories: {str(e)}"
        )


@router.get(
    "/{user_id}",
    response_model=GetMemoriesResponse,
    summary="Get all memories",
    description="Retrieve all memories for a specific user."
)
async def get_all_memories(
    user_id: str,
    service: MemoryService = Depends(get_memory_service)
) -> GetMemoriesResponse:
    """
    Get all memories for a user.

    Returns all stored memories in chronological order.
    Useful for:
    - Showing user what's remembered
    - Memory management UI
    - Exporting user data (GDPR compliance)
    """
    try:
        logger.info(f"API: Getting all memories for user {user_id}")
        return await service.get_all_memories(user_id)
    except Exception as e:
        logger.error(f"API: Failed to get memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get memories: {str(e)}"
        )


@router.delete(
    "/{memory_id}",
    response_model=DeleteMemoryResponse,
    summary="Delete memory",
    description="Delete a specific memory by ID."
)
async def delete_memory(
    memory_id: str,
    service: MemoryService = Depends(get_memory_service)
) -> DeleteMemoryResponse:
    """
    Delete a specific memory.

    Use cases:
    - User requests to forget specific information
    - LLM identifies outdated/incorrect memory
    - GDPR compliance (right to be forgotten)

    Example:
        DELETE /api/v1/memory/892db2ae-06d9-49e5-8b3e-585ef9b85b8e
    """
    try:
        logger.info(f"API: Deleting memory {memory_id}")
        return await service.delete_memory(memory_id)
    except Exception as e:
        logger.error(f"API: Failed to delete memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete memory: {str(e)}"
        )


@router.get(
    "/{user_id}/count",
    response_model=dict,
    summary="Get memory count",
    description="Get the total number of memories for a user."
)
async def get_memory_count(
    user_id: str,
    service: MemoryService = Depends(get_memory_service)
) -> dict:
    """
    Get memory count for a user.

    Returns:
        ```json
        {
            "user_id": "alice_123",
            "count": 15
        }
        ```
    """
    try:
        logger.info(f"API: Getting memory count for user {user_id}")
        count = await service.get_memory_count(user_id)
        return {
            "user_id": user_id,
            "count": count
        }
    except Exception as e:
        logger.error(f"API: Failed to get memory count: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get memory count: {str(e)}"
        )
