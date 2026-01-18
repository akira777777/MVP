"""
Basic unit tests for bot components.
"""

import pytest
from datetime import datetime, timedelta

from models.service import ServiceType, get_service, get_all_services
from models.booking import BookingStatus
from models.slot import SlotStatus


def test_service_models():
    """Test service models."""
    services = get_all_services()
    assert len(services) > 0

    manicure = get_service(ServiceType.MANICURE)
    assert manicure.price_czk == 150
    assert manicure.duration_minutes == 60


def test_booking_status_enum():
    """Test booking status enum."""
    assert BookingStatus.PENDING.value == "pending"
    assert BookingStatus.PAID.value == "paid"


def test_slot_status_enum():
    """Test slot status enum."""
    assert SlotStatus.AVAILABLE.value == "available"
    assert SlotStatus.BOOKED.value == "booked"


def test_service_types():
    """Test service types."""
    assert ServiceType.MANICURE in ServiceType
    assert ServiceType.HAIR in ServiceType
