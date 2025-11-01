"""
Ancileo API Client Service

Handles communication with Ancileo Travel Insurance API:
- Quotation endpoint: /v1/travel/front/pricing
- Purchase endpoint: /v1/travel/front/purchase

Usage:
    from backend.services.ancileo_client import AncileoClient
    
    client = AncileoClient()
    quotation = await client.get_quotation(...)
    purchase = await client.complete_purchase(...)
"""

import logging
from typing import Dict, Any, Optional, List
import httpx
from backend.config import settings

logger = logging.getLogger(__name__)


class AncileoClient:
    """Client for Ancileo Travel Insurance API."""
    
    def __init__(self):
        """Initialize Ancileo client with API key."""
        # Remove trailing /v1/travel/front if present, we'll add it in each endpoint
        base_url = settings.insurance_api_base_url.rstrip('/')
        if base_url.endswith('/v1/travel/front'):
            base_url = base_url[:-16]  # Remove '/v1/travel/front'
        self.base_url = base_url
        self.api_key = settings.insurance_api_key
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key
        }
    
    async def get_quotation(
        self,
        trip_type: str,  # "RT" or "ST"
        departure_date: str,  # YYYY-MM-DD
        return_date: Optional[str],  # YYYY-MM-DD (required for RT)
        departure_country: str,
        arrival_country: str,
        adults_count: int,
        children_count: int = 0,
        market: str = "SG",
        language_code: str = "en",
        channel: str = "white-label",
        device_type: str = "DESKTOP"
    ) -> Dict[str, Any]:
        """
        Get insurance quotation from Ancileo API.
        
        Args:
            trip_type: "RT" (Round Trip) or "ST" (Single Trip)
            departure_date: Departure date in YYYY-MM-DD format
            return_date: Return date in YYYY-MM-DD format (required for RT)
            departure_country: ISO country code (e.g., "SG")
            arrival_country: ISO country code (e.g., "CN")
            adults_count: Number of adults
            children_count: Number of children (default: 0)
            market: Market code (default: "SG")
            language_code: Language preference (default: "en")
            channel: Distribution channel (default: "white-label")
            device_type: Device type (default: "DESKTOP")
        
        Returns:
            Dictionary with Ancileo quotation response:
            - id: Quote ID (UUID) - this is ancileo_quote_id
            - languageCode: Language code
            - offerCategories: List of offer categories with offers
        
        Raises:
            ValueError: If return_date is missing for RT trip type
            httpx.HTTPStatusError: If API request fails
        """
        if trip_type == "RT" and not return_date:
            raise ValueError("returnDate is required for round trip (RT)")
        
        payload = {
            "market": market,
            "languageCode": language_code,
            "channel": channel,
            "deviceType": device_type,
            "context": {
                "tripType": trip_type,
                "departureDate": departure_date,
                "departureCountry": departure_country,
                "arrivalCountry": arrival_country,
                "adultsCount": adults_count,
                "childrenCount": children_count
            }
        }
        
        # Add returnDate for round trip
        if trip_type == "RT":
            payload["context"]["returnDate"] = return_date
        
        url = f"{self.base_url}/v1/travel/front/pricing"
        
        logger.info(
            f"Calling Ancileo Quotation API: {trip_type} "
            f"{departure_date} -> {arrival_country} "
            f"({adults_count} adults, {children_count} children)"
        )
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                result = response.json()
                
                logger.info(
                    f"Ancileo Quotation API success: quote_id={result.get('id')}, "
                    f"offers_count={len(result.get('offerCategories', [{}])[0].get('offers', []))}"
                )
                
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Ancileo Quotation API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Ancileo Quotation API unexpected error: {e}")
            raise
    
    async def complete_purchase(
        self,
        quote_id: str,
        purchase_offers: List[Dict[str, Any]],
        insureds: List[Dict[str, Any]],
        main_contact: Dict[str, Any],
        market: str = "SG",
        language_code: str = "en",
        channel: str = "white-label"
    ) -> Dict[str, Any]:
        """
        Complete purchase after payment via Ancileo Purchase API.
        
        Args:
            quote_id: Quote ID from quotation response (ancileo_quote_id)
            purchase_offers: List of offers to purchase with format:
                [{
                    "productType": "travel-insurance",
                    "offerId": "uuid",
                    "productCode": "SG_AXA_SCOOT_COMP",
                    "unitPrice": 17.6,
                    "currency": "SGD",
                    "quantity": 1,
                    "totalPrice": 17.6,
                    "isSendEmail": true
                }]
            insureds: List of insured persons with format:
                [{
                    "id": "1",
                    "title": "Mr",
                    "firstName": "John",
                    "lastName": "Doe",
                    "nationality": "SG",
                    "dateOfBirth": "2000-01-01",
                    "passport": "123456",
                    "email": "john.doe@gmail.com",
                    "phoneType": "mobile",
                    "phoneNumber": "081111111",
                    "relationship": "main"
                }]
            main_contact: Main contact object (includes all insured fields + address):
                {
                    "id": "1",
                    "title": "Mr",
                    "firstName": "John",
                    "lastName": "Doe",
                    "nationality": "SG",
                    "dateOfBirth": "2000-01-01",
                    "passport": "123456",
                    "email": "john.doe@gmail.com",
                    "phoneType": "mobile",
                    "phoneNumber": "081111111",
                    "address": "12 test test 12",
                    "city": "SG",
                    "zipCode": "12345",
                    "countryCode": "SG"
                }
            market: Market code (default: "SG")
            language_code: Language preference (default: "en")
            channel: Distribution channel (default: "white-label")
        
        Returns:
            Dictionary with Ancileo purchase response:
            - id: Purchase ID (UUID) - this is ancileo_purchase_id
            - quoteId: Quote ID
            - purchasedOffers: List of purchased offers
        
        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        payload = {
            "market": market,
            "languageCode": language_code,
            "channel": channel,
            "quoteId": quote_id,
            "purchaseOffers": purchase_offers,
            "insureds": insureds,
            "mainContact": main_contact
        }
        
        url = f"{self.base_url}/v1/travel/front/purchase"
        
        logger.info(
            f"Calling Ancileo Purchase API: quote_id={quote_id}, "
            f"offers_count={len(purchase_offers)}, insureds_count={len(insureds)}"
        )
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                result = response.json()
                
                logger.info(
                    f"Ancileo Purchase API success: purchase_id={result.get('id')}, "
                    f"quote_id={result.get('quoteId')}"
                )
                
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Ancileo Purchase API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Ancileo Purchase API unexpected error: {e}")
            raise


# Global service instance (optional)
_ancileo_client: Optional[AncileoClient] = None


def get_ancileo_client() -> AncileoClient:
    """
    Get or create global Ancileo client instance.
    
    Returns:
        AncileoClient: Configured client instance
    """
    global _ancileo_client
    if _ancileo_client is None:
        _ancileo_client = AncileoClient()
    return _ancileo_client

