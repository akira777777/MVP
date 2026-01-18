"""
Script for finding small businesses in France and exporting to Excel.
Searches Google Maps for French businesses and extracts owner information from websites.
"""

import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import pandas as pd
from pydantic import BaseModel, Field
from scripts.browser_scraper import BrowserScraper
from utils.lead_generation.google_maps import GoogleMapsClient

from utils.logging_config import setup_logging

logger = setup_logging(
    name=__name__, log_level="INFO", log_file="french_leads.log", log_dir="logs"
)


class FrenchBusinessLead(BaseModel):
    """French business lead information."""

    business_name: str = Field(..., description="Business name")
    address: Optional[str] = Field(None, description="Business address")
    phone: Optional[str] = Field(None, description="Phone number")
    email: Optional[str] = Field(None, description="Email address")
    website: Optional[str] = Field(None, description="Website URL")
    owner_first_name: Optional[str] = Field(None, description="Owner first name")
    owner_last_name: Optional[str] = Field(None, description="Owner last name")
    owner_full_name: Optional[str] = Field(None, description="Owner full name")
    google_maps_url: Optional[str] = Field(None, description="Google Maps URL")
    category: Optional[str] = Field(None, description="Business category")


class FrenchGoogleMapsClient(GoogleMapsClient):
    """Google Maps client configured for French language."""

    async def search_businesses(
        self,
        query: str,
        location: str = "France",
        max_results: int = 20,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Search for businesses using Google Maps Places API with French language.

        Overrides parent method to use French language instead of Czech.
        """
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        # Use parent's cache logic
        cache_key = self._get_cache_key(query, location)
        if use_cache:
            cached_results = self._get_from_cache(cache_key)
            if cached_results is not None:
                return cached_results[:max_results]

        self._cleanup_expired_cache()

        # Build search query
        search_query = f"{query} in {location}"

        results = []
        next_page_token = None
        delay = 1.0  # RETRY_DELAY

        # Import constants from parent
        from utils.lead_generation.google_maps import (
            _MAX_RETRIES,
            _PLACES_SEARCH_URL,
            _RETRY_BACKOFF,
        )

        while len(results) < max_results:
            try:
                params = {
                    "query": search_query,
                    "key": self.api_key,
                    "language": "fr",  # French language
                }

                if next_page_token:
                    params["pagetoken"] = next_page_token

                for attempt in range(_MAX_RETRIES):
                    try:
                        response = await self.client.get(
                            _PLACES_SEARCH_URL, params=params
                        )
                        response.raise_for_status()

                        data = response.json()

                        if data.get("status") == "OK":
                            places = data.get("results", [])
                            results.extend(places)

                            next_page_token = data.get("next_page_token")
                            if not next_page_token or len(results) >= max_results:
                                break

                            await asyncio.sleep(2)

                        elif data.get("status") == "ZERO_RESULTS":
                            logger.info(f"No results found for query: {search_query}")
                            break

                        elif data.get("status") == "OVER_QUERY_LIMIT":
                            logger.warning(
                                "Google Maps API quota exceeded, trying browser fallback"
                            )
                            if self.browser_scraper:
                                try:
                                    browser_results = (
                                        await self._search_with_browser_fallback(
                                            query, location, max_results
                                        )
                                    )
                                    if browser_results:
                                        self._set_cache(cache_key, browser_results)
                                        return browser_results[:max_results]
                                except Exception as e:
                                    logger.error(f"Browser fallback failed: {e}")

                            raise RuntimeError(
                                "Google Maps API quota exceeded and browser fallback unavailable"
                            )

                        else:
                            error_msg = data.get("error_message", "Unknown error")
                            logger.warning(
                                f"Google Maps API error: {data.get('status')} - {error_msg}"
                            )
                            if attempt < _MAX_RETRIES - 1:
                                await asyncio.sleep(delay)
                                delay *= _RETRY_BACKOFF
                                continue
                            break

                    except httpx.HTTPStatusError as e:
                        if attempt < _MAX_RETRIES - 1:
                            logger.warning(
                                f"HTTP error (attempt {attempt + 1}/{_MAX_RETRIES}): {e}. Retrying..."
                            )
                            await asyncio.sleep(delay)
                            delay *= _RETRY_BACKOFF
                        else:
                            raise RuntimeError(
                                f"HTTP error calling Google Maps API: {e}"
                            ) from e

                    except httpx.RequestError as e:
                        if attempt < _MAX_RETRIES - 1:
                            logger.warning(
                                f"Request error (attempt {attempt + 1}/{_MAX_RETRIES}): {e}. Retrying..."
                            )
                            await asyncio.sleep(delay)
                            delay *= _RETRY_BACKOFF
                        else:
                            raise RuntimeError(
                                f"Request error calling Google Maps API: {e}"
                            ) from e

                if not next_page_token:
                    break

            except RuntimeError as e:
                if "quota exceeded" in str(e).lower():
                    raise
                logger.error(f"Error searching businesses: {e}", exc_info=True)
                raise RuntimeError(f"Failed to search businesses: {e}") from e
            except Exception as e:
                logger.error(f"Error searching businesses: {e}", exc_info=True)
                if self.browser_scraper:
                    try:
                        logger.info("Attempting browser fallback due to API error")
                        browser_results = await self._search_with_browser_fallback(
                            query, location, max_results
                        )
                        if browser_results:
                            self._set_cache(cache_key, browser_results)
                            return browser_results[:max_results]
                    except Exception as fallback_error:
                        logger.error(f"Browser fallback also failed: {fallback_error}")

                raise RuntimeError(f"Failed to search businesses: {e}") from e

        if results:
            self._set_cache(cache_key, results)

        return results[:max_results]

    async def _search_with_browser_fallback(
        self,
        query: str,
        location: str,
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """Fallback to browser scraping when API is unavailable."""
        if not self.browser_scraper:
            return []

        logger.info(f"Using browser fallback for query: {query} in {location}")

        try:
            browser_result = await self.browser_scraper.search_google_maps(
                query, location
            )

            if not browser_result:
                return []

            result_dict = {
                "place_id": None,
                "name": browser_result.get("business_name") or query,
                "formatted_address": browser_result.get("address"),
                "formatted_phone_number": browser_result.get("phone"),
                "website": browser_result.get("website"),
                "rating": browser_result.get("rating"),
                "user_ratings_total": browser_result.get("reviews_count"),
                "url": browser_result.get("google_maps_url"),
                "types": [],
            }

            return [result_dict]

        except Exception as e:
            logger.error(f"Browser fallback error: {e}", exc_info=True)
            return []


class FrenchBusinessLeadGenerator:
    """Generator for French business leads."""

    def __init__(
        self,
        google_maps_api_key: Optional[str] = None,
        output_dir: str = "leads",
        use_browser_fallback: bool = True,
    ):
        """
        Initialize French business lead generator.

        Args:
            google_maps_api_key: Google Maps API key (optional, uses env var if not provided)
            output_dir: Directory to save results
            use_browser_fallback: Whether to enable browser scraper fallback
        """
        # Initialize browser scraper for website scraping
        self.browser_scraper = None
        if use_browser_fallback:
            try:
                self.browser_scraper = BrowserScraper(use_mcp_puppeteer=True)
                logger.info("Browser scraper initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize browser scraper: {e}")

        # Initialize Google Maps client (French version)
        self.google_maps = FrenchGoogleMapsClient(
            api_key=google_maps_api_key,
            browser_scraper=self.browser_scraper,
        )
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    async def close(self):
        """Close all clients."""
        await self.google_maps.close()
        if self.browser_scraper:
            await self.browser_scraper.close()

    def _parse_french_phone(self, text: str) -> Optional[str]:
        """Extract French phone number from text."""
        # French phone patterns
        patterns = [
            r"\+33\s?[1-9](?:[.\s-]?\d{2}){4}",  # +33 X XX XX XX XX
            r"0[1-9](?:[.\s-]?\d{2}){4}",  # 0X XX XX XX XX
            r"\+33\s?\d{9}",  # +33 followed by 9 digits
            r"0\d{9}",  # 0 followed by 9 digits
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                phone = match.group(0)
                # Normalize: remove spaces, dots, dashes
                phone = re.sub(r"[\s.\-]", "", phone)
                # Ensure +33 format
                if phone.startswith("0"):
                    phone = "+33" + phone[1:]
                elif not phone.startswith("+33"):
                    if phone.startswith("33"):
                        phone = "+" + phone
                    else:
                        phone = "+33" + phone
                return phone

        return None

    def _parse_email(self, text: str) -> Optional[str]:
        """Extract email from text."""
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        match = re.search(email_pattern, text)
        if match:
            return match.group(0).lower()
        return None

    def _parse_french_name(self, text: str) -> Optional[Dict[str, str]]:
        """
        Extract French name from text.
        Returns dict with 'first_name', 'last_name', 'full_name'.
        """
        # Common French name patterns
        # Look for "Propriétaire:", "Gérant:", "Directeur:", "Fondateur:", etc.
        owner_patterns = [
            r"(?:Propriétaire|Gérant|Directeur|Fondateur|Dirigeant|Owner|Manager|Director)[:\s]+([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]+(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]+)+)",
            r"([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]+(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]+)+)\s+(?:est|est le|est la|est un|est une)\s+(?:propriétaire|gérant|directeur|fondateur)",
        ]

        for pattern in owner_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                full_name = match.group(1).strip()
                # Split into first and last name
                name_parts = full_name.split()
                if len(name_parts) >= 2:
                    # Usually first name(s) then last name
                    # In France, last name often comes last
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

        try:
            # Scrape website
            website_data = await self.browser_scraper.scrape_website(website_url)
            if not website_data:
                return None

            # Extract owner name from website data
            owner_name = website_data.get("owner_name")
            if owner_name:
                parsed_name = self._parse_french_name(owner_name)
                if parsed_name:
                    return parsed_name

            # Try scraping specific pages
            pages_to_check = [
                "/a-propos",
                "/about",
                "/contact",
                "/equipe",
                "/team",
                "/qui-sommes-nous",
                "/proprietaire",
                "/gerant",
                "/notre-equipe",
                "/presentation",
                "/histoire",
                "/qui-sommes-nous",
            ]

            for page_path in pages_to_check:
                try:
                    page_url = website_url.rstrip("/") + page_path
                    page_data = await self.browser_scraper.scrape_website(page_url)
                    if page_data and page_data.get("owner_name"):
                        parsed_name = self._parse_french_name(page_data["owner_name"])
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
        location: str = "France",
        max_per_category: int = 20,
    ) -> List[FrenchBusinessLead]:
        """
        Find business leads by searching Google Maps.

        Args:
            categories: List of business categories to search (e.g., ["salon de beauté", "restaurant"])
            location: Location to search in (default: France)
            max_per_category: Maximum results per category

        Returns:
            List of FrenchBusinessLead objects
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
                            logger.info(
                                f"✓ [{place_idx}/{len(places)}] {lead.business_name} "
                                f"(Владелец: {owner_info}, Телефон: {phone_info}, Email: {email_info})"
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
    ) -> Optional[FrenchBusinessLead]:
        """
        Enrich Google Maps place data with website information.

        Args:
            place_data: Raw Google Maps place data
            category: Business category

        Returns:
            FrenchBusinessLead object or None if enrichment fails
        """
        # Parse Google Maps data
        google_info = self.google_maps.parse_place_data(place_data)

        # Create initial lead
        lead = FrenchBusinessLead(
            business_name=google_info.get("business_name", ""),
            address=google_info.get("google_address"),
            phone=google_info.get("google_phone"),
            website=google_info.get("google_website"),
            google_maps_url=google_info.get("google_maps_url"),
            category=category,
        )

        # Parse phone if available
        if lead.phone:
            parsed_phone = self._parse_french_phone(lead.phone)
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
                        lead.phone = self._parse_french_phone(
                            details.get("formatted_phone_number")
                        )
                    if details.get("website") and not lead.website:
                        lead.website = details.get("website")
                    if details.get("formatted_address") and not lead.address:
                        lead.address = details.get("formatted_address")
            except Exception as e:
                logger.debug(f"Failed to get place details: {e}")

        # Find owner information from website
        if lead.website:
            try:
                owner_info = await self._find_owner_from_website(lead.website)
                if owner_info:
                    lead.owner_first_name = owner_info.get("first_name")
                    lead.owner_last_name = owner_info.get("last_name")
                    lead.owner_full_name = owner_info.get("full_name")

                # Also try to extract email from website
                if not lead.email:
                    try:
                        website_data = await self.browser_scraper.scrape_website(
                            lead.website
                        )
                        if website_data:
                            # Extract email from website data
                            if website_data.get("email"):
                                lead.email = website_data["email"]
                            else:
                                # Try to extract email from contact pages
                                contact_pages = [
                                    "/contact",
                                    "/nous-contacter",
                                    "/contactez-nous",
                                ]
                                for page_path in contact_pages:
                                    try:
                                        page_url = lead.website.rstrip("/") + page_path
                                        page_data = (
                                            await self.browser_scraper.scrape_website(
                                                page_url
                                            )
                                        )
                                        if page_data and page_data.get("email"):
                                            lead.email = page_data["email"]
                                            break
                                    except Exception:
                                        continue
                    except Exception as e:
                        logger.debug(
                            f"Failed to extract email from {lead.website}: {e}"
                        )

            except Exception as e:
                logger.debug(f"Failed to find owner from website: {e}")

        return lead

    def save_to_excel(
        self,
        leads: List[FrenchBusinessLead],
        filename: Optional[str] = None,
    ) -> Path:
        """
        Save leads to Excel file.

        Args:
            leads: List of FrenchBusinessLead objects
            filename: Output filename (auto-generated if not provided)

        Returns:
            Path to saved Excel file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if not filename:
            filename = f"french_businesses_{timestamp}.xlsx"
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
        description="Generate French business leads and export to Excel"
    )
    parser.add_argument(
        "--categories",
        nargs="+",
        default=[
            "salon de beauté",
            "restaurant",
            "coiffeur",
            "boulangerie",
            "pharmacie",
            "café",
            "épicerie",
            "librairie",
        ],
        help="Business categories to search (French terms)",
    )
    parser.add_argument(
        "--location",
        default="France",
        help="Location to search in (default: France)",
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

    generator = FrenchBusinessLeadGenerator(output_dir=args.output_dir)

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
        print(f"\n{'=' * 60}")

    finally:
        await generator.close()


if __name__ == "__main__":
    asyncio.run(main())
