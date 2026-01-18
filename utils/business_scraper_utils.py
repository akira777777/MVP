"""
Utilities for business data validation, normalization, and deduplication.
"""

import re
import logging
from datetime import datetime
from typing import Optional, Dict, List
from urllib.parse import urlparse

from utils.validation import validate_email, validate_phone

logger = logging.getLogger(__name__)


def normalize_phone(phone: str) -> Optional[str]:
    """
    Normalize phone number to standard format.
    
    Args:
        phone: Raw phone number string
        
    Returns:
        Normalized phone number or None if invalid
    """
    if not phone or not isinstance(phone, str):
        return None
    
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone.strip())
    
    # Handle Czech phone numbers
    # Czech format: +420XXXXXXXXX or 420XXXXXXXXX
    if cleaned.startswith('420'):
        cleaned = '+' + cleaned
    elif cleaned.startswith('00420'):
        cleaned = '+420' + cleaned[5:]
    elif not cleaned.startswith('+'):
        # Assume Czech number if starts with 0
        if cleaned.startswith('0'):
            cleaned = '+420' + cleaned[1:]
        else:
            cleaned = '+420' + cleaned
    
    # Validate
    if validate_phone(cleaned):
        return cleaned
    
    return None


def normalize_email(email: str) -> Optional[str]:
    """
    Normalize email address.
    
    Args:
        email: Raw email string
        
    Returns:
        Normalized email (lowercase) or None if invalid
    """
    if not email or not isinstance(email, str):
        return None
    
    email = email.strip().lower()
    
    if validate_email(email):
        return email
    
    return None


def normalize_url(url: str) -> Optional[str]:
    """
    Normalize URL.
    
    Args:
        url: Raw URL string
        
    Returns:
        Normalized URL or None if invalid
    """
    if not url or not isinstance(url, str):
        return None
    
    url = url.strip()
    
    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    try:
        parsed = urlparse(url)
        if parsed.netloc:
            return url
    except Exception:
        pass
    
    return None


def extract_district_from_address(address: str) -> Optional[str]:
    """
    Extract Prague district from address.
    
    Args:
        address: Full address string
        
    Returns:
        District name (e.g., "Praha 1") or None
    """
    if not address:
        return None
    
    # Match patterns like "Praha 1", "Praha 2", "Prague 1", etc.
    patterns = [
        r'Praha\s*(\d+)',
        r'Prague\s*(\d+)',
        r'Praha\s*(\d+)\s*-\s*\d+',  # Praha 1 - 11000
    ]
    
    for pattern in patterns:
        match = re.search(pattern, address, re.IGNORECASE)
        if match:
            district_num = match.group(1)
            return f"Praha {district_num}"
    
    return None


def normalize_business_type(business_type: str) -> str:
    """
    Normalize business type to standard values.
    
    Args:
        business_type: Raw business type string
        
    Returns:
        Normalized business type
    """
    if not business_type:
        return "unknown"
    
    business_type = business_type.lower().strip()
    
    # Mapping of variations to standard types
    type_mapping = {
        'hair_salon': ['hair salon', 'hairdresser', 'kadeřnictví', 'hair', 'hairdressing'],
        'beauty_salon': ['beauty salon', 'kosmetika', 'salon krásy', 'beauty', 'cosmetic'],
        'nail_salon': ['nail salon', 'nehtové studio', 'nail studio', 'manikúra', 'nail'],
        'spa': ['spa', 'wellness', 'massage', 'masáž', 'wellness center'],
        'barbershop': ['barbershop', 'holicství', 'pánské kadeřnictví', 'barber'],
        'tattoo_studio': ['tattoo studio', 'tetování', 'tattoo', 'tatér', 'tattoo shop'],
    }
    
    for standard_type, variations in type_mapping.items():
        if any(var in business_type for var in variations):
            return standard_type
    
    return business_type


def deduplicate_businesses(businesses: List[Dict]) -> List[Dict]:
    """
    Remove duplicate businesses from list.
    
    Deduplication is based on:
    1. Exact name match
    2. Same phone number
    3. Same address
    
    Args:
        businesses: List of business dictionaries
        
    Returns:
        Deduplicated list
    """
    seen = set()
    deduplicated = []
    
    for business in businesses:
        # Create unique key from name, phone, and address
        name = (business.get('business_name') or '').lower().strip()
        phone = business.get('phone') or ''
        address = (business.get('address') or '').lower().strip()
        
        # Normalize phone for comparison
        normalized_phone = normalize_phone(phone) if phone else None
        
        # Create keys for comparison
        keys = []
        if name:
            keys.append(f"name:{name}")
        if normalized_phone:
            keys.append(f"phone:{normalized_phone}")
        if address:
            keys.append(f"address:{address}")
        
        # Check if we've seen this combination
        key = "|".join(sorted(keys))
        
        if key not in seen and keys:  # Only add if we have at least one identifier
            seen.add(key)
            deduplicated.append(business)
        else:
            logger.debug(f"Skipping duplicate business: {name}")
    
    return deduplicated


def validate_business_data(business: Dict) -> Dict:
    """
    Validate and normalize business data.
    
    Args:
        business: Business dictionary with raw data
        
    Returns:
        Validated and normalized business dictionary
    """
    validated = business.copy()
    
    # Normalize phone
    if 'phone' in validated:
        validated['phone'] = normalize_phone(validated['phone'])
    
    # Normalize email
    if 'email' in validated:
        validated['email'] = normalize_email(validated['email'])
    
    # Normalize URLs
    for url_field in ['website', 'facebook', 'instagram', 'google_maps_url']:
        if url_field in validated:
            validated[url_field] = normalize_url(validated[url_field])
    
    # Extract district from address if not present
    if 'address' in validated and not validated.get('district'):
        district = extract_district_from_address(validated['address'])
        if district:
            validated['district'] = district
    
    # Normalize business type
    if 'business_type' in validated:
        validated['business_type'] = normalize_business_type(validated['business_type'])
    
    # Add scraped_at timestamp if not present
    if 'scraped_at' not in validated:
        validated['scraped_at'] = datetime.now().isoformat()
    
    return validated


def calculate_data_completeness(business: Dict) -> float:
    """
    Calculate data completeness score (0.0 to 1.0).
    
    Args:
        business: Business dictionary
        
    Returns:
        Completeness score
    """
    required_fields = [
        'business_name',
        'address',
        'phone',
        'email',
        'website',
        'business_type',
    ]
    
    optional_fields = [
        'facebook',
        'instagram',
        'owner_name',
        'owner_contact',
        'rating',
    ]
    
    score = 0.0
    total_weight = len(required_fields) * 2 + len(optional_fields) * 1
    
    # Required fields worth 2 points each
    for field in required_fields:
        if business.get(field):
            score += 2.0
    
    # Optional fields worth 1 point each
    for field in optional_fields:
        if business.get(field):
            score += 1.0
    
    return score / total_weight if total_weight > 0 else 0.0
