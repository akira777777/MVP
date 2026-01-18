"""
Multi-browser scraper that supports multiple browser automation engines.
Provides unified interface for Selenium, Playwright, and requests-html.
"""

import asyncio
import logging
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class BrowserEngine(str, Enum):
    """Supported browser engines."""

    SELENIUM = "selenium"
    PLAYWRIGHT = "playwright"
    REQUESTS_HTML = "requests_html"
    AUTO = "auto"  # Automatically select best available


class MultiBrowserScraper:
    """
    Unified scraper interface supporting multiple browser engines.

    Automatically falls back to available engines if preferred one is not available.
    """

    def __init__(
        self,
        engine: BrowserEngine = BrowserEngine.AUTO,
        headless: bool = True,
        **kwargs,
    ):
        """
        Initialize multi-browser scraper.

        Args:
            engine: Browser engine to use (selenium, playwright, requests_html, auto)
            headless: Run browser in headless mode
            **kwargs: Additional arguments for specific engines
        """
        self.engine_preference = engine
        self.headless = headless
        self.kwargs = kwargs
        self.active_engine: Optional[str] = None
        self.scraper = None

        # Initialize scraper
        self._initialize_scraper()

    def _initialize_scraper(self):
        """Initialize the appropriate scraper based on availability and preference."""
        engines_to_try = []

        if self.engine_preference == BrowserEngine.AUTO:
            # Try engines in order of preference
            engines_to_try = [
                BrowserEngine.PLAYWRIGHT,
                BrowserEngine.SELENIUM,
                BrowserEngine.REQUESTS_HTML,
            ]
        else:
            engines_to_try = [self.engine_preference]

        for engine in engines_to_try:
            try:
                if engine == BrowserEngine.SELENIUM:
                    from scripts.selenium_scraper import SeleniumScraper

                    self.scraper = SeleniumScraper(
                        headless=self.headless, **self.kwargs
                    )
                    self.active_engine = "selenium"
                    logger.info("Initialized Selenium scraper")
                    return

                elif engine == BrowserEngine.PLAYWRIGHT:
                    from scripts.mcp_integration import MCPBrowserClient

                    self.scraper = MCPBrowserClient()
                    self.active_engine = "playwright"
                    logger.info("Initialized Playwright scraper")
                    return

                elif engine == BrowserEngine.REQUESTS_HTML:
                    from requests_html import AsyncHTMLSession

                    self.scraper = AsyncHTMLSession()
                    self.active_engine = "requests_html"
                    logger.info("Initialized requests-html scraper")
                    return

            except ImportError as e:
                logger.debug(f"{engine.value} not available: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error initializing {engine.value}: {e}")
                continue

        raise RuntimeError(
            "No browser automation engine available. "
            "Install at least one: selenium, playwright, or requests-html"
        )

    async def search_google_maps(
        self, business_name: str, location: str = "Prague"
    ) -> Optional[Dict]:
        """
        Search Google Maps for business.

        Args:
            business_name: Name of the business
            location: Location to search in

        Returns:
            Dict with business details or None
        """
        if self.active_engine == "selenium":
            from scripts.selenium_scraper import async_search_google_maps

            return await async_search_google_maps(
                business_name, location, headless=self.headless
            )

        elif self.active_engine == "playwright":
            # Use MCPBrowserClient
            search_url = (
                f"https://www.google.com/maps/search/"
                f"{business_name.replace(' ', '+')}+{location.replace(' ', '+')}"
            )
            content = await self.scraper.get_page_content(search_url)
            if content:
                return await self.scraper.extract_google_maps_data(search_url)
            return None

        elif self.active_engine == "requests_html":
            search_url = (
                f"https://www.google.com/maps/search/"
                f"{business_name.replace(' ', '+')}+{location.replace(' ', '+')}"
            )
            r = await self.scraper.get(search_url)
            await r.html.arender(timeout=20)

            # Extract data from rendered HTML
            return self._extract_from_html(r.html.html, search_url)

        return None

    async def scrape_website(self, website_url: str) -> Optional[Dict]:
        """
        Scrape business website.

        Args:
            website_url: URL of the website

        Returns:
            Dict with extracted data or None
        """
        if self.active_engine == "selenium":
            from scripts.selenium_scraper import async_scrape_website

            return await async_scrape_website(website_url, headless=self.headless)

        elif self.active_engine == "playwright":
            content = await self.scraper.get_page_content(website_url)
            if content:
                from scripts.business_data_extractor import enrich_business_data

                return enrich_business_data({}, content)
            return None

        elif self.active_engine == "requests_html":
            r = await self.scraper.get(website_url)
            await r.html.arender(timeout=20)

            # Extract data from rendered HTML
            return self._extract_from_html(r.html.html, website_url)

        return None

    def _extract_from_html(self, html_content: str, url: str) -> Dict:
        """Extract data from HTML content."""
        from scripts.business_data_extractor import (
            extract_email_from_text,
            extract_owner_info,
            extract_phone_from_text,
            extract_social_links,
        )

        data = {"website": url}

        # Extract email
        email = extract_email_from_text(html_content)
        if email:
            data["email"] = email

        # Extract phone
        phone = extract_phone_from_text(html_content)
        if phone:
            data["phone"] = phone

        # Extract social links
        social_links = extract_social_links(html_content, url)
        data.update(social_links)

        # Extract owner info
        owner_info = extract_owner_info(html_content)
        data.update(owner_info)

        return data

    async def extract_from_maps_url(self, maps_url: str) -> Optional[Dict]:
        """
        Extract business details from Google Maps URL.

        Args:
            maps_url: Google Maps URL

        Returns:
            Dict with business details or None
        """
        if self.active_engine == "selenium":
            if hasattr(self.scraper, "extract_from_maps_url"):
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None, self.scraper.extract_from_maps_url, maps_url
                )

        elif self.active_engine == "playwright":
            return await self.scraper.extract_google_maps_data(maps_url)

        elif self.active_engine == "requests_html":
            r = await self.scraper.get(maps_url)
            await r.html.arender(timeout=20)
            return self._extract_from_html(r.html.html, maps_url)

        return None

    async def batch_scrape_websites(
        self, website_urls: List[str], max_concurrent: int = 5
    ) -> List[Dict]:
        """
        Scrape multiple websites in parallel.

        Args:
            website_urls: List of website URLs
            max_concurrent: Maximum concurrent requests

        Returns:
            List of dictionaries with extracted data
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []

        async def scrape_with_semaphore(url):
            async with semaphore:
                return await self.scrape_website(url)

        tasks = [scrape_with_semaphore(url) for url in website_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and None results
        valid_results = [r for r in results if isinstance(r, dict) and r is not None]

        return valid_results

    def close(self):
        """Close scraper and cleanup resources."""
        if self.scraper:
            if hasattr(self.scraper, "stop"):
                self.scraper.stop()
            elif hasattr(self.scraper, "close"):
                self.scraper.close()
            elif self.active_engine == "requests_html":
                # requests_html session cleanup
                if hasattr(self.scraper, "close"):
                    self.scraper.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.close()


# Example usage
async def main():
    """Example usage of multi-browser scraper."""
    async with MultiBrowserScraper(engine=BrowserEngine.AUTO) as scraper:
        # Search Google Maps
        result = await scraper.search_google_maps("hair salon", "Prague")
        print(f"Found business: {result}")

        # Scrape website
        if result and result.get("website"):
            website_data = await scraper.scrape_website(result["website"])
            print(f"Website data: {website_data}")

        # Batch scrape multiple websites
        websites = [
            "https://example1.com",
            "https://example2.com",
        ]
        batch_results = await scraper.batch_scrape_websites(websites)
        print(f"Scraped {len(batch_results)} websites")


if __name__ == "__main__":
    asyncio.run(main())
