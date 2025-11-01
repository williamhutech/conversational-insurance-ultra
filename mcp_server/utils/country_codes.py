"""
Country Code Utilities for MCP Server

Handles conversion between natural language country names and ISO 2-letter codes
for Ancileo Travel Insurance API integration.

This module is independent and can be used without backend dependencies.
"""

from typing import Dict


# =============================================================================
# Ancileo Supported Countries Mapping
# =============================================================================
# Maps natural language country names to ISO 2-letter codes
# Based on Ancileo's supported countries list from their API documentation

ANCILEO_COUNTRY_MAP: Dict[str, str] = {
    # =========================================================================
    # ASIA REGION
    # =========================================================================
    # Australia
    "AUSTRALIA": "AU",
    "AU": "AU",
    
    # China
    "CHINA": "CN",
    "CN": "CN",
    "PEOPLE'S REPUBLIC OF CHINA": "CN",
    
    # Hong Kong
    "HONG KONG": "HK",
    "HK": "HK",
    "HONGKONG": "HK",
    
    # India
    "INDIA": "IN",
    "IN": "IN",
    
    # Indonesia
    "INDONESIA": "ID",
    "ID": "ID",
    
    # Israel
    "ISRAEL": "IL",
    "IL": "IL",
    
    # Japan
    "JAPAN": "JP",
    "JP": "JP",
    
    # Laos
    "LAOS": "LA",
    "LA": "LA",
    "LAO": "LA",
    
    # Macau
    "MACAU": "MO",
    "MO": "MO",
    "MACAO": "MO",
    
    # Malaysia
    "MALAYSIA": "MY",
    "MY": "MY",
    
    # Philippines
    "PHILIPPINES": "PH",
    "PH": "PH",
    "PHILIPPINE": "PH",
    
    # Saudi Arabia
    "SAUDI ARABIA": "SA",
    "SA": "SA",
    "SAUDI": "SA",
    
    # Singapore
    "SINGAPORE": "SG",
    "SG": "SG",
    
    # South Korea
    "SOUTH KOREA": "KR",
    "KR": "KR",
    "KOREA": "KR",
    "REPUBLIC OF KOREA": "KR",
    
    # Taiwan
    "TAIWAN": "TW",
    "TW": "TW",
    
    # Thailand
    "THAILAND": "TH",
    "TH": "TH",
    
    # Vietnam
    "VIETNAM": "VT",
    "VT": "VT",
    "VIET NAM": "VT",
    
    # =========================================================================
    # INTERNATIONAL REGION
    # =========================================================================
    # Albania
    "ALBANIA": "AL",
    "AL": "AL",
    
    # Belgium
    "BELGIUM": "BE",
    "BE": "BE",
    
    # Bulgaria
    "BULGARIA": "BG",
    "BG": "BG",
    
    # Cyprus
    "CYPRUS": "CY",
    "CY": "CY",
    "REPUBLIC OF CYPRUS": "CY",
    
    # Denmark
    "DENMARK": "DK",
    "DK": "DK",
    
    # Egypt
    "EGYPT": "EG",
    "EG": "EG",
    
    # France
    "FRANCE": "FR",
    "FR": "FR",
    
    # Germany
    "GERMANY": "DE",
    "DE": "DE",
    
    # Greece
    "GREECE": "GR",
    "GR": "GR",
    
    # Italy
    "ITALY": "IT",
    "IT": "IT",
    
    # Romania
    "ROMANIA": "RO",
    "RO": "RO",
    
    # Russian Federation
    "RUSSIAN FEDERATION": "RU",
    "RU": "RU",
    "RUSSIA": "RU",
    
    # Spain
    "SPAIN": "ES",
    "ES": "ES",
    
    # Sweden
    "SWEDEN": "SE",
    "SE": "SE",
    
    # Switzerland
    "SWITZERLAND": "CH",
    "CH": "CH",
    
    # Turkey
    "TURKEY": "TR",
    "TR": "TR",
    
    # United Kingdom
    "UNITED KINGDOM": "GB",
    "GB": "GB",
    "UK": "GB",
    "GREAT BRITAIN": "GB",
    "BRITAIN": "GB",
}


def normalize_country_code(country_input: str) -> str | None:
    """
    Normalize country input to ISO 2-letter code for Ancileo API.
    
    Supports multiple formats:
    - ISO codes: "GR", "JP", "AU"
    - Full names: "Greece", "Japan", "Australia"
    - Common aliases: "UK", "Hong Kong", "Saudi Arabia"
    - Case insensitive
    
    Args:
        country_input: Country name or code in any format
    
    Returns:
        Standardized ISO 2-letter code (e.g., "GR"), or None if not found
    
    Examples:
        >>> normalize_country_code("Greece")
        'GR'
        >>> normalize_country_code("GR")
        'GR'
        >>> normalize_country_code("greece")
        'GR'
        >>> normalize_country_code("UK")
        'GB'
        >>> normalize_country_code("Unknown")
        None
    """
    if not country_input:
        return None
    
    # Normalize input: uppercase and strip whitespace
    normalized = country_input.strip().upper()
    
    # Direct lookup
    return ANCILEO_COUNTRY_MAP.get(normalized)


def get_supported_countries() -> list[str]:
    """
    Get list of all supported country names.
    
    Returns:
        List of primary country names (full names)
    
    Examples:
        >>> countries = get_supported_countries()
        >>> "GREECE" in countries
        True
        >>> "UNITED KINGDOM" in countries
        True
    """
    countries = []
    seen_codes = set()
    
    for name, code in ANCILEO_COUNTRY_MAP.items():
        # Only include primary names (uppercase full names, not aliases)
        if name == name.upper() and code not in seen_codes:
            if len(name) > 2:  # It's a name, not a code
                countries.append(name.title())
                seen_codes.add(code)
    
    return sorted(countries)


def is_supported_country(country_input: str) -> bool:
    """
    Check if a country is supported by Ancileo.
    
    Args:
        country_input: Country name or code
    
    Returns:
        True if supported, False otherwise
    
    Examples:
        >>> is_supported_country("Greece")
        True
        >>> is_supported_country("GR")
        True
        >>> is_supported_country("Unknown")
        False
    """
    return normalize_country_code(country_input) is not None


def get_suggested_countries(query: str = "") -> list[str]:
    """
    Get list of supported country names for suggestions.
    
    Filters countries by search query (case-insensitive).
    
    Args:
        query: Optional search query to filter countries
    
    Returns:
        List of supported country names matching the query
    
    Examples:
        >>> get_suggested_countries("gr")
        ['Germany', 'Greece']
        >>> get_suggested_countries("united")
        ['United Kingdom']
    """
    all_countries = get_supported_countries()
    
    if not query:
        return all_countries
    
    query_upper = query.upper()
    return [c for c in all_countries if query_upper in c.upper()]

