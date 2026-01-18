"""
Stripe webhook handler (for production deployment).
This would typically be deployed as a separate HTTP endpoint.
"""

import time
from typing import Dict

import stripe
from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response

from config import settings
from payments import handle_webhook
from utils.logging_config import setup_logging

logger = setup_logging(
    name=__name__, log_level="INFO", log_file="webhook.log", log_dir="logs"
)

# Rate limiting: track requests per IP with automatic cleanup
_rate_limit_store: Dict[str, list] = {}
_RATE_LIMIT_WINDOW = 60  # 1 minute window
_RATE_LIMIT_MAX_REQUESTS = 100  # Max requests per window
_LAST_CLEANUP_TIME = time.time()
_CLEANUP_INTERVAL = 300  # Clean up every 5 minutes


def _cleanup_rate_limit_store():
    """Clean up old entries from rate limit store to prevent memory leaks."""
    global _LAST_CLEANUP_TIME
    current_time = time.time()
    
    # Only cleanup periodically to avoid overhead
    if current_time - _LAST_CLEANUP_TIME < _CLEANUP_INTERVAL:
        return
    
    _LAST_CLEANUP_TIME = current_time
    expired_ips = []
    
    for ip, timestamps in _rate_limit_store.items():
        # Remove expired timestamps
        valid_timestamps = [
            ts for ts in timestamps
            if current_time - ts < _RATE_LIMIT_WINDOW
        ]
        
        if valid_timestamps:
            _rate_limit_store[ip] = valid_timestamps
        else:
            # Remove IPs with no valid timestamps
            expired_ips.append(ip)
    
    for ip in expired_ips:
        del _rate_limit_store[ip]
    
    if expired_ips:
        logger.debug(f"Cleaned up {len(expired_ips)} expired IPs from rate limit store")


@web.middleware
async def rate_limit_middleware(request: Request, handler) -> Response:
    """
    Rate limiting middleware to prevent abuse.
    
    Limits requests per IP address to prevent DDoS and abuse.
    Automatically cleans up old entries to prevent memory leaks.
    """
    # Periodic cleanup to prevent memory leaks
    _cleanup_rate_limit_store()
    
    # Get client IP (consider X-Forwarded-For for proxied requests)
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else None
    if not client_ip:
        client_ip = request.remote or "unknown"
    
    current_time = time.time()
    
    # Clean old entries for this IP outside the window
    if client_ip in _rate_limit_store:
        _rate_limit_store[client_ip] = [
            ts
            for ts in _rate_limit_store[client_ip]
            if current_time - ts < _RATE_LIMIT_WINDOW
        ]
    else:
        _rate_limit_store[client_ip] = []
    
    # Check rate limit
    request_count = len(_rate_limit_store[client_ip])
    if request_count >= _RATE_LIMIT_MAX_REQUESTS:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        return web.json_response(
            {"status": "error", "message": "Rate limit exceeded"},
            status=429
        )
    
    # Record this request
    _rate_limit_store[client_ip].append(current_time)
    
    return await handler(request)


@web.middleware
async def security_headers_middleware(request: Request, handler) -> Response:
    """
    Add security headers to responses.

    Strict-Transport-Security (HSTS) is only set in production
    to enforce HTTPS in production, preventing HSTS from being
    cached in localhost/development environments.
    """
    response = await handler(request)

    # Set security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Only set HSTS in production to enforce HTTPS
    # This prevents HSTS from being cached in development/localhost
    if settings.environment.lower() == "production":
        hsts_value = "max-age=31536000; includeSubDomains"
        response.headers["Strict-Transport-Security"] = hsts_value
        logger.debug("HSTS header set for production environment")
    else:
        env_name = settings.environment
        logger.debug(f"HSTS header skipped for {env_name} environment")

    return response


def verify_stripe_signature(payload_body: bytes, signature_header: str) -> dict:
    """
    Verify Stripe webhook signature.
    
    Args:
        payload_body: Raw request body as bytes
        signature_header: Stripe-Signature header value
        
    Returns:
        Parsed event data
        
    Raises:
        ValueError: If signature verification fails
    """
    if not settings.stripe_webhook_secret:
        logger.warning("Stripe webhook secret not configured - skipping signature verification")
        # In development, allow requests without verification
        if settings.environment.lower() == "production":
            raise ValueError("Stripe webhook secret required in production")
        # Return empty dict to allow processing in dev
        return {}
    
    try:
        event = stripe.Webhook.construct_event(
            payload_body,
            signature_header,
            settings.stripe_webhook_secret
        )
        logger.debug(f"Stripe signature verified for event: {event.get('type')}")
        return event
    except ValueError as e:
        logger.error(f"Invalid Stripe webhook signature: {e}")
        raise ValueError(f"Invalid webhook signature: {e}") from e
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Stripe signature verification failed: {e}")
        raise ValueError(f"Signature verification failed: {e}") from e


async def stripe_webhook_handler(request: Request) -> Response:
    """
    Handle Stripe webhook events.

    Implements:
    1. Webhook signature verification
    2. Rate limiting (via middleware)
    3. Error handling and logging
    """
    try:
        # Get raw body for signature verification
        payload_body = await request.read()
        
        # Get signature header
        signature_header = request.headers.get("Stripe-Signature")
        
        if not signature_header and settings.environment.lower() == "production":
            logger.warning("Missing Stripe-Signature header in production")
            return web.json_response(
                {"status": "error", "message": "Missing signature"},
                status=400
            )
        
        # Verify signature
        try:
            if signature_header:
                event = verify_stripe_signature(payload_body, signature_header)
            else:
                # Development mode: parse JSON directly
                import json
                event = json.loads(payload_body.decode('utf-8'))
        except ValueError as e:
            logger.error(f"Signature verification failed: {e}")
            return web.json_response(
                {"status": "error", "message": "Invalid signature"},
                status=401
            )
        
        event_type = event.get("type")
        logger.info(f"Received verified Stripe webhook: {event_type}")

        # Handle webhook
        result = await handle_webhook(event)

        return web.json_response({"status": "success", "result": result})

    except ValueError as e:
        # Signature/validation errors
        logger.error(f"Webhook validation error: {e}", exc_info=True)
        return web.json_response(
            {"status": "error", "message": str(e)},
            status=400
        )
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return web.json_response(
            {"status": "error", "message": "Internal server error"},
            status=500
        )


async def health_check(request: Request) -> Response:
    """Health check endpoint."""
    return web.json_response({"status": "ok", "service": "telegram-beauty-salon-bot"})


def create_app() -> web.Application:
    """Create aiohttp application."""
    app = web.Application()

    # Add middlewares in order (last added is outermost)
    app.middlewares.append(security_headers_middleware)
    app.middlewares.append(rate_limit_middleware)

    # Routes
    app.router.add_post("/webhook/stripe", stripe_webhook_handler)
    app.router.add_get("/health", health_check)

    return app


if __name__ == "__main__":
    # For local testing
    app = create_app()
    web.run_app(app, host=settings.host, port=settings.port)
