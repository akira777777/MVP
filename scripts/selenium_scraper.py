"""
Selenium-based browser scraper for Google Maps and business websites.
Provides robust browser automation with anti-detection capabilities.
"""

import asyncio
import logging
import re
import time
from typing import Dict, Optional
from urllib.parse import quote

try:
    from selenium import webdriver
    from selenium.common.exceptions import NoSuchElementException, TimeoutException
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

try:
    import undetected_chromedriver as uc

    UNDETECTED_AVAILABLE = True
except ImportError:
    UNDETECTED_AVAILABLE = False

logger = logging.getLogger(__name__)


class SeleniumScraper:
    """
    Selenium-based browser scraper with anti-detection support.

    Supports both standard Selenium and undetected-chromedriver.
    """

    def __init__(
        self,
        headless: bool = True,
        use_undetected: bool = True,
        wait_timeout: int = 10,
        implicit_wait: int = 5,
    ):
        """
        Initialize Selenium scraper.

        Args:
            headless: Run browser in headless mode
            use_undetected: Use undetected-chromedriver (anti-detection)
            wait_timeout: Explicit wait timeout in seconds
            implicit_wait: Implicit wait timeout in seconds
        """
        if not SELENIUM_AVAILABLE:
            raise ImportError(
                "Selenium not installed. Install with: pip install selenium"
            )

        self.headless = headless
        self.use_undetected = use_undetected and UNDETECTED_AVAILABLE
        self.wait_timeout = wait_timeout
        self.implicit_wait = implicit_wait
        self.driver: Optional[webdriver.Chrome] = None

    def _create_driver(self) -> webdriver.Chrome:
        """Create and configure Chrome driver."""
        if self.use_undetected:
            logger.info("Using undetected-chromedriver for anti-detection")
            options = uc.ChromeOptions()
            if self.headless:
                options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)

            driver = uc.Chrome(options=options, version_main=None)
        else:
            logger.info("Using standard Selenium Chrome driver")
            options = Options()
            if self.headless:
                options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            options.add_argument(
                "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )

            driver = webdriver.Chrome(options=options)

        driver.implicitly_wait(self.implicit_wait)
        return driver

    def start(self):
        """Start browser driver."""
        if self.driver is None:
            self.driver = self._create_driver()
            logger.info("Browser driver started")

    def stop(self):
        """Stop browser driver."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.error(f"Error closing driver: {e}")
            finally:
                self.driver = None
            logger.info("Browser driver stopped")

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

    def search_google_maps(
        self, business_name: str, location: str = "Prague"
    ) -> Optional[Dict]:
        """
        Search Google Maps for business and extract details.

        Args:
            business_name: Name of the business
            location: Location to search in

        Returns:
            Dict with business details or None
        """
        if not self.driver:
            self.start()

        search_query = f"{business_name} {location}"
        search_url = f"https://www.google.com/maps/search/{quote(search_query)}"

        logger.info(f"Searching Google Maps: {search_query}")

        try:
            self.driver.get(search_url)
            time.sleep(3)  # Wait for page load

            # Wait for search results
            wait = WebDriverWait(self.driver, self.wait_timeout)

            # Try to find first result
            try:
                first_result = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "a[href*='/maps/place/']")
                    )
                )
                maps_url = first_result.get_attribute("href")

                # Click on first result
                first_result.click()
                time.sleep(2)  # Wait for details page

                # Extract business details
                return self._extract_maps_details()
            except TimeoutException:
                logger.warning("No search results found")
                return None

        except Exception as e:
            logger.error(f"Error searching Google Maps: {e}", exc_info=True)
            return None

    def _extract_maps_details(self) -> Optional[Dict]:
        """Extract business details from Google Maps page."""
        data = {}

        try:
            # Extract business name
            try:
                name_elem = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))
                )
                data["name"] = name_elem.text.strip()
            except TimeoutException:
                # Try alternative selector
                try:
                    name_elem = self.driver.find_element(
                        By.CSS_SELECTOR, "[data-value='Name']"
                    )
                    data["name"] = name_elem.text.strip()
                except NoSuchElementException:
                    pass

            # Extract address
            try:
                address_elem = self.driver.find_element(
                    By.CSS_SELECTOR, "button[data-item-id='address']"
                )
                data["address"] = address_elem.text.strip()
            except NoSuchElementException:
                pass

            # Extract phone
            try:
                phone_elem = self.driver.find_element(
                    By.CSS_SELECTOR, "button[data-item-id*='phone']"
                )
                data["phone"] = phone_elem.text.strip()
            except NoSuchElementException:
                pass

            # Extract website
            try:
                website_elem = self.driver.find_element(
                    By.CSS_SELECTOR, "a[data-item-id='authority']"
                )
                data["website"] = website_elem.get_attribute("href")
            except NoSuchElementException:
                pass

            # Extract rating
            try:
                rating_elem = self.driver.find_element(
                    By.CSS_SELECTOR, "[jsaction*='rating']"
                )
                rating_text = rating_elem.text.strip()
                rating_match = re.search(r"(\d+\.?\d*)", rating_text)
                if rating_match:
                    data["rating"] = float(rating_match.group(1))
            except NoSuchElementException:
                pass

            # Extract reviews count
            try:
                reviews_elem = self.driver.find_element(
                    By.CSS_SELECTOR, "button[jsaction*='reviews']"
                )
                reviews_text = reviews_elem.text.strip()
                reviews_match = re.search(r"(\d+)", reviews_text.replace(",", ""))
                if reviews_match:
                    data["reviews_count"] = int(reviews_match.group(1))
            except NoSuchElementException:
                pass

            # Get current URL as Google Maps URL
            data["google_maps_url"] = self.driver.current_url

            return data if data.get("name") else None

        except Exception as e:
            logger.error(f"Error extracting maps details: {e}", exc_info=True)
            return None

    def scrape_website(self, website_url: str) -> Optional[Dict]:
        """
        Scrape business website for contact information.

        Args:
            website_url: URL of the business website

        Returns:
            Dict with extracted data or None
        """
        if not self.driver:
            self.start()

        logger.info(f"Scraping website: {website_url}")

        try:
            self.driver.get(website_url)
            time.sleep(3)  # Wait for page load

            data = {}

            # Extract email
            page_text = self.driver.page_source
            email_match = re.search(
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", page_text
            )
            if email_match:
                data["email"] = email_match.group(0)

            # Extract phone (Czech format)
            phone_patterns = [
                r"\+420\s?\d{3}\s?\d{3}\s?\d{3}",
                r"00420\s?\d{3}\s?\d{3}\s?\d{3}",
                r"\d{3}\s?\d{3}\s?\d{3}",
            ]
            for pattern in phone_patterns:
                phone_match = re.search(pattern, page_text)
                if phone_match:
                    data["phone"] = phone_match.group(0).strip()
                    break

            # Extract social media links
            social_links = self._extract_social_links(page_text)
            data.update(social_links)

            # Extract owner info from common sections
            owner_info = self._extract_owner_info()
            data.update(owner_info)

            return data

        except Exception as e:
            logger.error(f"Error scraping website: {e}", exc_info=True)
            return None

    def _extract_social_links(self, html_content: str) -> Dict[str, Optional[str]]:
        """Extract social media links from HTML."""
        social_links = {
            "facebook": None,
            "instagram": None,
            "twitter": None,
        }

        # Facebook
        fb_match = re.search(
            r'https?://(?:www\.)?(?:facebook|fb)\.com/([^\s"\'<>]+)',
            html_content,
            re.IGNORECASE,
        )
        if fb_match:
            social_links["facebook"] = f"https://facebook.com/{fb_match.group(1)}"

        # Instagram
        ig_match = re.search(
            r'https?://(?:www\.)?instagram\.com/([^\s"\'<>]+)',
            html_content,
            re.IGNORECASE,
        )
        if ig_match:
            social_links["instagram"] = f"https://instagram.com/{ig_match.group(1)}"

        # Twitter/X
        twitter_match = re.search(
            r'https?://(?:www\.)?(?:twitter|x)\.com/([^\s"\'<>]+)',
            html_content,
            re.IGNORECASE,
        )
        if twitter_match:
            social_links["twitter"] = f"https://twitter.com/{twitter_match.group(1)}"

        return social_links

    def _extract_owner_info(self) -> Dict[str, Optional[str]]:
        """Extract owner information from page."""
        owner_info = {"owner_name": None, "owner_contact": None}

        try:
            # Look for common owner sections
            owner_selectors = [
                "//*[contains(text(), 'Owner')]",
                "//*[contains(text(), 'Vlastník')]",
                "//*[contains(text(), 'Majitel')]",
                "//*[contains(text(), 'Contact')]",
                "//*[contains(text(), 'Kontakt')]",
            ]

            for selector in owner_selectors:
                try:
                    elem = self.driver.find_element(By.XPATH, selector)
                    parent = elem.find_element(By.XPATH, "..")
                    text = parent.text

                    # Try to extract name
                    name_match = re.search(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", text)
                    if name_match:
                        owner_info["owner_name"] = name_match.group(1)
                        break
                except NoSuchElementException:
                    continue

        except Exception as e:
            logger.debug(f"Could not extract owner info: {e}")

        return owner_info

    def extract_from_maps_url(self, maps_url: str) -> Optional[Dict]:
        """
        Extract business details from Google Maps URL.

        Args:
            maps_url: Google Maps URL

        Returns:
            Dict with business details or None
        """
        if not self.driver:
            self.start()

        logger.info(f"Extracting from Maps URL: {maps_url}")

        try:
            self.driver.get(maps_url)
            time.sleep(3)  # Wait for page load
            return self._extract_maps_details()
        except Exception as e:
            logger.error(f"Error extracting from Maps URL: {e}", exc_info=True)
            return None


async def async_search_google_maps(
    business_name: str, location: str = "Prague", headless: bool = True
) -> Optional[Dict]:
    """
    Async wrapper for Google Maps search.

    Args:
        business_name: Name of the business
        location: Location to search in
        headless: Run browser in headless mode

    Returns:
        Dict with business details or None
    """
    loop = asyncio.get_event_loop()

    def _search():
        with SeleniumScraper(headless=headless) as scraper:
            return scraper.search_google_maps(business_name, location)

    return await loop.run_in_executor(None, _search)


async def async_scrape_website(
    website_url: str, headless: bool = True
) -> Optional[Dict]:
    """
    Async wrapper for website scraping.

    Args:
        website_url: URL of the website
        headless: Run browser in headless mode

    Returns:
        Dict with extracted data or None
    """
    loop = asyncio.get_event_loop()

    def _scrape():
        with SeleniumScraper(headless=headless) as scraper:
            return scraper.scrape_website(website_url)

    return await loop.run_in_executor(None, _scrape)
