"""
AI Q&A integration with Claude API.
"""

import logging
from typing import Optional

from anthropic import Anthropic

from config import settings

logger = logging.getLogger(__name__)

# Initialize Claude client
claude_client = Anthropic(api_key=settings.claude_api_key)


async def get_ai_response(question: str, context: Optional[str] = None) -> str:
    """
    Get AI response to user question.

    Args:
        question: User's question
        context: Optional context about the salon

    Returns:
        AI-generated response
    """
    try:
        system_prompt = (
            "You are a helpful assistant for a beauty salon booking bot. "
            "Answer questions about services, booking process, beauty tips, and general inquiries. "
            "Be friendly, professional, and concise. "
            "If asked about booking, guide users to use the booking feature in the bot."
        )

        if context:
            system_prompt += f"\n\nContext: {context}"

        message = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=system_prompt,
            messages=[
                {"role": "user", "content": question}
            ],
        )

        # Extract text from response
        if message.content and len(message.content) > 0:
            return message.content[0].text

        return "I'm sorry, I couldn't generate a response. Please try again."

    except Exception as e:
        logger.error(f"Claude API error: {e}", exc_info=True)
        return (
            "I'm having trouble connecting to the AI service. "
            "Please try again later or contact support."
        )
