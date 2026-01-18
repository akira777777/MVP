"""Browser automation for scraping Google Maps and business details."""

import asyncio
import logging
import re
from typing import Dict, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)


class BrowserScraper:
    """
    Browser scraper for Google Maps and business websites.

    Uses multiple browser engines with fallback:
    1. MCP Puppeteer (if available in Cursor environment)
    2. Selenium with undetected-chromedriver (anti-detection)
    3. Playwright (fallback)
    4. Multi-browser scraper (unified interface)
    """

    def __init__(
        self,
        use_mcp_puppeteer: bool = True,
        prefer_selenium: bool = False,
        use_multi_browser: bool = True,
    ):
        """
        Initialize browser scraper.

        Args:
            use_mcp_puppeteer: Whether to use MCP Puppeteer tools (default: True)
            prefer_selenium: Prefer Selenium over Playwright (default: False)
            use_multi_browser: Use multi-browser scraper for unified interface (default: True)
        """
        self.use_mcp_puppeteer = use_mcp_puppeteer
        self.prefer_selenium = prefer_selenium
        self.use_multi_browser = use_multi_browser
        self.use_browser = True  # Enable browser automation
        self._playwright_available = None  # Lazy check for Playwright
        self._selenium_available = None  # Lazy check for Selenium
        self._multi_browser_scraper = None  # Lazy initialization

    async def search_google_maps(
        self, business_name: str, location: str = "Prague"
    ) -> Optional[Dict]:
        """
        Search Google Maps for business and extract details.

        Uses MCP Puppeteer if available, falls back to Playwright or direct URL construction.

        Args:
            business_name: Name of the business to search
            location: Location to search in (default: Prague)

        Returns:
            Dict with: address, phone, website, google_maps_url, rating, reviews_count
        """
        search_query = f"{business_name} {location}"
        logger.info(f"Searching Google Maps for: {search_query}")

        # Construct Google Maps search URL
        maps_url = f"https://www.google.com/maps/search/{quote(search_query)}"

        # Try multi-browser scraper first if enabled
        if self.use_multi_browser:
            try:
                result = await self._search_with_multi_browser(business_name, location)
                if result:
                    return result
            except Exception as e:
                logger.debug(f"Multi-browser scraper failed: {e}, trying other methods")

        # Try MCP Puppeteer if enabled
        if self.use_mcp_puppeteer:
            try:
                result = await self._search_with_mcp_puppeteer(maps_url, business_name)
                if result:
                    return result
            except Exception as e:
                logger.debug(f"MCP Puppeteer search failed: {e}, trying fallbacks")

        # Try Selenium if preferred
        if self.prefer_selenium and await self._check_selenium_available():
            try:
                result = await self._search_with_selenium(business_name, location)
                if result:
                    return result
            except Exception as e:
                logger.debug(f"Selenium search failed: {e}, trying Playwright")

        # Fallback to Playwright
        if await self._check_playwright_available():
            try:
                result = await self._search_with_playwright(maps_url, business_name)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Playwright search failed: {e}")

        # Final fallback: return basic URL
        logger.info(
            f"Browser automation not available, returning basic URL for: {business_name}"
        )
        return {
            "google_maps_url": maps_url,
            "business_name": business_name,
        }

    async def extract_business_details(self, maps_url: str) -> Optional[Dict]:
        """
        Extract business details from Google Maps URL.

        Args:
            maps_url: Google Maps URL for the business

        Returns:
            Dict with business details: address, phone, website, rating, reviews_count
        """
        logger.info(f"Extracting details from: {maps_url}")

        # Try multi-browser scraper first if enabled
        if self.use_multi_browser:
            try:
                result = await self._extract_with_multi_browser(maps_url)
                if result:
                    return result
            except Exception as e:
                logger.debug(
                    f"Multi-browser extraction failed: {e}, trying other methods"
                )

        # Try MCP Puppeteer if enabled
        if self.use_mcp_puppeteer:
            try:
                result = await self._extract_with_mcp_puppeteer(maps_url)
                if result:
                    return result
            except Exception as e:
                logger.debug(f"MCP Puppeteer extraction failed: {e}, trying fallbacks")

        # Try Selenium if preferred
        if self.prefer_selenium and await self._check_selenium_available():
            try:
                result = await self._extract_with_selenium(maps_url)
                if result:
                    return result
            except Exception as e:
                logger.debug(f"Selenium extraction failed: {e}, trying Playwright")

        # Fallback to Playwright
        if await self._check_playwright_available():
            try:
                result = await self._extract_with_playwright(maps_url)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Playwright extraction failed: {e}")

        return None

    async def scrape_website(self, website_url: str) -> Optional[Dict]:
        """
        Scrape business website for contact information.

        Looks for: email, phone, social media links, owner info

        Args:
            website_url: URL of the business website

        Returns:
            Dict with: email, phone, social_facebook, social_instagram, owner_name
        """
        logger.info(f"Scraping website: {website_url}")

        if not website_url or not website_url.startswith(("http://", "https://")):
            logger.warning(f"Invalid website URL: {website_url}")
            return None

        # Try multi-browser scraper first if enabled
        if self.use_multi_browser:
            try:
                result = await self._scrape_website_with_multi_browser(website_url)
                if result:
                    return result
            except Exception as e:
                logger.debug(
                    f"Multi-browser website scraping failed: {e}, trying other methods"
                )

        # Try MCP Puppeteer if enabled
        if self.use_mcp_puppeteer:
            try:
                result = await self._scrape_website_with_mcp_puppeteer(website_url)
                if result:
                    return result
            except Exception as e:
                logger.debug(
                    f"MCP Puppeteer website scraping failed: {e}, trying fallbacks"
                )

        # Try Selenium if preferred
        if self.prefer_selenium and await self._check_selenium_available():
            try:
                result = await self._scrape_website_with_selenium(website_url)
                if result:
                    return result
            except Exception as e:
                logger.debug(
                    f"Selenium website scraping failed: {e}, trying Playwright"
                )

        # Fallback to Playwright
        if await self._check_playwright_available():
            try:
                result = await self._scrape_website_with_playwright(website_url)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Playwright website scraping failed: {e}")

        return None

    def parse_phone_from_text(self, text: str) -> Optional[str]:
        """Extract phone number from text."""
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

    def parse_email_from_text(self, text: str) -> Optional[str]:
        """Extract email from text."""
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        match = re.search(email_pattern, text)
        if match:
            return match.group(0)
        return None

    def extract_social_links(self, html_content: str) -> Dict[str, Optional[str]]:
        """Extract social media links from HTML."""
        social_links = {
            "facebook": None,
            "instagram": None,
            "twitter": None,
        }

        # Facebook patterns
        fb_patterns = [
            r'https?://(?:www\.)?facebook\.com/[^\s"\'<>]+',
            r'https?://(?:www\.)?fb\.com/[^\s"\'<>]+',
        ]
        for pattern in fb_patterns:
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                social_links["facebook"] = match.group(0)
                break

        # Instagram patterns
        ig_patterns = [
            r'https?://(?:www\.)?instagram\.com/[^\s"\'<>]+',
            r'https?://(?:www\.)?instagr\.am/[^\s"\'<>]+',
        ]
        for pattern in ig_patterns:
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                social_links["instagram"] = match.group(0)
                break

        return social_links

    # ========== Multi-Browser Scraper Methods ==========

    async def _get_multi_browser_scraper(self):
        """Get or create multi-browser scraper instance."""
        if self._multi_browser_scraper is None:
            try:
                from scripts.multi_browser_scraper import (
                    BrowserEngine,
                    MultiBrowserScraper,
                )

                engine = (
                    BrowserEngine.SELENIUM
                    if self.prefer_selenium
                    else BrowserEngine.AUTO
                )
                self._multi_browser_scraper = MultiBrowserScraper(
                    engine=engine,
                    headless=True,
                )
            except Exception as e:
                logger.debug(f"Multi-browser scraper not available: {e}")
                return None
        return self._multi_browser_scraper

    async def _search_with_multi_browser(
        self, business_name: str, location: str
    ) -> Optional[Dict]:
        """Search Google Maps using multi-browser scraper."""
        scraper = await self._get_multi_browser_scraper()
        if scraper:
            return await scraper.search_google_maps(business_name, location)
        return None

    async def _extract_with_multi_browser(self, maps_url: str) -> Optional[Dict]:
        """Extract business details using multi-browser scraper."""
        scraper = await self._get_multi_browser_scraper()
        if scraper:
            return await scraper.extract_from_maps_url(maps_url)
        return None

    async def _scrape_website_with_multi_browser(
        self, website_url: str
    ) -> Optional[Dict]:
        """Scrape website using multi-browser scraper."""
        scraper = await self._get_multi_browser_scraper()
        if scraper:
            return await scraper.scrape_website(website_url)
        return None

    # ========== Selenium Methods ==========

    async def _check_selenium_available(self) -> bool:
        """Check if Selenium is available."""
        if self._selenium_available is None:
            try:
                from scripts.selenium_scraper import SeleniumScraper

                self._selenium_available = True
            except ImportError:
                self._selenium_available = False
                logger.debug("Selenium not available")
        return self._selenium_available

    async def _search_with_selenium(
        self, business_name: str, location: str
    ) -> Optional[Dict]:
        """Search Google Maps using Selenium."""
        try:
            from scripts.selenium_scraper import async_search_google_maps

            return await async_search_google_maps(
                business_name, location, headless=True
            )
        except Exception as e:
            logger.error(f"Selenium search error: {e}")
            return None

    async def _extract_with_selenium(self, maps_url: str) -> Optional[Dict]:
        """Extract business details using Selenium."""
        try:
            from scripts.selenium_scraper import SeleniumScraper

            loop = asyncio.get_event_loop()

            def _extract():
                with SeleniumScraper(headless=True) as scraper:
                    return scraper.extract_from_maps_url(maps_url)

            return await loop.run_in_executor(None, _extract)
        except Exception as e:
            logger.error(f"Selenium extraction error: {e}")
            return None

    async def _scrape_website_with_selenium(self, website_url: str) -> Optional[Dict]:
        """Scrape website using Selenium."""
        try:
            from scripts.selenium_scraper import async_scrape_website

            return await async_scrape_website(website_url, headless=True)
        except Exception as e:
            logger.error(f"Selenium website scraping error: {e}")
            return None

    # ========== MCP Puppeteer Methods ==========

    async def _search_with_mcp_puppeteer(
        self, maps_url: str, business_name: str
    ) -> Optional[Dict]:
        """
        Search Google Maps using MCP Puppeteer tools.

        Note: In Cursor environment, MCP tools are called through the AI assistant.
        This method provides the structure for MCP tool calls.
        """
        # MCP Puppeteer tools would be called like:
        # mcp_puppeteer_puppeteer_navigate(url=maps_url)
        # content = mcp_puppeteer_puppeteer_evaluate(function="() => document.body.innerText")
        #
        # For now, this is a placeholder that indicates the structure
        logger.debug(f"Would use MCP Puppeteer to search: {maps_url}")

        # In actual implementation, this would call MCP tools through Cursor's interface
        # The actual extraction logic would be in _extract_with_mcp_puppeteer
        return None

    async def _extract_with_mcp_puppeteer(self, maps_url: str) -> Optional[Dict]:
        """
        Extract business details from Google Maps using MCP Puppeteer.

        This method would use MCP Puppeteer tools to:
        1. Navigate to maps_url
        2. Wait for page load
        3. Extract business information using JavaScript evaluation
        """
        logger.debug(f"Would use MCP Puppeteer to extract from: {maps_url}")

        # Example MCP tool calls (would be made through Cursor's MCP interface):
        # 1. Navigate: mcp_puppeteer_puppeteer_navigate(url=maps_url)
        # 2. Wait: mcp_puppeteer_puppeteer_evaluate(function="() => new Promise(resolve => setTimeout(resolve, 2000))")
        # 3. Extract: content = mcp_puppeteer_puppeteer_evaluate(function="() => document.body.innerText")

        # For now, return None to trigger fallback
        return None

    async def _scrape_website_with_mcp_puppeteer(
        self, website_url: str
    ) -> Optional[Dict]:
        """
        Scrape website using MCP Puppeteer.

        Extracts: email, phone, social media links, owner info
        """
        logger.debug(f"Would use MCP Puppeteer to scrape: {website_url}")

        # Example MCP tool calls:
        # 1. Navigate: mcp_puppeteer_puppeteer_navigate(url=website_url)
        # 2. Extract HTML: html = mcp_puppeteer_puppeteer_evaluate(function="() => document.documentElement.outerHTML")
        # 3. Parse and extract data

        return None

    # ========== Playwright Fallback Methods ==========

    async def _check_playwright_available(self) -> bool:
        """Check if Playwright is available as fallback."""
        if self._playwright_available is None:
            try:
                from playwright.async_api import async_playwright

                self._playwright_available = True
            except ImportError:
                self._playwright_available = False
                logger.debug("Playwright not available")
        return self._playwright_available

    async def _search_with_playwright(
        self, maps_url: str, business_name: str
    ) -> Optional[Dict]:
        """Search Google Maps using Playwright as fallback."""
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                # Navigate to Google Maps search
                await page.goto(maps_url, wait_until="networkidle", timeout=30000)

                # Wait a bit for dynamic content
                await page.wait_for_timeout(2000)

                # Extract business information
                result = await self._extract_maps_data_playwright(page)

                await browser.close()
                return result
        except Exception as e:
            logger.error(f"Playwright search error: {e}")
            return None

    async def _extract_with_playwright(self, maps_url: str) -> Optional[Dict]:
        """Extract business details from Google Maps using Playwright."""
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                await page.goto(maps_url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(2000)

                result = await self._extract_maps_data_playwright(page)

                await browser.close()
                return result
        except Exception as e:
            logger.error(f"Playwright extraction error: {e}")
            return None

    async def _extract_maps_data_playwright(self, page) -> Optional[Dict]:
        """Extract business data from Google Maps page using Playwright."""
        try:
            # Extract text content
            content = await page.evaluate("() => document.body.innerText")
            html_content = await page.content()

            # Extract business name from title
            title = await page.title()
            business_name = title.replace(" - Google Maps", "").strip()

            # Extract address
            address = None
            address_patterns = [
                r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*Praha\s*\d+",
                r"Praha\s*\d+[^,\n]*",
            ]
            for pattern in address_patterns:
                match = re.search(pattern, content)
                if match:
                    address = match.group(0).strip()
                    break

            # Extract phone
            phone = self.parse_phone_from_text(content)

            # Extract website from links
            website = None
            links = await page.evaluate("""
                () => Array.from(document.querySelectorAll('a[href^="http"]'))
                    .map(a => a.href)
                    .find(href => !href.includes('google.com') && !href.includes('maps'))
            """)
            if links:
                website = links

            # Extract rating
            rating = None
            rating_match = re.search(
                r"(\d+\.?\d*)\s*(?:stars?|⭐|z|hvěz)", content, re.IGNORECASE
            )
            if rating_match:
                try:
                    rating = float(rating_match.group(1))
                except ValueError:
                    pass

            # Extract reviews count
            reviews_count = None
            reviews_match = re.search(
                r"(\d+)\s*(?:reviews?|recenz|hodnocen)", content, re.IGNORECASE
            )
            if reviews_match:
                try:
                    reviews_count = int(reviews_match.group(1))
                except ValueError:
                    pass

            # Get current URL
            current_url = page.url

            result = {
                "business_name": business_name,
                "address": address,
                "phone": phone,
                "website": website,
                "rating": rating,
                "reviews_count": reviews_count,
                "google_maps_url": current_url,
            }

            # Only return if we have at least business name
            if result.get("business_name"):
                return result

        except Exception as e:
            logger.error(f"Error extracting maps data: {e}")

        return None

    async def _scrape_website_with_playwright(self, website_url: str) -> Optional[Dict]:
        """Scrape website using Playwright."""
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                await page.goto(website_url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(1000)

                # Get page content
                html_content = await page.content()
                text_content = await page.evaluate("() => document.body.innerText")

                # Extract email
                email = self.parse_email_from_text(text_content)

                # Extract phone
                phone = self.parse_phone_from_text(text_content)

                # Extract social links
                social_links = self.extract_social_links(html_content)

                # Extract owner info (look for "O nás", "About", "Kontakt" sections)
                owner_name = self._extract_owner_from_text(text_content)

                result = {
                    "email": email,
                    "phone": phone,
                    "social_facebook": social_links.get("facebook"),
                    "social_instagram": social_links.get("instagram"),
                    "owner_name": owner_name,
                }

                await browser.close()

                # Return if we found at least one piece of information
                if any(result.values()):
                    return result

        except Exception as e:
            logger.error(f"Playwright website scraping error: {e}")

        return None

    def _extract_owner_from_text(self, text: str) -> Optional[str]:
        """Extract owner name from website text."""
        # Look for owner patterns in Czech and English
        owner_patterns = [
            r"(?:Majitel|Vlastník|Owner|Ředitel|Director)[:\s]+([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+(?:\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+)+)",
            r"([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+(?:\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+)+\s+(?:je|is)\s+(?:majitel|vlastník|owner))",
        ]

        for pattern in owner_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                owner_name = match.group(1).strip()
                # Filter out common false positives
                if len(owner_name.split()) >= 2 and len(owner_name.split()) <= 4:
                    return owner_name

        return None

    async def find_owner_from_website(self, website_url: str) -> Optional[str]:
        """
        Find business owner information by scraping the website.

        Looks for owner information in:
        - "O nás" / "About" sections
        - "Kontakt" / "Contact" pages
        - Footer sections
        - Structured data (JSON-LD)

        Args:
            website_url: URL of the business website

        Returns:
            Owner name if found, None otherwise
        """
        logger.info(f"Searching for owner on website: {website_url}")

        if not website_url or not website_url.startswith(("http://", "https://")):
            logger.warning(f"Invalid website URL: {website_url}")
            return None

        # Scrape website for owner info
        website_data = await self.scrape_website(website_url)
        if website_data and website_data.get("owner_name"):
            return website_data["owner_name"]

        # Try to scrape specific pages that might contain owner info
        pages_to_check = [
            "/o-nas",
            "/about",
            "/kontakt",
            "/contact",
            "/majitel",
            "/owner",
            "/tym",
            "/team",
        ]

        for page_path in pages_to_check:
            try:
                page_url = website_url.rstrip("/") + page_path
                page_data = await self.scrape_website(page_url)
                if page_data and page_data.get("owner_name"):
                    logger.info(
                        f"Found owner on {page_path}: {page_data['owner_name']}"
                    )
                    return page_data["owner_name"]
            except Exception as e:
                logger.debug(f"Failed to scrape {page_path}: {e}")
                continue

        return None


class BrowserAutomationHelper:
    """
    Helper class for browser automation using available tools.

    This class provides methods that can be called with browser MCP tools.
    """

    @staticmethod
    async def search_and_extract_maps(
        business_name: str, location: str = "Prague"
    ) -> Optional[Dict]:
        """
        Search Google Maps and extract business details.

        This method is designed to be called with browser automation tools.
        Returns instructions for browser automation.
        """
        search_url = (
            f"https://www.google.com/maps/search/{quote(f'{business_name} {location}')}"
        )

        return {
            "action": "search_maps",
            "url": search_url,
            "extract": [
                "business_name",
                "address",
                "phone",
                "website",
                "rating",
                "reviews_count",
                "google_maps_url",
            ],
        }

    @staticmethod
    async def extract_from_maps_url(maps_url: str) -> Dict:
        """Get extraction instructions for Google Maps URL."""
        return {
            "action": "extract_maps",
            "url": maps_url,
            "extract": [
                "address",
                "phone",
                "website",
                "opening_hours",
                "rating",
                "reviews",
            ],
        }
