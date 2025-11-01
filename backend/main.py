"""
FastAPI Backend Application

Main entry point for the Conversational Insurance Ultra backend API.
Provides REST endpoints for all 5 blocks of functionality.

Run with:
    uvicorn backend.main:app --reload
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from backend.config import settings
from backend.routers import purchase_router
from backend.routers.memory import router as memory_router
from backend.routers.widgets import router as widgets_router
from backend.routers.concept_search import router as concept_search_router
from backend.routers.structured_policy import router as structured_policy_router
from backend.services.payment.stripe_webhook import app as webhook_app
from backend.services.payment.payment_pages import app as pages_app

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")

    # TODO: Initialize database connections
    # - Supabase client
    # - Neo4j driver
    # - Mem0 client
    # - Vector store

    # TODO: Load taxonomy data if enabled
    if settings.seed_database:
        logger.info("Database seeding enabled")
        # await seed_taxonomy()
        # await seed_policies()

    yield

    # Shutdown
    logger.info("Shutting down application")
    # TODO: Close database connections
    # - await supabase_client.close()
    # - await neo4j_driver.close()


# Initialize FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="AI-powered conversational insurance platform with FastMCP and FastAPI",
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# Health Check Endpoints
# -----------------------------------------------------------------------------

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "operational",
        "blocks": {
            "block_1_policy_intelligence": settings.enable_block_1,
            "block_2_conversational_faq": settings.enable_block_2,
            "block_3_document_intelligence": settings.enable_block_3,
            "block_4_purchase_execution": settings.enable_block_4,
            "block_5_data_driven_recommendations": settings.enable_block_5,
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    # TODO: Add actual health checks for:
    # - Database connectivity (Supabase, Neo4j)
    # - External services (Mem0, Stripe, Anthropic)
    # - Redis/cache availability
    return {
        "status": "healthy",
        "checks": {
            "api": "ok",
            # "database": "ok",
            # "neo4j": "ok",
            # "vector_store": "ok",
            # "mem0": "ok",
        }
    }


# -----------------------------------------------------------------------------
# API Routers
# -----------------------------------------------------------------------------

# Block 4: Purchase Execution
app.include_router(
    purchase_router,
    prefix="/api"
)

# Memory Management (supports all blocks)
app.include_router(memory_router)

# Concept Search - Neo4j semantic search with MemOS
app.include_router(concept_search_router)

# Structured Policy Search - Intelligent routing with vector search
app.include_router(structured_policy_router)

# Widget Router - Serves OpenAI Apps SDK widgets
app.include_router(widgets_router)

# Mount Payment Webhook Handler (separate FastAPI app for isolation)
app.mount("/webhook", webhook_app)

# Mount Payment Pages (success/cancel pages)
app.mount("", pages_app)

# TODO: Add routers for other blocks when implemented
# Block 1: Policy Intelligence Engine
# app.include_router(
#     policies.router,
#     prefix="/api/v1/policies",
#     tags=["Block 1: Policy Intelligence"]
# )

# Block 2 & 3: Documents & Quotations
# app.include_router(
#     documents.router,
#     prefix="/api/v1/documents",
#     tags=["Block 3: Document Intelligence"]
# )
#
# app.include_router(
#     quotations.router,
#     prefix="/api/v1/quotations",
#     tags=["Block 3: Auto-Quotation"]
# )

# Block 5: Analytics & Recommendations
# app.include_router(
#     analytics.router,
#     prefix="/api/v1/analytics",
#     tags=["Block 5: Data-Driven Recommendations"]
# )


# -----------------------------------------------------------------------------
# Error Handlers
# -----------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.debug else "An unexpected error occurred",
        }
    )


# TODO: Add specific exception handlers for:
# - ValidationError (422)
# - HTTPException (custom status codes)
# - DatabaseError (503)
# - ExternalServiceError (502)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.backend_reload,
        log_level=settings.log_level.lower(),
    )
