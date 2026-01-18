"""
Main script for scraping Prague businesses using MCP servers.
Collects data about beauty salons, hair salons, nail studios, etc.
"""

import csv
import logging
import asyncio
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from utils.business_scraper_utils import (
    validate_business_data,
    deduplicate_businesses,
    calculate_data_completeness,
)
from scripts.business_data_extractor import (
    parse_google_maps_data,
    enrich_business_data,
)
from scripts.mcp_integration import MCPSearchClient, MCPBrowserClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/prague_scraper.log'),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

# Ensure logs directory exists
Path('logs').mkdir(exist_ok=True)

# Prague districts
PRAGUE_DISTRICTS = [
    "Praha 1", "Praha 2", "Praha 3", "Praha 4", "Praha 5",
    "Praha 6", "Praha 7", "Praha 8", "Praha 9", "Praha 10",
]

# Business types and their Czech search terms
BUSINESS_TYPES = {
    'hair_salon': {
        'en': ['hair salon', 'hairdresser', 'hairdressing'],
        'cs': ['kadeřnictví', 'hairdresser'],
    },
    'beauty_salon': {
        'en': ['beauty salon', 'beauty center'],
        'cs': ['kosmetika', 'salon krásy', 'beauty salon'],
    },
    'nail_salon': {
        'en': ['nail salon', 'nail studio', 'manicure'],
        'cs': ['nehtové studio', 'nail studio', 'manikúra'],
    },
    'spa': {
        'en': ['spa', 'wellness', 'massage'],
        'cs': ['masáž', 'spa', 'wellness'],
    },
    'barbershop': {
        'en': ['barbershop', 'barber'],
        'cs': ['barbershop', 'holicství', 'pánské kadeřnictví'],
    },
    'tattoo_studio': {
        'en': ['tattoo studio', 'tattoo shop'],
        'cs': ['tetování', 'tattoo studio', 'tatér'],
    },
}

# CSV file path
CSV_FILE = Path('data/prague_businesses.csv')

# CSV columns
CSV_COLUMNS = [
    'business_name',
    'address',
    'district',
    'phone',
    'email',
    'website',
    'facebook',
    'instagram',
    'owner_name',
    'owner_contact',
    'business_type',
    'google_maps_url',
    'rating',
    'reviews_count',
    'scraped_at',
]


class PragueBusinessScraper:
    """Main scraper class for Prague businesses."""
    
    def __init__(self, rate_limit_delay: float = 2.0):
        """
        Initialize scraper.
        
        Args:
            rate_limit_delay: Delay between requests in seconds
        """
        self.rate_limit_delay = rate_limit_delay
        self.businesses: List[Dict] = []
        self.search_client = MCPSearchClient()
        self.browser_client = MCPBrowserClient()
        self._ensure_csv_exists()
    
    def _ensure_csv_exists(self):
        """Ensure CSV file exists with headers."""
        if not CSV_FILE.exists():
            CSV_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                writer.writeheader()
            logger.info(f"Created CSV file: {CSV_FILE}")
    
    def _load_existing_businesses(self) -> List[Dict]:
        """Load existing businesses from CSV."""
        businesses = []
        if CSV_FILE.exists():
            try:
                with open(CSV_FILE, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    businesses = list(reader)
                logger.info(f"Loaded {len(businesses)} existing businesses from CSV")
            except Exception as e:
                logger.error(f"Error loading CSV: {e}")
        return businesses
    
    def _save_businesses(self, businesses: List[Dict]):
        """Save businesses to CSV file."""
        # Load existing to merge
        existing = self._load_existing_businesses()
        all_businesses = existing + businesses
        
        # Deduplicate
        all_businesses = deduplicate_businesses(all_businesses)
        
        # Validate and normalize
        validated_businesses = []
        for business in all_businesses:
            try:
                validated = validate_business_data(business)
                validated_businesses.append(validated)
            except Exception as e:
                logger.error(f"Error validating business {business.get('business_name')}: {e}")
        
        # Sort by completeness score (best first)
        validated_businesses.sort(
            key=lambda b: calculate_data_completeness(b),
            reverse=True
        )
        
        # Write to CSV
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for business in validated_businesses:
                # Ensure all columns are present
                row = {col: business.get(col, '') for col in CSV_COLUMNS}
                writer.writerow(row)
        
        logger.info(f"Saved {len(validated_businesses)} businesses to {CSV_FILE}")
    
    async def search_businesses_web_search(
        self,
        business_type: str,
        district: str,
        search_terms: List[str]
    ) -> List[str]:
        """
        Search for businesses using web search (Brave Search/Tavily).
        
        Args:
            business_type: Type of business (hair_salon, etc.)
            district: Prague district
            search_terms: List of search terms to try
            
        Returns:
            List of Google Maps URLs or business URLs
        """
        all_urls = []
        
        logger.info(
            f"Searching {business_type} in {district} "
            f"with terms: {', '.join(search_terms)}"
        )
        
        for term in search_terms[:3]:  # Limit to first 3 terms
            query = f"{term} {district} Prague"
            
            try:
                results = await self.search_client.search(query, count=10)
                
                for result in results:
                    url = result.get('url', '')
                    if url:
                        # Check if it's a Google Maps URL
                        if 'google.com/maps' in url or 'maps.google.com' in url:
                            all_urls.append(url)
                        # Also collect business websites - we'll search Google Maps separately
                        elif any(domain in url for domain in [
                            '.cz', '.com', '.eu'
                        ]):
                            # Store for later Google Maps search
                            pass
                
                # Rate limiting between searches
                await asyncio.sleep(self.rate_limit_delay)
                
            except Exception as e:
                logger.error(f"Error searching for {query}: {e}")
                continue
        
        # Remove duplicates
        unique_urls = list(set(all_urls))
        logger.info(f"Found {len(unique_urls)} unique URLs for {business_type} in {district}")
        
        return unique_urls
    
    async def scrape_google_maps(
        self,
        maps_url: str,
        business_type: str
    ) -> Optional[Dict]:
        """
        Scrape business data from Google Maps using browser automation.
        
        Args:
            maps_url: Google Maps URL
            business_type: Type of business
            
        Returns:
            Business dictionary or None
        """
        logger.debug(f"Scraping Google Maps: {maps_url}")
        
        try:
            # Use browser client to extract data
            maps_data = await self.browser_client.extract_google_maps_data(maps_url)
            
            if maps_data:
                maps_data['url'] = maps_url
                maps_data['type'] = business_type
                return maps_data
            else:
                logger.warning(f"Could not extract data from {maps_url}")
                return None
                
        except Exception as e:
            logger.error(f"Error scraping Google Maps {maps_url}: {e}")
            return None
        finally:
            # Rate limiting
            await asyncio.sleep(self.rate_limit_delay)
    
    async def enrich_business_from_website(self, business: Dict) -> Dict:
        """
        Enrich business data by visiting their website.
        
        Args:
            business: Business dictionary
            
        Returns:
            Enriched business dictionary
        """
        website = business.get('website')
        if not website:
            return business
        
        logger.debug(f"Enriching from website: {website}")
        
        try:
            # Get HTML content
            html_content = await self.browser_client.get_page_content(website)
            
            if html_content:
                # Extract additional data
                enriched = enrich_business_data(business, html_content)
                return enriched
            else:
                logger.warning(f"Could not fetch content from {website}")
                return business
                
        except Exception as e:
            logger.error(f"Error enriching from website {website}: {e}")
            return business
        finally:
            # Rate limiting
            await asyncio.sleep(self.rate_limit_delay)
    
    async def scrape_district(
        self,
        district: str,
        business_type: str,
        search_terms: List[str]
    ):
        """
        Scrape all businesses of a type in a district.
        
        Args:
            district: Prague district
            business_type: Type of business
            search_terms: List of search terms
        """
        logger.info(f"Scraping {business_type} in {district}")
        
        # Step 1: Web search to find businesses (returns URLs)
        business_urls = await self.search_businesses_web_search(
            business_type=business_type,
            district=district,
            search_terms=search_terms
        )
        
        # Step 2: Also search Google Maps directly for this type and district
        google_maps_query = f"{search_terms[0]} {district} Prague"
        maps_search_results = await self.search_client.search(
            f"site:google.com/maps {google_maps_query}",
            count=10
        )
        
        # Extract Google Maps URLs from search results
        for result in maps_search_results:
            url = result.get('url', '')
            if 'google.com/maps' in url and url not in business_urls:
                business_urls.append(url)
        
        # Step 3: Scrape Google Maps for each business
        scraped_businesses = []
        for maps_url in business_urls[:20]:  # Limit to 20 per district/type
            maps_data = await self.scrape_google_maps(
                maps_url=maps_url,
                business_type=business_type
            )
            if maps_data:
                business = parse_google_maps_data(maps_data)
                business['business_type'] = business_type
                
                # Step 4: Enrich from website
                enriched = await self.enrich_business_from_website(business)
                scraped_businesses.append(enriched)
        
        # Save incrementally
        if scraped_businesses:
            self._save_businesses(scraped_businesses)
            logger.info(
                f"Found {len(scraped_businesses)} businesses "
                f"for {business_type} in {district}"
            )
    
    async def run(self, districts: Optional[List[str]] = None):
        """
        Run the scraper for all business types and districts.
        
        Args:
            districts: List of districts to scrape (None = all)
        """
        if districts is None:
            districts = PRAGUE_DISTRICTS
        
        logger.info(f"Starting scraper for {len(districts)} districts")
        
        total_combinations = len(BUSINESS_TYPES) * len(districts)
        current = 0
        
        for business_type, terms in BUSINESS_TYPES.items():
            # Combine English and Czech terms
            all_terms = terms['en'] + terms['cs']
            
            for district in districts:
                current += 1
                logger.info(
                    f"Progress: {current}/{total_combinations} - "
                    f"{business_type} in {district}"
                )
                
                try:
                    await self.scrape_district(
                        district=district,
                        business_type=business_type,
                        search_terms=all_terms
                    )
                except Exception as e:
                    logger.error(
                        f"Error scraping {business_type} in {district}: {e}",
                        exc_info=True
                    )
                
                # Longer delay between districts
                await asyncio.sleep(self.rate_limit_delay * 2)
        
        logger.info("Scraping completed!")
        
        # Final statistics
        final_businesses = self._load_existing_businesses()
        logger.info(f"Total businesses in database: {len(final_businesses)}")


async def main():
    """Main entry point."""
    scraper = PragueBusinessScraper(rate_limit_delay=2.0)
    
    # For testing, start with one district
    # Uncomment to run full scrape:
    # await scraper.run()
    
    # Test with one district and one business type
    await scraper.scrape_district(
        district="Praha 1",
        business_type="hair_salon",
        search_terms=["kadeřnictví", "hair salon"]
    )


if __name__ == "__main__":
    asyncio.run(main())
