"""
FSM (Finite State Machine) states for bot conversation flow.
"""

from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    """States for booking flow."""

    selecting_service = State()
    selecting_date = State()
    selecting_slot = State()
    confirming_booking = State()
    entering_notes = State()


class GDPRStates(StatesGroup):
    """States for GDPR consent flow."""

    waiting_for_consent = State()


class AIQnAStates(StatesGroup):
    """States for AI Q&A flow."""

    waiting_for_question = State()
