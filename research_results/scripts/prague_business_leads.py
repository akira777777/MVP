"""
Script for finding small businesses in Prague and exporting to Excel.
Searches Google Maps for Czech businesses and extracts owner information from websites and registries.
"""

import asyncio
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Fix Windows console encoding for Czech characters
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
from pydantic import BaseModel, Field
from utils.lead_generation.google_maps import GoogleMapsClient

from utils.logging_config import setup_logging

# Initialize logger first
logger = setup_logging(
    name=__name__, log_level="INFO", log_file="logs/prague_leads.log"
)

# Try to import BrowserScraper if available
BrowserScraper = None
HAS_BROWSER_SCRAPER = False
try:
    from scripts.browser_scraper import BrowserScraper

    HAS_BROWSER_SCRAPER = True
    logger.info("BrowserScraper imported successfully")
except ImportError as e:
    HAS_BROWSER_SCRAPER = False
    logger.warning(
        f"BrowserScraper not available: {e}. Website scraping will be limited."
    )
except Exception as e:
    HAS_BROWSER_SCRAPER = False
    logger.warning(
        f"Failed to import BrowserScraper: {e}. Website scraping will be limited."
    )
# Try to import Czech registry clients if available
try:
    from utils.lead_generation.ares import ARESClient
    from utils.lead_generation.obchodni_rejstrik import ObchodniRejstrikClient

    HAS_REGISTRY_CLIENTS = True
except ImportError:
    # If registry clients are not available, we'll skip registry searches
    HAS_REGISTRY_CLIENTS = False
    logger.warning("Czech registry clients not available, will only search websites")


class PragueBusinessLead(BaseModel):
    """Prague business lead information."""

    business_name: str = Field(..., description="Business name")
    address: Optional[str] = Field(None, description="Business address")
    phone: Optional[str] = Field(None, description="Phone number")
    email: Optional[str] = Field(None, description="Email address")
    website: Optional[str] = Field(None, description="Website URL")
    owner_first_name: Optional[str] = Field(None, description="Owner first name")
    owner_last_name: Optional[str] = Field(None, description="Owner last name")
    owner_full_name: Optional[str] = Field(None, description="Owner full name")
    ico: Optional[str] = Field(None, description="IČO - Company identification number")
    google_maps_url: Optional[str] = Field(None, description="Google Maps URL")
    category: Optional[str] = Field(None, description="Business category")


class PragueBusinessLeadGenerator:
    """Generator for Prague business leads."""

    def __init__(
        self,
        google_maps_api_key: Optional[str] = None,
        output_dir: str = "leads",
        use_browser_fallback: bool = True,
    ):
        """
        Initialize Prague business lead generator.

        Args:
            google_maps_api_key: Google Maps API key (optional, uses env var if not provided)
            output_dir: Directory to save results
            use_browser_fallback: Whether to enable browser scraper fallback
        """
        # Initialize browser scraper for website scraping
        self.browser_scraper = None
        if use_browser_fallback and HAS_BROWSER_SCRAPER and BrowserScraper:
            try:
                self.browser_scraper = BrowserScraper(use_mcp_puppeteer=True)
                logger.info("Browser scraper initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize browser scraper: {e}")

        # Initialize Google Maps client
        self.google_maps = GoogleMapsClient(
            api_key=google_maps_api_key,
            browser_scraper=self.browser_scraper,
        )

        # Initialize Czech business registries (if available)
        self.ares = None
        self.obchodni_rejstrik = None
        if HAS_REGISTRY_CLIENTS:
            try:
                self.ares = ARESClient()
                self.obchodni_rejstrik = ObchodniRejstrikClient()
                logger.info("Czech registry clients initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize registry clients: {e}")

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    async def close(self):
        """Close all clients."""
        await self.google_maps.close()
        if self.ares:
            await self.ares.close()
        if self.obchodni_rejstrik:
            await self.obchodni_rejstrik.close()
        if self.browser_scraper:
            await self.browser_scraper.close()

    def _parse_czech_phone(self, text: str) -> Optional[str]:
        """Extract Czech phone number from text."""
        # Czech phone patterns
        patterns = [
            r"\+420\s?\d{3}\s?\d{3}\s?\d{3}",  # +420 XXX XXX XXX
            r"420\s?\d{3}\s?\d{3}\s?\d{3}",  # 420 XXX XXX XXX
            r"\d{3}\s?\d{3}\s?\d{3}",  # XXX XXX XXX
            r"\(\+420\)\s?\d{3}\s?\d{3}\s?\d{3}",  # (+420) XXX XXX XXX
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                phone = match.group(0)
                # Normalize
                phone = re.sub(r"\s+", "", phone)
                if not phone.startswith("+"):
                    if phone.startswith("420"):
                        phone = "+" + phone
                    else:
                        phone = "+420" + phone
                return phone

        return None

    def _parse_email(self, text: str) -> Optional[str]:
        """Extract email from text."""
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        match = re.search(email_pattern, text)
        if match:
            return match.group(0).lower()
        return None

    def _parse_czech_name(self, text: str) -> Optional[Dict[str, str]]:
        """
        Extract Czech name from text.
        Returns dict with 'first_name', 'last_name', 'full_name'.
        """
        # Common Czech name patterns
        owner_patterns = [
            r"(?:Majitel|Vlastník|Ředitel|Statutární|Owner|Manager|Director)[:\s]+([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+(?:\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+)+)",
            r"([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+(?:\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+)+)\s+(?:je|je to|je toto)\s+(?:majitel|vlastník|ředitel)",
        ]

        for pattern in owner_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                full_name = match.group(1).strip()
                # Split into first and last name
                name_parts = full_name.split()
                if len(name_parts) >= 2:
                    # Usually first name(s) then last name
                    first_name = " ".join(name_parts[:-1])
                    last_name = name_parts[-1]
                    return {
                        "first_name": first_name,
                        "last_name": last_name,
                        "full_name": full_name,
                    }
                elif len(name_parts) == 1:
                    return {
                        "first_name": name_parts[0],
                        "last_name": "",
                        "full_name": full_name,
                    }

        return None

    async def _find_owner_from_registry(
        self, business_name: str, address: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find owner information from Czech business registries (ARES/Obchodní rejstřík).

        Args:
            business_name: Name of the business
            address: Optional address for matching

        Returns:
            Dict with owner and company information or None
        """
        if not self.ares or not self.obchodni_rejstrik:
            return None

        try:
            # Try ARES first
            ares_results = await self.ares.search_by_name(business_name, max_results=5)

            for result in ares_results:
                parsed = self.ares.parse_company_data(result)
                # Simple matching
                if (
                    parsed.name.lower() in business_name.lower()
                    or business_name.lower() in parsed.name.lower()
                ):
                    # Try to get owners from Obchodní rejstřík
                    try:
                        details = await self.obchodni_rejstrik.get_company_details(
                            parsed.ico
                        )
                        if details:
                            owners = self.obchodni_rejstrik.parse_owners(details)
                            if owners:
                                owner = owners[0]  # Get first owner
                                return {
                                    "ico": parsed.ico,
                                    "company_name": parsed.name,
                                    "owner_first_name": owner.name.split()[0]
                                    if owner.name.split()
                                    else "",
                                    "owner_last_name": owner.name.split()[-1]
                                    if len(owner.name.split()) > 1
                                    else "",
                                    "owner_full_name": owner.name,
                                    "email": parsed.email,
                                    "phone": parsed.phone,
                                }
                    except Exception as e:
                        logger.debug(f"Failed to get owners for IČO {parsed.ico}: {e}")

            # Try Obchodní rejstřík directly
            or_results = await self.obchodni_rejstrik.search_by_name(
                business_name, max_results=5
            )

            for result in or_results:
                try:
                    details = await self.obchodni_rejstrik.get_company_details(
                        result["ico"]
                    )
                    if details:
                        company_info = self.obchodni_rejstrik.parse_company_data(
                            details
                        )
                        owners = self.obchodni_rejstrik.parse_owners(details)
                        if owners:
                            owner = owners[0]
                            return {
                                "ico": company_info.ico,
                                "company_name": company_info.name,
                                "owner_first_name": owner.name.split()[0]
                                if owner.name.split()
                                else "",
                                "owner_last_name": owner.name.split()[-1]
                                if len(owner.name.split()) > 1
                                else "",
                                "owner_full_name": owner.name,
                                "email": company_info.email,
                                "phone": company_info.phone,
                            }
                except Exception as e:
                    logger.debug(f"Failed to get details for {result.get('ico')}: {e}")
                    continue

        except Exception as e:
            logger.debug(f"Registry search failed for {business_name}: {e}")

        return None

    async def _find_owner_from_website(
        self, website_url: str
    ) -> Optional[Dict[str, str]]:
        """
        Find owner information by scraping the business website.

        Args:
            website_url: URL of the business website

        Returns:
            Dict with owner information or None
        """
        if not website_url or not website_url.startswith(("http://", "https://")):
            return None

        logger.info(f"Searching for owner on website: {website_url}")

        if not self.browser_scraper:
            logger.debug("Browser scraper not available, skipping website scraping")
            return None

        try:
            # Scrape website
            website_data = await self.browser_scraper.scrape_website(website_url)
            if not website_data:
                return None

            # Extract owner name from website data
            owner_name = website_data.get("owner_name")
            if owner_name:
                parsed_name = self._parse_czech_name(owner_name)
                if parsed_name:
                    return parsed_name

            # Try scraping specific pages
            pages_to_check = [
                "/o-nas",
                "/about",
                "/kontakt",
                "/contact",
                "/tym",
                "/team",
                "/majitel",
                "/vlastnik",
            ]

            for page_path in pages_to_check:
                try:
                    page_url = website_url.rstrip("/") + page_path
                    page_data = await self.browser_scraper.scrape_website(page_url)
                    if page_data and page_data.get("owner_name"):
                        parsed_name = self._parse_czech_name(page_data["owner_name"])
                        if parsed_name:
                            logger.info(
                                f"Found owner on {page_path}: {parsed_name['full_name']}"
                            )
                            return parsed_name
                except Exception as e:
                    logger.debug(f"Failed to scrape {page_path}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error finding owner from website {website_url}: {e}")

        return None

    async def find_leads(
        self,
        categories: List[str],
        location: str = "Prague, Czech Republic",
        max_per_category: int = 20,
    ) -> List[PragueBusinessLead]:
        """
        Find business leads by searching Google Maps and enriching with registry data.

        Args:
            categories: List of business categories to search (e.g., ["kadeřnictví", "restaurace"])
            location: Location to search in (default: Prague)
            max_per_category: Maximum results per category

        Returns:
            List of PragueBusinessLead objects
        """
        all_leads = []

        total_categories = len(categories)
        for idx, category in enumerate(categories, 1):
            logger.info(
                f"[{idx}/{total_categories}] Searching for '{category}' in {location}..."
            )
            print(f"[{idx}/{total_categories}] Поиск: {category} в {location}...")

            try:
                # Search Google Maps
                places = await self.google_maps.search_businesses(
                    query=category,
                    location=location,
                    max_results=max_per_category,
                )

                logger.info(f"Found {len(places)} places for '{category}'")
                print(f"  ✓ Найдено мест: {len(places)}")

                # Process each place
                for place_idx, place_data in enumerate(places, 1):
                    try:
                        lead = await self._enrich_lead(place_data, category)
                        if lead:
                            all_leads.append(lead)
                            owner_info = lead.owner_full_name or "не найден"
                            phone_info = "✓" if lead.phone else "✗"
                            email_info = "✓" if lead.email else "✗"
                            ico_info = lead.ico or "N/A"
                            logger.info(
                                f"✓ [{place_idx}/{len(places)}] {lead.business_name} "
                                f"(IČO: {ico_info}, Владелец: {owner_info}, Телефон: {phone_info}, Email: {email_info})"
                            )

                        # Rate limiting
                        await asyncio.sleep(1)

                    except Exception as e:
                        logger.error(f"Error processing place: {e}", exc_info=True)
                        continue

            except Exception as e:
                logger.error(
                    f"Error searching category '{category}': {e}", exc_info=True
                )
                continue

        return all_leads

    async def _enrich_lead(
        self, place_data: dict, category: str
    ) -> Optional[PragueBusinessLead]:
        """
        Enrich Google Maps place data with registry and website information.

        Args:
            place_data: Raw Google Maps place data
            category: Business category

        Returns:
            PragueBusinessLead object or None if enrichment fails
        """
        # Parse Google Maps data
        google_info = self.google_maps.parse_place_data(place_data)

        # Create initial lead
        lead = PragueBusinessLead(
            business_name=google_info.get("business_name", ""),
            address=google_info.get("google_address"),
            phone=google_info.get("google_phone"),
            website=google_info.get("google_website"),
            google_maps_url=google_info.get("google_maps_url"),
            category=category,
        )

        # Parse phone if available
        if lead.phone:
            parsed_phone = self._parse_czech_phone(lead.phone)
            if parsed_phone:
                lead.phone = parsed_phone

        # Try to get place details for more information
        place_id = google_info.get("google_maps_id")
        if place_id:
            try:
                details = await self.google_maps.get_place_details(place_id)
                if details:
                    # Update with details
                    if details.get("formatted_phone_number") and not lead.phone:
                        lead.phone = self._parse_czech_phone(
                            details.get("formatted_phone_number")
                        )
                    if details.get("website") and not lead.website:
                        lead.website = details.get("website")
                    if details.get("formatted_address") and not lead.address:
                        lead.address = details.get("formatted_address")
            except Exception as e:
                logger.debug(f"Failed to get place details: {e}")

        # Try to find company info and owners from Czech registries
        registry_info = await self._find_owner_from_registry(
            lead.business_name, lead.address
        )
        if registry_info:
            lead.ico = registry_info.get("ico")
            lead.owner_first_name = registry_info.get("owner_first_name")
            lead.owner_last_name = registry_info.get("owner_last_name")
            lead.owner_full_name = registry_info.get("owner_full_name")
            if registry_info.get("email") and not lead.email:
                lead.email = registry_info.get("email")
            if registry_info.get("phone") and not lead.phone:
                lead.phone = self._parse_czech_phone(registry_info.get("phone"))

        # If no owner found in registry, try website
        if not lead.owner_full_name and lead.website:
            try:
                owner_info = await self._find_owner_from_website(lead.website)
                if owner_info:
                    lead.owner_first_name = owner_info.get("first_name")
                    lead.owner_last_name = owner_info.get("last_name")
                    lead.owner_full_name = owner_info.get("full_name")
            except Exception as e:
                logger.debug(f"Failed to find owner from website: {e}")

        # Try to extract email from website if not found
        if not lead.email and lead.website and self.browser_scraper:
            try:
                website_data = await self.browser_scraper.scrape_website(lead.website)
                if website_data:
                    if website_data.get("email"):
                        lead.email = website_data["email"]
                    else:
                        # Try contact pages
                        contact_pages = ["/kontakt", "/contact", "/kontaktujte-nas"]
                        for page_path in contact_pages:
                            try:
                                page_url = lead.website.rstrip("/") + page_path
                                page_data = await self.browser_scraper.scrape_website(
                                    page_url
                                )
                                if page_data and page_data.get("email"):
                                    lead.email = page_data["email"]
                                    break
                            except Exception:
                                continue
            except Exception as e:
                logger.debug(f"Failed to extract email from {lead.website}: {e}")

        return lead

    def save_to_excel(
        self,
        leads: List[PragueBusinessLead],
        filename: Optional[str] = None,
    ) -> Path:
        """
        Save leads to Excel file.

        Args:
            leads: List of PragueBusinessLead objects
            filename: Output filename (auto-generated if not provided)

        Returns:
            Path to saved Excel file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if not filename:
            filename = f"prague_businesses_{timestamp}.xlsx"
        filepath = self.output_dir / filename

        # Prepare data for Excel
        excel_data = []
        for lead in leads:
            excel_data.append(
                {
                    "Название бизнеса": lead.business_name,
                    "Телефон": lead.phone or "",
                    "Email": lead.email or "",
                    "Имя владельца": lead.owner_first_name or "",
                    "Фамилия владельца": lead.owner_last_name or "",
                    "Полное имя владельца": lead.owner_full_name or "",
                    "IČO": lead.ico or "",
                    "Адрес": lead.address or "",
                    "Веб-сайт": lead.website or "",
                    "Категория": lead.category or "",
                    "Google Maps URL": lead.google_maps_url or "",
                }
            )

        # Create DataFrame
        df = pd.DataFrame(excel_data)

        # Save to Excel
        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Бизнесы")

            # Auto-adjust column widths
            worksheet = writer.sheets["Бизнесы"]
            from openpyxl.utils import get_column_letter

            for idx, col in enumerate(df.columns, 1):
                max_length = max(
                    df[col].astype(str).map(len).max(),
                    len(str(col)),
                )
                column_letter = get_column_letter(idx)
                worksheet.column_dimensions[column_letter].width = min(
                    max_length + 2, 50
                )

        logger.info(f"Saved {len(leads)} leads to {filepath}")
        return filepath


async def main():
    """Main function for CLI usage."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate Prague business leads and export to Excel"
    )
    parser.add_argument(
        "--categories",
        nargs="+",
        default=[
            "kadeřnictví",
            "kosmetika",
            "restaurace",
            "kavárna",
            "masáž",
            "manikúra",
        ],
        help="Business categories to search (Czech terms)",
    )
    parser.add_argument(
        "--location",
        default="Prague, Czech Republic",
        help="Location to search in (default: Prague)",
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
        "--output-file",
        help="Output Excel filename (auto-generated if not provided)",
    )

    args = parser.parse_args()

    generator = PragueBusinessLeadGenerator(output_dir=args.output_dir)

    try:
        # Find leads
        leads = await generator.find_leads(
            categories=args.categories,
            location=args.location,
            max_per_category=args.max_per_category,
        )

        logger.info(f"Found {len(leads)} total leads")
        print(f"\n{'=' * 60}")
        print("ОБРАБОТКА ЗАВЕРШЕНА")
        print(f"{'=' * 60}")

        # Save to Excel
        excel_file = generator.save_to_excel(leads, filename=args.output_file)
        print(f"\n✓ Результаты сохранены в: {excel_file}")

        # Print summary
        leads_with_phone = sum(1 for lead in leads if lead.phone)
        leads_with_email = sum(1 for lead in leads if lead.email)
        leads_with_owner = sum(1 for lead in leads if lead.owner_full_name)
        leads_with_ico = sum(1 for lead in leads if lead.ico)

        print("\n📊 СТАТИСТИКА:")
        print(f"  Всего найдено бизнесов: {len(leads)}")
        print(
            f"  С телефоном: {leads_with_phone} ({leads_with_phone * 100 // len(leads) if leads else 0}%)"
        )
        print(
            f"  С email: {leads_with_email} ({leads_with_email * 100 // len(leads) if leads else 0}%)"
        )
        print(
            f"  С именем владельца: {leads_with_owner} ({leads_with_owner * 100 // len(leads) if leads else 0}%)"
        )
        print(
            f"  С IČO: {leads_with_ico} ({leads_with_ico * 100 // len(leads) if leads else 0}%)"
        )
        print(f"\n{'=' * 60}")

    finally:
        await generator.close()


if __name__ == "__main__":
    asyncio.run(main())
