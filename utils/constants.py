"""
Application-wide constants.
Centralizes magic numbers and configuration values.
"""

# Display formatting
BOOKING_ID_DISPLAY_LENGTH = 8  # Length of booking ID to show in UI
SLOTS_DISPLAY_LIMIT = 5  # Maximum slots to show in booking UI
BOOKINGS_DISPLAY_LIMIT = 5  # Maximum bookings to show in user's booking list

# Validation limits
MAX_SERVICE_NAME_LENGTH = 100
MAX_NOTES_LENGTH = 1000
MIN_PRICE_CZK = 0
MAX_PRICE_CZK = 100000  # Reasonable upper limit

# Time constants
DAYS_AHEAD_FOR_SLOTS = 1  # Show slots starting from tomorrow
HOURS_IN_DAY = 24
