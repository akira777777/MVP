"""
Unit tests for admin panel functionality.
Tests admin handlers and access control.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import CallbackQuery, Message, User

from bot.handlers import is_admin_user
from config import settings


@pytest.fixture
def mock_admin_user():
    """Mock admin user."""
    user = MagicMock(spec=User)
    user.id = 123456789
    return user


@pytest.fixture
def mock_non_admin_user():
    """Mock non-admin user."""
    user = MagicMock(spec=User)
    user.id = 999999999
    return user


def test_is_admin_user_with_admin_id(mock_admin_user):
    """Test admin check with admin ID."""
    with patch("bot.handlers.settings") as mock_settings:
        mock_settings.is_admin.return_value = True
        assert is_admin_user(mock_admin_user.id) is True


def test_is_admin_user_with_non_admin_id(mock_non_admin_user):
    """Test admin check with non-admin ID."""
    with patch("bot.handlers.settings") as mock_settings:
        mock_settings.is_admin.return_value = False
        assert is_admin_user(mock_non_admin_user.id) is False


@pytest.mark.asyncio
async def test_admin_command_access_denied(mock_non_admin_user):
    """Test /admin command denies access to non-admin."""
    from bot.handlers import cmd_admin

    message = MagicMock(spec=Message)
    message.from_user = mock_non_admin_user
    message.answer = AsyncMock()
    state = MagicMock()

    with patch("bot.handlers.is_admin_user", return_value=False):
        await cmd_admin(message, state)
        message.answer.assert_called_once()
        assert "denied" in message.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_admin_command_access_granted(mock_admin_user):
    """Test /admin command grants access to admin."""
    from bot.handlers import cmd_admin

    message = MagicMock(spec=Message)
    message.from_user = mock_admin_user
    message.answer = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()

    with patch("bot.handlers.is_admin_user", return_value=True), patch(
        "bot.handlers.get_admin_menu_keyboard"
    ) as mock_keyboard:
        await cmd_admin(message, state)
        message.answer.assert_called_once()
        state.clear.assert_called_once()


@pytest.mark.asyncio
async def test_admin_slots_menu_access_denied(mock_non_admin_user):
    """Test admin slots menu denies access to non-admin."""
    from bot.handlers import admin_slots_menu

    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = mock_non_admin_user
    callback.answer = AsyncMock()
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    state = MagicMock()

    with patch("bot.handlers.is_admin_user", return_value=False):
        await admin_slots_menu(callback, state)
        callback.answer.assert_called_once()
        assert "denied" in callback.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_admin_list_slots(mock_admin_user):
    """Test admin list slots functionality."""
    from bot.handlers import admin_list_slots

    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = mock_admin_user
    callback.answer = AsyncMock()
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    state = MagicMock()

    mock_slots = [
        MagicMock(
            id="slot_123",
            start_time=MagicMock(strftime=lambda fmt: "15.01.2026 10:00"),
            service_type="manicure",
            status=MagicMock(value="available"),
        )
    ]

    with patch("bot.handlers.is_admin_user", return_value=True), patch(
        "bot.handlers.get_db_client"
    ) as mock_db_client, patch("bot.handlers.get_admin_slots_keyboard") as mock_keyboard:
        mock_db = AsyncMock()
        mock_db.get_all_slots = AsyncMock(return_value=mock_slots)
        mock_db_client.return_value = mock_db

        await admin_list_slots(callback)

        callback.message.edit_text.assert_called_once()
        mock_db.get_all_slots.assert_called_once()


@pytest.mark.asyncio
async def test_admin_view_bookings(mock_admin_user):
    """Test admin view bookings functionality."""
    from bot.handlers import admin_view_bookings

    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = mock_admin_user
    callback.data = "admin_bookings_pending"
    callback.answer = AsyncMock()
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()

    mock_booking = MagicMock(
        id="booking_123",
        service_type="manicure",
        status=MagicMock(value="pending"),
        price_czk=150,
        slot_id="slot_123",
    )
    mock_slot = MagicMock(
        start_time=MagicMock(strftime=lambda fmt: "15.01.2026 10:00")
    )

    with patch("bot.handlers.is_admin_user", return_value=True), patch(
        "bot.handlers.get_db_client"
    ) as mock_db_client, patch("bot.handlers.get_admin_bookings_keyboard") as mock_keyboard:
        mock_db = AsyncMock()
        mock_db.get_all_bookings = AsyncMock(return_value=[mock_booking])
        mock_db.get_slot_by_id = AsyncMock(return_value=mock_slot)
        mock_db_client.return_value = mock_db

        await admin_view_bookings(callback)

        callback.message.edit_text.assert_called_once()
        mock_db.get_all_bookings.assert_called_once()
