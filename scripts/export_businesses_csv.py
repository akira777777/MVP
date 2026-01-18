"""
Script to export collected business data to CSV format.

Reads business data from JSON progress file and exports to CSV.
"""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.business import Business
from utils.logging_config import setup_logging

logger = setup_logging(__name__)


def load_businesses_from_json(json_file: Path) -> list[Business]:
    """
    Load businesses from JSON file.

    Args:
        json_file: Path to JSON file with business data

    Returns:
        List of Business instances
    """
    if not json_file.exists():
        logger.error(f"JSON file not found: {json_file}")
        return []

    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        businesses = []
        for b_data in data.get("businesses", []):
            try:
                business = Business(**b_data)
                businesses.append(business)
            except Exception as e:
                logger.warning(f"Error loading business: {e}")
                continue

        logger.info(f"Loaded {len(businesses)} businesses from {json_file}")
        return businesses
    except Exception as e:
        logger.error(f"Error loading JSON file: {e}")
        return []


def deduplicate_businesses(businesses: list[Business]) -> list[Business]:
    """
    Remove duplicate businesses based on name and address.

    Args:
        businesses: List of businesses

    Returns:
        Deduplicated list
    """
    seen = set()
    unique = []

    for business in businesses:
        # Create unique key from normalized name and address
        key = (
            business.name.lower().strip(),
            business.address.lower().strip(),
        )
        if key not in seen:
            seen.add(key)
            unique.append(business)
        else:
            logger.debug(f"Removing duplicate: {business.name}")

    logger.info(f"Deduplicated: {len(businesses)} -> {len(unique)} businesses")
    return unique


def export_to_csv(businesses: list[Business], output_file: Path):
    """
    Export businesses to CSV file.

    Args:
        businesses: List of businesses to export
        output_file: Path to output CSV file
    """
    if not businesses:
        logger.warning("No businesses to export")
        return

    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # CSV columns
    fieldnames = [
        "name",
        "category",
        "address",
        "phone",
        "email",
        "website",
        "owner_name",
        "social_facebook",
        "social_instagram",
        "google_maps_url",
        "notes",
        "collected_at",
    ]

    try:
        with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for business in businesses:
                row = {
                    "name": business.name,
                    "category": business.category,
                    "address": business.address,
                    "phone": business.phone or "",
                    "email": business.email or "",
                    "website": str(business.website) if business.website else "",
                    "owner_name": business.owner_name or "",
                    "social_facebook": str(business.social_facebook) if business.social_facebook else "",
                    "social_instagram": str(business.social_instagram) if business.social_instagram else "",
                    "google_maps_url": str(business.google_maps_url) if business.google_maps_url else "",
                    "notes": business.notes or "",
                    "collected_at": business.collected_at.isoformat() if business.collected_at else "",
                }
                writer.writerow(row)

        logger.info(f"Exported {len(businesses)} businesses to {output_file}")
    except Exception as e:
        logger.error(f"Error exporting to CSV: {e}")
        raise


def main(
    input_file: Optional[Path] = None,
    output_file: Optional[Path] = None,
    deduplicate: bool = True,
):
    """
    Main entry point.

    Args:
        input_file: Path to input JSON file (default: data/prague_businesses_progress.json)
        output_file: Path to output CSV file (default: data/prague_businesses.csv)
        deduplicate: Whether to remove duplicates
    """
    if input_file is None:
        input_file = Path("data/prague_businesses_progress.json")
    if output_file is None:
        output_file = Path("data/prague_businesses.csv")

    logger.info(f"Loading businesses from {input_file}")
    businesses = load_businesses_from_json(input_file)

    if not businesses:
        logger.error("No businesses found. Run collect_prague_businesses.py first.")
        sys.exit(1)

    if deduplicate:
        businesses = deduplicate_businesses(businesses)

    logger.info(f"Exporting {len(businesses)} businesses to {output_file}")
    export_to_csv(businesses, output_file)

    # Print statistics
    print(f"\nExport complete!")
    print(f"Total businesses: {len(businesses)}")
    print(f"Output file: {output_file}")
    print("\nCategory breakdown:")
    categories = {}
    for business in businesses:
        categories[business.category] = categories.get(business.category, 0) + 1
    for category, count in sorted(categories.items()):
        print(f"  {category}: {count}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Export business data to CSV")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/prague_businesses_progress.json"),
        help="Input JSON file path",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/prague_businesses.csv"),
        help="Output CSV file path",
    )
    parser.add_argument(
        "--no-deduplicate",
        action="store_true",
        help="Skip deduplication",
    )

    args = parser.parse_args()
    main(
        input_file=args.input,
        output_file=args.output,
        deduplicate=not args.no_deduplicate,
    )
