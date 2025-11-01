"""
Widget Router - Serves built OpenAI Apps SDK widgets
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/widgets", tags=["widgets"])

# Path to built widgets (relative to backend/)
WIDGETS_DIR = Path(__file__).parent.parent.parent.parent / "widgets"


@router.get("/payment-widget.html")
async def serve_payment_widget():
    """
    Serve the built payment widget HTML/JS bundle

    This is referenced in MCP tool responses via:
    _meta.openai/outputTemplate: "http://localhost:8085/widgets/payment-widget.html"
    """
    widget_path = WIDGETS_DIR / "payment" / "dist" / "index.html"

    if not widget_path.exists():
        logger.error(f"Payment widget not found at {widget_path}")
        raise HTTPException(
            status_code=404,
            detail="Payment widget not built. Run 'cd widgets/payment && npm run build'"
        )

    return FileResponse(
        path=widget_path,
        media_type="text/html",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )


@router.get("/payment-widget.js")
async def serve_payment_widget_js():
    """
    Serve the built payment widget JavaScript bundle
    """
    js_path = WIDGETS_DIR / "payment" / "dist" / "payment-widget.js"

    if not js_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Payment widget JS not found. Run 'cd widgets/payment && npm run build'"
        )

    return FileResponse(
        path=js_path,
        media_type="application/javascript",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )


@router.get("/health")
async def widget_health():
    """
    Health check endpoint for widget serving
    """
    payment_widget_exists = (WIDGETS_DIR / "payment" / "dist" / "index.html").exists()

    return {
        "status": "healthy",
        "widgets": {
            "payment": {
                "built": payment_widget_exists,
                "path": str(WIDGETS_DIR / "payment" / "dist")
            }
        }
    }


@router.options("/{path:path}")
async def options_handler(path: str):
    """
    Handle CORS preflight requests
    """
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )
