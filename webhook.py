"""
Stripe webhook handler (for production deployment).
This would typically be deployed as a separate HTTP endpoint.
"""

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response

from config import settings
from payments import handle_webhook
from utils.logging_config import setup_logging

logger = setup_logging(
    name=__name__, log_level="INFO", log_file="webhook.log", log_dir="logs"
)


@web.middleware
async def security_headers_middleware(
    request: Request, handler
) -> Response:
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

    # Only set HSTS in production to enforce HTTPS in production
    # This prevents HSTS from being cached in development/localhost
    if settings.environment.lower() == "production":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        logger.debug("HSTS header set for production environment")
    else:
        logger.debug(
            f"HSTS header skipped for {settings.environment} environment"
        )

    return response


async def stripe_webhook_handler(request: Request) -> Response:
    """
    Handle Stripe webhook events.

    In production, you should:
    1. Verify webhook signature
    2. Handle idempotency
    3. Process events asynchronously
    """
    try:
        payload = await request.json()
        event_type = payload.get("type")

        logger.info(f"Received Stripe webhook: {event_type}")

        # Verify webhook signature (implement in production)
        # signature = request.headers.get("Stripe-Signature")
        # stripe.Webhook.construct_event(
        #     payload, signature, settings.stripe_webhook_secret
        # )

        # Handle webhook
        result = await handle_webhook(payload)

        return web.json_response({"status": "success", "result": result})

    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return web.json_response(
            {"status": "error", "message": str(e)}, status=500
        )


async def health_check(request: Request) -> Response:
    """Health check endpoint."""
    return web.json_response(
        {"status": "ok", "service": "telegram-beauty-salon-bot"}
    )


def create_app() -> web.Application:
    """Create aiohttp application."""
    app = web.Application()

    # Add security headers middleware
    app.middlewares.append(security_headers_middleware)

    # Routes
    app.router.add_post("/webhook/stripe", stripe_webhook_handler)
    app.router.add_get("/health", health_check)

    return app


if __name__ == "__main__":
    # For local testing
    app = create_app()
    web.run_app(app, host=settings.host, port=settings.port)
