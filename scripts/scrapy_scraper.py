"""
Scrapy-based scraper for large-scale web scraping.
Designed for efficient parallel scraping of multiple businesses.
"""

import logging
from typing import Dict, List, Optional
from urllib.parse import urljoin

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

logger = logging.getLogger(__name__)


class GoogleMapsSpider(scrapy.Spider):
    """
    Scrapy spider for scraping Google Maps business listings.
    """

    name = "google_maps"
    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "DOWNLOAD_DELAY": 2,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS": 4,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 1,
        "AUTOTHROTTLE_MAX_DELAY": 10,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 2.0,
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    def __init__(self, search_query: str = None, *args, **kwargs):
        super(GoogleMapsSpider, self).__init__(*args, **kwargs)
        self.search_query = search_query or "hair salon Prague"
        self.start_urls = [
            f"https://www.google.com/maps/search/{self.search_query.replace(' ', '+')}"
        ]
        self.results: List[Dict] = []

    def parse(self, response):
        """Parse Google Maps search results."""
        # Extract business links
        business_links = response.css("a[href*='/maps/place/']::attr(href)").getall()

        for link in business_links[:10]:  # Limit to first 10 results
            full_url = urljoin(response.url, link)
            yield scrapy.Request(
                url=full_url,
                callback=self.parse_business,
                meta={"dont_cache": True},
            )

    def parse_business(self, response):
        """Parse individual business page."""
        business = {}

        # Extract business name
        name = response.css("h1::text").get()
        if name:
            business["name"] = name.strip()

        # Extract address
        address = response.css("button[data-item-id='address']::text").get()
        if address:
            business["address"] = address.strip()

        # Extract phone
        phone = response.css("button[data-item-id*='phone']::text").get()
        if phone:
            business["phone"] = phone.strip()

        # Extract website
        website = response.css("a[data-item-id='authority']::attr(href)").get()
        if website:
            business["website"] = website

        # Extract rating
        rating_text = response.css("[jsaction*='rating']::text").get()
        if rating_text:
            import re

            rating_match = re.search(r"(\d+\.?\d*)", rating_text)
            if rating_match:
                business["rating"] = float(rating_match.group(1))

        # Extract reviews count
        reviews_text = response.css("button[jsaction*='reviews']::text").get()
        if reviews_text:
            import re

            reviews_match = re.search(r"(\d+)", reviews_text.replace(",", ""))
            if reviews_match:
                business["reviews_count"] = int(reviews_match.group(1))

        # Store Google Maps URL
        business["google_maps_url"] = response.url

        if business.get("name"):
            self.results.append(business)
            yield business


class BusinessWebsiteSpider(scrapy.Spider):
    """
    Scrapy spider for scraping business websites.
    """

    name = "business_website"
    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 1,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS": 8,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 4,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 1,
        "AUTOTHROTTLE_MAX_DELAY": 5,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 4.0,
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    def __init__(self, website_urls: List[str] = None, *args, **kwargs):
        super(BusinessWebsiteSpider, self).__init__(*args, **kwargs)
        self.start_urls = website_urls or []
        self.results: List[Dict] = []

    def parse(self, response):
        """Parse business website."""
        business = {"website": response.url}

        # Extract email
        email_match = response.css("::text").re(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        )
        if email_match:
            business["email"] = email_match[0]

        # Extract phone (Czech format)
        phone_patterns = [
            r"\+420\s?\d{3}\s?\d{3}\s?\d{3}",
            r"00420\s?\d{3}\s?\d{3}\s?\d{3}",
            r"\d{3}\s?\d{3}\s?\d{3}",
        ]
        for pattern in phone_patterns:
            phone_match = response.css("::text").re(pattern)
            if phone_match:
                business["phone"] = phone_match[0].strip()
                break

        # Extract social media links
        social_links = {
            "facebook": None,
            "instagram": None,
            "twitter": None,
        }

        # Facebook
        fb_links = response.css("a[href*='facebook.com']::attr(href)").getall()
        if fb_links:
            social_links["facebook"] = fb_links[0]

        # Instagram
        ig_links = response.css("a[href*='instagram.com']::attr(href)").getall()
        if ig_links:
            social_links["instagram"] = ig_links[0]

        # Twitter/X
        twitter_links = response.css(
            "a[href*='twitter.com'], a[href*='x.com']::attr(href)"
        ).getall()
        if twitter_links:
            social_links["twitter"] = twitter_links[0]

        business.update(social_links)

        # Extract owner info from common sections
        owner_sections = response.css(
            "*:contains('Owner'), *:contains('Vlastník'), *:contains('Majitel')"
        )
        if owner_sections:
            owner_text = " ".join(owner_sections.css("::text").getall())
            import re

            name_match = re.search(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", owner_text)
            if name_match:
                business["owner_name"] = name_match.group(1)

        self.results.append(business)
        yield business


class ScrapyScraper:
    """
    Wrapper class for Scrapy-based scraping.
    """

    def __init__(self):
        """Initialize Scrapy scraper."""
        self.process: Optional[CrawlerProcess] = None

    def scrape_google_maps(
        self, search_query: str, max_results: int = 20
    ) -> List[Dict]:
        """
        Scrape Google Maps search results.

        Args:
            search_query: Search query (e.g., "hair salon Prague")
            max_results: Maximum number of results

        Returns:
            List of business dictionaries
        """
        settings = get_project_settings()
        settings.set("LOG_LEVEL", "WARNING")  # Reduce Scrapy noise

        process = CrawlerProcess(settings)

        spider = GoogleMapsSpider(search_query=search_query)
        process.crawl(GoogleMapsSpider, search_query=search_query)
        process.start()

        return spider.results[:max_results]

    def scrape_websites(self, website_urls: List[str]) -> List[Dict]:
        """
        Scrape multiple business websites.

        Args:
            website_urls: List of website URLs

        Returns:
            List of business dictionaries with extracted data
        """
        settings = get_project_settings()
        settings.set("LOG_LEVEL", "WARNING")

        process = CrawlerProcess(settings)

        spider = BusinessWebsiteSpider(website_urls=website_urls)
        process.crawl(BusinessWebsiteSpider, website_urls=website_urls)
        process.start()

        return spider.results

    def close(self):
        """Close Scrapy process."""
        if self.process:
            self.process.stop()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Example usage
if __name__ == "__main__":
    scraper = ScrapyScraper()

    # Scrape Google Maps
    results = scraper.scrape_google_maps("hair salon Prague", max_results=10)
    print(f"Found {len(results)} businesses")

    # Scrape websites
    websites = [r.get("website") for r in results if r.get("website")]
    if websites:
        website_data = scraper.scrape_websites(websites)
        print(f"Scraped {len(website_data)} websites")
