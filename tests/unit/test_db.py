"""
Unit tests for Supabase database client.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from db.supabase_client import SupabaseClient
from models.booking import BookingCreate, BookingStatus
from models.client import ClientCreate
from models.slot import SlotCreate, SlotStatus


class TestSupabaseClient:
    """Test Supabase client operations."""

    @pytest.fixture
    def mock_supabase_client(self):
        """Create mock Supabase client."""
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        return mock_client, mock_table

    @pytest.fixture
    def db_client(self, mock_supabase_client):
        """Create database client with mocked Supabase."""
        mock_client, _ = mock_supabase_client
        with patch("db.supabase_client.create_client", return_value=mock_client):
            client = SupabaseClient()
            client.client = mock_client
            return client, mock_supabase_client[1]

    @pytest.mark.asyncio
    async def test_get_client_by_telegram_id_found(self, db_client):
        """Test getting client by Telegram ID when found."""
        client, mock_table = db_client
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[{"id": "client_123", "telegram_id": 123456789, "first_name": "Test"}]
        )
        
        result = await client.get_client_by_telegram_id(123456789)
        
        assert result is not None
        assert result.telegram_id == 123456789

    @pytest.mark.asyncio
    async def test_get_client_by_telegram_id_not_found(self, db_client):
        """Test getting client by Telegram ID when not found."""
        client, mock_table = db_client
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        
        result = await client.get_client_by_telegram_id(123456789)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_create_client_success(self, db_client):
        """Test successful client creation."""
        client, mock_table = db_client
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[{"id": "client_123", "telegram_id": 123456789, "first_name": "Test"}]
        )
        
        client_data = ClientCreate(
            telegram_id=123456789,
            first_name="Test",
            last_name="User",
        )
        
        result = await client.create_client(client_data)
        
        assert result is not None
        assert result.telegram_id == 123456789

    @pytest.mark.asyncio
    async def test_create_slot_success(self, db_client):
        """Test successful slot creation."""
        client, mock_table = db_client
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[
                {
                    "id": "slot_123",
                    "start_time": "2024-01-01T10:00:00Z",
                    "end_time": "2024-01-01T11:00:00Z",
                    "service_type": "manicure",
                    "status": "available",
                }
            ]
        )
        
        slot_data = SlotCreate(
            start_time=datetime.now() + timedelta(days=1),
            end_time=datetime.now() + timedelta(days=1, hours=1),
            service_type="manicure",
        )
        
        result = await client.create_slot(slot_data)
        
        assert result is not None
        assert result.service_type == "manicure"

    @pytest.mark.asyncio
    async def test_get_available_slots(self, db_client):
        """Test getting available slots."""
        client, mock_table = db_client
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[
                {
                    "id": "slot_123",
                    "start_time": "2024-01-01T10:00:00Z",
                    "end_time": "2024-01-01T11:00:00Z",
                    "service_type": "manicure",
                    "status": "available",
                }
            ]
        )
        
        result = await client.get_available_slots("manicure")
        
        assert len(result) == 1
        assert result[0].service_type == "manicure"

    @pytest.mark.asyncio
    async def test_create_booking_success(self, db_client):
        """Test successful booking creation."""
        client, mock_table = db_client
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[
                {
                    "id": "booking_123",
                    "client_id": "client_123",
                    "slot_id": "slot_123",
                    "service_type": "manicure",
                    "status": "pending",
                    "price_czk": 150,
                }
            ]
        )
        
        booking_data = BookingCreate(
            client_id="client_123",
            slot_id="slot_123",
            service_type="manicure",
            price_czk=150,
            status=BookingStatus.PENDING,
        )
        
        result = await client.create_booking(booking_data)
        
        assert result is not None
        assert result.status == BookingStatus.PENDING

    @pytest.mark.asyncio
    async def test_update_slot_status(self, db_client):
        """Test updating slot status."""
        client, mock_table = db_client
        mock_table.update.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[
                {
                    "id": "slot_123",
                    "start_time": "2024-01-01T10:00:00Z",
                    "end_time": "2024-01-01T11:00:00Z",
                    "service_type": "manicure",
                    "status": "booked",
                }
            ]
        )
        
        result = await client.update_slot_status("slot_123", SlotStatus.BOOKED)
        
        assert result is not None
        assert result.status == SlotStatus.BOOKED

    @pytest.mark.asyncio
    async def test_get_all_slots_admin(self, db_client):
        """Test admin operation to get all slots."""
        client, mock_table = db_client
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[
                {
                    "id": "slot_123",
                    "start_time": "2024-01-01T10:00:00Z",
                    "end_time": "2024-01-01T11:00:00Z",
                    "service_type": "manicure",
                    "status": "available",
                }
            ]
        )
        
        result = await client.get_all_slots(service_type="manicure")
        
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_all_bookings_admin(self, db_client):
        """Test admin operation to get all bookings."""
        client, mock_table = db_client
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[
                {
                    "id": "booking_123",
                    "client_id": "client_123",
                    "slot_id": "slot_123",
                    "service_type": "manicure",
                    "status": "pending",
                    "price_czk": 150,
                }
            ]
        )
        
        # Mock get_slot_by_id for filtering
        with patch.object(client, "get_slot_by_id", new_callable=AsyncMock) as mock_get_slot:
            mock_get_slot.return_value = MagicMock(
                start_time=datetime.now() + timedelta(days=1)
            )
            
            result = await client.get_all_bookings()
            
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_delete_slot_admin(self, db_client):
        """Test admin operation to delete slot."""
        client, mock_table = db_client
        mock_table.delete.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{"id": "slot_123"}])
        
        result = await client.delete_slot("slot_123")
        
        assert result is True
