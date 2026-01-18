"""Service models for beauty salon services."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ServiceType(str, Enum):
    """Available service types."""

    MANICURE = "manicure"
    HAIR = "hair"
    PEDICURE = "pedicure"
    FACIAL = "facial"


class Service(BaseModel):
    """Service model."""

    id: Optional[str] = None
    type: ServiceType
    name: str
    description: str
    price_czk: int = Field(..., ge=0, description="Price in CZK")
    duration_minutes: int = Field(..., ge=15, le=300, description="Duration in minutes")

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "type": "manicure",
                "name": "Classic Manicure",
                "description": "Classic nail care and polish",
                "price_czk": 150,
                "duration_minutes": 60,
            }
        }


# Predefined services
SERVICES = {
    ServiceType.MANICURE: Service(
        type=ServiceType.MANICURE,
        name="Manicure",
        description="Classic nail care and polish",
        price_czk=150,
        duration_minutes=60,
    ),
    ServiceType.HAIR: Service(
        type=ServiceType.HAIR,
        name="Haircut & Styling",
        description="Professional haircut and styling",
        price_czk=200,
        duration_minutes=90,
    ),
    ServiceType.PEDICURE: Service(
        type=ServiceType.PEDICURE,
        name="Pedicure",
        description="Foot care and nail polish",
        price_czk=180,
        duration_minutes=75,
    ),
    ServiceType.FACIAL: Service(
        type=ServiceType.FACIAL,
        name="Facial Treatment",
        description="Deep cleansing and moisturizing facial",
        price_czk=250,
        duration_minutes=60,
    ),
}


def get_service(service_type: ServiceType) -> Service:
    """Get service by type."""
    return SERVICES[service_type]


def get_all_services() -> list[Service]:
    """Get all available services."""
    return list(SERVICES.values())
