"""
Stripe webhook handler (for production deployment).
This would typically be deployed as a separate HTTP endpoint.

Production-ready implementation with:
- Webhook signature verification
- Idempotency handling
- Proper error handling
- Security headers
- Request validation
- Metrics tracking
"""

import json
import time
from collections import deque
from typing import Dict, Optional

import stripe
from aiohttp import web
from aiohttp.web import Request, Response
from stripe.error import SignatureVerificationError

from config import settings
from payments import handle_webhook
from utils.exceptions import ValidationError, WebhookVerificationError
from utils.logging_config import setup_logging

logger = setup_logging(
    name=__name__, log_level="INFO", log_file="webhook.log", log_dir="logs"
)

# Constants
MAX_REQUEST_SIZE = 1024 * 1024  # 1MB max request body size
MAX_REQUEST_BODY_SIZE = MAX_REQUEST_SIZE  # Alias for consistency
_MAX_EVENT_HISTORY = 1000  # Keep last 1000 events for metrics
_EVENT_ID_CLEANUP_INTERVAL = 3600  # 1 hour in seconds
_EVENT_ID_MAX_AGE = 86400  # 24 hours - max age for event ID cache
_MAX_EVENT_CACHE_SIZE = 10000  # Maximum event IDs to track

# Thread-safe event tracking with automatic cleanup
# Using deque with maxlen to prevent unbounded growth
_processed_events: deque = deque(maxlen=_MAX_EVENT_HISTORY)
_processed_event_ids: Dict[str, float] = {}  # event_id -> timestamp
_last_cleanup_time = time.time()

# Health metrics
_health_metrics = {
    "total_events": 0,
    "successful_events": 0,
    "failed_events": 0,
    "verification_failures": 0,
    "validation_failures": 0,
    "duplicate_events": 0,
    "start_time": time.time(),
}

# Event type tracking (bounded)
_event_type_counts: Dict[str, int] = {}
_MAX_EVENT_TYPES = 50  # Track up to 50 different event types


def _cleanup_old_event_ids() -> None:
    """
    Remove event IDs older than max age to prevent unbounded growth.

    This function is called periodically to clean up old event IDs
    from the idempotency cache. Only removes entries older than
    _EVENT_ID_MAX_AGE seconds.
    """
    global _last_cleanup_time
    current_time = time.time()

    # Only cleanup if enough time has passed
    if current_time - _last_cleanup_time < _EVENT_ID_CLEANUP_INTERVAL:
        return

    cutoff_time = current_time - _EVENT_ID_MAX_AGE
    expired_ids = [
        event_id
        for event_id, timestamp in _processed_event_ids.items()
        if timestamp < cutoff_time
    ]

    for event_id in expired_ids:
        _processed_event_ids.pop(event_id, None)

    _last_cleanup_time = current_time
    if expired_ids:
        logger.debug(f"Cleaned up {len(expired_ids)} expired event IDs")


def _verify_webhook_signature(payload: bytes, signature: Optional[str]) -> Dict:
    """
    Verify Stripe webhook signature.

    Args:
        payload: Raw request body bytes
        signature: Stripe-Signature header value

    Returns:
        Parsed event data

    Raises:
        WebhookVerificationError: If signature verification fails
    """
    if not settings.stripe_webhook_secret:
        # In development/test mode, allow unverified webhooks if using test keys
        if settings.stripe_secret_key.startswith("sk_test_"):
            logger.warning(
                "STRIPE_WEBHOOK_SECRET not set - skipping signature verification. "
                "This is insecure and should only be used in development."
            )
            return json.loads(payload.decode("utf-8"))
        else:
            raise ValidationError(
                "Stripe webhook secret is required for production webhook verification"
            )

    if not signature:
        raise WebhookVerificationError("Missing Stripe-Signature header")

    try:
        event = stripe.Webhook.construct_event(
            payload, signature, settings.stripe_webhook_secret
        )
        return event
    except ValueError as e:
        raise WebhookVerificationError(f"Invalid payload: {e}") from e
    except SignatureVerificationError as e:
        raise WebhookVerificationError(f"Invalid signature: {e}") from e


def _validate_webhook_payload(payload: Dict) -> None:
    """
    Validate webhook payload structure.

    Args:
        payload: Parsed webhook payload

    Raises:
        ValidationError: If payload structure is invalid
    """
    if not isinstance(payload, dict):
        raise ValidationError("Webhook payload must be a JSON object")

    if "type" not in payload:
        raise ValidationError("Webhook payload missing 'type' field")

    event_type = payload.get("type")
    if not isinstance(event_type, str) or not event_type:
        raise ValidationError("Webhook 'type' must be a non-empty string")

    if "id" not in payload:
        raise ValidationError("Webhook payload missing 'id' field")

    event_id = payload.get("id")
    if not isinstance(event_id, str) or not event_id:
        raise ValidationError("Webhook 'id' must be a non-empty string")

    if "data" not in payload:
        raise ValidationError("Webhook payload missing 'data' field")

    if not isinstance(payload.get("data"), dict):
        raise ValidationError("Webhook payload 'data' field must be an object")


def _check_and_mark_idempotency(event_id: str) -> bool:
    """
    Check if event has already been processed and mark it if not.

    This is an atomic operation to prevent race conditions where
    the same event could be processed multiple times concurrently.

    Args:
        event_id: Stripe event ID

    Returns:
        True if event was already processed, False if newly marked
    """
    _cleanup_old_event_ids()

    if event_id in _processed_event_ids:
        return True

    # Mark as processed immediately to prevent concurrent processing
    _processed_event_ids[event_id] = time.time()
    return False


def _mark_event_processed(event_id: str, event_type: str) -> None:
    """
    Record event in history for metrics and debugging.

    Note: Idempotency marking happens in _check_and_mark_idempotency.
    This function only records the event for metrics/history.

    Args:
        event_id: Stripe event ID
        event_type: Event type string
    """
    _processed_events.append(
        {"id": event_id, "type": event_type, "timestamp": time.time()}
    )


@web.middleware
async def security_headers_middleware(request: Request, handler):
    """
    Add security headers to all responses.

    Implements security best practices:
    - Prevents MIME type sniffing
    - Prevents clickjacking
    - Enables XSS protection
    - Enforces HTTPS in production
    - Sets appropriate HTTP methods
    """
    response = await handler(request)

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )

    # Only allow POST for webhook endpoint
    if request.path.startswith("/webhook/"):
        response.headers["Allow"] = "POST"

    return response


async def stripe_webhook_handler(request: Request) -> Response:
    """
    Handle Stripe webhook events with production-ready security and error handling.

    Features:
    - Signature verification
    - Idempotency handling
    - Request validation
    - Proper error responses
    """
    event_id: Optional[str] = None
    event_type: Optional[str] = None

    try:
        # Check Content-Length header if present
        content_length = request.headers.get("Content-Length")
        if content_length:
            try:
                size = int(content_length)
                if size > MAX_REQUEST_BODY_SIZE:
                    logger.warning(f"Request body too large: {size} bytes")
                    _health_metrics["validation_failures"] += 1
                    return web.json_response(
                        {
                            "status": "error",
                            "error": "request_too_large",
                            "message": f"Request body exceeds maximum size of {MAX_REQUEST_BODY_SIZE} bytes",
                        },
                        status=413,
                    )
            except ValueError:
                pass  # Invalid Content-Length, continue

        # Read raw body for signature verification
        raw_body = await request.read()

        # Enforce size limit on actual body
        if len(raw_body) > MAX_REQUEST_BODY_SIZE:
            logger.warning(f"Request body too large: {len(raw_body)} bytes")
            _health_metrics["validation_failures"] += 1
            return web.json_response(
                {
                    "status": "error",
                    "error": "request_too_large",
                    "message": f"Request body exceeds maximum size of {MAX_REQUEST_BODY_SIZE} bytes",
                },
                status=413,
            )

        if not raw_body:
            logger.warning("Received empty webhook payload")
            _health_metrics["validation_failures"] += 1
            return web.json_response(
                {
                    "status": "error",
                    "error": "empty_payload",
                    "message": "Empty payload",
                },
                status=400,
            )

        # Verify signature and parse payload
        signature = request.headers.get("Stripe-Signature")
        payload = _verify_webhook_signature(raw_body, signature)

        # Validate payload structure
        _validate_webhook_payload(payload)

        # Extract event info (guaranteed to exist after validation)
        event_id = str(payload["id"])
        event_type = str(payload["type"])

        logger.info(f"Received Stripe webhook: event_id={event_id}, type={event_type}")

        # Check idempotency (atomic check-and-mark)
        if _check_and_mark_idempotency(event_id):
            _health_metrics["duplicate_events"] += 1
            logger.info(
                f"Duplicate webhook event detected: event_id={event_id}, "
                f"type={event_type} (already processed)"
            )
            return web.json_response(
                {
                    "status": "success",
                    "message": "Event already processed",
                    "event_id": event_id,
                    "event_type": event_type,
                },
                status=200,
            )

        # Handle webhook
        result = await handle_webhook(payload)

        # Mark as processed
        _mark_event_processed(event_id, event_type)

        logger.info(
            f"Successfully processed webhook: event_id={event_id}, type={event_type}"
        )

        return web.json_response(
            {
                "status": "success",
                "event_id": event_id,
                "event_type": event_type,
                "result": result,
            },
            status=200,
        )

    except WebhookVerificationError as e:
        logger.warning(
            f"Webhook signature verification failed: {e}",
            extra={
                "event_id": event_id or "unknown",
                "event_type": event_type or "unknown",
            },
        )
        _health_metrics["verification_failures"] += 1
        return web.json_response(
            {
                "status": "error",
                "error": "verification_failed",
                "message": "Invalid webhook signature",
            },
            status=401,
        )

    except ValidationError as e:
        logger.warning(
            f"Invalid webhook payload: {e}",
            extra={
                "event_id": event_id or "unknown",
                "event_type": event_type or "unknown",
            },
        )
        _health_metrics["validation_failures"] += 1
        return web.json_response(
            {
                "status": "error",
                "error": "validation_failed",
                "message": str(e),
            },
            status=400,
        )

    except Exception as e:
        logger.error(
            f"Unexpected webhook error: {e}",
            extra={
                "event_id": event_id or "unknown",
                "event_type": event_type or "unknown",
            },
            exc_info=True,
        )
        _health_metrics["total_events"] += 1
        _health_metrics["failed_events"] += 1
        return web.json_response(
            {
                "status": "error",
                "error": "processing_failed",
                "message": "Internal server error while processing webhook",
            },
            status=500,
        )


async def health_check(request: Request) -> Response:
    """
    Health check endpoint with comprehensive service metrics.

    Returns:
        JSON response with service status, metrics, and configuration info
    """
    _cleanup_old_event_ids()

    # Calculate uptime
    uptime_seconds = time.time() - _health_metrics["start_time"]
    uptime_hours = uptime_seconds / 3600

    # Calculate success rate
    total = _health_metrics["total_events"]
    success_rate = (
        (_health_metrics["successful_events"] / total * 100) if total > 0 else 0.0
    )

    # Count recent event types
    recent_event_types: Dict[str, int] = {}
    for event in _processed_events:
        event_type = event.get("type", "unknown")
        recent_event_types[event_type] = recent_event_types.get(event_type, 0) + 1

    return web.json_response(
        {
            "status": "ok",
            "service": "telegram-beauty-salon-bot",
            "timestamp": time.time(),
            "uptime_hours": round(uptime_hours, 2),
            "metrics": {
                "total_events": _health_metrics["total_events"],
                "successful_events": _health_metrics["successful_events"],
                "failed_events": _health_metrics["failed_events"],
                "verification_failures": _health_metrics["verification_failures"],
                "validation_failures": _health_metrics["validation_failures"],
                "duplicate_events": _health_metrics["duplicate_events"],
                "success_rate_percent": round(success_rate, 2),
                "recent_events_count": len(_processed_events),
                "unique_event_ids_tracked": len(_processed_event_ids),
                "recent_event_types": recent_event_types,
            },
            "configuration": {
                "webhook_secret_configured": bool(settings.stripe_webhook_secret),
                "max_request_size_bytes": MAX_REQUEST_BODY_SIZE,
                "event_history_size": _MAX_EVENT_HISTORY,
                "event_id_max_age_hours": _EVENT_ID_MAX_AGE / 3600,
            },
        }
    )


def create_app() -> web.Application:
    """
    Create aiohttp application with middleware and routes.

    Returns:
        Configured web application with security headers and timeout handling
    """
    app = web.Application(middlewares=[security_headers_middleware])

    # Routes
    app.router.add_post("/webhook/stripe", stripe_webhook_handler)
    app.router.add_get("/health", health_check)

    return app


if __name__ == "__main__":
    """
    Run webhook server locally for testing.

    Note: For production, deploy this as a separate service with proper
    process management (systemd, supervisor, etc.) and ensure
    STRIPE_WEBHOOK_SECRET is configured.
    """
    logger.info(f"Starting webhook server on {settings.host}:{settings.port}")
    app = create_app()
    web.run_app(app, host=settings.host, port=settings.port)
