"""
Memory Service

Business logic for memory management operations.
Handles conversation memory, user preferences, and context management.

Usage:
    from backend.services.memory_service import MemoryService

    service = MemoryService(mem0_client)
    result = await service.add_memory(request)
"""

import logging
from typing import List, Dict, Any

from backend.database.mem0_client import Mem0Client
from backend.models.memory import (
    AddMemoryRequest,
    AddMemoryResponse,
    SearchMemoryRequest,
    SearchMemoryResponse,
    GetMemoriesResponse,
    DeleteMemoryResponse,
    MemoryResult,
)

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Service layer for memory management.

    Coordinates between API layer and Mem0 client.
    Handles validation, transformation, and error handling.
    """

    def __init__(self, mem0_client: Mem0Client):
        """
        Initialize memory service.

        Args:
            mem0_client: Mem0 client instance
        """
        self.mem0_client = mem0_client
        logger.info("MemoryService initialized")

    async def add_memory(
        self,
        request: AddMemoryRequest
    ) -> AddMemoryResponse:
        """
        Add new memory for user from conversation messages.

        Args:
            request: Memory addition request with user_id and messages

        Returns:
            Response with created memory IDs and content

        Raises:
            Exception: If memory creation fails
        """
        logger.info(f"Adding memory for user {request.user_id}")

        try:
            # Convert Pydantic models to dicts for Mem0 API
            messages = [msg.model_dump() for msg in request.messages]

            # Call Mem0 client
            result = await self.mem0_client.add_memory(
                user_id=request.user_id,
                messages=messages,
                metadata=request.metadata
            )

            logger.info(
                f"Successfully added {len(result.get('results', []))} "
                f"memories for user {request.user_id}"
            )

            return AddMemoryResponse(results=result.get('results', []))

        except Exception as e:
            logger.error(f"Failed to add memory for user {request.user_id}: {e}")
            raise

    async def search_memories(
        self,
        request: SearchMemoryRequest
    ) -> SearchMemoryResponse:
        """
        Search user memories using semantic similarity.

        Args:
            request: Search request with user_id, query, and limit

        Returns:
            Response with matching memories and scores

        Raises:
            Exception: If search fails
        """
        logger.info(
            f"Searching memories for user {request.user_id} "
            f"with query '{request.query}'"
        )

        try:
            # Call Mem0 client
            memories = await self.mem0_client.search_memories(
                user_id=request.user_id,
                query=request.query,
                limit=request.limit
            )

            # Convert to Pydantic models
            results = [MemoryResult(**mem) for mem in memories]

            logger.info(
                f"Found {len(results)} memories for user {request.user_id}"
            )

            return SearchMemoryResponse(
                results=results,
                total=len(results)
            )

        except Exception as e:
            logger.error(
                f"Failed to search memories for user {request.user_id}: {e}"
            )
            raise

    async def get_all_memories(
        self,
        user_id: str
    ) -> GetMemoriesResponse:
        """
        Get all memories for a user.

        Args:
            user_id: User identifier

        Returns:
            Response with all user memories

        Raises:
            Exception: If retrieval fails
        """
        logger.info(f"Getting all memories for user {user_id}")

        try:
            # Call Mem0 client
            memories = await self.mem0_client.get_all_memories(user_id=user_id)

            # Convert to Pydantic models
            results = [MemoryResult(**mem) for mem in memories]

            logger.info(
                f"Retrieved {len(results)} memories for user {user_id}"
            )

            return GetMemoriesResponse(
                results=results,
                total=len(results)
            )

        except Exception as e:
            logger.error(f"Failed to get memories for user {user_id}: {e}")
            raise

    async def delete_memory(
        self,
        memory_id: str
    ) -> DeleteMemoryResponse:
        """
        Delete a specific memory by ID.

        Args:
            memory_id: Memory identifier to delete

        Returns:
            Response with deletion status

        Raises:
            Exception: If deletion fails
        """
        logger.info(f"Deleting memory {memory_id}")

        try:
            # Call Mem0 client
            success = await self.mem0_client.delete_memory(memory_id=memory_id)

            logger.info(f"Successfully deleted memory {memory_id}")

            return DeleteMemoryResponse(
                success=success,
                memory_id=memory_id,
                message="Memory deleted successfully"
            )

        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            raise

    async def get_memory_count(self, user_id: str) -> int:
        """
        Get count of memories for a user.

        Args:
            user_id: User identifier

        Returns:
            Number of memories

        Raises:
            Exception: If retrieval fails
        """
        logger.info(f"Getting memory count for user {user_id}")

        try:
            memories = await self.mem0_client.get_all_memories(user_id=user_id)
            count = len(memories)

            logger.info(f"User {user_id} has {count} memories")
            return count

        except Exception as e:
            logger.error(f"Failed to get memory count for user {user_id}: {e}")
            raise
