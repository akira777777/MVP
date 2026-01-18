"""
Main script for collecting business data from Prague via Google Maps.

This script systematically searches for small businesses across Prague districts
and business categories, collecting contact information and saving to CSV.
"""

import asyncio
import csv
import json
import logging
import random
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.lead_generation import (
    BusinessData,
    ScraperConfig,
    GoogleMapsScraper,
    MCPGoogleMapsClient,
)
from utils.lead_generation.utils import deduplicate_businesses, format_business_for_csv
from utils.logging_config import setup_logging

# Setup logging
logger = setup_logging(
    __name__,
    log_level="INFO",
    log_file="collect_prague_businesses.log",
)


class BusinessCollector:
    """Main class for collecting business data."""

    def __init__(self, config: ScraperConfig, output_file: str = "research_results/prague_businesses.csv"):
        """
        Initialize business collector.

        Args:
            config: Scraper configuration
            output_file: Output CSV file path
        """
        self.config = config
        self.output_file = Path(output_file)
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.progress_file = self.output_file.with_suffix(".progress.json")
        self.all_businesses: List[BusinessData] = []
        self.progress: Dict[str, Any] = self._load_progress()

    def _load_progress(self) -> Dict[str, Any]:
        """Load progress from file if exists."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading progress file: {e}")
        return {
            "completed_categories": [],
            "completed_districts": [],
            "last_update": None,
        }

    def _save_progress(self):
        """Save progress to file."""
        self.progress["last_update"] = datetime.now().isoformat()
        try:
            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump(self.progress, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving progress: {e}")

    async def collect_all(self):
        """Collect businesses from all categories and districts."""
        logger.info("Starting business data collection for Prague")

        # Try MCP first, fallback to browser scraping
        mcp_client = MCPGoogleMapsClient(self.config)
        mcp_available = await mcp_client.check_mcp_availability()

        if mcp_available:
            logger.info("Using MCP Google Maps client")
            await self._collect_with_mcp(mcp_client)
        else:
            logger.info("Using browser-based scraper")
            await self._collect_with_scraper()

        # Deduplicate all collected businesses
        logger.info(f"Total businesses collected: {len(self.all_businesses)}")
        self.all_businesses = deduplicate_businesses(self.all_businesses)
        logger.info(f"Unique businesses after deduplication: {len(self.all_businesses)}")

        # Save to CSV
        self._save_to_csv()

    async def _collect_with_mcp(self, mcp_client: MCPGoogleMapsClient):
        """Collect businesses using MCP client."""
        for category in self.config.business_categories:
            if category in self.progress.get("completed_categories", []):
                logger.info(f"Skipping completed category: {category}")
                continue

            logger.info(f"Collecting businesses for category: {category}")

            for district in self.config.prague_districts:
                district_key = f"{category}_{district}"
                if district_key in self.progress.get("completed_districts", []):
                    logger.info(f"Skipping completed district: {district_key}")
                    continue

                try:
                    location = {"latitude": 50.0755, "longitude": 14.4378}  # Prague center
                    businesses = await mcp_client.search_businesses(
                        query=f"{category} {district}",
                        location=location,
                        max_results=self.config.max_results_per_query,
                    )

                    self.all_businesses.extend(businesses)
                    logger.info(
                        f"Found {len(businesses)} businesses for {category} in {district}"
                    )

                    # Save progress
                    if district_key not in self.progress.get("completed_districts", []):
                        self.progress.setdefault("completed_districts", []).append(
                            district_key
                        )
                    self._save_progress()

                    # Rate limiting
                    await asyncio.sleep(
                        random.uniform(
                            self.config.min_delay_seconds,
                            self.config.max_delay_seconds,
                        )
                    )

                except Exception as e:
                    logger.error(
                        f"Error collecting {category} in {district}: {e}", exc_info=True
                    )
                    continue

            # Mark category as completed
            if category not in self.progress.get("completed_categories", []):
                self.progress.setdefault("completed_categories", []).append(category)
            self._save_progress()

    async def _collect_with_scraper(self):
        """Collect businesses using browser scraper."""
        async with GoogleMapsScraper(self.config) as scraper:
            for category in self.config.business_categories:
                if category in self.progress.get("completed_categories", []):
                    logger.info(f"Skipping completed category: {category}")
                    continue

                logger.info(f"Collecting businesses for category: {category}")

                for district in self.config.prague_districts:
                    district_key = f"{category}_{district}"
                    if district_key in self.progress.get("completed_districts", []):
                        logger.info(f"Skipping completed district: {district_key}")
                        continue

                    try:
                        businesses = await scraper.search_businesses(
                            query=category,
                            location=district,
                            max_results=self.config.max_results_per_query,
                        )

                        self.all_businesses.extend(businesses)
                        logger.info(
                            f"Found {len(businesses)} businesses for {category} in {district}"
                        )

                        # Save progress
                        if district_key not in self.progress.get("completed_districts", []):
                            self.progress.setdefault("completed_districts", []).append(
                                district_key
                            )
                        self._save_progress()

                    except Exception as e:
                        logger.error(
                            f"Error collecting {category} in {district}: {e}",
                            exc_info=True,
                        )
                        continue

                # Mark category as completed
                if category not in self.progress.get("completed_categories", []):
                    self.progress.setdefault("completed_categories", []).append(category)
                self._save_progress()

    def _save_to_csv(self):
        """Save collected businesses to CSV file."""
        if not self.all_businesses:
            logger.warning("No businesses to save")
            return

        csv_file = self.output_file
        file_exists = csv_file.exists()

        try:
            with open(csv_file, "w", newline="", encoding="utf-8") as f:
                fieldnames = [
                    "name",
                    "address",
                    "phone",
                    "website",
                    "category",
                    "rating",
                    "review_count",
                    "place_id",
                    "latitude",
                    "longitude",
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for business in self.all_businesses:
                    writer.writerow(format_business_for_csv(business))

            logger.info(f"Saved {len(self.all_businesses)} businesses to {csv_file}")

        except Exception as e:
            logger.error(f"Error saving CSV file: {e}", exc_info=True)
            raise


async def main():
    """Main entry point."""
    # Configuration
    config = ScraperConfig(
        headless=False,
        max_results_per_query=20,
        min_delay_seconds=2.0,
        max_delay_seconds=5.0,
    )

    # Output file
    output_file = "research_results/prague_businesses.csv"

    # Create collector and run
    collector = BusinessCollector(config, output_file)
    await collector.collect_all()

    logger.info("Business data collection completed")


if __name__ == "__main__":
    asyncio.run(main())
