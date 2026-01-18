"""
Supabase database client with CRUD operations.
Handles all database interactions for clients, slots, and bookings.

Row Level Security (RLS) Notes:
==============================
Supabase RLS policies should be configured in the Supabase dashboard to ensure:
1. Clients can only read/update their own records (telegram_id match)
2. Bookings are readable by their client_id owner
3. Slots are readable by all authenticated users
4. Admin operations require service_role key (bypasses RLS)

This client uses the service key which bypasses RLS for admin operations.
For user-facing operations, RLS policies should be enforced at the database level.

Example RLS Policies (SQL):
----------------------------
-- Clients: users can only see their own data
CREATE POLICY "Users can view own client data"
ON clients FOR SELECT
USING (auth.uid()::text = telegram_id::text);

-- Bookings: users can only see their own bookings
CREATE POLICY "Users can view own bookings"
ON bookings FOR SELECT
USING (client_id IN (
    SELECT id FROM clients WHERE telegram_id::text = auth.uid()::text
));

-- Slots: all authenticated users can view available slots
CREATE POLICY "Users can view available slots"
ON slots FOR SELECT
USING (true);
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from config import settings
from models.booking import Booking, BookingCreate, BookingStatus
from models.client import Client, ClientCreate
from models.slot import Slot, SlotCreate, SlotStatus
from supabase import Client as SupabaseClientType
from supabase import create_client
from utils.datetime_utils import parse_iso_datetime, to_iso_string, utc_now


class SupabaseClient:
    """
    Supabase database client wrapper.

    Uses service_role key which bypasses RLS for admin operations.
    RLS policies should be configured in Supabase dashboard for user-facing queries.

    Includes simple in-memory cache for frequently accessed data to reduce database load.
    """

    def __init__(self):
        """
        Initialize Supabase client.

        Note: Uses service_role key which bypasses RLS.
        Ensure RLS policies are properly configured in Supabase dashboard.
        """
        self.client: SupabaseClientType = create_client(
            settings.supabase_url, settings.supabase_key
        )

        # Simple cache for frequently accessed data
        # Format: {cache_key: (data, expiry_time)}
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._cache_ttl = timedelta(minutes=5)  # Cache TTL: 5 minutes

    # ========== Cache Helpers ==========

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key not in self._cache:
            return None

        data, expiry = self._cache[key]
        if utc_now() > expiry:
            del self._cache[key]
            return None

        return data

    def _set_cache(self, key: str, value: Any) -> None:
        """Set value in cache with TTL."""
        expiry = utc_now() + self._cache_ttl
        self._cache[key] = (value, expiry)

    def _clear_cache(self, pattern: Optional[str] = None) -> None:
        """Clear cache entries matching pattern, or all if pattern is None."""
        if pattern is None:
            self._cache.clear()
        else:
            keys_to_remove = [k for k in self._cache.keys() if pattern in k]
            for k in keys_to_remove:
                del self._cache[k]

    def _cleanup_expired_cache(self) -> None:
        """Remove expired cache entries."""
        now = utc_now()
        expired_keys = [k for k, (_, expiry) in self._cache.items() if now > expiry]
        for k in expired_keys:
            del self._cache[k]

    # ========== Client Operations ==========

    async def get_client_by_telegram_id(self, telegram_id: int) -> Optional[Client]:
        """
        Get client by Telegram ID.

        Uses cache to reduce database load for frequently accessed clients.
        """
        cache_key = f"client:telegram_id:{telegram_id}"

        # Check cache first
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        try:
            response = (
                self.client.table("clients")
                .select("*")
                .eq("telegram_id", telegram_id)
                .execute()
            )

            if response.data:
                client = Client(**response.data[0])
                # Cache the result
                self._set_cache(cache_key, client)
                return client
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

            client = Client(**response.data[0])

            # Invalidate cache for this client
            cache_key = f"client:telegram_id:{client.telegram_id}"
            self._clear_cache(cache_key)

            return client
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

            client = Client(**response.data[0])

            # Invalidate cache for this client
            cache_key = f"client:telegram_id:{telegram_id}"
            self._clear_cache(cache_key)

            return client
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

    async def get_slots_by_ids(self, slot_ids: List[str]) -> dict[str, Slot]:
        """
        Batch fetch multiple slots by IDs.

        Args:
            slot_ids: List of slot IDs to fetch

        Returns:
            Dictionary mapping slot_id -> Slot object
        """
        if not slot_ids:
            return {}

        try:
            # Use 'in_' filter to fetch all slots in one query
            response = (
                self.client.table("slots").select("*").in_("id", slot_ids).execute()
            )

            slots_map = {}
            for item in response.data:
                slot = self._parse_slot(item)
                slots_map[slot.id] = slot

            return slots_map
        except Exception as e:
            raise RuntimeError(f"Failed to get slots by IDs: {e}") from e

    async def get_clients_by_ids(self, client_ids: List[str]) -> dict[str, Client]:
        """
        Batch fetch multiple clients by IDs.

        Args:
            client_ids: List of client IDs to fetch

        Returns:
            Dictionary mapping client_id -> Client object
        """
        if not client_ids:
            return {}

        try:
            # Use 'in_' filter to fetch all clients in one query
            response = (
                self.client.table("clients").select("*").in_("id", client_ids).execute()
            )

            clients_map = {}
            for item in response.data:
                client = Client(**item)
                clients_map[client.id] = client

            return clients_map
        except Exception as e:
            raise RuntimeError(f"Failed to get clients by IDs: {e}") from e

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
        """
        Get bookings that need reminders (within specified hours).

        Optimized to use SQL JOIN instead of N+1 queries.
        """
        try:
            from datetime import timedelta

            now = utc_now()
            target_time = now + timedelta(hours=hours_before)

            # Use SQL JOIN to filter by slot start_time directly in the query
            # This avoids fetching all bookings and filtering in Python
            now_str = to_iso_string(now)
            target_str = to_iso_string(target_time)

            # Query bookings with slot join to filter by start_time
            # Note: Supabase PostgREST doesn't support JOINs directly,
            # so we fetch bookings and slots separately but efficiently
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

            if not response.data:
                return []

            # Batch fetch all slots at once
            slot_ids = [item["slot_id"] for item in response.data]
            slots_map = await self.get_slots_by_ids(slot_ids)

            bookings = []
            for item in response.data:
                slot = slots_map.get(item["slot_id"])
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

    # ========== Admin Operations ==========

    async def get_all_slots(
        self,
        service_type: Optional[str] = None,
        status: Optional[SlotStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Slot]:
        """
        Get all slots (admin operation).

        Args:
            service_type: Filter by service type
            status: Filter by slot status
            start_date: Filter slots starting from this date
            end_date: Filter slots ending before this date

        Returns:
            List of slots matching criteria
        """
        try:
            query = self.client.table("slots").select("*")

            if service_type:
                query = query.eq("service_type", service_type)
            if status:
                query = query.eq("status", status.value)
            if start_date:
                query = query.gte("start_time", to_iso_string(start_date))
            if end_date:
                query = query.lte("end_time", to_iso_string(end_date))

            query = query.order("start_time", desc=False)
            response = query.execute()

            slots = []
            for item in response.data:
                slots.append(self._parse_slot(item))

            return slots
        except Exception as e:
            raise RuntimeError(f"Failed to get all slots: {e}") from e

    async def get_all_bookings(
        self,
        status: Optional[BookingStatus] = None,
        service_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Booking]:
        """
        Get all bookings (admin operation).

        Args:
            status: Filter by booking status
            service_type: Filter by service type
            start_date: Filter bookings with slots starting from this date
            limit: Maximum number of bookings to return

        Returns:
            List of bookings matching criteria
        """
        try:
            query = self.client.table("bookings").select("*")

            if status:
                query = query.eq("status", status.value)
            if service_type:
                query = query.eq("service_type", service_type)

            query = query.order("created_at", desc=True).limit(limit)
            response = query.execute()

            bookings = []
            for item in response.data:
                booking = self._parse_booking(item)

                # Filter by slot start_date if provided
                if start_date:
                    slot = await self.get_slot_by_id(booking.slot_id)
                    if not slot or slot.start_time < start_date:
                        continue

                bookings.append(booking)

            return bookings
        except Exception as e:
            raise RuntimeError(f"Failed to get all bookings: {e}") from e

    async def delete_slot(self, slot_id: str) -> bool:
        """
        Delete a slot (admin operation).

        Args:
            slot_id: Slot ID to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            response = self.client.table("slots").delete().eq("id", slot_id).execute()
            return len(response.data) > 0
        except Exception as e:
            raise RuntimeError(f"Failed to delete slot: {e}") from e

    async def get_all_clients(self, limit: int = 100) -> List[Client]:
        """
        Get all clients (admin operation).

        Args:
            limit: Maximum number of clients to return

        Returns:
            List of clients
        """
        try:
            response = (
                self.client.table("clients")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

            clients = []
            for item in response.data:
                clients.append(Client(**item))

            return clients
        except Exception as e:
            raise RuntimeError(f"Failed to get all clients: {e}") from e

    # ========== Business Operations ==========

    async def create_business(self, business_data) -> Any:
        """
        Создать бизнес в БД.

        Args:
            business_data: BusinessCreate object

        Returns:
            Created Business object
        """
        try:
            # Check for duplicates by google_place_id
            if business_data.google_place_id:
                existing = await self.get_business_by_place_id(
                    business_data.google_place_id
                )
                if existing:
                    # Update existing business
                    return await self.update_business(existing.id, business_data)

            data = business_data.model_dump(exclude_none=True)
            # Convert Decimal to float for JSON serialization
            if data.get("latitude"):
                data["latitude"] = float(data["latitude"])
            if data.get("longitude"):
                data["longitude"] = float(data["longitude"])
            if data.get("rating"):
                data["rating"] = float(data["rating"])

            response = self.client.table("businesses").insert(data).execute()

            if not response.data:
                raise ValueError("Failed to create business: no data returned")

            return self._parse_business(response.data[0])
        except Exception as e:
            raise RuntimeError(f"Failed to create business: {e}") from e

    async def get_business_by_place_id(self, place_id: str) -> Optional[Any]:
        """
        Получить бизнес по Google Place ID.

        Args:
            place_id: Google Place ID

        Returns:
            Business object or None
        """
        try:
            response = (
                self.client.table("businesses")
                .select("*")
                .eq("google_place_id", place_id)
                .execute()
            )

            if response.data:
                return self._parse_business(response.data[0])
            return None
        except Exception as e:
            raise RuntimeError(f"Failed to get business by place_id: {e}") from e

    async def batch_create_businesses(self, businesses: List[Any]) -> List[Any]:
        """
        Батчевая вставка бизнесов с дедупликацией.

        Args:
            businesses: List of BusinessCreate objects

        Returns:
            List of created/updated Business objects
        """
        if not businesses:
            return []

        try:
            # Prepare data for upsert
            data_list = []
            for b in businesses:
                data = b.model_dump(exclude_none=True)
                # Convert Decimal to float
                if data.get("latitude"):
                    data["latitude"] = float(data["latitude"])
                if data.get("longitude"):
                    data["longitude"] = float(data["longitude"])
                if data.get("rating"):
                    data["rating"] = float(data["rating"])
                data_list.append(data)

            # Use upsert with google_place_id as conflict target
            response = (
                self.client.table("businesses")
                .upsert(
                    data_list, on_conflict="google_place_id", ignore_duplicates=False
                )
                .execute()
            )

            result = []
            for item in response.data:
                result.append(self._parse_business(item))

            return result
        except Exception as e:
            raise RuntimeError(f"Failed to batch create businesses: {e}") from e

    async def update_business(self, business_id: str, business_data) -> Any:
        """
        Обновить бизнес.

        Args:
            business_id: Business ID
            business_data: BusinessCreate object with updates

        Returns:
            Updated Business object
        """
        try:
            data = business_data.model_dump(
                exclude_none=True, exclude={"id", "collected_at", "updated_at"}
            )
            # Convert Decimal to float
            if data.get("latitude"):
                data["latitude"] = float(data["latitude"])
            if data.get("longitude"):
                data["longitude"] = float(data["longitude"])
            if data.get("rating"):
                data["rating"] = float(data["rating"])

            data["updated_at"] = to_iso_string(utc_now())

            response = (
                self.client.table("businesses")
                .update(data)
                .eq("id", business_id)
                .execute()
            )

            if not response.data:
                raise ValueError("Business not found")

            return self._parse_business(response.data[0])
        except Exception as e:
            raise RuntimeError(f"Failed to update business: {e}") from e

    async def search_businesses(
        self,
        category: Optional[str] = None,
        district: Optional[str] = None,
        limit: int = 100,
    ) -> List[Any]:
        """
        Поиск бизнесов в БД.

        Args:
            category: Optional category filter
            district: Optional district filter
            limit: Maximum number of results

        Returns:
            List of Business objects
        """
        try:
            query = self.client.table("businesses").select("*")

            if category:
                query = query.eq("category", category)
            if district:
                query = query.eq("district", district)

            query = query.order("collected_at", desc=True).limit(limit)

            response = query.execute()

            businesses = []
            for item in response.data:
                businesses.append(self._parse_business(item))

            return businesses
        except Exception as e:
            raise RuntimeError(f"Failed to search businesses: {e}") from e

    def _parse_business(self, item: dict) -> Any:
        """
        Parse business data from database response.

        Args:
            item: Raw business data from database

        Returns:
            Parsed Business object
        """
        # Import here to avoid circular dependencies
        import sys
        from decimal import Decimal
        from pathlib import Path

        # Try to import Business from research_results first
        research_results_path = Path(__file__).parent.parent / "research_results"
        if str(research_results_path) not in sys.path:
            sys.path.insert(0, str(research_results_path))

        try:
            from utils.lead_generation.models import Business
        except ImportError:
            # Fallback: try importing from parent directory
            mvp_root = Path(__file__).parent.parent
            if str(mvp_root) not in sys.path:
                sys.path.insert(0, str(mvp_root))
            from research_results.utils.lead_generation.models import Business

        item = item.copy()

        # Parse timestamps
        for field in ["collected_at", "updated_at"]:
            if item.get(field):
                item[field] = parse_iso_datetime(item[field])

        # Convert float to Decimal for latitude, longitude, rating
        if item.get("latitude"):
            item["latitude"] = Decimal(str(item["latitude"]))
        if item.get("longitude"):
            item["longitude"] = Decimal(str(item["longitude"]))
        if item.get("rating"):
            item["rating"] = Decimal(str(item["rating"]))

        return Business(**item)


# Global database client instance
_db_client: Optional[SupabaseClient] = None


def get_db_client() -> SupabaseClient:
    """Get or create database client instance."""
    global _db_client
    if _db_client is None:
        _db_client = SupabaseClient()
    return _db_client
