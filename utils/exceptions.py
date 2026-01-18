"""
Custom exception classes for better error handling.
Provides specific error types instead of generic exceptions.
"""


class DatabaseError(Exception):
    """Base exception for database operations."""

    pass


class ClientNotFoundError(DatabaseError):
    """Raised when a client is not found."""

    pass


class SlotNotFoundError(DatabaseError):
    """Raised when a slot is not found."""

    pass


class SlotNotAvailableError(DatabaseError):
    """Raised when attempting to book an unavailable slot."""

    pass


class BookingNotFoundError(DatabaseError):
    """Raised when a booking is not found."""

    pass


class BookingCreationError(DatabaseError):
    """Raised when booking creation fails."""

    pass


class PaymentError(Exception):
    """Base exception for payment operations."""

    pass


class PaymentIntentError(PaymentError):
    """Raised when payment intent creation/retrieval fails."""

    pass


class WebhookVerificationError(Exception):
    """Raised when webhook signature verification fails."""

    pass


class ValidationError(Exception):
    """Raised when input validation fails."""

    pass


class AgentError(Exception):
    """Base exception for agent operations."""

    pass


class TaskValidationError(AgentError):
    """Raised when task validation fails."""

    pass


class TaskTimeoutError(AgentError):
    """Raised when a task exceeds its timeout."""

    pass


class AgentNotAvailableError(AgentError):
    """Raised when an agent is not available for processing."""

    pass
