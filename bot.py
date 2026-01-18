"""
Main entry point for Telegram Beauty Salon Booking Bot.
Supports both polling and webhook modes.
"""

import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from bot import register_handlers
from bot.admin_handlers import register_admin_handlers
from config import settings
from scheduler import setup_scheduler
from utils.logging_config import setup_logging

# Configure logging using centralized configuration
logger = setup_logging(
    name=__name__, log_level="INFO", log_file="bot.log", log_dir="logs"
)

# Validate configuration
try:
    settings.validate_all_required()
except ValueError as e:
    logger.error(f"Configuration error: {e}")
    sys.exit(1)

# Initialize bot and dispatcher
bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

dp = Dispatcher(storage=MemoryStorage())


async def on_startup(bot: Bot) -> None:
    """Configure webhook on startup."""
    if settings.bot_webhook_url:
        webhook_path = "/webhook/telegram"
        webhook_url = f"{settings.bot_webhook_url.rstrip('/')}{webhook_path}"

        await bot.set_webhook(
            url=webhook_url,
            allowed_updates=dp.resolve_used_update_types(),
        )
        logger.info(f"Webhook configured: {webhook_url}")
    else:
        logger.info("Webhook URL not configured, using polling mode")


async def on_shutdown(bot: Bot) -> None:
    """Cleanup on shutdown."""
    if settings.bot_webhook_url:
        await bot.delete_webhook()
        logger.info("Webhook removed")

    from scheduler import shutdown_scheduler

    shutdown_scheduler()
    logger.info("Scheduler stopped")


async def main() -> None:
    """Main async function to run the bot."""
    try:
        logger.info("Starting Telegram Beauty Salon Bot...")

        # Register handlers
        register_handlers(dp)
        register_admin_handlers(dp)
        logger.info("Handlers registered")

        # Setup scheduler for reminders with bot instance
        setup_scheduler(bot=bot)
        logger.info("Scheduler started")

        # Choose webhook or polling mode
        if settings.bot_webhook_url:
            # Webhook mode (production)
            app = web.Application()

            # Setup webhook handler
            webhook_requests_handler = SimpleRequestHandler(
                dispatcher=dp,
                bot=bot,
            )
            webhook_requests_handler.register(app, path="/webhook/telegram")

            # Setup startup/shutdown handlers
            setup_application(app, dp, bot=bot)

            # Configure webhook on startup
            await on_startup(bot)

            # Start webhook server
            logger.info(
                f"Bot webhook server starting on {settings.host}:{settings.port}"
            )
            await web._run_app(
                app,
                host=settings.host,
                port=settings.port,
            )
        else:
            # Polling mode (development)
            logger.info("Bot is running in polling mode. Press Ctrl+C to stop.")
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except asyncio.CancelledError:
        logger.info("Bot cancelled")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise  # Re-raise to ensure proper exit code
    finally:
        # Cleanup resources
        logger.info("Shutting down...")
        await on_shutdown(bot)

        try:
            await bot.session.close()
            logger.info("Bot session closed")
        except Exception as e:
            logger.error(f"Error closing bot session: {e}", exc_info=True)

        logger.info("Bot shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
