"""
Pytest configuration and shared fixtures.
"""

import os
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_settings():
    """Mock settings for all tests."""
    with patch("config.settings") as mock_settings:
        mock_settings.bot_token = "test_token"
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_key = "test_key"
        mock_settings.stripe_secret_key = "sk_test_123"
        mock_settings.stripe_publishable_key = "pk_test_123"
        mock_settings.stripe_webhook_secret = "whsec_test_123"
        mock_settings.claude_api_key = "sk-ant-test"
        mock_settings.environment = "test"
        mock_settings.host = "0.0.0.0"
        mock_settings.port = 8000
        mock_settings.bot_webhook_url = None
        mock_settings.redis_url = None
        mock_settings.admin_telegram_ids = None
        yield mock_settings


@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client."""
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    return mock_client, mock_table
