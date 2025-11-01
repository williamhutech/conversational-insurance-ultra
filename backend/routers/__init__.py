"""
Backend API Routers

Exports all router modules for FastAPI application.
"""

from backend.routers.block_4_purchase import router as purchase_router

__all__ = ["purchase_router"]
