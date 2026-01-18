"""
Unit tests for scheduler functionality.
Tests reminder scheduling with mocked dependencies.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scheduler.reminders import (
    check_and_send_reminders,
    send_reminder,
    setup_scheduler,
)


@pytest.fixture
def mock_bot():
    """Mock Telegram bot."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    return bot


@pytest.mark.asyncio
async def test_send_reminder_success(mock_bot):
    """Test successful reminder sending."""
    booking_id = "booking_123"
    client_telegram_id = 123456789
    slot_time = datetime.now() + timedelta(hours=24)

    mock_booking = MagicMock()
    mock_booking.id = booking_id

    with patch("scheduler.reminders._bot_instance", mock_bot), patch(
        "scheduler.reminders.get_db_client"
    ) as mock_db_client:
        mock_db = AsyncMock()
        mock_db.mark_reminder_sent = AsyncMock(return_value=mock_booking)
        mock_db_client.return_value = mock_db

        result = await send_reminder(booking_id, client_telegram_id, slot_time)

        assert result is True
        mock_bot.send_message.assert_called_once()
        mock_db.mark_reminder_sent.assert_called_once_with(booking_id)


@pytest.mark.asyncio
async def test_send_reminder_no_bot_instance():
    """Test reminder sending fails when bot instance not set."""
    with patch("scheduler.reminders._bot_instance", None):
        result = await send_reminder("booking_123", 123456789, datetime.now())

        assert result is False


@pytest.mark.asyncio
async def test_send_reminder_bot_error(mock_bot):
    """Test reminder sending handles bot errors."""
    booking_id = "booking_123"
    client_telegram_id = 123456789
    slot_time = datetime.now() + timedelta(hours=24)

    mock_bot.send_message.side_effect = Exception("Bot error")

    with patch("scheduler.reminders._bot_instance", mock_bot):
        result = await send_reminder(booking_id, client_telegram_id, slot_time)

        assert result is False


@pytest.mark.asyncio
async def test_check_and_send_reminders_no_bookings(mock_bot):
    """Test reminder check when no bookings need reminders."""
    with patch("scheduler.reminders.get_db_client") as mock_db_client, patch(
        "scheduler.reminders._bot_instance", mock_bot
    ), patch("scheduler.reminders.settings") as mock_settings:
        mock_settings.reminder_hours_before = 24
        mock_db = AsyncMock()
        mock_db.get_bookings_for_reminder = AsyncMock(return_value=[])
        mock_db_client.return_value = mock_db

        await check_and_send_reminders()

        mock_db.get_bookings_for_reminder.assert_called_once_with(24)
        mock_bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_check_and_send_reminders_with_bookings(mock_bot):
    """Test reminder check when bookings need reminders."""
    booking = MagicMock()
    booking.id = "booking_123"
    booking.slot_id = "slot_123"
    booking.client_id = "client_123"

    slot = MagicMock()
    slot.start_time = datetime.now() + timedelta(hours=23)

    client = MagicMock()
    client.telegram_id = 123456789

    mock_booking_updated = MagicMock()
    mock_booking_updated.id = "booking_123"

    with patch("scheduler.reminders.get_db_client") as mock_db_client, patch(
        "scheduler.reminders._bot_instance", mock_bot
    ), patch("scheduler.reminders.settings") as mock_settings:
        mock_settings.reminder_hours_before = 24
        mock_db = AsyncMock()
        mock_db.get_bookings_for_reminder = AsyncMock(return_value=[booking])
        mock_db.get_slot_by_id = AsyncMock(return_value=slot)
        mock_db.client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "client_123", "telegram_id": 123456789}
        ]
        mock_db.mark_reminder_sent = AsyncMock(return_value=mock_booking_updated)
        mock_db_client.return_value = mock_db

        await check_and_send_reminders()

        mock_bot.send_message.assert_called_once()
        mock_db.mark_reminder_sent.assert_called_once()


def test_setup_scheduler(mock_bot):
    """Test scheduler setup."""
    with patch("scheduler.reminders.scheduler") as mock_scheduler:
        mock_scheduler.add_job = MagicMock()
        mock_scheduler.start = MagicMock()

        setup_scheduler(bot=mock_bot)

        mock_scheduler.add_job.assert_called_once()
        mock_scheduler.start.assert_called_once()
