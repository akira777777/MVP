"""Slot models for appointment time slots."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SlotStatus(str, Enum):
    """Slot availability status."""

    AVAILABLE = "available"
    BOOKED = "booked"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Slot(BaseModel):
    """Time slot model."""

    id: Optional[str] = None
    start_time: datetime
    end_time: datetime
    status: SlotStatus = SlotStatus.AVAILABLE
    service_type: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "start_time": "2026-01-15T10:00:00",
                "end_time": "2026-01-15T11:00:00",
                "status": "available",
                "service_type": "manicure",
            }
        }


class SlotCreate(BaseModel):
    """Slot creation model."""

    start_time: datetime
    end_time: datetime
    service_type: str
    status: SlotStatus = SlotStatus.AVAILABLE
