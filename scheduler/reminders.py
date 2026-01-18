"""
Scheduler for appointment reminders using APScheduler.
Sends reminders 24 hours before appointments.
"""

from datetime import datetime
from typing import Optional

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import settings
from db import get_db_client
from utils.exceptions import DatabaseError
from utils.logging_config import setup_logging

logger = setup_logging(
    name=__name__, log_level="INFO", log_file="scheduler.log", log_dir="logs"
)

scheduler = AsyncIOScheduler()

# Bot instance - injected via setup_scheduler
_bot_instance: Optional[Bot] = None


def set_bot_instance(bot: Bot) -> None:
    """Set the bot instance for sending reminders.

    Args:
        bot: Aiogram Bot instance
    """
    global _bot_instance
    _bot_instance = bot
    logger.info("Bot instance set for scheduler")


async def send_reminder(
    booking_id: str, client_telegram_id: int, slot_time: datetime
) -> bool:
    """
    Send reminder to client about upcoming appointment.

    Args:
        booking_id: Booking ID
        client_telegram_id: Telegram user ID
        slot_time: Appointment time

    Returns:
        True if sent successfully, False otherwise
    """
    global _bot_instance

    if not _bot_instance:
        logger.error("Bot instance not available - cannot send reminder")
        return False

    try:
        reminder_text = (
            f"🔔 Reminder: You have an appointment tomorrow!\n\n"
            f"Time: {slot_time.strftime('%d.%m.%Y at %H:%M')}\n\n"
            f"See you soon! 💅"
        )

        await _bot_instance.send_message(client_telegram_id, reminder_text)

        # Mark reminder as sent
        db = get_db_client()
        updated_booking = await db.mark_reminder_sent(booking_id)

        if not updated_booking:
            logger.warning(f"Failed to mark reminder as sent for booking {booking_id}")
            return False

        logger.info(
            f"Reminder sent for booking {booking_id} to user {client_telegram_id}"
        )
        return True

    except Exception as e:
        logger.error(
            f"Failed to send reminder for booking {booking_id}: {e}", exc_info=True
        )
        return False


async def check_and_send_reminders():
    """Check for bookings that need reminders and send them."""
    try:
        db = get_db_client()
        bookings = await db.get_bookings_for_reminder(settings.reminder_hours_before)

        if not bookings:
            logger.debug("No bookings require reminders at this time")
            return

        logger.info(f"Processing {len(bookings)} bookings for reminders")

        # Batch fetch slots and clients to reduce N+1 queries
        slot_ids = {booking.slot_id for booking in bookings}
        client_ids = {booking.client_id for booking in bookings}

        # Fetch all slots in batch
        slots_map = {}
        for slot_id in slot_ids:
            slot = await db.get_slot_by_id(slot_id)
            if slot:
                slots_map[slot_id] = slot

        # Fetch all clients in batch
        clients_map = {}
        for client_id in client_ids:
            try:
                client_response = (
                    db.client.table("clients").select("*").eq("id", client_id).execute()
                )
                if client_response.data:
                    from models.client import Client

                    clients_map[client_id] = Client(**client_response.data[0])
            except Exception as e:
                logger.warning(f"Failed to fetch client {client_id}: {e}")
                continue

        # Process each booking
        sent_count = 0
        failed_count = 0

        for booking in bookings:
            # Validate booking ID
            if not booking.id:
                logger.warning(f"Booking missing ID, skipping: {booking}")
                failed_count += 1
                continue

            # Get slot
            slot = slots_map.get(booking.slot_id)
            if not slot:
                logger.warning(
                    f"Slot {booking.slot_id} not found for booking {booking.id}"
                )
                failed_count += 1
                continue

            # Get client
            client = clients_map.get(booking.client_id)
            if not client:
                logger.warning(
                    f"Client {booking.client_id} not found for booking {booking.id}"
                )
                failed_count += 1
                continue

            # Send reminder
            success = await send_reminder(
                booking.id, client.telegram_id, slot.start_time
            )
            if success:
                sent_count += 1
            else:
                failed_count += 1

        logger.info(
            f"Reminder processing complete: {sent_count} sent, {failed_count} failed"
        )

    except DatabaseError as e:
        logger.error(f"Database error checking reminders: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error checking reminders: {e}", exc_info=True)


def setup_scheduler(bot: Optional[Bot] = None) -> None:
    """Setup and start the scheduler.

    Args:
        bot: Optional Bot instance to inject. If None, must be set later via set_bot_instance()
    """
    if bot:
        set_bot_instance(bot)

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
