"""Client models for user data."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class Client(BaseModel):
    """Client model."""

    id: Optional[str] = None
    telegram_id: int = Field(..., description="Telegram user ID")
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    gdpr_consent: bool = Field(default=False, description="GDPR consent status")
    gdpr_consent_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "telegram_id": 123456789,
                "first_name": "John",
                "last_name": "Doe",
                "username": "johndoe",
                "phone": "+420123456789",
                "email": "john@example.com",
                "gdpr_consent": True,
            }
        }


class ClientCreate(BaseModel):
    """Client creation model."""

    telegram_id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    gdpr_consent: bool = False
    gdpr_consent_date: Optional[datetime] = None
