"""
Input validation utilities for user data and API inputs.
"""

import re
from typing import Optional


def validate_telegram_id(telegram_id: int) -> bool:
    """
    Validate Telegram user ID.
    
    Args:
        telegram_id: Telegram user ID
        
    Returns:
        True if valid, False otherwise
    """
    # Telegram IDs are positive integers, typically 9-10 digits
    return isinstance(telegram_id, int) and telegram_id > 0


def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address string
        
    Returns:
        True if valid format, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
    
    # Basic email regex (RFC 5322 simplified)
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """
    Validate phone number format.
    Accepts international format with optional + prefix.
    
    Args:
        phone: Phone number string
        
    Returns:
        True if valid format, False otherwise
    """
    if not phone or not isinstance(phone, str):
        return False
    
    # Remove spaces, dashes, parentheses
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    
    # Check if it starts with + and has digits, or just digits
    pattern = r'^\+?[1-9]\d{6,14}$'
    return bool(re.match(pattern, cleaned))


def validate_uuid(uuid_string: str) -> bool:
    """
    Validate UUID format.
    
    Args:
        uuid_string: UUID string
        
    Returns:
        True if valid UUID format, False otherwise
    """
    if not uuid_string or not isinstance(uuid_string, str):
        return False
    
    # UUID format: 8-4-4-4-12 hexadecimal digits
    pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(pattern, uuid_string.lower()))


def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize user input text.
    
    Args:
        text: Input text
        max_length: Optional maximum length
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Remove control characters except newlines and tabs
    sanitized = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', str(text))
    
    # Trim whitespace
    sanitized = sanitized.strip()
    
    # Apply length limit if specified
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized
