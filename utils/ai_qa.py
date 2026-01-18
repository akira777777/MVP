"""
AI Q&A integration with Claude API.
"""

import asyncio
import logging
from typing import Optional

from anthropic import Anthropic, APIError

from config import settings

logger = logging.getLogger(__name__)

# Initialize Claude client
claude_client = Anthropic(api_key=settings.claude_api_key)

# Retry configuration
_MAX_RETRIES = 3
_RETRY_DELAY = 1.0  # seconds
_RETRY_BACKOFF = 2.0  # exponential backoff multiplier
_API_TIMEOUT = 30.0  # seconds


async def get_ai_response(question: str, context: Optional[str] = None) -> str:
    """
    Get AI response to user question.

    Includes retry logic and timeout handling for reliability.

    Args:
        question: User's question
        context: Optional context about the salon

    Returns:
        AI-generated response
    """
    if not question or not question.strip():
        return "Please provide a question."

    system_prompt = (
        "You are a helpful assistant for a beauty salon booking bot. "
        "Answer questions about services, booking process, beauty tips, and general inquiries. "
        "Be friendly, professional, and concise. "
        "If asked about booking, guide users to use the booking feature in the bot."
    )

    if context:
        system_prompt += f"\n\nContext: {context}"

    delay = _RETRY_DELAY

    for attempt in range(_MAX_RETRIES):
        try:
            # Use asyncio.wait_for for timeout handling
            message = await asyncio.wait_for(
                asyncio.to_thread(
                    claude_client.messages.create,
                    model="claude-sonnet-4-20250514",
                    max_tokens=500,
                    system=system_prompt,
                    messages=[{"role": "user", "content": question}],
                ),
                timeout=_API_TIMEOUT,
            )

            # Extract text from response
            if message.content and len(message.content) > 0:
                return message.content[0].text

            return "I'm sorry, I couldn't generate a response. Please try again."

        except asyncio.TimeoutError:
            if attempt < _MAX_RETRIES - 1:
                logger.warning(
                    f"Claude API timeout (attempt {attempt + 1}/{_MAX_RETRIES}). Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
                delay *= _RETRY_BACKOFF
            else:
                logger.error(f"Claude API timeout after {_MAX_RETRIES} attempts")
                return (
                    "I'm having trouble connecting to the AI service. "
                    "Please try again later or contact support."
                )
        except APIError as e:
            last_error = e
            # Don't retry on client errors (4xx), only on server errors (5xx)
            if e.status_code and 400 <= e.status_code < 500:
                logger.error(f"Claude API client error: {e}", exc_info=True)
                return (
                    "I'm having trouble processing your question. "
                    "Please try rephrasing it or contact support."
                )

            if attempt < _MAX_RETRIES - 1:
                logger.warning(
                    f"Claude API error (attempt {attempt + 1}/{_MAX_RETRIES}): {e}. Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
                delay *= _RETRY_BACKOFF
            else:
                logger.error(
                    f"Claude API error after {_MAX_RETRIES} attempts: {e}",
                    exc_info=True,
                )
                return (
                    "I'm having trouble connecting to the AI service. "
                    "Please try again later or contact support."
                )
        except Exception as e:
            if attempt < _MAX_RETRIES - 1:
                logger.warning(
                    f"Unexpected error (attempt {attempt + 1}/{_MAX_RETRIES}) calling Claude API: {e}. Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
                delay *= _RETRY_BACKOFF
            else:
                logger.error(
                    f"Unexpected Claude API error after {_MAX_RETRIES} attempts: {e}",
                    exc_info=True,
                )
                return (
                    "I'm having trouble connecting to the AI service. "
                    "Please try again later or contact support."
                )

    # Fallback response
    return (
        "I'm having trouble connecting to the AI service. "
        "Please try again later or contact support."
    )
