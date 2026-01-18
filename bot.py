"""
Main entry point for Telegram Beauty Salon Booking Bot.
"""

import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot import register_handlers
from config import settings
from scheduler import setup_scheduler
from utils.logging_config import setup_logging

# Configure logging using centralized configuration
logger = setup_logging(
    name=__name__,
    log_level="INFO",
    log_file="bot.log",
    log_dir="logs"
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


async def main() -> None:
    """Main async function to run the bot."""
    try:
        logger.info("Starting Telegram Beauty Salon Bot...")

        # Register handlers
        register_handlers(dp)
        logger.info("Handlers registered")

        # Setup scheduler for reminders with bot instance
        setup_scheduler(bot=bot)
        logger.info("Scheduler started")

        # Start polling
        logger.info("Bot is running. Press Ctrl+C to stop.")
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
        try:
            from scheduler import shutdown_scheduler

            shutdown_scheduler()
            logger.info("Scheduler stopped")
        except Exception as e:
            logger.error(f"Error shutting down scheduler: {e}", exc_info=True)

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
