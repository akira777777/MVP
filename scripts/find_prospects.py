"""
Main script for finding business prospects in Prague.
Combines Google Maps search with Czech registry lookups to find business owners.
"""

import asyncio
import csv
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.czech_registry_scraper import CzechRegistryScraper
from scripts.google_maps_scraper import GoogleMapsScraper
from models.prospect import BusinessProspect

# Setup logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_dir / "prospect_finder.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class ProspectFinder:
    """Main class for finding and enriching business prospects."""

    # Prague business categories for lead generation
    PRAGUE_CATEGORIES = {
        "beauty_salon": [
            "kadeřnictví Praha",
            "kosmetika Praha",
            "manikúra Praha",
            "pedikúra Praha",
        ],
        "spa": ["wellness Praha", "masáže Praha", "spa Praha"],
        "restaurant": ["restaurace Praha", "kavárna Praha"],
        "fitness": ["fitness Praha", "posilovna Praha"],
        "tourism": ["turistické služby Praha", "cestovní kancelář Praha"],
    }

    def __init__(self, google_maps_api_key: str):
        """
        Initialize prospect finder.

        Args:
            google_maps_api_key: Google Maps API key
        """
        self.google_maps_api_key = google_maps_api_key

    async def find_prospects(
        self,
        category: str,
        max_results: int = 20,
        enrich_with_registry: bool = True,
    ) -> list[BusinessProspect]:
        """
        Find prospects for a given category.

        Args:
            category: Business category (beauty_salon, spa, restaurant, etc.)
            max_results: Maximum number of prospects to find
            enrich_with_registry: Whether to enrich with Czech registry data

        Returns:
            List of BusinessProspect objects
        """
        prospects = []

        async with GoogleMapsScraper(self.google_maps_api_key) as maps_scraper:
            # Get search queries for category
            queries = self.PRAGUE_CATEGORIES.get(category, [category])

            for query in queries:
                logger.info(f"Searching Google Maps for: {query}")

                # Search Google Maps
                category_prospects = await maps_scraper.search_places(
                    query=query,
                    max_results=max_results // len(queries) + 1,
                )

                prospects.extend(category_prospects)

                # Limit total results
                if len(prospects) >= max_results:
                    prospects = prospects[:max_results]
                    break

        # Enrich with registry data
        if enrich_with_registry:
            logger.info("Enriching prospects with Czech registry data...")
            async with CzechRegistryScraper() as registry_scraper:
                enriched_prospects = []
                for prospect in prospects:
                    try:
                        enriched = await registry_scraper.enrich_prospect(prospect)
                        enriched_prospects.append(enriched)
                        # Rate limiting - be respectful
                        await asyncio.sleep(1)
                    except Exception as e:
                        logger.error(f"Error enriching prospect {prospect.name}: {e}")
                        enriched_prospects.append(prospect)

                prospects = enriched_prospects

        return prospects

    async def find_by_query(
        self,
        query: str,
        max_results: int = 20,
        enrich_with_registry: bool = True,
    ) -> list[BusinessProspect]:
        """
        Find prospects by custom search query.

        Args:
            query: Search query (e.g., "beauty salon Prague")
            max_results: Maximum number of prospects
            enrich_with_registry: Whether to enrich with registry data

        Returns:
            List of BusinessProspect objects
        """
        prospects = []

        async with GoogleMapsScraper(self.google_maps_api_key) as maps_scraper:
            logger.info(f"Searching Google Maps for: {query}")

            prospects = await maps_scraper.search_places(
                query=query,
                max_results=max_results,
            )

        # Enrich with registry data
        if enrich_with_registry:
            logger.info("Enriching prospects with Czech registry data...")
            async with CzechRegistryScraper() as registry_scraper:
                enriched_prospects = []
                for prospect in prospects:
                    try:
                        enriched = await registry_scraper.enrich_prospect(prospect)
                        enriched_prospects.append(enriched)
                        await asyncio.sleep(1)  # Rate limiting
                    except Exception as e:
                        logger.error(f"Error enriching prospect {prospect.name}: {e}")
                        enriched_prospects.append(prospect)

                prospects = enriched_prospects

        return prospects

    def save_to_csv(
        self, prospects: list[BusinessProspect], output_file: str = "prospects.csv"
    ):
        """
        Save prospects to CSV file.

        Args:
            prospects: List of BusinessProspect objects
            output_file: Output CSV file path
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "name",
                    "legal_name",
                    "address",
                    "phone",
                    "website",
                    "ico",
                    "category",
                    "rating",
                    "reviews_count",
                    "owners",
                    "status",
                    "google_maps_url",
                    "found_at",
                ],
            )
            writer.writeheader()

            for prospect in prospects:
                owners_str = "; ".join(
                    [f"{o.name} ({o.role})" for o in prospect.owners]
                )
                writer.writerow(
                    {
                        "name": prospect.name,
                        "legal_name": prospect.legal_name or "",
                        "address": prospect.address or "",
                        "phone": prospect.phone or "",
                        "website": str(prospect.website) if prospect.website else "",
                        "ico": prospect.ico or "",
                        "category": prospect.category or "",
                        "rating": prospect.rating or "",
                        "reviews_count": prospect.reviews_count or "",
                        "owners": owners_str,
                        "status": prospect.status or "",
                        "google_maps_url": str(prospect.google_maps_url)
                        if prospect.google_maps_url
                        else "",
                        "found_at": prospect.found_at.isoformat() if prospect.found_at else "",
                    }
                )

        logger.info(f"Saved {len(prospects)} prospects to {output_path}")

    def save_to_json(
        self, prospects: list[BusinessProspect], output_file: str = "prospects.json"
    ):
        """
        Save prospects to JSON file.

        Args:
            prospects: List of BusinessProspect objects
            output_file: Output JSON file path
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                [p.model_dump(mode="json", exclude_none=True) for p in prospects],
                f,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

        logger.info(f"Saved {len(prospects)} prospects to {output_path}")


async def main():
    """Main function for CLI usage."""
    import os
    import sys

    # Get Google Maps API key from environment
    google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not google_maps_api_key:
        logger.error(
            "GOOGLE_MAPS_API_KEY environment variable is required. "
            "Get your API key from https://console.cloud.google.com/"
        )
        sys.exit(1)

    finder = ProspectFinder(google_maps_api_key)

    # Example usage
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        logger.info(f"Searching for: {query}")
        prospects = await finder.find_by_query(query, max_results=20)
    else:
        # Default: search beauty salons
        logger.info("Searching for beauty salons in Prague...")
        prospects = await finder.find_prospects("beauty_salon", max_results=20)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    finder.save_to_csv(prospects, f"output/prospects_{timestamp}.csv")
    finder.save_to_json(prospects, f"output/prospects_{timestamp}.json")

    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info(f"Found {len(prospects)} prospects")
    logger.info(f"{'='*60}\n")

    # Print first few prospects
    for i, prospect in enumerate(prospects[:5], 1):
        logger.info(f"\n{i}. {prospect.name}")
        logger.info(f"   Address: {prospect.address}")
        logger.info(f"   Phone: {prospect.phone}")
        if prospect.ico:
            logger.info(f"   IČO: {prospect.ico}")
        if prospect.owners:
            logger.info(f"   Owners: {', '.join([o.name for o in prospect.owners])}")


if __name__ == "__main__":
    asyncio.run(main())
