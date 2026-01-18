"""
Inline keyboards for bot interactions.
"""

from typing import List, Optional

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from models.booking import Booking
from models.service import Service, ServiceType, get_all_services
from models.slot import Slot


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Get main menu keyboard."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📅 Book Appointment", callback_data="book_appointment")
    )
    builder.row(
        InlineKeyboardButton(text="📋 My Bookings", callback_data="my_bookings")
    )
    builder.row(
        InlineKeyboardButton(text="❓ Ask Question", callback_data="ask_question")
    )
    builder.row(
        InlineKeyboardButton(text="ℹ️ About", callback_data="about")
    )

    return builder.as_markup()


def get_services_keyboard() -> InlineKeyboardMarkup:
    """Get services selection keyboard."""
    builder = InlineKeyboardBuilder()

    services = get_all_services()
    for service in services:
        builder.row(
            InlineKeyboardButton(
                text=f"{service.name} - {service.price_czk} CZK",
                callback_data=f"service_{service.type.value}",
            )
        )

    builder.row(InlineKeyboardButton(text="🔙 Back", callback_data="main_menu"))

    return builder.as_markup()


def get_slots_keyboard(slots: List[Slot], service_type: str) -> InlineKeyboardMarkup:
    """Get available slots keyboard."""
    builder = InlineKeyboardBuilder()

    if not slots:
        builder.row(
            InlineKeyboardButton(text="🔙 Back to Services", callback_data="book_appointment")
        )
        return builder.as_markup()

    for slot in slots[:10]:  # Limit to 10 slots
        time_str = slot.start_time.strftime("%d.%m %H:%M")
        builder.row(
            InlineKeyboardButton(
                text=time_str,
                callback_data=f"slot_{slot.id}_{service_type}",
            )
        )

    builder.row(InlineKeyboardButton(text="🔙 Back to Services", callback_data="book_appointment"))

    return builder.as_markup()


def get_confirm_booking_keyboard(booking_id: str) -> InlineKeyboardMarkup:
    """Get booking confirmation keyboard."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Confirm & Pay", callback_data=f"confirm_booking_{booking_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_booking")
    )

    return builder.as_markup()


def get_gdpr_consent_keyboard() -> InlineKeyboardMarkup:
    """Get GDPR consent keyboard."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="✅ I Agree", callback_data="gdpr_agree")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Decline", callback_data="gdpr_decline")
    )

    return builder.as_markup()


def get_payment_keyboard(payment_url: str, booking_id: str) -> InlineKeyboardMarkup:
    """Get payment keyboard with Stripe link."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="💳 Pay Now", url=payment_url)
    )
    builder.row(
        InlineKeyboardButton(
            text="✅ Payment Completed", callback_data=f"payment_done_{booking_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="❌ Cancel Booking", callback_data=f"cancel_booking_{booking_id}")
    )

    return builder.as_markup()


def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Get simple back to menu keyboard."""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="🔙 Main Menu", callback_data="main_menu"))

    return builder.as_markup()


def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Get admin menu keyboard."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📅 Manage Slots", callback_data="admin_slots")
    )
    builder.row(
        InlineKeyboardButton(text="📋 View Bookings", callback_data="admin_bookings")
    )
    builder.row(
        InlineKeyboardButton(text="➕ Create Slot", callback_data="admin_create_slot")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Main Menu", callback_data="main_menu")
    )

    return builder.as_markup()


def get_slot_management_keyboard(slot_id: str) -> InlineKeyboardMarkup:
    """Get slot management keyboard."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="❌ Delete Slot", callback_data=f"admin_delete_slot_{slot_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Back to Admin", callback_data="admin_menu")
    )

    return builder.as_markup()


def get_bookings_list_keyboard(bookings: List, page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    """Get bookings list keyboard with pagination."""
    builder = InlineKeyboardBuilder()

    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_bookings = bookings[start_idx:end_idx]

    for booking in page_bookings:
        builder.row(
            InlineKeyboardButton(
                text=f"📋 {booking.id[:8]}... - {booking.status.value}",
                callback_data=f"admin_booking_{booking.id}",
            )
        )

    # Pagination
    if page > 0:
        builder.row(
            InlineKeyboardButton(
                text="⬅️ Previous", callback_data=f"admin_bookings_page_{page - 1}"
            )
        )
    if end_idx < len(bookings):
        builder.row(
            InlineKeyboardButton(
                text="➡️ Next", callback_data=f"admin_bookings_page_{page + 1}"
            )
        )

    builder.row(
        InlineKeyboardButton(text="🔙 Back to Admin", callback_data="admin_menu")
    )

    return builder.as_markup()
