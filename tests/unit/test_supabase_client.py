"""
Unit tests for Supabase database client.
Tests with mocked Supabase API calls.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from db.supabase_client import SupabaseClient
from models.booking import BookingCreate, BookingStatus
from models.client import ClientCreate
from models.slot import SlotCreate, SlotStatus


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client."""
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    return mock_client, mock_table


@pytest.fixture
def supabase_client(mock_supabase_client):
    """Create SupabaseClient with mocked client."""
    mock_client, _ = mock_supabase_client
    with patch("db.supabase_client.create_client", return_value=mock_client):
        client = SupabaseClient()
        client.client = mock_client
        return client


@pytest.mark.asyncio
async def test_get_client_by_telegram_id_found(supabase_client, mock_supabase_client):
    """Test getting client by Telegram ID when found."""
    _, mock_table = mock_supabase_client
    mock_response = MagicMock()
    mock_response.data = [{"id": "client_123", "telegram_id": 123456789}]
    mock_table.select.return_value.eq.return_value.execute.return_value = mock_response

    result = await supabase_client.get_client_by_telegram_id(123456789)

    assert result is not None
    assert result.telegram_id == 123456789


@pytest.mark.asyncio
async def test_get_client_by_telegram_id_not_found(supabase_client, mock_supabase_client):
    """Test getting client by Telegram ID when not found."""
    _, mock_table = mock_supabase_client
    mock_response = MagicMock()
    mock_response.data = []
    mock_table.select.return_value.eq.return_value.execute.return_value = mock_response

    result = await supabase_client.get_client_by_telegram_id(123456789)

    assert result is None


@pytest.mark.asyncio
async def test_create_client_success(supabase_client, mock_supabase_client):
    """Test successful client creation."""
    _, mock_table = mock_supabase_client
    mock_response = MagicMock()
    mock_response.data = [{"id": "client_123", "telegram_id": 123456789, "first_name": "Test"}]
    mock_table.insert.return_value.execute.return_value = mock_response

    client_data = ClientCreate(
        telegram_id=123456789,
        first_name="Test",
    )

    result = await supabase_client.create_client(client_data)

    assert result.id == "client_123"
    assert result.telegram_id == 123456789


@pytest.mark.asyncio
async def test_create_slot_success(supabase_client, mock_supabase_client):
    """Test successful slot creation."""
    _, mock_table = mock_supabase_client
    start_time = datetime.now() + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)

    mock_response = MagicMock()
    mock_response.data = [{
        "id": "slot_123",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "service_type": "manicure",
        "status": "available",
    }]
    mock_table.insert.return_value.execute.return_value = mock_response

    slot_data = SlotCreate(
        start_time=start_time,
        end_time=end_time,
        service_type="manicure",
    )

    result = await supabase_client.create_slot(slot_data)

    assert result.id == "slot_123"
    assert result.service_type == "manicure"


@pytest.mark.asyncio
async def test_get_available_slots(supabase_client, mock_supabase_client):
    """Test getting available slots."""
    _, mock_table = mock_supabase_client
    start_time = datetime.now() + timedelta(days=1)

    mock_response = MagicMock()
    mock_response.data = [{
        "id": "slot_123",
        "start_time": start_time.isoformat(),
        "end_time": (start_time + timedelta(hours=1)).isoformat(),
        "service_type": "manicure",
        "status": "available",
    }]
    mock_table.select.return_value.eq.return_value.gte.return_value.order.return_value.execute.return_value = mock_response

    result = await supabase_client.get_available_slots("manicure", start_date=start_time)

    assert len(result) == 1
    assert result[0].id == "slot_123"


@pytest.mark.asyncio
async def test_create_booking_success(supabase_client, mock_supabase_client):
    """Test successful booking creation."""
    _, mock_table = mock_supabase_client
    mock_response = MagicMock()
    mock_response.data = [{
        "id": "booking_123",
        "client_id": "client_123",
        "slot_id": "slot_123",
        "service_type": "manicure",
        "status": "pending",
        "price_czk": 150,
    }]
    mock_table.insert.return_value.execute.return_value = mock_response

    booking_data = BookingCreate(
        client_id="client_123",
        slot_id="slot_123",
        service_type="manicure",
        price_czk=150,
    )

    result = await supabase_client.create_booking(booking_data)

    assert result.id == "booking_123"
    assert result.status == BookingStatus.PENDING


@pytest.mark.asyncio
async def test_update_slot_status(supabase_client, mock_supabase_client):
    """Test updating slot status."""
    _, mock_table = mock_supabase_client
    mock_response = MagicMock()
    mock_response.data = [{
        "id": "slot_123",
        "status": "booked",
    }]
    mock_table.update.return_value.eq.return_value.execute.return_value = mock_response

    result = await supabase_client.update_slot_status("slot_123", SlotStatus.BOOKED)

    assert result is not None
    assert result.status == SlotStatus.BOOKED


@pytest.mark.asyncio
async def test_update_booking_status(supabase_client, mock_supabase_client):
    """Test updating booking status."""
    _, mock_table = mock_supabase_client
    mock_response = MagicMock()
    mock_response.data = [{
        "id": "booking_123",
        "status": "confirmed",
    }]
    mock_table.update.return_value.eq.return_value.execute.return_value = mock_response

    result = await supabase_client.update_booking_status("booking_123", BookingStatus.CONFIRMED)

    assert result is not None
    assert result.status == BookingStatus.CONFIRMED


@pytest.mark.asyncio
async def test_get_all_slots_admin(supabase_client, mock_supabase_client):
    """Test admin function to get all slots."""
    _, mock_table = mock_supabase_client
    mock_response = MagicMock()
    mock_response.data = [
        {
            "id": "slot_123",
            "start_time": datetime.now().isoformat(),
            "end_time": (datetime.now() + timedelta(hours=1)).isoformat(),
            "service_type": "manicure",
            "status": "available",
        }
    ]
    mock_table.select.return_value.order.return_value.limit.return_value.execute.return_value = mock_response

    result = await supabase_client.get_all_slots(limit=10)

    assert len(result) == 1


@pytest.mark.asyncio
async def test_get_all_bookings_admin(supabase_client, mock_supabase_client):
    """Test admin function to get all bookings."""
    _, mock_table = mock_supabase_client
    mock_response = MagicMock()
    mock_response.data = [
        {
            "id": "booking_123",
            "client_id": "client_123",
            "slot_id": "slot_123",
            "service_type": "manicure",
            "status": "pending",
            "price_czk": 150,
        }
    ]
    mock_table.select.return_value.order.return_value.limit.return_value.execute.return_value = mock_response

    result = await supabase_client.get_all_bookings(limit=10)

    assert len(result) == 1
