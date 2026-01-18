#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to collect Prague business database using MCP servers and web scraping.

This script:
1. Searches for businesses using Brave Search MCP
2. Collects detailed information using browser automation
3. Searches for owner information via web search
4. Validates and deduplicates data
5. Exports to CSV format
"""

import asyncio
import csv
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import quote, urlparse

import httpx
from pydantic import ValidationError

from models.business import Business, BusinessCategory, BusinessCreate
from scripts.browser_scraper import BrowserScraper, BrowserAutomationHelper
from scripts.mcp_search import MCPSearchClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("data/collection.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Business categories and search queries
BUSINESS_CATEGORIES = {
    BusinessCategory.HAIR_SALON: [
        "hair salons Prague",
        "kadeřnictví Praha",
        "hair salon Praha",
        "kadeřnictví Prague",
    ],
    BusinessCategory.BEAUTY_SALON: [
        "beauty salons Prague",
        "kosmetika Praha",
        "beauty salon Praha",
        "kosmetický salon Prague",
    ],
    BusinessCategory.NAIL_SALON: [
        "nail salons Prague",
        "manikúra Praha",
        "nail salon Praha",
        "nehtové studio Prague",
    ],
    BusinessCategory.MASSAGE_SALON: [
        "massage salons Prague",
        "masáže Praha",
        "massage salon Praha",
        "masážní salon Prague",
    ],
    BusinessCategory.TANNING_SALON: [
        "tanning salons Prague",
        "solárium Praha",
        "tanning salon Praha",
    ],
    BusinessCategory.BARBERSHOP: [
        "barbershops Prague",
        "holičství Praha",
        "barbershop Praha",
        "holič Prague",
    ],
}

# Rate limiting
REQUEST_DELAY = 2  # seconds between requests
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Prague location keywords for validation
PRAGUE_KEYWORDS = ["prague", "praha", "praze", "prahy", "110 00", "120 00", "130 00", "140 00", "150 00", "160 00", "170 00", "180 00", "190 00"]


class BusinessCollector:
    """Main class for collecting business data."""

    def __init__(self, output_file: str = "data/prague_businesses.csv", max_businesses: int = 100):
        """Initialize collector."""
        self.output_file = Path(output_file)
        self.max_businesses = max_businesses
        self.collected_businesses: List[Business] = []
        self.seen_addresses: Set[str] = set()
        self.seen_names: Set[str] = set()
        self.http_client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        self.search_client = MCPSearchClient()
        self.browser_scraper = BrowserScraper(use_mcp_puppeteer=True)

    async def search_businesses_brave(self, query: str, category: str) -> List[Dict]:
        """
        Search for businesses using Brave Search MCP.
        
        Uses local search API which is better for businesses.
        """
        results = []
        
        # Try local search first (better for businesses)
        local_results = await self.search_client.local_search(query, "Prague, Czech Republic")
        
        for item in local_results:
            results.append({
                "title": item.get("title", ""),
                "address": item.get("address", ""),
                "phone": item.get("phone"),
                "website": item.get("website"),
                "url": item.get("url", ""),
                "category": category,
            })
        
        # If not enough results, try web search
        if len(results) < 10:
            web_results = await self.search_client.brave_search(query, count=20)
            for item in web_results:
                # Extract business name from title
                title = item.get("title", "")
                # Skip if already in results
                if not any(r["title"] == title for r in results):
                    results.append({
                        "title": title,
                        "url": item.get("url", ""),
                        "description": item.get("description", ""),
                        "category": category,
                    })
        
        return results

    async def get_business_details_from_maps(self, business_name: str, address_hint: Optional[str] = None) -> Optional[Dict]:
        """
        Get business details from Google Maps using browser automation.
        
        Returns:
            Dict with: address, phone, website, google_maps_url, rating, reviews
        """
        logger.info(f"Getting details for: {business_name}")
        
        # Use browser scraper
        details = await self.browser_scraper.search_google_maps(business_name, "Prague")
        
        if details:
            return details
        
        # If browser automation not available, try to construct Google Maps URL
        # and return basic info
        search_query = f"{business_name} Prague"
        maps_url = f"https://www.google.com/maps/search/{quote(search_query)}"
        
        return {
            "google_maps_url": maps_url,
            "address": address_hint or "",
        }

    async def search_owner_info(self, business_name: str, address: str, website: Optional[str] = None) -> Optional[str]:
        """
        Search for business owner information using multiple methods.
        
        Combines:
        1. Website scraping (most reliable)
        2. Web search
        3. Registry lookup (if ICO available)
        
        Args:
            business_name: Name of the business
            address: Business address
            website: Business website URL (optional)
            
        Returns:
            Owner name if found, None otherwise
        """
        # Method 1: Scrape website if available (most reliable)
        if website:
            try:
                owner_name = await self.browser_scraper.find_owner_from_website(website)
                if owner_name:
                    logger.info(f"Found owner from website: {owner_name}")
                    return owner_name
            except Exception as e:
                logger.warning(f"Failed to scrape website for owner info: {e}")
        
        # Method 2: Web search
        search_queries = [
            f"{business_name} owner Praha",
            f"{business_name} majitel",
            f"{business_name} vlastník",
            f'"{business_name}" owner',
            f"{business_name} {address} majitel",
        ]
        
        for query in search_queries:
            logger.info(f"Searching for owner info: {query}")
            try:
                results = await self.search_client.brave_search(query, count=5)
                
                for result in results:
                    text = f"{result.get('title', '')} {result.get('description', '')}"
                    
                    # Look for owner patterns in Czech and English
                    owner_patterns = [
                        r'majitel[:\s]+([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+)',
                        r'vlastník[:\s]+([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+)',
                        r'owner[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                        r'([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+)\s+(?:je|is)\s+(?:majitel|vlastník|owner)',
                    ]
                    
                    for pattern in owner_patterns:
                        match = re.search(pattern, text, re.IGNORECASE)
                        if match:
                            owner_name = match.group(1).strip()
                            if len(owner_name.split()) >= 2:  # At least first and last name
                                logger.info(f"Found owner from web search: {owner_name}")
                                return owner_name
                
                await asyncio.sleep(REQUEST_DELAY)
            except Exception as e:
                logger.warning(f"Web search for owner failed: {e}")
                continue
        
        # Method 3: Try to scrape websites found in search results
        # This is done as a last resort since it's slower
        for query in search_queries[:2]:  # Only try first 2 queries
            try:
                results = await self.search_client.brave_search(query, count=3)
                for result in results:
                    result_url = result.get('url', '')
                    # Only scrape if it looks like a business website
                    if result_url and not any(domain in result_url for domain in ['google.com', 'facebook.com', 'instagram.com']):
                        try:
                            owner_name = await self.browser_scraper.find_owner_from_website(result_url)
                            if owner_name:
                                logger.info(f"Found owner from scraped search result: {owner_name}")
                                return owner_name
                        except Exception as e:
                            logger.debug(f"Failed to scrape search result {result_url}: {e}")
                            continue
            except Exception as e:
                logger.debug(f"Failed to scrape search results: {e}")
                continue
        
        return None

    def is_in_prague(self, address: str) -> bool:
        """Check if address is in Prague."""
        if not address or len(address.strip()) < 5:
            return False
        
        address_lower = address.lower()
        # Check for Prague keywords
        prague_found = any(keyword in address_lower for keyword in PRAGUE_KEYWORDS)
        
        # Also check for Prague postal codes (11000-19999)
        prague_postal = re.search(r'\b(1[1-9]\d{3})\b', address)
        
        return prague_found or (prague_postal is not None)

    def normalize_address(self, address: str) -> str:
        """Normalize address for deduplication."""
        # Remove extra spaces, normalize case
        normalized = " ".join(address.split()).lower()
        # Remove common variations
        normalized = normalized.replace("praha", "prague")
        normalized = normalized.replace("praze", "prague")
        return normalized

    def is_duplicate(self, business: BusinessCreate) -> bool:
        """Check if business is duplicate based on name or address."""
        normalized_address = self.normalize_address(business.address)
        normalized_name = business.name.lower().strip()

        # Check exact matches
        if normalized_address in self.seen_addresses:
            return True
        if normalized_name in self.seen_names:
            return True

        # Check fuzzy matches (similar names)
        for seen_name in self.seen_names:
            # If names are very similar (Levenshtein distance < 3)
            if self._similarity(normalized_name, seen_name) > 0.8:
                return True

        return False

    def _similarity(self, s1: str, s2: str) -> float:
        """Calculate simple similarity ratio between two strings."""
        if not s1 or not s2:
            return 0.0
        
        # Simple character overlap ratio
        set1 = set(s1.lower())
        set2 = set(s2.lower())
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0

    def validate_business(self, business_data: Dict) -> Optional[Business]:
        """Validate and create Business model."""
        try:
            # Basic validation
            if not business_data.get("name") or len(business_data["name"].strip()) < 2:
                logger.warning("Business name too short, skipping")
                return None

            if not business_data.get("address") or len(business_data["address"].strip()) < 5:
                logger.warning(f"Business address too short: {business_data.get('name')}")
                return None

            # Create BusinessCreate first
            business_create = BusinessCreate(**business_data)
            
            # Check if in Prague
            if not self.is_in_prague(business_create.address):
                logger.warning(f"Business not in Prague: {business_create.name} - {business_create.address}")
                return None

            # Check for duplicates
            if self.is_duplicate(business_create):
                logger.info(f"Duplicate business skipped: {business_create.name}")
                return None

            # Create full Business model
            business = Business(**business_create.model_dump())
            
            # Mark as seen
            self.seen_addresses.add(self.normalize_address(business.address))
            self.seen_names.add(business.name.lower().strip())

            return business

        except ValidationError as e:
            logger.error(f"Validation error for business {business_data.get('name', 'unknown')}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating business: {e}", exc_info=True)
            return None

    async def collect_businesses(self):
        """Main collection loop."""
        logger.info("Starting business collection...")
        logger.info(f"Target: {self.max_businesses} businesses")

        # Search for businesses by category
        for category, queries in BUSINESS_CATEGORIES.items():
            if len(self.collected_businesses) >= self.max_businesses:
                break

            logger.info(f"Searching category: {category}")
            
            for query in queries:
                if len(self.collected_businesses) >= self.max_businesses:
                    break

                # Retry logic for search
                search_results = []
                for attempt in range(MAX_RETRIES):
                    try:
                        search_results = await self.search_businesses_brave(query, category)
                        break
                    except Exception as e:
                        logger.warning(f"Search attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")
                        if attempt < MAX_RETRIES - 1:
                            await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                        else:
                            logger.error(f"Failed to search after {MAX_RETRIES} attempts: {query}")
                            continue
                
                for result in search_results:
                    if len(self.collected_businesses) >= self.max_businesses:
                        break

                    business_name = result.get("title", "").strip()
                    if not business_name:
                        continue

                    # Retry logic for getting details
                    details = None
                    for attempt in range(MAX_RETRIES):
                        try:
                            address_hint = result.get("address") or result.get("description", "")
                            details = await self.get_business_details_from_maps(business_name, address_hint)
                            break
                        except Exception as e:
                            logger.warning(f"Details fetch attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")
                            if attempt < MAX_RETRIES - 1:
                                await asyncio.sleep(RETRY_DELAY)
                            else:
                                logger.warning(f"Failed to get details for {business_name}, using basic info")
                                break
                    
                    # Build business data
                    business_data = {
                        "name": business_name,
                        "category": category,
                        "address": (
                            details.get("address") if details and details.get("address")
                            else result.get("address") or result.get("description", "")
                        ),
                        "phone": (
                            details.get("phone") if details
                            else result.get("phone")
                        ),
                        "email": details.get("email") if details else None,
                        "website": (
                            details.get("website") if details and details.get("website")
                            else result.get("website") or result.get("url")
                        ),
                        "google_maps_url": details.get("google_maps_url") if details else None,
                        "social_facebook": details.get("social_facebook") if details else None,
                        "social_instagram": details.get("social_instagram") if details else None,
                    }
                    
                    # If we have a website, try to scrape it for more info
                    if business_data["website"] and not business_data.get("email"):
                        try:
                            website_info = await self.browser_scraper.scrape_website(business_data["website"])
                            if website_info:
                                if website_info.get("email") and not business_data.get("email"):
                                    business_data["email"] = website_info["email"]
                                if website_info.get("phone") and not business_data.get("phone"):
                                    business_data["phone"] = website_info["phone"]
                                if website_info.get("social_facebook") and not business_data.get("social_facebook"):
                                    business_data["social_facebook"] = website_info["social_facebook"]
                                if website_info.get("social_instagram") and not business_data.get("social_instagram"):
                                    business_data["social_instagram"] = website_info["social_instagram"]
                        except Exception as e:
                            logger.warning(f"Failed to scrape website {business_data['website']}: {e}")

                    # Search for owner info (with retry)
                    if business_data["address"]:
                        try:
                            owner_name = await self.search_owner_info(
                                business_name,
                                business_data["address"],
                                website=business_data.get("website")
                            )
                            if owner_name:
                                business_data["owner_name"] = owner_name
                        except Exception as e:
                            logger.warning(f"Failed to search owner info for {business_name}: {e}")

                    # Validate and add business
                    business = self.validate_business(business_data)
                    if business:
                        self.collected_businesses.append(business)
                        logger.info(f"Collected: {business.name} ({len(self.collected_businesses)}/{self.max_businesses})")

                    # Rate limiting
                    await asyncio.sleep(REQUEST_DELAY)

        logger.info(f"Collection complete: {len(self.collected_businesses)} businesses collected")

    async def export_to_csv(self):
        """Export collected businesses to CSV file."""
        if not self.collected_businesses:
            logger.warning("No businesses to export")
            return

        self.output_file.parent.mkdir(parents=True, exist_ok=True)

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

        with open(self.output_file, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for business in self.collected_businesses:
                row = {
                    "name": business.name,
                    "category": business.category,
                    "address": business.address,
                    "phone": business.phone or "",
                    "email": business.email or "",
                    "website": business.website or "",
                    "owner_name": business.owner_name or "",
                    "social_facebook": business.social_facebook or "",
                    "social_instagram": business.social_instagram or "",
                    "google_maps_url": business.google_maps_url or "",
                    "notes": business.notes or "",
                    "collected_at": business.collected_at.isoformat(),
                }
                writer.writerow(row)

        logger.info(f"Exported {len(self.collected_businesses)} businesses to {self.output_file}")

    async def cleanup(self):
        """Cleanup resources."""
        await self.http_client.aclose()


async def main():
    """Main entry point."""
    collector = BusinessCollector(max_businesses=100)
    
    try:
        await collector.collect_businesses()
        await collector.export_to_csv()
        
        logger.info("=" * 50)
        logger.info("Collection Summary:")
        logger.info(f"Total businesses collected: {len(collector.collected_businesses)}")
        logger.info(f"Output file: {collector.output_file}")
        logger.info("=" * 50)
        
    except KeyboardInterrupt:
        logger.info("Collection interrupted by user")
        await collector.export_to_csv()  # Save progress
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await collector.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
