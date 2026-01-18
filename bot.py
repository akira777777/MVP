"""
Main entry point for Telegram Beauty Salon Booking Bot.
"""

import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot import register_handlers
from config import settings
from scheduler import setup_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)

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

# Store bot instance for scheduler
from scheduler import reminders

reminders.bot_instance = bot

dp = Dispatcher(storage=MemoryStorage())


async def main():
    """Main async function to run the bot."""
    try:
        logger.info("Starting Telegram Beauty Salon Bot...")

        # Register handlers
        register_handlers(dp)

        # Setup scheduler for reminders
        setup_scheduler()
        logger.info("Scheduler started")

        # Start polling
        logger.info("Bot is running. Press Ctrl+C to stop.")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        # Cleanup
        from scheduler import shutdown_scheduler

        shutdown_scheduler()
        await bot.session.close()
        logger.info("Bot shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
