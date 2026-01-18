"""
Admin panel handlers for slot management and bookings view.
Accessible only to configured admin users.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.keyboards import get_back_to_menu_keyboard
from config import settings
from db import get_db_client
from models.booking import BookingStatus
from models.slot import SlotCreate, SlotStatus
from utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

admin_router = Router()


def is_admin_user(telegram_id: int) -> bool:
    """Check if user is admin."""
    return settings.is_admin(telegram_id)


async def require_admin(message: Message) -> bool:
    """Check admin access and send error if not admin."""
    if not is_admin_user(message.from_user.id):
        await message.answer(
            "❌ Access denied. This command is only available to administrators."
        )
        return False
    return True


# ========== Admin Menu ==========


@admin_router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Admin panel entry point."""
    if not await require_admin(message):
        return

    admin_text = (
        "🔐 <b>Admin Panel</b>\n\n"
        "Available commands:\n"
        "• /admin_slots - Manage time slots\n"
        "• /admin_bookings - View all bookings\n"
        "• /admin_stats - View statistics\n\n"
        "Use commands above to manage the salon."
    )

    await message.answer(admin_text, parse_mode="HTML")


# ========== Slot Management ==========


@admin_router.message(Command("admin_slots"))
async def cmd_admin_slots(message: Message):
    """Show slot management menu."""
    if not await require_admin(message):
        return

    db = get_db_client()

    # Get upcoming slots (next 7 days)
    start_date = utc_now()
    end_date = start_date + timedelta(days=7)

    try:
        # Get all slots in the next 7 days
        response = (
            db.client.table("slots")
            .select("*")
            .gte("start_time", start_date.isoformat())
            .lte("start_time", end_date.isoformat())
            .order("start_time", desc=False)
            .execute()
        )

        slots = response.data if response.data else []

        if not slots:
            await message.answer(
                "📅 No slots found for the next 7 days.\n\n"
                "Use /admin_create_slot to create new slots.",
                reply_markup=get_admin_slots_keyboard(),
            )
            return

        # Group by status
        available = [s for s in slots if s.get("status") == SlotStatus.AVAILABLE.value]
        booked = [s for s in slots if s.get("status") == SlotStatus.BOOKED.value]

        stats_text = (
            f"📅 <b>Slot Management</b>\n\n"
            f"Next 7 days:\n"
            f"• Available: {len(available)}\n"
            f"• Booked: {len(booked)}\n"
            f"• Total: {len(slots)}\n\n"
            f"<b>Upcoming slots:</b>\n"
        )

        # Show first 10 slots
        for slot in slots[:10]:
            start_time = datetime.fromisoformat(slot["start_time"].replace("Z", "+00:00"))
            status_emoji = "✅" if slot["status"] == SlotStatus.AVAILABLE.value else "🔒"
            stats_text += (
                f"{status_emoji} {start_time.strftime('%d.%m %H:%M')} - "
                f"{slot['service_type']} ({slot['status']})\n"
            )

        if len(slots) > 10:
            stats_text += f"\n... and {len(slots) - 10} more"

        await message.answer(
            stats_text,
            parse_mode="HTML",
            reply_markup=get_admin_slots_keyboard(),
        )

    except Exception as e:
        logger.error(f"Error fetching slots: {e}", exc_info=True)
        await message.answer(
            f"❌ Error loading slots: {e}",
            reply_markup=get_admin_slots_keyboard(),
        )


@admin_router.message(Command("admin_create_slot"))
async def cmd_admin_create_slot(message: Message):
    """Create a new slot (interactive)."""
    if not await require_admin(message):
        return

    await message.answer(
        "📅 <b>Create New Slot</b>\n\n"
        "Format: /create_slot YYYY-MM-DD HH:MM SERVICE_TYPE\n\n"
        "Example:\n"
        "<code>/create_slot 2024-12-25 14:00 manicure</code>\n\n"
        "Available services: manicure, haircut, pedicure, facial",
        parse_mode="HTML",
    )


@admin_router.message(Command("create_slot"))
async def cmd_create_slot(message: Message):
    """Create a slot from command."""
    if not await require_admin(message):
        return

    parts = message.text.split()
    if len(parts) < 4:
        await message.answer(
            "❌ Invalid format. Use:\n"
            "<code>/create_slot YYYY-MM-DD HH:MM SERVICE_TYPE</code>",
            parse_mode="HTML",
        )
        return

    try:
        date_str = parts[1]
        time_str = parts[2]
        service_type = parts[3]

        # Parse datetime
        datetime_str = f"{date_str} {time_str}"
        start_time = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        start_time = start_time.replace(tzinfo=None)  # Make naive for UTC conversion
        start_time = datetime.utcnow().replace(
            year=start_time.year,
            month=start_time.month,
            day=start_time.day,
            hour=start_time.hour,
            minute=start_time.minute,
        )

        # Validate service type
        valid_services = ["manicure", "haircut", "pedicure", "facial"]
        if service_type not in valid_services:
            await message.answer(
                f"❌ Invalid service type. Use one of: {', '.join(valid_services)}"
            )
            return

        # Create slot (1 hour duration)
        end_time = start_time + timedelta(hours=1)

        db = get_db_client()
        slot_data = SlotCreate(
            start_time=start_time,
            end_time=end_time,
            service_type=service_type,
            status=SlotStatus.AVAILABLE,
        )

        slot = await db.create_slot(slot_data)

        await message.answer(
            f"✅ Slot created!\n\n"
            f"ID: {slot.id[:8]}...\n"
            f"Time: {start_time.strftime('%d.%m.%Y %H:%M')}\n"
            f"Service: {service_type}\n"
            f"Status: {slot.status.value}",
        )

    except ValueError as e:
        await message.answer(f"❌ Invalid date/time format: {e}")
    except Exception as e:
        logger.error(f"Error creating slot: {e}", exc_info=True)
        await message.answer(f"❌ Error creating slot: {e}")


# ========== Bookings View ==========


@admin_router.message(Command("admin_bookings"))
async def cmd_admin_bookings(message: Message):
    """View all bookings."""
    if not await require_admin(message):
        return

    db = get_db_client()

    try:
        # Get recent bookings (last 30 days)
        start_date = utc_now() - timedelta(days=30)

        response = (
            db.client.table("bookings")
            .select("*, clients(*), slots(*)")
            .gte("created_at", start_date.isoformat())
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )

        bookings = response.data if response.data else []

        if not bookings:
            await message.answer("📋 No bookings found in the last 30 days.")
            return

        # Group by status
        pending = [b for b in bookings if b.get("status") == BookingStatus.PENDING.value]
        paid = [b for b in bookings if b.get("status") == BookingStatus.PAID.value]
        confirmed = [
            b for b in bookings if b.get("status") == BookingStatus.CONFIRMED.value
        ]
        cancelled = [
            b for b in bookings if b.get("status") == BookingStatus.CANCELLED.value
        ]

        stats_text = (
            f"📋 <b>All Bookings (Last 30 Days)</b>\n\n"
            f"<b>Statistics:</b>\n"
            f"• Pending: {len(pending)}\n"
            f"• Confirmed: {len(confirmed)}\n"
            f"• Paid: {len(paid)}\n"
            f"• Cancelled: {len(cancelled)}\n"
            f"• Total: {len(bookings)}\n\n"
            f"<b>Recent bookings:</b>\n"
        )

        # Show first 10 bookings
        for booking in bookings[:10]:
            client = booking.get("clients", {})
            slot = booking.get("slots", {})
            client_name = (
                f"{client.get('first_name', '')} {client.get('last_name', '')}".strip()
                or "Unknown"
            )

            slot_time = "N/A"
            if slot and slot.get("start_time"):
                try:
                    slot_dt = datetime.fromisoformat(
                        slot["start_time"].replace("Z", "+00:00")
                    )
                    slot_time = slot_dt.strftime("%d.%m %H:%M")
                except:
                    pass

            status_emoji = {
                BookingStatus.PENDING.value: "⏳",
                BookingStatus.CONFIRMED.value: "✅",
                BookingStatus.PAID.value: "💳",
                BookingStatus.CANCELLED.value: "❌",
            }.get(booking.get("status"), "❓")

            stats_text += (
                f"{status_emoji} {client_name} - {slot_time} - "
                f"{booking.get('service_type', 'N/A')} "
                f"({booking.get('price_czk', 0)} CZK)\n"
            )

        if len(bookings) > 10:
            stats_text += f"\n... and {len(bookings) - 10} more"

        await message.answer(stats_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error fetching bookings: {e}", exc_info=True)
        await message.answer(f"❌ Error loading bookings: {e}")


# ========== Statistics ==========


@admin_router.message(Command("admin_stats"))
async def cmd_admin_stats(message: Message):
    """Show admin statistics."""
    if not await require_admin(message):
        return

    db = get_db_client()

    try:
        # Get client count
        clients_response = db.client.table("clients").select("id", count="exact").execute()
        client_count = clients_response.count if hasattr(clients_response, "count") else 0

        # Get booking stats
        bookings_response = (
            db.client.table("bookings")
            .select("status", count="exact")
            .execute()
        )
        total_bookings = (
            bookings_response.count if hasattr(bookings_response, "count") else 0
        )

        # Get revenue (sum of paid bookings)
        revenue_response = (
            db.client.table("bookings")
            .select("price_czk")
            .eq("status", BookingStatus.PAID.value)
            .execute()
        )
        revenue = sum(b.get("price_czk", 0) for b in (revenue_response.data or []))

        # Get upcoming bookings
        upcoming_response = (
            db.client.table("bookings")
            .select("id")
            .in_("status", [BookingStatus.CONFIRMED.value, BookingStatus.PAID.value])
            .execute()
        )
        upcoming_count = len(upcoming_response.data or [])

        stats_text = (
            f"📊 <b>Admin Statistics</b>\n\n"
            f"<b>Overview:</b>\n"
            f"• Total Clients: {client_count}\n"
            f"• Total Bookings: {total_bookings}\n"
            f"• Upcoming Appointments: {upcoming_count}\n"
            f"• Total Revenue: {revenue} CZK\n\n"
            f"Use /admin_slots and /admin_bookings for detailed views."
        )

        await message.answer(stats_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error fetching stats: {e}", exc_info=True)
        await message.answer(f"❌ Error loading statistics: {e}")


# ========== Helper Functions ==========


def get_admin_slots_keyboard():
    """Get admin slots management keyboard."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_refresh_slots")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats")
    )
    return builder.as_markup()


def register_admin_handlers(dp) -> None:
    """Register admin handlers with dispatcher."""
    dp.include_router(admin_router)
