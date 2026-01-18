"""
Browser-based Google Maps scraper using Playwright.
"""

import asyncio
import random
import re
import logging
from typing import List, Optional, Dict, Any
from urllib.parse import quote_plus

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError

from .models import BusinessData
from .config import ScraperConfig
from .utils import normalize_prague_address

logger = logging.getLogger(__name__)


class GoogleMapsScraper:
    """
    Browser-based scraper for Google Maps using Playwright.
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        """
        Initialize Google Maps scraper.

        Args:
            config: Scraper configuration
        """
        self.config = config or ScraperConfig()
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self._request_count = 0
        self._last_request_time = 0.0

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def start(self):
        """Start browser and create page."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.config.headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        self.page = await self.browser.new_page()
        await self.page.set_extra_http_headers({"User-Agent": self.config.user_agent})
        logger.info("Browser started successfully")

    async def close(self):
        """Close browser and cleanup."""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        logger.info("Browser closed")

    async def _rate_limit(self):
        """Apply rate limiting between requests."""
        current_time = asyncio.get_event_loop().time()

        # Check hourly limit
        if self._request_count >= self.config.max_requests_per_hour:
            logger.warning("Hourly request limit reached, waiting...")
            await asyncio.sleep(3600)  # Wait 1 hour
            self._request_count = 0

        # Random delay between requests
        delay = random.uniform(
            self.config.min_delay_seconds, self.config.max_delay_seconds
        )
        time_since_last = current_time - self._last_request_time

        if time_since_last < delay:
            await asyncio.sleep(delay - time_since_last)

        self._request_count += 1
        self._last_request_time = asyncio.get_event_loop().time()

    async def search_businesses(
        self, query: str, location: str = "Praha, Czechia", max_results: int = 20
    ) -> List[BusinessData]:
        """
        Search for businesses on Google Maps.

        Args:
            query: Search query (e.g., "kavárna")
            location: Location string (e.g., "Praha 1")
            max_results: Maximum number of results to return

        Returns:
            List of BusinessData objects
        """
        if not self.page:
            await self.start()

        await self._rate_limit()

        # Construct Google Maps search URL
        search_query = f"{query} {location}"
        encoded_query = quote_plus(search_query)
        url = f"https://www.google.com/maps/search/{encoded_query}"

        logger.info(f"Searching Google Maps: {search_query}")

        try:
            await self.page.goto(url, timeout=self.config.page_load_timeout * 1000)
            await self.page.wait_for_load_state("networkidle")

            # Wait for results to load
            await asyncio.sleep(2)

            businesses = []
            results_loaded = 0

            # Scroll to load more results
            while results_loaded < max_results:
                # Extract visible results
                new_businesses = await self._extract_visible_results(query)
                businesses.extend(new_businesses)

                # Remove duplicates
                unique_businesses = list({b: None for b in businesses}.keys())
                businesses = unique_businesses

                results_loaded = len(businesses)

                if results_loaded >= max_results:
                    break

                # Scroll down to load more
                await self._scroll_to_load_more()

                # Wait for new results
                await asyncio.sleep(1)

            logger.info(f"Found {len(businesses)} businesses for query: {search_query}")
            return businesses[:max_results]

        except PlaywrightTimeoutError:
            logger.error(f"Timeout while searching: {search_query}")
            return []
        except Exception as e:
            logger.error(f"Error searching businesses: {e}", exc_info=True)
            return []

    async def _extract_visible_results(self, category: str) -> List[BusinessData]:
        """
        Extract business data from visible results on the page.

        Args:
            category: Business category for tagging

        Returns:
            List of BusinessData objects
        """
        businesses = []

        try:
            # Google Maps results are in divs with specific classes
            # This selector may need adjustment based on Google Maps structure
            result_selectors = [
                'div[role="article"]',
                'div[data-value="Directions"]',
                'a[href*="/maps/place/"]',
            ]

            for selector in result_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        logger.debug(f"Found {len(elements)} elements with selector: {selector}")
                        break
                except Exception:
                    continue

            if not elements:
                logger.warning("No result elements found on page")
                return businesses

            for element in elements[:20]:  # Limit to first 20 visible
                try:
                    business = await self._extract_business_data(element, category)
                    if business:
                        businesses.append(business)
                except Exception as e:
                    logger.debug(f"Error extracting business data: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error extracting visible results: {e}", exc_info=True)

        return businesses

    async def _extract_business_data(
        self, element, category: str
    ) -> Optional[BusinessData]:
        """
        Extract business data from a single result element.

        Args:
            element: Playwright element handle
            category: Business category

        Returns:
            BusinessData object or None
        """
        try:
            # Extract name
            name_element = await element.query_selector('div[role="button"] span')
            name = ""
            if name_element:
                name = await name_element.inner_text()
                name = name.strip()

            if not name:
                return None

            # Extract address
            address = ""
            address_selectors = [
                'span[aria-label*="Address"]',
                'div[data-value="Address"]',
            ]
            for selector in address_selectors:
                addr_element = await element.query_selector(selector)
                if addr_element:
                    address = await addr_element.inner_text()
                    address = normalize_prague_address(address.strip())
                    break

            # Extract rating
            rating = None
            rating_element = await element.query_selector('span[aria-label*="stars"]')
            if rating_element:
                rating_text = await rating_element.get_attribute("aria-label")
                if rating_text:
                    # Extract number from "4.5 stars" format
                    match = re.search(r"(\d+\.?\d*)", rating_text)
                    if match:
                        rating = float(match.group(1))

            # Extract review count
            review_count = None
            review_element = await element.query_selector('span[aria-label*="reviews"]')
            if review_element:
                review_text = await review_element.inner_text()
                if review_text:
                    match = re.search(r"(\d+)", review_text.replace(",", ""))
                    if match:
                        review_count = int(match.group(1))

            # Try to get place URL for more details
            place_url = None
            link_element = await element.query_selector('a[href*="/maps/place/"]')
            if link_element:
                place_url = await link_element.get_attribute("href")

            # Extract district from address
            district = None
            for i in range(1, 11):
                if f"Praha {i}" in address or f"Prague {i}" in address:
                    district = f"Prague {i}"
                    break
            
            from decimal import Decimal
            
            # Create business data
            business = BusinessData(
                name=name,
                address=address or "Unknown",
                city="Prague",
                district=district,
                category=category,
                rating=Decimal(str(rating)) if rating else None,
                review_count=review_count,
            )

            # If we have a place URL, try to get more details
            if place_url:
                details = await self._get_business_details(place_url)
                if details:
                    business.phone = details.get("phone")
                    business.website = details.get("website")
                    place_id = details.get("place_id")
                    business.place_id = place_id  # Keep for backward compatibility
                    business.google_place_id = place_id
                    business.latitude = Decimal(str(details.get("latitude"))) if details.get("latitude") else None
                    business.longitude = Decimal(str(details.get("longitude"))) if details.get("longitude") else None

            return business

        except Exception as e:
            logger.debug(f"Error extracting business data from element: {e}")
            return None

    async def _scroll_to_load_more(self):
        """Scroll the page to load more results."""
        try:
            # Scroll the results panel
            await self.page.evaluate(
                """
                const resultsPanel = document.querySelector('div[role="main"]');
                if (resultsPanel) {
                    resultsPanel.scrollTop += 500;
                }
                """
            )
            await asyncio.sleep(1)
        except Exception as e:
            logger.debug(f"Error scrolling: {e}")

    async def _get_business_details(self, place_url: str) -> Optional[Dict[str, Any]]:
        """
        Navigate to business details page and extract additional information.

        Args:
            place_url: URL to business details page

        Returns:
            Dictionary with additional business details
        """
        try:
            await self._rate_limit()

            # Open details in new tab or navigate
            await self.page.goto(place_url, timeout=self.config.page_load_timeout * 1000)
            await self.page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)

            details = {}

            # Extract phone
            phone_selectors = [
                'button[data-item-id="phone"]',
                'span[aria-label*="phone"]',
                'a[href^="tel:"]',
            ]
            for selector in phone_selectors:
                phone_element = await self.page.query_selector(selector)
                if phone_element:
                    phone_text = await phone_element.inner_text()
                    if phone_text:
                        details["phone"] = phone_text.strip()
                        break

            # Extract website
            website_element = await self.page.query_selector('a[data-item-id="authority"]')
            if website_element:
                website = await website_element.get_attribute("href")
                if website:
                    details["website"] = website

            # Extract place_id from URL
            if "/place/" in place_url:
                parts = place_url.split("/place/")
                if len(parts) > 1:
                    place_id = parts[1].split("/")[0]
                    details["place_id"] = place_id

            return details if details else None

        except Exception as e:
            logger.debug(f"Error getting business details: {e}")
            return None
