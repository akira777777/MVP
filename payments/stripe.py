"""
Stripe payment integration for booking payments.
"""

from typing import Optional

import stripe
from stripe import PaymentIntent
from stripe.error import StripeError

from config import settings
from utils.logging_config import setup_logging

logger = setup_logging(
    name=__name__,
    log_level="INFO",
    log_file="payments.log",
    log_dir="logs"
)

# Initialize Stripe
stripe.api_key = settings.stripe_secret_key


async def create_payment_intent(
    amount_czk: int,
    booking_id: str,
    client_telegram_id: int,
    currency: str = "czk",
) -> PaymentIntent:
    """
    Create Stripe payment intent for a booking.

    Args:
        amount_czk: Amount in CZK (must be positive)
        booking_id: Booking ID (UUID format)
        client_telegram_id: Telegram user ID (positive integer)
        currency: Currency code (default: czk)

    Returns:
        Stripe PaymentIntent object

    Raises:
        ValueError: If input validation fails
        RuntimeError: If Stripe API call fails
    """
    # Input validation
    if amount_czk <= 0:
        raise ValueError(f"Invalid amount: {amount_czk} CZK must be positive")
    
    if not booking_id:
        raise ValueError("Booking ID is required")
    
    if not client_telegram_id or client_telegram_id <= 0:
        raise ValueError(f"Invalid Telegram user ID: {client_telegram_id}")

    try:
        # Convert CZK to smallest currency unit (CZK uses whole numbers)
        amount = amount_czk

        payment_intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
            metadata={
                "booking_id": booking_id,
                "telegram_user_id": str(client_telegram_id),
            },
            description=f"Beauty Salon Booking - {booking_id[:8]}",
            automatic_payment_methods={
                "enabled": True,
            },
        )

        logger.info(
            f"Created payment intent {payment_intent.id} for booking {booking_id}"
        )
        return payment_intent

    except StripeError as e:
        logger.error(
            f"Stripe error creating payment intent for booking {booking_id}: {e}",
            exc_info=True
        )
        raise RuntimeError(f"Payment processing error: {e}") from e
    except Exception as e:
        logger.error(
            f"Unexpected error creating payment intent: {e}",
            exc_info=True
        )
        raise RuntimeError(f"Unexpected payment error: {e}") from e


async def get_payment_intent(payment_intent_id: str) -> Optional[PaymentIntent]:
    """
    Get payment intent by ID.

    Args:
        payment_intent_id: Stripe payment intent ID

    Returns:
        PaymentIntent object or None if not found

    Raises:
        ValueError: If payment_intent_id is empty
    """
    if not payment_intent_id:
        raise ValueError("Payment intent ID is required")
    
    try:
        return stripe.PaymentIntent.retrieve(payment_intent_id)
    except StripeError as e:
        logger.error(
            f"Stripe error retrieving payment intent {payment_intent_id}: {e}",
            exc_info=True
        )
        return None


async def handle_webhook(event_data: dict) -> dict:
    """
    Handle Stripe webhook events.

    Args:
        event_data: Stripe webhook event data

    Returns:
        Response dict
    """
    event_type = event_data.get("type")
    payment_intent = event_data.get("data", {}).get("object")

    if not payment_intent:
        return {"status": "error", "message": "Invalid webhook data"}

    booking_id = payment_intent.get("metadata", {}).get("booking_id")

    if not booking_id:
        logger.warning("Webhook received without booking_id")
        return {"status": "ignored", "message": "No booking_id in metadata"}

    from db import get_db_client

    db = get_db_client()

    if event_type == "payment_intent.succeeded":
        booking = await db.get_booking_by_id(booking_id)
        if booking:
            await db.update_booking_payment(
                booking_id,
                payment_intent["id"],
                "succeeded",
            )
            logger.info(f"Payment confirmed for booking {booking_id}")
            return {"status": "success", "booking_id": booking_id}

    elif event_type == "payment_intent.payment_failed":
        logger.warning(f"Payment failed for booking {booking_id}")
        return {"status": "failed", "booking_id": booking_id}

    return {"status": "processed", "event_type": event_type}
