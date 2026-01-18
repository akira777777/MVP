"""
Data models for business information collected from Google Maps.
"""

import re
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from pydantic import BaseModel, field_validator, Field, HttpUrl


class BusinessData(BaseModel):
    """Модель бизнеса для валидации входящих данных."""

    name: str = Field(..., min_length=1, max_length=200)
    address: str = Field(..., min_length=5)
    city: str = Field(default="Prague")
    district: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    phone: Optional[str] = None
    website: Optional[str] = None
    category: str = Field(..., min_length=1)
    subcategory: Optional[str] = None
    google_place_id: Optional[str] = None
    rating: Optional[Decimal] = Field(None, ge=0, le=5)
    review_count: Optional[int] = Field(None, ge=0)
    opening_hours: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    # Keep place_id for backward compatibility
    place_id: Optional[str] = Field(None, max_length=200)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Нормализация чешских телефонных номеров."""
        if v is None:
            return None
        # Нормализация чешских телефонных номеров
        cleaned = ''.join(filter(str.isdigit, v))
        if cleaned.startswith('420'):
            cleaned = cleaned[3:]
        if len(cleaned) == 9:
            return f"+420 {cleaned[:3]} {cleaned[3:6]} {cleaned[6:]}"
        return v

    @field_validator("website")
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        """Validate website URL format."""
        if not v:
            return None
        # Add protocol if missing
        if not v.startswith(("http://", "https://")):
            v = f"https://{v}"
        return v

    @field_validator("address")
    @classmethod
    def normalize_address(cls, v: str) -> str:
        """Normalize Prague addresses."""
        if not v:
            return v

        # Remove extra whitespace
        normalized = re.sub(r"\s+", " ", v.strip())

        # Normalize common Prague address patterns
        # "Prague 1" -> "Praha 1"
        normalized = re.sub(r"\bPrague\b", "Praha", normalized, flags=re.IGNORECASE)

        return normalized

    def __hash__(self) -> int:
        """Make BusinessData hashable for deduplication."""
        return hash((self.name.lower(), self.address.lower()))

    def __eq__(self, other: object) -> bool:
        """Compare businesses by name and address."""
        if not isinstance(other, BusinessData):
            return False
        return (
            self.name.lower() == other.name.lower()
            and self.address.lower() == other.address.lower()
        )


class BusinessCreate(BusinessData):
    """Модель для создания бизнеса в БД."""
    data_source: str = Field(..., pattern="^(api|mcp|scraper)$")
    verified: bool = False


class Business(BusinessCreate):
    """Модель бизнеса из БД."""
    id: str
    collected_at: datetime
    updated_at: datetime
