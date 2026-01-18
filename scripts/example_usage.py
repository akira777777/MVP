"""
Example usage of ProspectFinder for finding business prospects in Prague.
"""

import asyncio
import os
from scripts.find_prospects import ProspectFinder


async def example_search_beauty_salons():
    """Example: Search for beauty salons."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        print("Please set GOOGLE_MAPS_API_KEY environment variable")
        return

    finder = ProspectFinder(api_key)

    print("🔍 Searching for beauty salons in Prague...")
    prospects = await finder.find_prospects(
        category="beauty_salon",
        max_results=10,
        enrich_with_registry=True,
    )

    print(f"\n✅ Found {len(prospects)} prospects\n")

    # Print first 3 prospects
    for i, prospect in enumerate(prospects[:3], 1):
        print(f"{i}. {prospect.name}")
        print(f"   📍 {prospect.address}")
        if prospect.phone:
            print(f"   📞 {prospect.phone}")
        if prospect.ico:
            print(f"   🏢 IČO: {prospect.ico}")
        if prospect.owners:
            owners_str = ", ".join([o.name for o in prospect.owners])
            print(f"   👤 Owners: {owners_str}")
        print()

    # Save results
    finder.save_to_csv(prospects, "output/beauty_salons.csv")
    finder.save_to_json(prospects, "output/beauty_salons.json")


async def example_search_custom_query():
    """Example: Search by custom query."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        print("Please set GOOGLE_MAPS_API_KEY environment variable")
        return

    finder = ProspectFinder(api_key)

    query = "wellness Praha Vinohrady"
    print(f"🔍 Searching for: {query}")

    prospects = await finder.find_by_query(
        query=query,
        max_results=15,
        enrich_with_registry=True,
    )

    print(f"\n✅ Found {len(prospects)} prospects\n")

    # Filter by rating
    high_rated = [p for p in prospects if p.rating and p.rating >= 4.0]
    print(f"⭐ High-rated (≥4.0): {len(high_rated)}")

    # Save results
    finder.save_to_csv(prospects, "output/wellness_vinohrady.csv")


async def example_multiple_categories():
    """Example: Search multiple categories."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        print("Please set GOOGLE_MAPS_API_KEY environment variable")
        return

    finder = ProspectFinder(api_key)

    categories = ["beauty_salon", "spa", "restaurant"]

    all_prospects = []

    for category in categories:
        print(f"\n🔍 Searching {category}...")
        prospects = await finder.find_prospects(
            category=category,
            max_results=10,
            enrich_with_registry=True,
        )
        all_prospects.extend(prospects)
        print(f"✅ Found {len(prospects)} prospects")

    print(f"\n📊 Total prospects: {len(all_prospects)}")

    # Save combined results
    finder.save_to_csv(all_prospects, "output/all_categories.csv")


if __name__ == "__main__":
    # Run examples
    print("=" * 60)
    print("Prospect Finder - Example Usage")
    print("=" * 60)

    # Uncomment the example you want to run:
    # asyncio.run(example_search_beauty_salons())
    # asyncio.run(example_search_custom_query())
    # asyncio.run(example_multiple_categories())

    print("\n💡 Uncomment an example in the code to run it!")
