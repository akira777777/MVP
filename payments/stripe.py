"""
Stripe payment integration for booking payments.
"""

import logging
from typing import Optional

import stripe
from stripe import PaymentIntent

from config import settings

logger = logging.getLogger(__name__)

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
        amount_czk: Amount in CZK
        booking_id: Booking ID
        client_telegram_id: Telegram user ID
        currency: Currency code (default: czk)

    Returns:
        Stripe PaymentIntent object
    """
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

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating payment intent: {e}", exc_info=True)
        raise RuntimeError(f"Payment processing error: {e}") from e


async def get_payment_intent(payment_intent_id: str) -> Optional[PaymentIntent]:
    """
    Get payment intent by ID.

    Args:
        payment_intent_id: Stripe payment intent ID

    Returns:
        PaymentIntent object or None if not found
    """
    try:
        return stripe.PaymentIntent.retrieve(payment_intent_id)
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error retrieving payment intent: {e}", exc_info=True)
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
