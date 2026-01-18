"""
Unit tests for Stripe payment integration.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import stripe
from stripe import PaymentIntent

from payments import create_payment_intent, get_payment_intent, handle_webhook


class TestCreatePaymentIntent:
    """Test payment intent creation."""

    @pytest.mark.asyncio
    async def test_create_payment_intent_success(self):
        """Test successful payment intent creation."""
        mock_payment_intent = MagicMock(spec=PaymentIntent)
        mock_payment_intent.id = "pi_test_123"
        mock_payment_intent.status = "requires_payment_method"
        mock_payment_intent.client_secret = "pi_test_123_secret"
        
        with patch("payments.stripe.PaymentIntent.create") as mock_create:
            mock_create.return_value = mock_payment_intent
            
            result = await create_payment_intent(
                amount_czk=150,
                booking_id="booking_123",
                client_telegram_id=123456789,
            )
            
            assert result.id == "pi_test_123"
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["amount"] == 150
            assert call_kwargs["currency"] == "czk"
            assert call_kwargs["metadata"]["booking_id"] == "booking_123"

    @pytest.mark.asyncio
    async def test_create_payment_intent_invalid_amount(self):
        """Test payment intent with invalid amount."""
        with pytest.raises(ValueError, match="Invalid amount"):
            await create_payment_intent(
                amount_czk=0,
                booking_id="booking_123",
                client_telegram_id=123456789,
            )

    @pytest.mark.asyncio
    async def test_create_payment_intent_missing_booking_id(self):
        """Test payment intent with missing booking ID."""
        with pytest.raises(ValueError, match="Booking ID is required"):
            await create_payment_intent(
                amount_czk=150,
                booking_id="",
                client_telegram_id=123456789,
            )

    @pytest.mark.asyncio
    async def test_create_payment_intent_stripe_error(self):
        """Test payment intent with Stripe error."""
        with patch("payments.stripe.PaymentIntent.create") as mock_create:
            mock_create.side_effect = stripe.error.InvalidRequestError(
                "Invalid request", "amount"
            )
            
            with pytest.raises(RuntimeError, match="Payment processing error"):
                await create_payment_intent(
                    amount_czk=150,
                    booking_id="booking_123",
                    client_telegram_id=123456789,
                )


class TestGetPaymentIntent:
    """Test payment intent retrieval."""

    @pytest.mark.asyncio
    async def test_get_payment_intent_success(self):
        """Test successful payment intent retrieval."""
        mock_payment_intent = MagicMock(spec=PaymentIntent)
        mock_payment_intent.id = "pi_test_123"
        mock_payment_intent.status = "succeeded"
        
        with patch("payments.stripe.PaymentIntent.retrieve") as mock_retrieve:
            mock_retrieve.return_value = mock_payment_intent
            
            result = await get_payment_intent("pi_test_123")
            
            assert result.id == "pi_test_123"
            mock_retrieve.assert_called_once_with("pi_test_123")

    @pytest.mark.asyncio
    async def test_get_payment_intent_not_found(self):
        """Test payment intent not found."""
        with patch("payments.stripe.PaymentIntent.retrieve") as mock_retrieve:
            mock_retrieve.side_effect = stripe.error.InvalidRequestError(
                "No such payment_intent", "id"
            )
            
            result = await get_payment_intent("pi_invalid")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_get_payment_intent_empty_id(self):
        """Test payment intent with empty ID."""
        with pytest.raises(ValueError, match="Payment intent ID is required"):
            await get_payment_intent("")


class TestHandleWebhook:
    """Test webhook handling."""

    @pytest.mark.asyncio
    async def test_handle_webhook_payment_succeeded(self):
        """Test handling payment succeeded event."""
        event_data = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_test_123",
                    "status": "succeeded",
                    "metadata": {"booking_id": "booking_123"},
                }
            },
        }
        
        mock_booking = MagicMock()
        mock_booking.id = "booking_123"
        
        with patch("payments.get_db_client") as mock_db:
            mock_db_client = AsyncMock()
            mock_db.return_value = mock_db_client
            mock_db_client.get_booking_by_id = AsyncMock(return_value=mock_booking)
            mock_db_client.update_booking_payment = AsyncMock(return_value=mock_booking)
            
            result = await handle_webhook(event_data)
            
            assert result["status"] == "success"
            assert result["booking_id"] == "booking_123"
            mock_db_client.update_booking_payment.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_webhook_payment_failed(self):
        """Test handling payment failed event."""
        event_data = {
            "type": "payment_intent.payment_failed",
            "data": {
                "object": {
                    "id": "pi_test_123",
                    "metadata": {"booking_id": "booking_123"},
                }
            },
        }
        
        result = await handle_webhook(event_data)
        
        assert result["status"] == "failed"
        assert result["booking_id"] == "booking_123"

    @pytest.mark.asyncio
    async def test_handle_webhook_no_booking_id(self):
        """Test webhook without booking ID."""
        event_data = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_test_123",
                    "metadata": {},
                }
            },
        }
        
        result = await handle_webhook(event_data)
        
        assert result["status"] == "ignored"

    @pytest.mark.asyncio
    async def test_handle_webhook_unknown_event(self):
        """Test handling unknown event type."""
        event_data = {
            "type": "charge.created",
            "data": {"object": {"id": "ch_test_123"}},
        }
        
        result = await handle_webhook(event_data)
        
        assert result["status"] == "processed"
        assert result["event_type"] == "charge.created"
