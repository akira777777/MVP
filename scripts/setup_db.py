"""
Database setup script for Supabase.
Run this to create initial tables and seed data.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import get_db_client
from models.service import ServiceType
from models.slot import SlotCreate


async def create_sample_slots():
    """Create sample time slots for testing."""
    db = get_db_client()

    # Create slots for the next 7 days
    base_date = datetime.utcnow().replace(hour=10, minute=0, second=0, microsecond=0)
    base_date = base_date + timedelta(days=1)  # Start from tomorrow

    slots_created = 0

    for day in range(7):
        for hour in [10, 12, 14, 16]:  # 4 slots per day
            slot_time = base_date + timedelta(days=day, hours=hour)

            for service_type in ServiceType:
                service = service_type.value
                slot_data = SlotCreate(
                    start_time=slot_time,
                    end_time=slot_time + timedelta(hours=1),
                    service_type=service,
                )

                try:
                    slot = await db.create_slot(slot_data)
                    slots_created += 1
                    print(f"Created slot: {service} at {slot_time.strftime('%Y-%m-%d %H:%M')}")
                except Exception as e:
                    print(f"Failed to create slot: {e}")

    print(f"\n✅ Created {slots_created} slots")


async def main():
    """Main setup function."""
    print("🚀 Setting up database...")
    print("\nNote: Make sure you've run the SQL migrations in Supabase SQL Editor first!")
    print("See README.md for SQL migration scripts.\n")

    try:
        # Test database connection
        db = get_db_client()
        print("✅ Database connection successful")

        # Create sample slots
        response = input("\nCreate sample slots? (y/n): ")
        if response.lower() == "y":
            await create_sample_slots()

        print("\n✅ Database setup complete!")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
