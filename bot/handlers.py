"""
Bot handlers for Telegram beauty salon booking bot.
Handles all user interactions: booking, payments, GDPR, AI Q&A.
"""

import logging
from datetime import timedelta

from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards import (
    get_back_to_menu_keyboard,
    get_confirm_booking_keyboard,
    get_gdpr_consent_keyboard,
    get_main_menu_keyboard,
    get_payment_keyboard,
    get_services_keyboard,
    get_slots_keyboard,
)
from bot.states import AIQnAStates, BookingStates, GDPRStates
from db import get_db_client
from models.booking import BookingStatus
from models.client import ClientCreate
from models.service import ServiceType, get_service
from models.slot import SlotStatus
from payments import create_payment_intent, get_payment_intent
from utils.ai_qa import get_ai_response
from utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

router = Router()


# ========== Start Command & Main Menu ==========


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command."""
    await state.clear()

    db = get_db_client()
    user = message.from_user

    # Check if user exists, create if not
    client = await db.get_client_by_telegram_id(user.id)
    if not client:
        client_data = ClientCreate(
            telegram_id=user.id,
            first_name=user.first_name or "User",
            last_name=user.last_name,
            username=user.username,
        )
        client = await db.create_client(client_data)

    # Check GDPR consent
    if not client.gdpr_consent:
        await show_gdpr_consent(message, state)
        return

    await message.answer(
        "👋 Welcome to Beauty Salon Bot!\n\n"
        "Choose an option:",
        reply_markup=get_main_menu_keyboard(),
    )


@router.callback_query(lambda c: c.data == "main_menu")
async def show_main_menu(callback: CallbackQuery, state: FSMContext):
    """Show main menu."""
    await state.clear()
    await callback.message.edit_text(
        "👋 Welcome to Beauty Salon Bot!\n\n" "Choose an option:",
        reply_markup=get_main_menu_keyboard(),
    )
    await callback.answer()


# ========== GDPR Consent ==========


async def show_gdpr_consent(message: Message, state: FSMContext):
    """Show GDPR consent screen."""
    await state.set_state(GDPRStates.waiting_for_consent)

    gdpr_text = (
        "📋 GDPR Consent\n\n"
        "To use our booking service, we need your consent to process your personal data:\n\n"
        "• Your name and contact information for appointment management\n"
        "• Payment information processed securely via Stripe\n"
        "• Appointment reminders via Telegram\n\n"
        "Your data is stored securely and used only for booking purposes.\n"
        "You can request deletion at any time.\n\n"
        "Do you agree to our data processing?"
    )

    if isinstance(message, CallbackQuery):
        await message.message.edit_text(gdpr_text, reply_markup=get_gdpr_consent_keyboard())
        await message.answer()
    else:
        await message.answer(gdpr_text, reply_markup=get_gdpr_consent_keyboard())


@router.callback_query(lambda c: c.data == "gdpr_agree", StateFilter(GDPRStates.waiting_for_consent))
async def handle_gdpr_agree(callback: CallbackQuery, state: FSMContext):
    """Handle GDPR agreement."""
    db = get_db_client()
    await db.update_client_gdpr_consent(callback.from_user.id, True)

    await callback.message.edit_text(
        "✅ Thank you! You can now use our booking service.",
        reply_markup=get_main_menu_keyboard(),
    )
    await state.clear()
    await callback.answer()


@router.callback_query(lambda c: c.data == "gdpr_decline")
async def handle_gdpr_decline(callback: CallbackQuery):
    """Handle GDPR decline."""
    await callback.message.edit_text(
        "❌ We cannot provide our service without your consent.\n"
        "If you change your mind, use /start again.",
    )
    await callback.answer()


# ========== Booking Flow ==========


@router.callback_query(lambda c: c.data == "book_appointment")
async def start_booking(callback: CallbackQuery, state: FSMContext):
    """Start booking flow."""
    await state.set_state(BookingStates.selecting_service)

    await callback.message.edit_text(
        "📅 Book Appointment\n\n" "Select a service:",
        reply_markup=get_services_keyboard(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("service_"))
async def select_service(callback: CallbackQuery, state: FSMContext):
    """Handle service selection."""
    service_type_str = callback.data.split("_", 1)[1]
    try:
        service_type = ServiceType(service_type_str)
    except ValueError:
        await callback.answer("Invalid service type", show_alert=True)
        return

    service = get_service(service_type)
    await state.update_data(service_type=service_type.value, price_czk=service.price_czk)

    await state.set_state(BookingStates.selecting_slot)

    db = get_db_client()
    # Get available slots starting from tomorrow
    start_date = utc_now() + timedelta(days=1)
    slots = await db.get_available_slots(service_type.value, start_date)

    if not slots:
        await callback.message.edit_text(
            f"❌ No available slots for {service.name}.\n"
            "Please try another service or check back later.",
            reply_markup=get_back_to_menu_keyboard(),
        )
        await callback.answer()
        return

    slots_text = "\n".join(
        [
            f"• {slot.start_time.strftime('%d.%m.%Y %H:%M')}"
            for slot in slots[:5]
        ]
    )

    await callback.message.edit_text(
        f"📅 Available slots for {service.name} ({service.price_czk} CZK):\n\n{slots_text}\n\n"
        "Select a time slot:",
        reply_markup=get_slots_keyboard(slots, service_type.value),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("slot_"))
async def select_slot(callback: CallbackQuery, state: FSMContext):
    """Handle slot selection."""
    parts = callback.data.split("_")
    if len(parts) < 3:
        await callback.answer("Invalid slot selection", show_alert=True)
        return

    slot_id = parts[1]
    service_type = parts[2]

    data = await state.get_data()
    if not data.get("service_type"):
        await state.update_data(service_type=service_type)

    await state.update_data(slot_id=slot_id)

    db = get_db_client()
    slot = await db.get_slot_by_id(slot_id)

    if not slot or slot.status != SlotStatus.AVAILABLE:
        await callback.answer("This slot is no longer available", show_alert=True)
        await start_booking(callback, state)
        return

    service = get_service(ServiceType(service_type))
    price = data.get("price_czk", service.price_czk)

    booking_summary = (
        f"📋 Booking Summary\n\n"
        f"Service: {service.name}\n"
        f"Date & Time: {slot.start_time.strftime('%d.%m.%Y at %H:%M')}\n"
        f"Price: {price} CZK\n\n"
        f"Confirm and proceed to payment?"
    )

    await state.set_state(BookingStates.confirming_booking)
    await callback.message.edit_text(
        booking_summary,
        reply_markup=get_confirm_booking_keyboard("pending"),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("confirm_booking_"))
async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    """Confirm booking and create payment."""
    data = await state.get_data()
    slot_id = data.get("slot_id")
    service_type = data.get("service_type")
    price_czk = data.get("price_czk")

    if not all([slot_id, service_type, price_czk]):
        await callback.answer("Missing booking information", show_alert=True)
        await state.clear()
        await callback.message.edit_text(
            "👋 Welcome to Beauty Salon Bot!\n\n" "Choose an option:",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    db = get_db_client()

    # Get client
    client = await db.get_client_by_telegram_id(callback.from_user.id)
    if not client:
        await callback.answer("Client not found. Please use /start", show_alert=True)
        return

    # Verify slot is still available (double-check before creating booking)
    slot = await db.get_slot_by_id(slot_id)
    if not slot:
        await callback.answer("Slot not found", show_alert=True)
        await start_booking(callback, state)
        return
    
    if slot.status != SlotStatus.AVAILABLE:
        await callback.answer("Slot no longer available", show_alert=True)
        await start_booking(callback, state)
        return

        # Create booking and mark slot as booked atomically
        # Note: Supabase doesn't support transactions in the Python client,
        # so we handle this with careful ordering and error handling
        from models.booking import BookingCreate

        booking_data = BookingCreate(
            client_id=client.id,
            slot_id=slot_id,
            service_type=service_type,
            price_czk=price_czk,
            status=BookingStatus.PENDING,
        )

        try:
            # Create booking first
            booking = await db.create_booking(booking_data)
            
            if not booking or not booking.id:
                raise ValueError("Failed to create booking: no ID returned")

            # Mark slot as booked immediately after booking creation
            updated_slot = await db.update_slot_status(
                slot_id, SlotStatus.BOOKED
            )
            if not updated_slot:
                # Slot update failed - rollback booking by cancelling it
                logger.error(
                    f"Failed to mark slot {slot_id} as booked "
                    f"after creating booking {booking.id}"
                )
                await db.update_booking_status(
                    booking.id, BookingStatus.CANCELLED
                )
                await callback.answer(
                    "Failed to reserve slot. Please try again.",
                    show_alert=True
                )
                await start_booking(callback, state)
                return

            # Create Stripe payment intent
            payment_intent = await create_payment_intent(
                amount_czk=price_czk,
                booking_id=booking.id,
                client_telegram_id=callback.from_user.id,
            )

            # Update booking with payment intent
            await db.update_booking_payment(
                booking.id,
                payment_intent.id,
                payment_intent.status,
            )

            await callback.message.edit_text(
                f"✅ Booking created!\n\n"
                f"Booking ID: {booking.id[:8]}...\n"
                f"Service: {get_service(ServiceType(service_type)).name}\n"
                f"Date: {slot.start_time.strftime('%d.%m.%Y at %H:%M')}\n"
                f"Price: {price_czk} CZK\n\n"
                f"Please complete the payment:",
                reply_markup=get_payment_keyboard(
                    f"https://checkout.stripe.com/pay/{payment_intent.id}",
                    booking.id,
                ),
            )

            await state.update_data(booking_id=booking.id)
            await callback.answer()

        except Exception as e:
            logger.error(f"Failed to create booking: {e}", exc_info=True)

            # Attempt cleanup: if booking was created but slot update failed,
            # the booking should already be cancelled in the try block above
            # Here we handle other exceptions

            await callback.answer(
                "Failed to create booking. "
                "Please try again or contact support.",
                show_alert=True
            )
            await state.clear()
            await callback.message.edit_text(
                "👋 Welcome to Beauty Salon Bot!\n\n" "Choose an option:",
                reply_markup=get_main_menu_keyboard(),
            )


@router.callback_query(lambda c: c.data.startswith("payment_done_"))
async def handle_payment_done(callback: CallbackQuery, state: FSMContext):
    """Handle payment completion check."""
    booking_id = callback.data.split("_", 2)[2]

    db = get_db_client()
    booking = await db.get_booking_by_id(booking_id)

    if not booking:
        await callback.answer("Booking not found", show_alert=True)
        return

    # Check payment status via Stripe
    if booking.stripe_payment_intent_id and booking.id:
        payment_intent = await get_payment_intent(
            booking.stripe_payment_intent_id
        )
        if payment_intent and payment_intent.status == "succeeded":
            await db.update_booking_status(booking.id, BookingStatus.PAID)
            await callback.message.edit_text(
                "✅ Payment confirmed!\n\n"
                f"Your appointment is confirmed for "
                f"{booking.id[:8]}...\n\n"
                "You will receive a reminder 24 hours "
                "before your appointment.",
                reply_markup=get_main_menu_keyboard(),
            )
            await state.clear()
            await callback.answer()
            return

    await callback.answer(
        "Payment not yet confirmed. Please complete payment or contact support.",
        show_alert=True,
    )


@router.callback_query(lambda c: c.data.startswith("cancel_booking"))
async def cancel_booking(callback: CallbackQuery, state: FSMContext):
    """Cancel booking."""
    data = await state.get_data()
    booking_id = data.get("booking_id")

    if not booking_id:
        await callback.answer("No booking to cancel", show_alert=True)
        await state.clear()
        return

    try:
        db = get_db_client()
        booking = await db.get_booking_by_id(booking_id)

        if not booking:
            await callback.answer("Booking not found", show_alert=True)
            await state.clear()
            return

        # Only allow cancellation of pending or confirmed bookings
        if booking.status not in [BookingStatus.PENDING, BookingStatus.CONFIRMED]:
            await callback.answer(
                f"Cannot cancel booking with status: {booking.status.value}",
                show_alert=True
            )
            return

        # Free up the slot
        slot = await db.update_slot_status(booking.slot_id, SlotStatus.AVAILABLE)
        if not slot:
            logger.warning(f"Failed to free slot {booking.slot_id} for cancelled booking {booking_id}")

        # Update booking status
        await db.update_booking_status(booking.id, BookingStatus.CANCELLED)

        await callback.message.edit_text(
            "❌ Booking cancelled.\n\n"
            "The time slot has been freed and is available for booking again.",
            reply_markup=get_main_menu_keyboard(),
        )
        await state.clear()
        await callback.answer()

    except Exception as e:
        logger.error(f"Failed to cancel booking {booking_id}: {e}", exc_info=True)
        await callback.answer(
            "Failed to cancel booking. Please contact support.",
            show_alert=True
        )


# ========== My Bookings ==========


@router.callback_query(lambda c: c.data == "my_bookings")
async def show_my_bookings(callback: CallbackQuery):
    """Show user's bookings."""
    db = get_db_client()
    client = await db.get_client_by_telegram_id(callback.from_user.id)

    if not client:
        await callback.answer("Client not found", show_alert=True)
        return

    if not client.id:
        await callback.answer("Client ID not found", show_alert=True)
        return

    bookings = await db.get_bookings_by_client(client.id)

    if not bookings:
        await callback.message.edit_text(
            "📋 You have no bookings yet.\n\n" "Book your first appointment!",
            reply_markup=get_back_to_menu_keyboard(),
        )
        await callback.answer()
        return

    # Batch fetch slots to avoid N+1 queries
    slot_ids = [booking.slot_id for booking in bookings[:5]]
    slots_map = await db.get_slots_by_ids(slot_ids)

    bookings_text = "📋 Your Bookings:\n\n"
    for booking in bookings[:5]:  # Show last 5
        slot = slots_map.get(booking.slot_id)
        slot_time = slot.start_time.strftime("%d.%m.%Y %H:%M") if slot else "N/A"
        bookings_text += (
            f"• {booking.service_type} - {slot_time}\n"
            f"  Status: {booking.status.value}\n"
            f"  Price: {booking.price_czk} CZK\n\n"
        )

    await callback.message.edit_text(
        bookings_text,
        reply_markup=get_back_to_menu_keyboard(),
    )
    await callback.answer()


# ========== AI Q&A ==========


@router.callback_query(lambda c: c.data == "ask_question")
async def start_ai_qa(callback: CallbackQuery, state: FSMContext):
    """Start AI Q&A flow."""
    await state.set_state(AIQnAStates.waiting_for_question)

    await callback.message.edit_text(
        "❓ Ask a Question\n\n"
        "Ask me anything about our services, booking process, or beauty tips!\n\n"
        "Type your question:",
        reply_markup=get_back_to_menu_keyboard(),
    )
    await callback.answer()


@router.message(StateFilter(AIQnAStates.waiting_for_question))
async def handle_ai_question(message: Message, state: FSMContext):
    """Handle AI question."""
    question = message.text

    if not question:
        await message.answer("Please send a text question.")
        return

    # Show typing indicator
    await message.bot.send_chat_action(message.chat.id, "typing")

    try:
        response = await get_ai_response(question)
        await message.answer(
            f"💬 {response}\n\n" "Ask another question or return to menu:",
            reply_markup=get_back_to_menu_keyboard(),
        )
    except Exception as e:
        logger.error(f"AI Q&A error: {e}", exc_info=True)
        await message.answer(
            "Sorry, I encountered an error. Please try again later.",
            reply_markup=get_back_to_menu_keyboard(),
        )


# ========== About ==========


@router.callback_query(lambda c: c.data == "about")
async def show_about(callback: CallbackQuery):
    """Show about information."""
    about_text = (
        "ℹ️ About Beauty Salon Bot\n\n"
        "Professional beauty services:\n"
        "• Manicure - 150 CZK\n"
        "• Haircut & Styling - 200 CZK\n"
        "• Pedicure - 180 CZK\n"
        "• Facial Treatment - 250 CZK\n\n"
        "Features:\n"
        "• Easy online booking\n"
        "• Secure Stripe payments\n"
        "• Appointment reminders\n"
        "• AI-powered Q&A\n\n"
        "Book your appointment now! 👇"
    )

    await callback.message.edit_text(
        about_text,
        reply_markup=get_back_to_menu_keyboard(),
    )
    await callback.answer()


def register_handlers(dp) -> None:
    """Register all handlers with dispatcher."""
    dp.include_router(router)
