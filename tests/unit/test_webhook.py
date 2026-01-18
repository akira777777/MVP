"""
Unit tests for Stripe webhook handler.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import make_mocked_request

from webhook import (
    create_app,
    health_check,
    rate_limit_middleware,
    stripe_webhook_handler,
    verify_stripe_signature,
)


@pytest.fixture
def app():
    """Create test application."""
    return create_app()


@pytest.fixture
def mock_stripe_event():
    """Mock Stripe webhook event."""
    return {
        "id": "evt_test_123",
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": "pi_test_123",
                "status": "succeeded",
                "metadata": {
                    "booking_id": "booking_123",
                    "telegram_user_id": "123456789",
                },
            }
        },
    }


@pytest.fixture
def mock_stripe_signature():
    """Mock Stripe signature header."""
    return "t=1234567890,v1=test_signature"


class TestHealthCheck:
    """Test health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check returns OK."""
        request = make_mocked_request("GET", "/health")
        response = await health_check(request)
        
        assert response.status == 200
        data = json.loads(response.text)
        assert data["status"] == "ok"


class TestStripeWebhookSignature:
    """Test Stripe webhook signature verification."""

    @pytest.mark.asyncio
    async def test_verify_signature_success(self, mock_stripe_event, mock_stripe_signature):
        """Test successful signature verification."""
        with patch("webhook.stripe.Webhook.construct_event") as mock_construct:
            mock_construct.return_value = mock_stripe_event
            
            payload_body = json.dumps(mock_stripe_event).encode("utf-8")
            event = verify_stripe_signature(payload_body, mock_stripe_signature)
            
            assert event == mock_stripe_event
            mock_construct.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_signature_failure(self, mock_stripe_signature):
        """Test signature verification failure."""
        with patch("webhook.stripe.Webhook.construct_event") as mock_construct:
            import stripe
            mock_construct.side_effect = stripe.error.SignatureVerificationError(
                "Invalid signature", "sig_header"
            )
            
            payload_body = b"test payload"
            
            with pytest.raises(ValueError, match="Signature verification failed"):
                verify_stripe_signature(payload_body, mock_stripe_signature)

    @pytest.mark.asyncio
    async def test_verify_signature_no_secret_dev(self):
        """Test signature verification in development without secret."""
        with patch("webhook.settings") as mock_settings:
            mock_settings.stripe_webhook_secret = None
            mock_settings.environment = "development"
            
            payload_body = b"test payload"
            result = verify_stripe_signature(payload_body, None)
            
            assert result == {}


class TestStripeWebhookHandler:
    """Test Stripe webhook handler."""

    @pytest.mark.asyncio
    async def test_webhook_handler_success(self, mock_stripe_event):
        """Test successful webhook processing."""
        with patch("webhook.verify_stripe_signature") as mock_verify, patch(
            "webhook.handle_webhook"
        ) as mock_handle:
            mock_verify.return_value = mock_stripe_event
            mock_handle.return_value = {"status": "success", "booking_id": "booking_123"}
            
            request = make_mocked_request(
                "POST",
                "/webhook/stripe",
                headers={"Stripe-Signature": "test_sig"},
            )
            request.read = AsyncMock(return_value=json.dumps(mock_stripe_event).encode())
            
            response = await stripe_webhook_handler(request)
            
            assert response.status == 200
            data = json.loads(response.text)
            assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_webhook_handler_invalid_signature(self):
        """Test webhook handler with invalid signature."""
        with patch("webhook.verify_stripe_signature") as mock_verify:
            mock_verify.side_effect = ValueError("Invalid signature")
            
            request = make_mocked_request(
                "POST",
                "/webhook/stripe",
                headers={"Stripe-Signature": "invalid"},
            )
            request.read = AsyncMock(return_value=b"test payload")
            
            response = await stripe_webhook_handler(request)
            
            assert response.status == 400
            data = json.loads(response.text)
            assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_webhook_handler_missing_signature_production(self):
        """Test webhook handler missing signature in production."""
        with patch("webhook.settings") as mock_settings:
            mock_settings.environment = "production"
            
            request = make_mocked_request("POST", "/webhook/stripe")
            request.read = AsyncMock(return_value=b"test payload")
            
            response = await stripe_webhook_handler(request)
            
            assert response.status == 400


class TestRateLimitMiddleware:
    """Test rate limiting middleware."""

    @pytest.mark.asyncio
    async def test_rate_limit_within_limit(self):
        """Test requests within rate limit."""
        handler = AsyncMock(return_value=web.Response(text="OK"))
        
        request = make_mocked_request("GET", "/test")
        request.remote = "127.0.0.1"
        request.headers = {}
        
        response = await rate_limit_middleware(request, handler)
        
        assert response.status == 200
        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self):
        """Test rate limit exceeded."""
        handler = AsyncMock()
        
        request = make_mocked_request("GET", "/test")
        request.remote = "127.0.0.1"
        request.headers = {}
        
        # Exceed rate limit
        import time
        from webhook import _rate_limit_store, _RATE_LIMIT_MAX_REQUESTS
        
        _rate_limit_store["127.0.0.1"] = [time.time()] * (_RATE_LIMIT_MAX_REQUESTS + 1)
        
        response = await rate_limit_middleware(request, handler)
        
        assert response.status == 429
        handler.assert_not_called()
        
        # Cleanup
        _rate_limit_store.clear()


class TestWebhookApp:
    """Test webhook application."""

    def test_create_app(self, app):
        """Test application creation."""
        assert app is not None
        assert len(app.middlewares) == 2  # rate_limit + security_headers

    def test_routes_registered(self, app):
        """Test routes are registered."""
        routes = [route.path for route in app.router.routes()]
        assert "/webhook/stripe" in routes
        assert "/health" in routes
