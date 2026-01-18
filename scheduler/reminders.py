"""
Scheduler for appointment reminders using APScheduler.
Sends reminders 24 hours before appointments.
"""

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import settings
from db import get_db_client

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


# Bot instance will be set by bot.py
bot_instance = None


async def send_reminder(booking_id: str, client_telegram_id: int, slot_time: datetime) -> bool:
    """
    Send reminder to client about upcoming appointment.

    Args:
        booking_id: Booking ID
        client_telegram_id: Telegram user ID
        slot_time: Appointment time

    Returns:
        True if sent successfully
    """
    try:
        if not bot_instance:
            logger.error("Bot instance not available")
            return False

        reminder_text = (
            f"🔔 Reminder: You have an appointment tomorrow!\n\n"
            f"Time: {slot_time.strftime('%d.%m.%Y at %H:%M')}\n\n"
            f"See you soon! 💅"
        )

        await bot_instance.send_message(client_telegram_id, reminder_text)

        # Mark reminder as sent
        db = get_db_client()
        await db.mark_reminder_sent(booking_id)

        logger.info(f"Reminder sent for booking {booking_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to send reminder: {e}", exc_info=True)
        return False


async def check_and_send_reminders():
    """Check for bookings that need reminders and send them."""
    try:
        db = get_db_client()
        bookings = await db.get_bookings_for_reminder(settings.reminder_hours_before)

        for booking in bookings:
            slot = await db.get_slot_by_id(booking.slot_id)
            if not slot:
                continue

            # Get client
            client_response = (
                db.client.table("clients")
                .select("*")
                .eq("id", booking.client_id)
                .execute()
            )

            if not client_response.data:
                continue

            from models.client import Client
            client = Client(**client_response.data[0])

            # Send reminder
            await send_reminder(booking.id, client.telegram_id, slot.start_time)

    except Exception as e:
        logger.error(f"Error checking reminders: {e}", exc_info=True)


def setup_scheduler():
    """Setup and start the scheduler."""
    # Run reminder check every hour
    scheduler.add_job(
        check_and_send_reminders,
        trigger=CronTrigger(minute=0),  # Every hour at minute 0
        id="check_reminders",
        name="Check and send appointment reminders",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started")


def shutdown_scheduler():
    """Shutdown the scheduler."""
    scheduler.shutdown()
    logger.info("Scheduler stopped")
