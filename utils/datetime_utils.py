"""
Datetime utilities for consistent timezone handling across the application.
All datetime operations should use timezone-aware datetimes.
"""

from datetime import datetime, timezone
from typing import Optional


def utc_now() -> datetime:
    """
    Get current UTC time as timezone-aware datetime.
    
    Returns:
        Current UTC datetime with timezone info
    """
    return datetime.now(timezone.utc)


def parse_iso_datetime(iso_string: str) -> datetime:
    """
    Parse ISO format datetime string to timezone-aware datetime.
    Handles both 'Z' suffix and '+00:00' timezone formats.
    
    Args:
        iso_string: ISO format datetime string
        
    Returns:
        Timezone-aware datetime object
        
    Raises:
        ValueError: If datetime string cannot be parsed
    """
    # Normalize 'Z' suffix to '+00:00'
    normalized = iso_string.replace("Z", "+00:00")
    
    # Parse with timezone info
    try:
        dt = datetime.fromisoformat(normalized)
        # Ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError as e:
        raise ValueError(f"Invalid datetime string: {iso_string}") from e


def to_iso_string(dt: datetime) -> str:
    """
    Convert datetime to ISO format string.
    Ensures timezone-aware datetimes are properly formatted.
    
    Args:
        dt: Datetime object (timezone-aware or naive)
        
    Returns:
        ISO format string
    """
    # Ensure timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt.isoformat()
