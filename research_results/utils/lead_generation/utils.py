"""
Utility functions for lead generation module.
"""

import re
from typing import List, Set
from .models import BusinessData


def normalize_prague_address(address: str) -> str:
    """
    Normalize Prague address format.

    Args:
        address: Raw address string

    Returns:
        Normalized address string
    """
    if not address:
        return ""

    # Remove extra whitespace
    normalized = re.sub(r"\s+", " ", address.strip())

    # Normalize common patterns
    normalized = re.sub(r"\bPrague\b", "Praha", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bPrague\b", "Praha", normalized, flags=re.IGNORECASE)

    # Normalize district names
    district_patterns = [
        (r"\bPrague\s*(\d+)\b", r"Praha \1"),
        (r"\bPraha\s*(\d+)\b", r"Praha \1"),
    ]

    for pattern, replacement in district_patterns:
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

    return normalized


def validate_czech_phone(phone: str) -> bool:
    """
    Validate Czech phone number format.

    Args:
        phone: Phone number string

    Returns:
        True if valid Czech phone number, False otherwise
    """
    if not phone:
        return False

    # Remove spaces, dashes, parentheses
    cleaned = re.sub(r"[\s\-\(\)]", "", phone)

    # Czech phone formats:
    # +420 XXX XXX XXX (international)
    # 420 XXX XXX XXX (without +)
    # XXX XXX XXX (local, without country code)
    if cleaned.startswith("+420"):
        cleaned = cleaned[4:]
    elif cleaned.startswith("420"):
        cleaned = cleaned[3:]

    # Should be 9 digits for Czech numbers
    return bool(re.match(r"^\d{9}$", cleaned))


def deduplicate_businesses(businesses: List[BusinessData]) -> List[BusinessData]:
    """
    Remove duplicate businesses based on name and address.

    Args:
        businesses: List of business data

    Returns:
        List of unique businesses
    """
    seen: Set[BusinessData] = set()
    unique: List[BusinessData] = []

    for business in businesses:
        if business not in seen:
            seen.add(business)
            unique.append(business)

    return unique


def format_business_for_csv(business: BusinessData) -> dict:
    """
    Format business data for CSV export.

    Args:
        business: Business data model

    Returns:
        Dictionary suitable for CSV export
    """
    return {
        "name": business.name,
        "address": business.address,
        "phone": business.phone or "",
        "website": business.website or "",
        "category": business.category or "",
        "rating": business.rating or "",
        "review_count": business.review_count or "",
        "place_id": business.place_id or "",
        "latitude": business.latitude or "",
        "longitude": business.longitude or "",
    }
