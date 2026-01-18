"""
Configuration module for Telegram Beauty Salon Bot.
Loads environment variables and provides typed configuration.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Telegram Bot
    bot_token: str

    # Supabase
    supabase_url: str
    supabase_key: str

    # Stripe
    stripe_secret_key: str
    stripe_publishable_key: str
    stripe_webhook_secret: Optional[str] = None

    # Claude AI
    claude_api_key: str

    # Bot Settings
    timezone: str = "Europe/Prague"
    reminder_hours_before: int = 24

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def validate_all_required(self) -> None:
        """Validate that all required settings are present."""
        required_fields = [
            "bot_token",
            "supabase_url",
            "supabase_key",
            "stripe_secret_key",
            "stripe_publishable_key",
            "claude_api_key",
        ]

        missing = []
        for field in required_fields:
            value = getattr(self, field, None)
            if not value or value.startswith("your_") or value.startswith("sk_test_") and "test" in field:
                # Allow test keys but warn
                if "test" not in str(value):
                    missing.append(field)

        if missing:
            raise ValueError(
                f"Missing required configuration: {', '.join(missing)}. "
                f"Please check your .env file."
            )


# Global settings instance
settings = Settings()
