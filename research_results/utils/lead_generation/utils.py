"""
Utility functions for lead generation module.
"""

import re
from typing import List, Set, Dict
from .models import BusinessData

# Районы Праги
PRAGUE_DISTRICTS = [
    "Prague 1", "Prague 2", "Prague 3", "Prague 4", "Prague 5",
    "Prague 6", "Prague 7", "Prague 8", "Prague 9", "Prague 10"
]

# Категории бизнесов
BUSINESS_CATEGORIES = {
    "cafe_restaurant": [
        "kavárna", "restaurace", "bistro", "café", "kavárna Praha"
    ],
    "beauty_salon": [
        "kadeřnictví", "kosmetika", "manikúra", "pedikúra", "salon krásy"
    ],
    "retail": [
        "obchod", "obchůdek", "prodejna", "butik"
    ],
    "services": [
        "úklid", "opravy", "servis", "instalatér", "elektrikář"
    ],
    "medical": [
        "lékař", "zubní lékař", "fyzioterapeut", "masáž"
    ],
    "fitness": [
        "fitness", "posilovna", "yoga", "pilates", "sportovní centrum"
    ]
}


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


def generate_prague_queries() -> List[Dict]:
    """Генерация запросов для всех категорий и районов."""
    queries = []

    # Центр Праги (координаты)
    prague_center = (50.0755, 14.4378)

    for category, search_terms in BUSINESS_CATEGORIES.items():
        for term in search_terms:
            for district in PRAGUE_DISTRICTS:
                queries.append({
                    "query": f"{term} {district}",
                    "location": prague_center,  # Можно уточнить координаты районов
                    "category": category,
                    "radius": 5000,
                    "district": district
                })

    return queries


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
        "city": business.city or "",
        "district": business.district or "",
        "postal_code": business.postal_code or "",
        "phone": business.phone or "",
        "website": business.website or "",
        "category": business.category or "",
        "subcategory": business.subcategory or "",
        "rating": float(business.rating) if business.rating else "",
        "review_count": business.review_count or "",
        "place_id": business.place_id or "",
        "google_place_id": business.google_place_id or "",
        "latitude": float(business.latitude) if business.latitude else "",
        "longitude": float(business.longitude) if business.longitude else "",
    }
