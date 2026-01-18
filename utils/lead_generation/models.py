"""
Data models for lead generation.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class CompanyInfo(BaseModel):
    """Company information from Czech business registries."""

    ico: str = Field(..., description="IČO - Company identification number")
    name: str = Field(..., description="Company name")
    address: Optional[str] = Field(None, description="Registered address")
    phone: Optional[str] = Field(None, description="Phone number")
    website: Optional[str] = Field(None, description="Website URL")
    email: Optional[str] = Field(None, description="Email address")
    legal_form: Optional[str] = Field(None, description="Legal form (s.r.o., a.s., etc.)")
    status: Optional[str] = Field(None, description="Company status (active, dissolved, etc.)")
    registration_date: Optional[datetime] = Field(None, description="Registration date")
    source: str = Field(..., description="Source registry (ARES or Obchodní rejstřík)")

    @field_validator("ico")
    @classmethod
    def validate_ico(cls, v: str) -> str:
        """Validate IČO format (8 digits)."""
        if not v.isdigit() or len(v) != 8:
            raise ValueError("IČO must be 8 digits")
        return v


class OwnerInfo(BaseModel):
    """Owner/director information."""

    name: str = Field(..., description="Full name")
    role: Optional[str] = Field(None, description="Role (statutární orgán, společník, etc.)")
    share_percentage: Optional[float] = Field(None, description="Ownership percentage")
    address: Optional[str] = Field(None, description="Address")
    birth_date: Optional[datetime] = Field(None, description="Date of birth")


class BusinessLead(BaseModel):
    """Complete business lead information."""

    # Google Maps data
    google_maps_id: Optional[str] = Field(None, description="Google Maps Place ID")
    business_name: str = Field(..., description="Business name from Google Maps")
    google_address: Optional[str] = Field(None, description="Address from Google Maps")
    google_phone: Optional[str] = Field(None, description="Phone from Google Maps")
    google_website: Optional[str] = Field(None, description="Website from Google Maps")
    google_rating: Optional[float] = Field(None, description="Google rating")
    google_reviews_count: Optional[int] = Field(None, description="Number of reviews")
    category: Optional[str] = Field(None, description="Business category")
    google_maps_url: Optional[str] = Field(None, description="Google Maps URL")

    # Registry data
    company_info: Optional[CompanyInfo] = Field(None, description="Company registry information")
    owners: List[OwnerInfo] = Field(default_factory=list, description="List of owners/directors")

    # Metadata
    found_at: datetime = Field(default_factory=datetime.now, description="When lead was found")
    processed: bool = Field(default=False, description="Whether lead has been processed")
    contacted: bool = Field(default=False, description="Whether owner has been contacted")
    contacted_at: Optional[datetime] = Field(None, description="When owner was contacted")
    notes: Optional[str] = Field(None, description="Additional notes")

    def get_primary_owner(self) -> Optional[OwnerInfo]:
        """Get primary owner (statutární orgán) or first owner."""
        for owner in self.owners:
            if owner.role and "statutární" in owner.role.lower():
                return owner
        return self.owners[0] if self.owners else None

    def get_contact_name(self) -> str:
        """Get contact name (owner name or business name)."""
        owner = self.get_primary_owner()
        if owner:
            return owner.name
        return self.business_name

    def has_complete_info(self) -> bool:
        """Check if lead has complete information (company info and at least one owner)."""
        return self.company_info is not None and len(self.owners) > 0
