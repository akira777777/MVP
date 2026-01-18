"""
Module for extracting business data from web pages and social media.
"""

import re
import logging
from typing import Optional, Dict
from urllib.parse import urlparse, urljoin

logger = logging.getLogger(__name__)


def extract_email_from_text(text: str) -> Optional[str]:
    """
    Extract email addresses from text.
    
    Args:
        text: Text to search
        
    Returns:
        First valid email found or None
    """
    if not text:
        return None
    
    # Email regex pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    matches = re.findall(email_pattern, text)
    
    # Filter out common non-business emails
    excluded_domains = ['example.com', 'test.com', 'domain.com', 'email.com']
    
    for email in matches:
        email_lower = email.lower()
        if not any(domain in email_lower for domain in excluded_domains):
            return email_lower
    
    return None


def extract_phone_from_text(text: str) -> Optional[str]:
    """
    Extract phone numbers from text.
    
    Args:
        text: Text to search
        
    Returns:
        First valid phone found or None
    """
    if not text:
        return None
    
    # Czech phone patterns
    patterns = [
        r'\+420\s*\d{3}\s*\d{3}\s*\d{3}',  # +420 XXX XXX XXX
        r'00420\s*\d{3}\s*\d{3}\s*\d{3}',  # 00420 XXX XXX XXX
        r'0\d{2}\s*\d{3}\s*\d{3}',  # 0XX XXX XXX
        r'\d{3}\s*\d{3}\s*\d{3}',  # XXX XXX XXX
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            return matches[0].strip()
    
    return None


def extract_social_links(text: str, base_url: Optional[str] = None) -> Dict[str, Optional[str]]:
    """
    Extract social media links from text or HTML.
    
    Args:
        text: Text or HTML to search
        base_url: Base URL for resolving relative links
        
    Returns:
        Dictionary with facebook, instagram, etc.
    """
    social_links = {
        'facebook': None,
        'instagram': None,
        'twitter': None,
    }
    
    if not text:
        return social_links
    
    # Facebook patterns
    facebook_patterns = [
        r'facebook\.com/([a-zA-Z0-9.]+)',
        r'fb\.com/([a-zA-Z0-9.]+)',
        r'fb\.me/([a-zA-Z0-9.]+)',
    ]
    
    for pattern in facebook_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            page = match.group(1)
            social_links['facebook'] = f"https://facebook.com/{page}"
            break
    
    # Instagram patterns
    instagram_patterns = [
        r'instagram\.com/([a-zA-Z0-9._]+)',
        r'instagr\.am/([a-zA-Z0-9._]+)',
    ]
    
    for pattern in instagram_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            username = match.group(1)
            social_links['instagram'] = f"https://instagram.com/{username}"
            break
    
    # Twitter/X patterns
    twitter_patterns = [
        r'twitter\.com/([a-zA-Z0-9_]+)',
        r'x\.com/([a-zA-Z0-9_]+)',
    ]
    
    for pattern in twitter_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            username = match.group(1)
            social_links['twitter'] = f"https://twitter.com/{username}"
            break
    
    return social_links


def extract_owner_info(text: str) -> Dict[str, Optional[str]]:
    """
    Extract owner information from text.
    
    Looks for patterns like "Owner:", "Vlastník:", "Contact:", etc.
    
    Args:
        text: Text to search
        
    Returns:
        Dictionary with owner_name and owner_contact
    """
    owner_info = {
        'owner_name': None,
        'owner_contact': None,
    }
    
    if not text:
        return owner_info
    
    # Patterns for owner name
    owner_patterns = [
        r'(?:Owner|Vlastník|Majitel|Kontakt):\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*(?:Owner|Vlastník|Majitel)',
    ]
    
    for pattern in owner_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Filter out common false positives
            if name and len(name.split()) <= 3 and name.lower() not in ['contact', 'email', 'phone']:
                owner_info['owner_name'] = name
                break
    
    # Extract Telegram/WhatsApp contacts
    telegram_pattern = r'(?:telegram|tg):\s*@?([a-zA-Z0-9_]+)'
    whatsapp_pattern = r'whatsapp[:\s]+(\+?\d+)'
    
    telegram_match = re.search(telegram_pattern, text, re.IGNORECASE)
    if telegram_match:
        owner_info['owner_contact'] = f"@{telegram_match.group(1)}"
    
    whatsapp_match = re.search(whatsapp_pattern, text, re.IGNORECASE)
    if whatsapp_match and not owner_info['owner_contact']:
        owner_info['owner_contact'] = whatsapp_match.group(1)
    
    return owner_info


def parse_google_maps_data(maps_data: Dict) -> Dict:
    """
    Parse data extracted from Google Maps.
    
    Args:
        maps_data: Dictionary with Google Maps data
        
    Returns:
        Normalized business data dictionary
    """
    business = {
        'business_name': maps_data.get('name', '').strip(),
        'address': maps_data.get('address', '').strip(),
        'phone': maps_data.get('phone', '').strip(),
        'website': maps_data.get('website', '').strip(),
        'rating': maps_data.get('rating'),
        'reviews_count': maps_data.get('reviews_count'),
        'google_maps_url': maps_data.get('url', '').strip(),
        'business_type': maps_data.get('type', '').strip(),
    }
    
    # Extract district from address
    from utils.business_scraper_utils import extract_district_from_address
    district = extract_district_from_address(business['address'])
    if district:
        business['district'] = district
    
    return business


def enrich_business_data(business: Dict, html_content: Optional[str] = None) -> Dict:
    """
    Enrich business data by extracting additional information from HTML content.
    
    Args:
        business: Base business dictionary
        html_content: HTML content of business website
        
    Returns:
        Enriched business dictionary
    """
    enriched = business.copy()
    
    if not html_content:
        return enriched
    
    # Extract email
    if not enriched.get('email'):
        email = extract_email_from_text(html_content)
        if email:
            enriched['email'] = email
    
    # Extract phone if missing
    if not enriched.get('phone'):
        phone = extract_phone_from_text(html_content)
        if phone:
            enriched['phone'] = phone
    
    # Extract social links
    social_links = extract_social_links(html_content, enriched.get('website'))
    if social_links.get('facebook') and not enriched.get('facebook'):
        enriched['facebook'] = social_links['facebook']
    if social_links.get('instagram') and not enriched.get('instagram'):
        enriched['instagram'] = social_links['instagram']
    
    # Extract owner info
    owner_info = extract_owner_info(html_content)
    if owner_info.get('owner_name') and not enriched.get('owner_name'):
        enriched['owner_name'] = owner_info['owner_name']
    if owner_info.get('owner_contact') and not enriched.get('owner_contact'):
        enriched['owner_contact'] = owner_info['owner_contact']
    
    return enriched
