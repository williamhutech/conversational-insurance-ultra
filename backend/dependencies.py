"""
FastAPI Dependency Injection

Provides reusable dependencies for database connections, authentication,
and service layer instances.

Usage:
    from fastapi import Depends
    from backend.dependencies import get_supabase_client

    @app.get("/endpoint")
    async def endpoint(supabase = Depends(get_supabase_client)):
        # Use supabase client
        pass
"""

from typing import Annotated
from fastapi import Depends, HTTPException, status
from backend.config import settings

# TODO: Import database clients when implemented
# from backend.database.postgres_client import SupabaseClient
# from backend.database.neo4j_client import Neo4jClient
# from backend.database.vector_client import VectorClient
# from backend.database.mem0_client import Mem0Client


# -----------------------------------------------------------------------------
# Database Dependencies
# -----------------------------------------------------------------------------

async def get_supabase_client():
    """
    Dependency for Supabase (Postgres + pgvector) client.

    Returns:
        SupabaseClient: Configured Supabase client instance

    Raises:
        HTTPException: If connection fails
    """
    # TODO: Implement connection pooling
    # TODO: Add connection health check
    # TODO: Handle connection errors gracefully

    try:
        # client = SupabaseClient(
        #     url=settings.supabase_url,
        #     key=settings.supabase_key
        # )
        # yield client
        pass
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable: {str(e)}"
        )
    # finally:
    #     await client.close()


async def get_neo4j_client():
    """
    Dependency for Neo4j graph database client.

    Returns:
        Neo4jClient: Configured Neo4j driver instance

    Raises:
        HTTPException: If connection fails
    """
    # TODO: Implement Neo4j connection with retry logic
    # TODO: Add query timeout configuration
    # TODO: Handle connection pooling

    try:
        # client = Neo4jClient(
        #     uri=settings.neo4j_uri,
        #     user=settings.neo4j_user,
        #     password=settings.neo4j_password,
        #     database=settings.neo4j_database
        # )
        # yield client
        pass
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Graph database unavailable: {str(e)}"
        )
    # finally:
    #     await client.close()


async def get_vector_client():
    """
    Dependency for vector search client (Supabase pgvector).

    Returns:
        VectorClient: Configured vector search client

    Raises:
        HTTPException: If connection fails
    """
    # TODO: Implement vector search client
    # TODO: Add embedding generation capabilities
    # TODO: Configure similarity search parameters

    try:
        # client = VectorClient(
        #     supabase_url=settings.supabase_url,
        #     supabase_key=settings.supabase_key
        # )
        # yield client
        pass
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Vector store unavailable: {str(e)}"
        )


async def get_mem0_client():
    """
    Dependency for Mem0 customer conversation memory client.

    Returns:
        Mem0Client: Configured Mem0 API client

    Raises:
        HTTPException: If connection fails
    """
    # TODO: Implement Mem0 client
    # TODO: Add session management
    # TODO: Configure memory retention policies

    try:
        # client = Mem0Client(
        #     api_key=settings.mem0_api_key,
        #     org_id=settings.mem0_org_id,
        #     project_id=settings.mem0_project_id
        # )
        # yield client
        pass
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Memory service unavailable: {str(e)}"
        )


# -----------------------------------------------------------------------------
# Service Layer Dependencies
# -----------------------------------------------------------------------------

async def get_policy_service():
    """
    Dependency for policy intelligence service.

    Provides access to policy comparison, normalization, and search.
    """
    # TODO: Implement PolicyService
    # from backend.services.policy_comparison import PolicyService
    # return PolicyService()
    pass


async def get_document_service():
    """
    Dependency for document processing service.

    Provides OCR and data extraction from uploaded documents.
    """
    # TODO: Implement DocumentService
    # from backend.services.document_processor import DocumentService
    # return DocumentService()
    pass


async def get_quotation_service():
    """
    Dependency for quotation generation service.

    Generates personalized insurance quotes based on extracted travel data.
    """
    # TODO: Implement QuotationService
    # from backend.services.quotation_generator import QuotationService
    # return QuotationService()
    pass


async def get_purchase_service():
    """
    Dependency for purchase execution service.

    Handles payment processing and policy generation.
    """
    # TODO: Implement PurchaseService
    # from backend.services.purchase_service import PurchaseService
    # return PurchaseService()
    pass


async def get_analytics_service():
    """
    Dependency for analytics and recommendation service.

    Provides data-driven recommendations based on claims data.
    """
    # TODO: Implement AnalyticsService
    # from backend.services.recommendation_engine import AnalyticsService
    # return AnalyticsService()
    pass


# -----------------------------------------------------------------------------
# Authentication Dependencies
# -----------------------------------------------------------------------------

async def get_current_user():
    """
    Dependency for user authentication.

    Validates JWT token and returns current user.

    Returns:
        dict: Current user information

    Raises:
        HTTPException: If authentication fails
    """
    # TODO: Implement JWT token validation
    # TODO: Extract user from token
    # TODO: Check user permissions

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_active_user(current_user: dict = Depends(get_current_user)):
    """
    Dependency for active user validation.

    Ensures user account is active and not suspended.
    """
    # TODO: Check user active status
    # if not current_user.get("is_active"):
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Inactive user account"
    #     )
    # return current_user
    pass


# -----------------------------------------------------------------------------
# Feature Flag Dependencies
# -----------------------------------------------------------------------------

def require_block_1():
    """Require Block 1 (Policy Intelligence) to be enabled."""
    if not settings.enable_block_1:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Policy Intelligence feature is currently disabled"
        )


def require_block_2():
    """Require Block 2 (Conversational FAQ) to be enabled."""
    if not settings.enable_block_2:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Conversational FAQ feature is currently disabled"
        )


def require_block_3():
    """Require Block 3 (Document Intelligence) to be enabled."""
    if not settings.enable_block_3:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document Intelligence feature is currently disabled"
        )


def require_block_4():
    """Require Block 4 (Purchase Execution) to be enabled."""
    if not settings.enable_block_4:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Purchase Execution feature is currently disabled"
        )


def require_block_5():
    """Require Block 5 (Data-Driven Recommendations) to be enabled."""
    if not settings.enable_block_5:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data-Driven Recommendations feature is currently disabled"
        )


# -----------------------------------------------------------------------------
# Type Aliases for Dependency Injection
# -----------------------------------------------------------------------------

# SupabaseClientDep = Annotated[SupabaseClient, Depends(get_supabase_client)]
# Neo4jClientDep = Annotated[Neo4jClient, Depends(get_neo4j_client)]
# VectorClientDep = Annotated[VectorClient, Depends(get_vector_client)]
# Mem0ClientDep = Annotated[Mem0Client, Depends(get_mem0_client)]
# CurrentUserDep = Annotated[dict, Depends(get_current_user)]
