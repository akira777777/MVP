"""Models for business prospects (potential clients)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class CompanyOwner(BaseModel):
    """Company owner/director information."""

    name: str = Field(..., description="Owner/director name")
    role: Optional[str] = Field(None, description="Role (statutární orgán, společník, etc.)")
    ico: Optional[str] = Field(None, description="Company IČO (ID)")


class BusinessProspect(BaseModel):
    """Business prospect model for lead generation."""

    # Google Maps data
    name: str = Field(..., description="Business name")
    address: Optional[str] = Field(None, description="Full address")
    phone: Optional[str] = Field(None, description="Phone number")
    website: Optional[HttpUrl] = Field(None, description="Website URL")
    google_maps_url: Optional[HttpUrl] = Field(None, description="Google Maps URL")
    category: Optional[str] = Field(None, description="Business category")
    rating: Optional[float] = Field(None, description="Google Maps rating")
    reviews_count: Optional[int] = Field(None, description="Number of reviews")

    # ARES/Obchodní rejstřík data
    ico: Optional[str] = Field(None, description="Company IČO (ID)")
    legal_name: Optional[str] = Field(None, description="Legal company name")
    owners: list[CompanyOwner] = Field(default_factory=list, description="List of owners/directors")
    registration_date: Optional[datetime] = Field(None, description="Company registration date")
    status: Optional[str] = Field(None, description="Company status (aktivní, zaniklá, etc.)")

    # Lead generation metadata
    source: str = Field(default="google_maps", description="Source of the lead")
    found_at: datetime = Field(default_factory=datetime.utcnow, description="When prospect was found")
    contacted: bool = Field(default=False, description="Whether prospect has been contacted")
    contacted_at: Optional[datetime] = Field(None, description="When prospect was contacted")
    notes: Optional[str] = Field(None, description="Additional notes")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Salon Krásy Praha",
                "address": "Václavské náměstí 1, Praha 1",
                "phone": "+420123456789",
                "website": "https://example.com",
                "category": "beauty_salon",
                "ico": "12345678",
                "legal_name": "Salon Krásy Praha s.r.o.",
                "owners": [
                    {"name": "Jan Novák", "role": "statutární orgán", "ico": "12345678"}
                ],
            }
        }
