"""
Unit tests for bot handlers.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import CallbackQuery, Message, User

from bot.handlers import is_admin


class TestAdminHandlers:
    """Test admin handlers."""

    @pytest.fixture
    def mock_message(self):
        """Create mock message."""
        user = User(
            id=123456789,
            is_bot=False,
            first_name="Test",
        )
        message = MagicMock(spec=Message)
        message.from_user = user
        message.chat.id = 123456789
        return message

    @pytest.fixture
    def mock_callback(self):
        """Create mock callback query."""
        user = User(
            id=123456789,
            is_bot=False,
            first_name="Test",
        )
        callback = MagicMock(spec=CallbackQuery)
        callback.from_user = user
        callback.data = "admin_menu"
        callback.message = MagicMock()
        callback.message.edit_text = AsyncMock()
        callback.message.answer = MagicMock()
        callback.answer = AsyncMock()
        return callback

    def test_is_admin_true(self):
        """Test admin check returns True for admin user."""
        with patch("bot.handlers.settings") as mock_settings:
            mock_settings.admin_telegram_ids = "123456789,987654321"
            
            assert is_admin(123456789) is True
            assert is_admin(987654321) is True

    def test_is_admin_false(self):
        """Test admin check returns False for non-admin user."""
        with patch("bot.handlers.settings") as mock_settings:
            mock_settings.admin_telegram_ids = "123456789"
            
            assert is_admin(999999999) is False

    def test_is_admin_no_config(self):
        """Test admin check returns False when no admin IDs configured."""
        with patch("bot.handlers.settings") as mock_settings:
            mock_settings.admin_telegram_ids = None
            
            assert is_admin(123456789) is False

    @pytest.mark.asyncio
    async def test_cmd_admin_access_denied(self, mock_message):
        """Test /admin command denies access to non-admin."""
        from bot.handlers import cmd_admin
        from aiogram.fsm.context import FSMContext
        
        with patch("bot.handlers.is_admin", return_value=False), patch(
            "bot.handlers.Message.answer", new_callable=AsyncMock
        ) as mock_answer:
            mock_state = MagicMock(spec=FSMContext)
            mock_state.clear = AsyncMock()
            
            await cmd_admin(mock_message, mock_state)
            
            mock_answer.assert_called_once()
            call_args = mock_answer.call_args[0][0]
            assert "Access denied" in call_args

    @pytest.mark.asyncio
    async def test_cmd_admin_success(self, mock_message):
        """Test /admin command allows access to admin."""
        from bot.handlers import cmd_admin
        from aiogram.fsm.context import FSMContext
        
        with patch("bot.handlers.is_admin", return_value=True), patch(
            "bot.handlers.Message.answer", new_callable=AsyncMock
        ) as mock_answer:
            mock_state = MagicMock(spec=FSMContext)
            mock_state.clear = AsyncMock()
            
            await cmd_admin(mock_message, mock_state)
            
            mock_answer.assert_called_once()
            call_args = mock_answer.call_args[0][0]
            assert "Admin Panel" in call_args
