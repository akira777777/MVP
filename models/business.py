"""Business model for Prague business database collection."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class BusinessCategory:
    """Business category constants."""

    HAIR_SALON = "hair_salon"
    BEAUTY_SALON = "beauty_salon"
    NAIL_SALON = "nail_salon"
    MASSAGE_SALON = "massage_salon"
    TANNING_SALON = "tanning_salon"
    BARBERSHOP = "barbershop"
    OTHER = "other"


class Business(BaseModel):
    """Business model for Prague business database."""

    name: str = Field(..., description="Business name")
    category: str = Field(..., description="Business category")
    address: str = Field(..., description="Full address in Prague")
    phone: Optional[str] = Field(None, description="Phone number")
    email: Optional[EmailStr] = Field(None, description="Email address")
    website: Optional[str] = Field(None, description="Website URL")
    owner_name: Optional[str] = Field(None, description="Owner name")
    social_facebook: Optional[str] = Field(None, description="Facebook page URL")
    social_instagram: Optional[str] = Field(None, description="Instagram page URL")
    google_maps_url: Optional[str] = Field(None, description="Google Maps URL")
    notes: Optional[str] = Field(None, description="Additional notes")
    collected_at: datetime = Field(default_factory=datetime.utcnow, description="Collection timestamp")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validate business category."""
        valid_categories = [
            BusinessCategory.HAIR_SALON,
            BusinessCategory.BEAUTY_SALON,
            BusinessCategory.NAIL_SALON,
            BusinessCategory.MASSAGE_SALON,
            BusinessCategory.TANNING_SALON,
            BusinessCategory.BARBERSHOP,
            BusinessCategory.OTHER,
        ]
        if v not in valid_categories:
            return BusinessCategory.OTHER
        return v

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        """Validate that address contains Prague reference."""
        v_lower = v.lower()
        prague_keywords = ["prague", "praha", "praze", "prahy"]
        if not any(keyword in v_lower for keyword in prague_keywords):
            # Still allow, but log warning - will be filtered later
            pass
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Normalize phone number format."""
        if not v:
            return None
        # Remove common separators
        cleaned = v.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        # Add +420 if Czech number without country code
        if cleaned.startswith("420"):
            cleaned = "+" + cleaned
        elif cleaned.startswith("+420"):
            pass
        elif len(cleaned) == 9 and cleaned.isdigit():
            cleaned = "+420" + cleaned
        return cleaned

    @field_validator("website")
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        """Normalize website URL."""
        if not v:
            return None
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Salon Beauty",
                "category": "beauty_salon",
                "address": "Václavské náměstí 1, 110 00 Praha 1",
                "phone": "+420123456789",
                "email": "info@salonbeauty.cz",
                "website": "https://salonbeauty.cz",
                "owner_name": "Jan Novák",
                "social_facebook": "https://facebook.com/salonbeauty",
                "social_instagram": "https://instagram.com/salonbeauty",
                "google_maps_url": "https://maps.google.com/...",
                "notes": "Small family business",
                "collected_at": "2024-01-15T10:00:00Z",
            }
        }


class BusinessCreate(BaseModel):
    """Business creation model (without collected_at)."""

    name: str
    category: str
    address: str
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    owner_name: Optional[str] = None
    social_facebook: Optional[str] = None
    social_instagram: Optional[str] = None
    google_maps_url: Optional[str] = None
    notes: Optional[str] = None
