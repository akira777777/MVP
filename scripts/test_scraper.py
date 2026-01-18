"""
Test script for Prague business scraper.
Tests basic functionality without full scraping.
"""

import asyncio
import logging
from scripts.prague_business_scraper import PragueBusinessScraper
from scripts.mcp_integration import MCPSearchClient, MCPBrowserClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_search_client():
    """Test search client functionality."""
    logger.info("Testing search client...")
    
    client = MCPSearchClient()
    
    # Test search
    results = await client.search("kadeřnictví Praha 1", count=5)
    
    logger.info(f"Search returned {len(results)} results")
    for i, result in enumerate(results[:3], 1):
        logger.info(f"{i}. {result.get('title', 'No title')} - {result.get('url', 'No URL')}")
    
    return len(results) > 0


async def test_browser_client():
    """Test browser client functionality."""
    logger.info("Testing browser client...")
    
    client = MCPBrowserClient()
    
    # Test navigation (use a simple test URL)
    test_url = "https://www.google.com"
    success = await client.navigate(test_url)
    
    logger.info(f"Navigation to {test_url}: {'Success' if success else 'Failed'}")
    
    return success


async def test_scraper_basic():
    """Test basic scraper functionality."""
    logger.info("Testing scraper basic functionality...")
    
    scraper = PragueBusinessScraper(rate_limit_delay=1.0)
    
    # Test CSV creation
    logger.info("Testing CSV file creation...")
    scraper._ensure_csv_exists()
    
    # Test loading existing businesses
    existing = scraper._load_existing_businesses()
    logger.info(f"Loaded {len(existing)} existing businesses")
    
    return True


async def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("Prague Business Scraper - Test Suite")
    logger.info("=" * 60)
    
    tests = [
        ("Search Client", test_search_client),
        ("Browser Client", test_browser_client),
        ("Scraper Basic", test_scraper_basic),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Running test: {test_name} ---")
        try:
            result = await test_func()
            results[test_name] = result
            logger.info(f"✓ {test_name}: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            results[test_name] = False
            logger.error(f"✗ {test_name}: FAILED - {e}", exc_info=True)
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    
    for test_name, result in results.items():
        status = "PASSED" if result else "FAILED"
        logger.info(f"{test_name}: {status}")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("✓ All tests passed!")
    else:
        logger.warning("⚠ Some tests failed. Check logs for details.")


if __name__ == "__main__":
    asyncio.run(main())
