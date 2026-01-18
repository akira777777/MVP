"""
Supabase database client with CRUD operations.
Handles all database interactions for clients, slots, and bookings.
"""

from datetime import datetime
from typing import List, Optional

from supabase import Client as SupabaseClientType
from supabase import create_client

from config import settings
from models.booking import Booking, BookingCreate, BookingStatus
from models.client import Client, ClientCreate
from models.slot import Slot, SlotCreate, SlotStatus
from utils.datetime_utils import parse_iso_datetime, to_iso_string, utc_now


class SupabaseClient:
    """Supabase database client wrapper."""

    def __init__(self):
        """Initialize Supabase client."""
        self.client: SupabaseClientType = create_client(
            settings.supabase_url, settings.supabase_key
        )

    # ========== Client Operations ==========

    async def get_client_by_telegram_id(self, telegram_id: int) -> Optional[Client]:
        """Get client by Telegram ID."""
        try:
            response = (
                self.client.table("clients")
                .select("*")
                .eq("telegram_id", telegram_id)
                .execute()
            )

            if response.data:
                return Client(**response.data[0])
            return None
        except Exception as e:
            raise RuntimeError(f"Failed to get client: {e}") from e

    async def create_client(self, client_data: ClientCreate) -> Client:
        """Create a new client."""
        try:
            data = client_data.model_dump(exclude_none=True)
            if client_data.gdpr_consent_date:
                data["gdpr_consent_date"] = to_iso_string(client_data.gdpr_consent_date)

            response = self.client.table("clients").insert(data).execute()

            if not response.data:
                raise ValueError("Failed to create client: no data returned")

            return Client(**response.data[0])
        except Exception as e:
            raise RuntimeError(f"Failed to create client: {e}") from e

    async def update_client_gdpr_consent(
        self, telegram_id: int, consent: bool
    ) -> Client:
        """Update GDPR consent for a client."""
        try:
            now = utc_now()
            update_data = {
                "gdpr_consent": consent,
                "gdpr_consent_date": to_iso_string(now),
                "updated_at": to_iso_string(now),
            }

            response = (
                self.client.table("clients")
                .update(update_data)
                .eq("telegram_id", telegram_id)
                .execute()
            )

            if not response.data:
                raise ValueError("Client not found")

            return Client(**response.data[0])
        except Exception as e:
            raise RuntimeError(f"Failed to update GDPR consent: {e}") from e

    # ========== Slot Operations ==========

    async def create_slot(self, slot_data: SlotCreate) -> Slot:
        """Create a new time slot."""
        try:
            data = slot_data.model_dump(exclude_none=True)
            data["start_time"] = to_iso_string(slot_data.start_time)
            data["end_time"] = to_iso_string(slot_data.end_time)

            response = self.client.table("slots").insert(data).execute()

            if not response.data:
                raise ValueError("Failed to create slot: no data returned")

            return self._parse_slot(response.data[0])
        except Exception as e:
            raise RuntimeError(f"Failed to create slot: {e}") from e

    async def get_available_slots(
        self, service_type: str, start_date: Optional[datetime] = None
    ) -> List[Slot]:
        """Get available slots for a service type."""
        try:
            query = (
                self.client.table("slots")
                .select("*")
                .eq("service_type", service_type)
                .eq("status", SlotStatus.AVAILABLE.value)
            )

            if start_date:
                query = query.gte("start_time", to_iso_string(start_date))

            query = query.order("start_time", desc=False)

            response = query.execute()

            slots = []
            for item in response.data:
                slots.append(self._parse_slot(item))

            return slots
        except Exception as e:
            raise RuntimeError(f"Failed to get available slots: {e}") from e

    async def get_slot_by_id(self, slot_id: str) -> Optional[Slot]:
        """Get slot by ID."""
        try:
            response = (
                self.client.table("slots").select("*").eq("id", slot_id).execute()
            )

            if response.data:
                return self._parse_slot(response.data[0])
            return None
        except Exception as e:
            raise RuntimeError(f"Failed to get slot: {e}") from e

    async def update_slot_status(
        self, slot_id: str, status: SlotStatus
    ) -> Optional[Slot]:
        """Update slot status."""
        try:
            update_data = {
                "status": status.value,
                "updated_at": to_iso_string(utc_now()),
            }

            response = (
                self.client.table("slots")
                .update(update_data)
                .eq("id", slot_id)
                .execute()
            )

            if not response.data:
                return None

            return self._parse_slot(response.data[0])
        except Exception as e:
            raise RuntimeError(f"Failed to update slot status: {e}") from e

    # ========== Booking Operations ==========

    async def create_booking(self, booking_data: BookingCreate) -> Booking:
        """Create a new booking."""
        try:
            data = booking_data.model_dump(exclude_none=True)

            response = self.client.table("bookings").insert(data).execute()

            if not response.data:
                raise ValueError("Failed to create booking: no data returned")

            return Booking(**response.data[0])
        except Exception as e:
            raise RuntimeError(f"Failed to create booking: {e}") from e

    async def get_booking_by_id(self, booking_id: str) -> Optional[Booking]:
        """Get booking by ID."""
        try:
            response = (
                self.client.table("bookings").select("*").eq("id", booking_id).execute()
            )

            if response.data:
                return self._parse_booking(response.data[0])
            return None
        except Exception as e:
            raise RuntimeError(f"Failed to get booking: {e}") from e

    async def get_bookings_by_client(self, client_id: str) -> List[Booking]:
        """Get all bookings for a client."""
        try:
            response = (
                self.client.table("bookings")
                .select("*")
                .eq("client_id", client_id)
                .order("created_at", desc=True)
                .execute()
            )

            bookings = []
            for item in response.data:
                bookings.append(self._parse_booking(item))

            return bookings
        except Exception as e:
            raise RuntimeError(f"Failed to get bookings: {e}") from e

    async def update_booking_status(
        self, booking_id: str, status: BookingStatus
    ) -> Optional[Booking]:
        """Update booking status."""
        try:
            update_data = {
                "status": status.value,
                "updated_at": to_iso_string(utc_now()),
            }

            response = (
                self.client.table("bookings")
                .update(update_data)
                .eq("id", booking_id)
                .execute()
            )

            if not response.data:
                return None

            return self._parse_booking(response.data[0])
        except Exception as e:
            raise RuntimeError(f"Failed to update booking status: {e}") from e

    async def update_booking_payment(
        self,
        booking_id: str,
        payment_intent_id: str,
        payment_status: str,
    ) -> Optional[Booking]:
        """Update booking payment information."""
        try:
            update_data = {
                "stripe_payment_intent_id": payment_intent_id,
                "stripe_payment_status": payment_status,
                "status": BookingStatus.PAID.value,
                "updated_at": to_iso_string(utc_now()),
            }

            response = (
                self.client.table("bookings")
                .update(update_data)
                .eq("id", booking_id)
                .execute()
            )

            if not response.data:
                return None

            return self._parse_booking(response.data[0])
        except Exception as e:
            raise RuntimeError(f"Failed to update booking payment: {e}") from e

    async def mark_reminder_sent(self, booking_id: str) -> Optional[Booking]:
        """Mark reminder as sent for a booking."""
        try:
            now = utc_now()
            update_data = {
                "reminder_sent": True,
                "reminder_sent_at": to_iso_string(now),
                "updated_at": to_iso_string(now),
            }

            response = (
                self.client.table("bookings")
                .update(update_data)
                .eq("id", booking_id)
                .execute()
            )

            if not response.data:
                return None

            return self._parse_booking(response.data[0])
        except Exception as e:
            raise RuntimeError(f"Failed to mark reminder sent: {e}") from e

    async def get_bookings_for_reminder(self, hours_before: int) -> List[Booking]:
        """Get bookings that need reminders (within specified hours)."""
        try:
            from datetime import timedelta

            now = utc_now()
            target_time = now + timedelta(hours=hours_before)

            # Get bookings that are confirmed or paid
            # and don't have reminder sent
            response = (
                self.client.table("bookings")
                .select("*")
                .in_(
                    "status",
                    [BookingStatus.CONFIRMED.value, BookingStatus.PAID.value],
                )
                .eq("reminder_sent", False)
                .execute()
            )

            bookings = []
            for item in response.data:
                # Get slot to check start_time
                slot = await self.get_slot_by_id(item["slot_id"])
                if not slot:
                    continue

                # Check if slot is within reminder window
                if now <= slot.start_time <= target_time:
                    bookings.append(self._parse_booking(item))

            return bookings
        except Exception as e:
            raise RuntimeError(f"Failed to get bookings for reminder: {e}") from e

    # ========== Helper Methods ==========

    def _parse_slot(self, item: dict) -> Slot:
        """
        Parse slot data from database response.

        Args:
            item: Raw slot data from database

        Returns:
            Parsed Slot object
        """
        item = item.copy()
        if item.get("start_time"):
            item["start_time"] = parse_iso_datetime(item["start_time"])
        if item.get("end_time"):
            item["end_time"] = parse_iso_datetime(item["end_time"])
        if item.get("created_at"):
            item["created_at"] = parse_iso_datetime(item["created_at"])
        if item.get("updated_at"):
            item["updated_at"] = parse_iso_datetime(item["updated_at"])
        return Slot(**item)

    def _parse_booking(self, item: dict) -> Booking:
        """
        Parse booking data from database response.

        Args:
            item: Raw booking data from database

        Returns:
            Parsed Booking object
        """
        item = item.copy()
        for field in ["reminder_sent_at", "created_at", "updated_at"]:
            if item.get(field):
                item[field] = parse_iso_datetime(item[field])
        return Booking(**item)


# Global database client instance
_db_client: Optional[SupabaseClient] = None


def get_db_client() -> SupabaseClient:
    """Get or create database client instance."""
    global _db_client
    if _db_client is None:
        _db_client = SupabaseClient()
    return _db_client
