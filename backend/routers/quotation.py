"""
Quotation Router

Handles quotation generation via Ancileo API and storage in Supabase.
Provides endpoints for generating quotations and managing selections.

Routes:
    POST /api/quotation/generate - Generate quotation via Ancileo API
    POST /api/selection/create - Create selection record
    GET /api/selection/payment/{payment_id} - Get selection by payment_id
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field

from backend.services.ancileo_client import AncileoClient
from backend.database.postgres_client import SupabaseClient, get_supabase

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/quotation",
    tags=["Block 3: Auto-Quotation"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)


# =============================================================================
# Request/Response Models
# =============================================================================

class GenerateQuotationRequest(BaseModel):
    """Request to generate a quotation."""
    customer_id: str = Field(..., description="Customer ID")
    trip_type: str = Field(..., description="Trip type: RT or ST")
    departure_date: str = Field(..., description="Departure date: YYYY-MM-DD")
    return_date: Optional[str] = Field(None, description="Return date: YYYY-MM-DD (required for RT)")
    departure_country: str = Field(default="SG", description="Departure country ISO code")
    arrival_country: str = Field(default="CN", description="Arrival country ISO code")
    adults_count: int = Field(default=1, gt=0, description="Number of adults")
    children_count: int = Field(default=0, ge=0, description="Number of children")
    market: str = Field(default="SG", description="Market code")
    language_code: str = Field(default="en", description="Language code")
    channel: str = Field(default="white-label", description="Distribution channel")


class GenerateQuotationResponse(BaseModel):
    """Response after generating quotation."""
    quotation_id: str  # This is now the Ancileo quote ID directly
    offers: list[Dict[str, Any]]
    trip_summary: Dict[str, Any]
    created_at: str
    expires_at: Optional[str] = None


class CreateSelectionRequest(BaseModel):
    """Request to create a selection record."""
    user_id: str
    quote_id: str
    selected_offer_id: str
    payment_id: Optional[str] = None
    insureds: Optional[list[Dict[str, Any]]] = None
    main_contact: Optional[Dict[str, Any]] = None
    product_type: str = Field(default="travel-insurance")
    quantity: int = Field(default=1)
    total_price: Optional[float] = None
    is_send_email: bool = Field(default=True)


class CreateSelectionResponse(BaseModel):
    """Response after creating selection."""
    selection_id: str
    quote_id: str
    payment_id: Optional[str] = None
    status: str
    created_at: str


# =============================================================================
# Quotation Endpoints
# =============================================================================

@router.post(
    "/generate",
    response_model=GenerateQuotationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Quotation",
    description="Generate insurance quotation via Ancileo API and save to database"
)
async def generate_quotation(
    request: GenerateQuotationRequest
) -> GenerateQuotationResponse:
    """
    Generate quotation via Ancileo API and save to Supabase.
    
    Args:
        request: Quotation generation request
    
    Returns:
        GenerateQuotationResponse with quotation details
    """
    try:
        logger.info(f"Generating quotation for customer {request.customer_id}")
        
        # Initialize clients
        ancileo_client = AncileoClient()
        supabase_client = await get_supabase()
        
        # Step 1: Call Ancileo Quotation API
        ancileo_response = await ancileo_client.get_quotation(
            trip_type=request.trip_type,
            departure_date=request.departure_date,
            return_date=request.return_date,
            departure_country=request.departure_country,
            arrival_country=request.arrival_country,
            adults_count=request.adults_count,
            children_count=request.children_count,
            market=request.market,
            language_code=request.language_code,
            channel=request.channel
        )
        
        # Step 2: Extract data from Ancileo response
        ancileo_quote_id = ancileo_response.get('id')
        if not ancileo_quote_id:
            raise ValueError("Ancileo response missing 'id' field")
        
        offer_categories = ancileo_response.get('offerCategories', [])
        offers = offer_categories[0].get('offers', []) if offer_categories else []
        
        # Step 3: Save to Supabase quotes table
        # Use Ancileo quote ID directly as quote_id (no internal ID generation)
        quote_id = ancileo_quote_id
        
        quotation_data = {
            'quote_id': quote_id,  # Directly use Ancileo quote ID
            'user_id': request.customer_id,
            'trip_type': request.trip_type,
            'departure_date': request.departure_date,
            'return_date': request.return_date,
            'departure_country': request.departure_country,
            'arrival_country': request.arrival_country,
            'adults_count': request.adults_count,
            'children_count': request.children_count,
            'offer_id': None,  # Will be set when user selects
            'product_code': offers[0].get('productCode') if offers else None,
            'unit_price': float(offers[0].get('unitPrice', 0)) if offers else 0,
            'currency': offers[0].get('currency', 'SGD') if offers else 'SGD',
            'quotation_response': ancileo_response,
            'market': request.market,
            'language_code': request.language_code,
            'channel': request.channel,
            'status': 'active'
        }
        
        # Save to Supabase
        response = supabase_client.client.table('quotes').insert(quotation_data).execute()
        saved_quote = response.data[0] if response.data else quotation_data
        
        logger.info(f"Quotation saved: quote_id={quote_id} (Ancileo ID)")
        
        # Format offers for response
        formatted_offers = []
        for offer in offers:
            formatted_offers.append({
                'id': offer.get('id'),
                'product_code': offer.get('productCode'),
                'unit_price': offer.get('unitPrice'),
                'currency': offer.get('currency'),
                'cover_dates': offer.get('coverDates', {}),
                'product_information': offer.get('productInformation', {})
            })
        
        return GenerateQuotationResponse(
            quotation_id=quote_id,  # This is the Ancileo quote ID
            offers=formatted_offers,
            trip_summary={
                "trip_type": request.trip_type,
                "departure_date": request.departure_date,
                "return_date": request.return_date,
                "departure_country": request.departure_country,
                "arrival_country": request.arrival_country,
                "adults_count": request.adults_count,
                "children_count": request.children_count
            },
            created_at=saved_quote.get('created_at'),
            expires_at=saved_quote.get('expires_at')
        )
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating quotation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate quotation: {str(e)}"
        )


# =============================================================================
# Selection Endpoints
# =============================================================================

@router.post(
    "/selection/create",
    response_model=CreateSelectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Selection",
    description="Create selection record linking quotation, offer, and payment"
)
async def create_selection(
    request: CreateSelectionRequest
) -> CreateSelectionResponse:
    """
    Create selection record.
    
    Args:
        request: Selection creation request
    
    Returns:
        CreateSelectionResponse with selection details
    """
    try:
        logger.info(f"Creating selection for quote {request.quote_id}")
        
        # Initialize Supabase client
        supabase_client = await get_supabase()
        
        # Get quotation to extract offer info
        # Note: request.quote_id is now the Ancileo quote ID directly
        quotation = await supabase_client.get_quotation_with_offers(request.quote_id)
        if not quotation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quotation {request.quote_id} not found"
            )
        
        # Find selected offer
        offers = quotation.get('offers', [])
        selected_offer = next((o for o in offers if o.get('id') == request.selected_offer_id), None)
        
        # Build selection data
        # Note: quote_id is the Ancileo quote ID, no need for separate ancileo_quote_id field
        selection_data = {
            'user_id': request.user_id,
            'quote_id': request.quote_id,  # This is the Ancileo quote ID
            'payment_id': request.payment_id,
            'selected_offer_id': request.selected_offer_id,
            'selected_product_code': selected_offer.get('productCode') if selected_offer else None,
            'product_type': request.product_type,
            'quantity': request.quantity,
            'total_price': request.total_price,
            'is_send_email': request.is_send_email,
            'status': 'pending_payment' if request.payment_id else 'draft'
        }
        
        if request.insureds:
            selection_data['insureds'] = request.insureds
        if request.main_contact:
            selection_data['main_contact'] = request.main_contact
        
        # Create selection
        selection = await supabase_client.create_selection(selection_data)
        
        return CreateSelectionResponse(
            selection_id=selection['selection_id'],
            quote_id=selection['quote_id'],
            payment_id=selection.get('payment_id'),
            status=selection['status'],
            created_at=selection['created_at']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating selection: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create selection: {str(e)}"
        )


@router.get(
    "/selection/payment/{payment_id}",
    summary="Get Selection by Payment ID",
    description="Get selection record with quotation data by payment_id"
)
async def get_selection_by_payment_id(
    payment_id: str
) -> Dict[str, Any]:
    """
    Get selection by payment_id.
    
    Args:
        payment_id: Payment intent ID
    
    Returns:
        Selection record with quotation data
    """
    try:
        supabase_client = await get_supabase()
        selection = await supabase_client.get_selection_by_payment_id(payment_id)
        
        if not selection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Selection not found for payment {payment_id}"
            )
        
        return selection
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting selection: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get selection: {str(e)}"
        )

