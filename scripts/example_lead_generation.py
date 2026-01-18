"""
Example script for lead generation.
Demonstrates how to use the lead generation tools programmatically.
"""

import asyncio
from utils.lead_generation import LeadGenerator


async def example_simple_search():
    """Simple example: search for beauty salons in Prague."""
    generator = LeadGenerator(output_dir="leads", language="cs")

    try:
        # Search for beauty salons
        leads = await generator.find_leads(
            categories=["salon krásy", "masáž"],
            location="Prague, Czech Republic",
            max_per_category=10,
        )

        print(f"Found {len(leads)} leads")

        # Save results
        leads_file = generator.save_leads(leads, format="json")
        print(f"Saved to: {leads_file}")

        # Show summary
        complete_leads = [lead for lead in leads if lead.has_complete_info()]
        print(f"Complete leads (with owners): {len(complete_leads)}")

        for lead in complete_leads[:3]:  # Show first 3
            owner = lead.get_primary_owner()
            print(f"\n{lead.business_name}")
            print(f"  IČO: {lead.company_info.ico if lead.company_info else 'N/A'}")
            print(f"  Owner: {owner.name if owner else 'N/A'}")

    finally:
        await generator.close()


async def example_with_messages():
    """Example with message generation."""
    generator = LeadGenerator(output_dir="leads", language="cs")

    try:
        # Find leads
        leads = await generator.find_leads(
            categories=["kavárna"],
            location="Prague 1",
            max_per_category=5,
        )

        # Filter complete leads
        complete_leads = [lead for lead in leads if lead.has_complete_info()]

        # Generate messages
        messages = generator.generate_messages(
            complete_leads,
            sender_name="Jan Novák",
            include_demo=True,
        )

        # Save messages
        messages_file = generator.save_messages(messages)
        print(f"Generated {len(messages)} messages")
        print(f"Saved to: {messages_file}")

        # Show first message
        if messages:
            print("\n--- First Message ---")
            print(messages[0]["message"])

    finally:
        await generator.close()


if __name__ == "__main__":
    print("Example 1: Simple search")
    print("=" * 50)
    asyncio.run(example_simple_search())

    print("\n\nExample 2: With messages")
    print("=" * 50)
    asyncio.run(example_with_messages())
