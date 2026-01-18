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
        return web.json_response({"status": "error", "message": str(e)}, status=500)


async def health_check(request: Request) -> Response:
    """Health check endpoint."""
    return web.json_response({"status": "ok", "service": "telegram-beauty-salon-bot"})


def create_app() -> web.Application:
    """Create aiohttp application."""
    app = web.Application()

    # Routes
    app.router.add_post("/webhook/stripe", stripe_webhook_handler)
    app.router.add_get("/health", health_check)

    return app


if __name__ == "__main__":
    # For local testing
    app = create_app()
    web.run_app(app, host=settings.host, port=settings.port)
