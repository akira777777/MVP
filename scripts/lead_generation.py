"""
Lead generation script for finding business owners in Czech Republic.
Searches Google Maps, then finds company info and owners via ARES/Obchodní rejstřík.
"""

import asyncio
import json
import csv
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from utils.lead_generation import (
    GoogleMapsClient,
    ARESClient,
    ObchodniRejstrikClient,
    MessageGenerator,
    BusinessLead,
    CompanyInfo,
    OwnerInfo,
)
from scripts.browser_scraper import BrowserScraper
from utils.logging_config import setup_logging

logger = setup_logging(
    name=__name__, log_level="INFO", log_file="lead_generation.log", log_dir="logs"
)


class LeadGenerator:
    """Main lead generation orchestrator."""

    def __init__(
        self,
        google_maps_api_key: Optional[str] = None,
        output_dir: str = "leads",
        language: str = "cs",
        use_browser_fallback: bool = True,
    ):
        """
        Initialize lead generator.

        Args:
            google_maps_api_key: Google Maps API key (optional, uses env var if not provided)
            output_dir: Directory to save results
            language: Language for messages ('cs', 'en', 'ru')
<<<<<<< Current (Your changes)
            use_browser_fallback: Whether to enable browser scraper fallback for Google Maps API
        """
        # Initialize browser scraper for fallback
<<<<<<< Current (Your changes)
        self.browser_scraper = None
        if use_browser_fallback:
            try:
                self.browser_scraper = BrowserScraper(use_mcp_puppeteer=True)
                logger.info("Browser scraper initialized for fallback")
            except Exception as e:
                logger.warning(f"Failed to initialize browser scraper: {e}")
        
        # Initialize Google Maps client with browser scraper fallback
        self.google_maps = GoogleMapsClient(
            api_key=google_maps_api_key,
            browser_scraper=self.browser_scraper,
            enable_cache=True
=======
            use_browser_fallback: Whether to use browser scraper as fallback for Google Maps API
        """
        browser_scraper = BrowserScraper(use_mcp_puppeteer=True) if use_browser_fallback else None
        self.google_maps = GoogleMapsClient(
            api_key=google_maps_api_key,
            browser_scraper=browser_scraper,
            enable_cache=True,
>>>>>>> Incoming (Background Agent changes)
=======
        self.browser_scraper = BrowserScraper(use_mcp_puppeteer=True)
        self.google_maps = GoogleMapsClient(
            api_key=google_maps_api_key,
            browser_scraper=self.browser_scraper
>>>>>>> Incoming (Background Agent changes)
        )
        self.ares = ARESClient()
        self.obchodni_rejstrik = ObchodniRejstrikClient()
        self.message_generator = MessageGenerator(language=language)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    async def close(self):
        """Close all clients."""
        await self.google_maps.close()
        await self.ares.close()
        await self.obchodni_rejstrik.close()
        if self.browser_scraper:
            await self.browser_scraper.close()

    async def find_leads(
        self,
        categories: List[str],
        location: str = "Prague, Czech Republic",
        max_per_category: int = 20,
    ) -> List[BusinessLead]:
        """
        Find business leads by searching Google Maps and enriching with registry data.

        Args:
            categories: List of business categories to search (e.g., ["beauty salon", "kavárna"])
            location: Location to search in
            max_per_category: Maximum results per category

        Returns:
            List of BusinessLead objects
        """
        all_leads = []

        for category in categories:
            logger.info(f"Searching for '{category}' in {location}...")

            try:
                # Search Google Maps
                places = await self.google_maps.search_businesses(
                    query=category, location=location, max_results=max_per_category
                )

                logger.info(f"Found {len(places)} places for '{category}'")

                # Process each place
                for place_data in places:
                    try:
                        lead = await self._enrich_lead(place_data)
                        if lead:
                            all_leads.append(lead)
                            logger.info(
                                f"✓ Enriched lead: {lead.business_name} "
                                f"(IČO: {lead.company_info.ico if lead.company_info else 'N/A'})"
                            )

                        # Rate limiting - be respectful
                        await asyncio.sleep(1)

                    except Exception as e:
                        logger.error(f"Error processing place: {e}", exc_info=True)
                        continue

            except Exception as e:
                logger.error(f"Error searching category '{category}': {e}", exc_info=True)
                continue

        return all_leads

    async def _enrich_lead(self, place_data: dict) -> Optional[BusinessLead]:
        """
        Enrich Google Maps place data with company registry information.

        Args:
            place_data: Raw Google Maps place data

        Returns:
            BusinessLead object or None if enrichment fails
        """
        # Parse Google Maps data
        google_info = self.google_maps.parse_place_data(place_data)

        # Create initial lead
        lead = BusinessLead(**google_info)

        # Try to find company by name
        business_name = lead.business_name
        company_info = None
        owners = []

        # Search ARES by name
        try:
            ares_results = await self.ares.search_by_name(business_name, max_results=5)

            # Try to match by name similarity or address
            for result in ares_results:
                parsed = self.ares.parse_company_data(result)
                # Simple matching - could be improved
                if parsed.name.lower() in business_name.lower() or business_name.lower() in parsed.name.lower():
                    company_info = parsed
                    break

        except Exception as e:
            logger.debug(f"ARES search failed for {business_name}: {e}")

        # If not found in ARES, try Obchodní rejstřík
        if not company_info:
            try:
                or_results = await self.obchodni_rejstrik.search_by_name(
                    business_name, max_results=5
                )

                for result in or_results:
                    # Get detailed info including owners
                    details = await self.obchodni_rejstrik.get_company_details(
                        result["ico"]
                    )
                    if details:
                        company_info = self.obchodni_rejstrik.parse_company_data(details)
                        owners = self.obchodni_rejstrik.parse_owners(details)
                        break

            except Exception as e:
                logger.debug(f"Obchodní rejstřík search failed for {business_name}: {e}")

        # If still not found, try searching by address
        if not company_info and lead.google_address:
            try:
                ares_address_results = await self.ares.search_by_address(
                    lead.google_address
                )
                if ares_address_results:
                    # Take first match
                    company_info = self.ares.parse_company_data(ares_address_results[0])
            except Exception as e:
                logger.debug(f"ARES address search failed: {e}")

        # If we have IČO but no owners, try to get details from Obchodní rejstřík
        if company_info and not owners:
            try:
                details = await self.obchodni_rejstrik.get_company_details(
                    company_info.ico
                )
                if details:
                    owners = self.obchodni_rejstrik.parse_owners(details)
            except Exception as e:
                logger.debug(f"Failed to get owners for IČO {company_info.ico}: {e}")

        # Update lead with registry data
        lead.company_info = company_info
        lead.owners = owners

        return lead

    def save_leads(
        self,
        leads: List[BusinessLead],
        format: str = "json",
        filename: Optional[str] = None,
    ) -> Path:
        """
        Save leads to file.

        Args:
            leads: List of BusinessLead objects
            format: Output format ('json', 'csv')
            filename: Output filename (auto-generated if not provided)

        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format == "json":
            if not filename:
                filename = f"leads_{timestamp}.json"
            filepath = self.output_dir / filename

            # Convert to dict for JSON serialization
            leads_data = [lead.model_dump(mode="json") for lead in leads]

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(leads_data, f, ensure_ascii=False, indent=2, default=str)

            logger.info(f"Saved {len(leads)} leads to {filepath}")

        elif format == "csv":
            if not filename:
                filename = f"leads_{timestamp}.csv"
            filepath = self.output_dir / filename

            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "business_name",
                        "address",
                        "phone",
                        "website",
                        "ico",
                        "company_name",
                        "owner_name",
                        "owner_role",
                        "google_maps_url",
                        "category",
                    ],
                )
                writer.writeheader()

                for lead in leads:
                    owner = lead.get_primary_owner()
                    writer.writerow(
                        {
                            "business_name": lead.business_name,
                            "address": lead.google_address or "",
                            "phone": lead.google_phone or "",
                            "website": lead.google_website or "",
                            "ico": lead.company_info.ico if lead.company_info else "",
                            "company_name": lead.company_info.name if lead.company_info else "",
                            "owner_name": owner.name if owner else "",
                            "owner_role": owner.role if owner else "",
                            "google_maps_url": lead.google_maps_url or "",
                            "category": lead.category or "",
                        }
                    )

            logger.info(f"Saved {len(leads)} leads to {filepath}")

        else:
            raise ValueError(f"Unsupported format: {format}")

        return filepath

    def generate_messages(
        self,
        leads: List[BusinessLead],
        sender_name: Optional[str] = None,
        include_demo: bool = True,
    ) -> List[dict]:
        """
        Generate personalized messages for leads.

        Args:
            leads: List of BusinessLead objects
            sender_name: Name of sender
            include_demo: Whether to include demo offer

        Returns:
            List of dicts with lead info and message
        """
        messages = []

        for lead in leads:
            if not lead.has_complete_info():
                continue

            message = self.message_generator.generate_cold_message(
                lead, sender_name=sender_name, include_demo_offer=include_demo
            )

            messages.append(
                {
                    "lead": lead,
                    "message": message,
                    "contact_name": lead.get_contact_name(),
                    "business_name": lead.business_name,
                    "phone": lead.google_phone,
                    "email": lead.company_info.email if lead.company_info else None,
                }
            )

        return messages

    def save_messages(
        self,
        messages: List[dict],
        filename: Optional[str] = None,
    ) -> Path:
        """
        Save generated messages to file.

        Args:
            messages: List of message dicts from generate_messages()
            filename: Output filename

        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if not filename:
            filename = f"messages_{timestamp}.txt"
        filepath = self.output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            for i, msg_data in enumerate(messages, 1):
                lead = msg_data["lead"]
                f.write(f"{'='*80}\n")
                f.write(f"Lead #{i}: {msg_data['business_name']}\n")
                f.write(f"{'='*80}\n\n")
                f.write(f"Contact: {msg_data['contact_name']}\n")
                f.write(f"Phone: {msg_data['phone'] or 'N/A'}\n")
                f.write(f"Email: {msg_data['email'] or 'N/A'}\n")
                f.write(f"IČO: {lead.company_info.ico if lead.company_info else 'N/A'}\n")
                f.write(f"Address: {lead.google_address or 'N/A'}\n")
                f.write(f"\n--- Message ---\n\n")
                f.write(msg_data["message"])
                f.write(f"\n\n\n")

        logger.info(f"Saved {len(messages)} messages to {filepath}")
        return filepath


async def main():
    """Main function for CLI usage."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate leads from Google Maps and Czech business registries"
    )
    parser.add_argument(
        "--categories",
        nargs="+",
        default=["beauty salon", "kavárna", "restaurant"],
        help="Business categories to search",
    )
    parser.add_argument(
        "--location",
        default="Prague, Czech Republic",
        help="Location to search in",
    )
    parser.add_argument(
        "--max-per-category",
        type=int,
        default=20,
        help="Maximum results per category",
    )
    parser.add_argument(
        "--output-dir",
        default="leads",
        help="Output directory for results",
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv"],
        default="json",
        help="Output format",
    )
    parser.add_argument(
        "--language",
        choices=["cs", "en", "ru"],
        default="cs",
        help="Language for messages",
    )
    parser.add_argument(
        "--generate-messages",
        action="store_true",
        help="Generate personalized messages",
    )
    parser.add_argument(
        "--sender-name",
        help="Sender name for messages",
    )

    args = parser.parse_args()

    generator = LeadGenerator(output_dir=args.output_dir, language=args.language)

    try:
        # Find leads
        leads = await generator.find_leads(
            categories=args.categories,
            location=args.location,
            max_per_category=args.max_per_category,
        )

        logger.info(f"Found {len(leads)} total leads")

        # Save leads
        leads_file = generator.save_leads(leads, format=args.format)
        print(f"✓ Leads saved to: {leads_file}")

        # Generate messages if requested
        if args.generate_messages:
            complete_leads = [lead for lead in leads if lead.has_complete_info()]
            logger.info(f"Generating messages for {len(complete_leads)} complete leads...")

            messages = generator.generate_messages(
                complete_leads, sender_name=args.sender_name
            )

            messages_file = generator.save_messages(messages)
            print(f"✓ Messages saved to: {messages_file}")

    finally:
        await generator.close()


if __name__ == "__main__":
    asyncio.run(main())
