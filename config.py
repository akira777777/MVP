"""
Configuration module for Telegram Beauty Salon Bot.
Loads environment variables and provides typed configuration.
"""

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
    stripe_webhook_secret: Optional[str] = (
        None  # Required in production for webhook verification
    )

    # Claude AI
    claude_api_key: str

    # Google Maps API (for lead generation)
    google_maps_api_key: Optional[str] = None
    google_maps_rate_limit_per_minute: int = 60

    # Lead Generation Settings
    lead_generation_enabled: bool = False
    lead_generation_batch_size: int = 50
    lead_generation_delay_seconds: float = 2.0
    lead_generation_max_retries: int = 3
    lead_generation_use_api: bool = True  # Приоритет API
    lead_generation_use_mcp: bool = True  # Fallback на MCP
    lead_generation_use_scraper: bool = False  # Последний fallback

    # Bot Settings
    timezone: str = "Europe/Prague"
    reminder_hours_before: int = 24

    # Admin Settings
    admin_telegram_ids: str = (
        ""  # Comma-separated Telegram user IDs (e.g., "123456,789012")
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    environment: str = "development"  # development, staging, production
    # Set via ENVIRONMENT env var, defaults to development

    # Webhook Configuration
    bot_webhook_url: Optional[str] = (
        None  # Full webhook URL for bot (e.g., https://yourdomain.com/webhook/telegram)
    )

    # Redis Configuration (for APScheduler cluster support)
    redis_url: Optional[str] = (
        None  # Redis connection URL (e.g., redis://localhost:6379/0)
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def is_admin(self, telegram_id: int) -> bool:
        """
        Check if a Telegram user ID is an admin.

        Args:
            telegram_id: Telegram user ID to check

        Returns:
            True if user is admin, False otherwise
        """
        if not self.admin_telegram_ids:
            return False
        admin_ids = [
            int(id.strip()) for id in self.admin_telegram_ids.split(",") if id.strip()
        ]
        return telegram_id in admin_ids

    def validate_all_required(self) -> None:
        """
        Validate that all required settings are present.

        Raises:
            ValueError: If required fields are missing or invalid
        """
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

            # Check if value is missing or placeholder
            if not value:
                missing.append(field)
                continue

            # Check for placeholder values
            value_str = str(value).lower()
            if value_str.startswith("your_"):
                missing.append(field)
                continue

            # Special handling for Stripe test keys
            # Test keys (sk_test_*, pk_test_*) are valid for development
            if "stripe" in field.lower() and (
                value_str.startswith("sk_test_") or value_str.startswith("pk_test_")
            ):
                continue  # Test keys are acceptable

        if missing:
            raise ValueError(
                f"Missing or invalid required configuration: "
                f"{', '.join(missing)}. "
                f"Please check your .env file and ensure all required "
                f"values are set."
            )


# Global settings instance
settings = Settings()
