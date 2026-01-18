"""Booking models for appointments."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class BookingStatus(str, Enum):
    """Booking status."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    PAID = "paid"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class Booking(BaseModel):
    """Booking model."""

    id: Optional[str] = None
    client_id: str = Field(..., description="Client ID (Supabase UUID)")
    slot_id: str = Field(..., description="Slot ID (Supabase UUID)")
    service_type: str
    status: BookingStatus = BookingStatus.PENDING
    price_czk: int = Field(..., ge=0)
    stripe_payment_intent_id: Optional[str] = None
    stripe_payment_status: Optional[str] = None
    reminder_sent: bool = Field(default=False)
    reminder_sent_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "client_id": "uuid-here",
                "slot_id": "uuid-here",
                "service_type": "manicure",
                "status": "pending",
                "price_czk": 150,
            }
        }


class BookingCreate(BaseModel):
    """Booking creation model."""

    client_id: str
    slot_id: str
    service_type: str
    price_czk: int
    status: BookingStatus = BookingStatus.PENDING
    notes: Optional[str] = None
