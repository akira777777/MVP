"""
Test script for browser scrapers.
Tests BrowserScraper and SeleniumScraper functionality.
"""

import asyncio
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_browser_scraper():
    """Test BrowserScraper."""
    print("\n" + "=" * 60)
    print("Testing BrowserScraper")
    print("=" * 60)

    try:
        from scripts.browser_scraper import BrowserScraper

        scraper = BrowserScraper(
            use_mcp_puppeteer=False,  # Disable MCP for standalone test
            prefer_selenium=False,
            use_multi_browser=True,
        )

        print("\nSearching Google Maps for 'hair salon' in 'Prague'...")
        result = await scraper.search_google_maps("hair salon", "Prague")

        if result:
            print("\n✅ BrowserScraper - Success!")
            print(f"   Business Name: {result.get('business_name', 'N/A')}")
            print(f"   Address: {result.get('address', 'N/A')}")
            print(f"   Phone: {result.get('phone', 'N/A')}")
            print(f"   Website: {result.get('website', 'N/A')}")
            print(f"   Rating: {result.get('rating', 'N/A')}")
            print(f"   Google Maps URL: {result.get('google_maps_url', 'N/A')}")
            return True
        else:
            print("\n⚠️  BrowserScraper - No results returned")
            return False

    except Exception as e:
        print(f"\n❌ BrowserScraper - Error: {e}")
        logger.exception("BrowserScraper test failed")
        return False


def test_selenium_scraper():
    """Test SeleniumScraper."""
    print("\n" + "=" * 60)
    print("Testing SeleniumScraper")
    print("=" * 60)

    try:
        from scripts.selenium_scraper import SeleniumScraper

        print("\nInitializing SeleniumScraper with undetected-chromedriver...")
        print("(This may take a moment to start the browser)")

        with SeleniumScraper(headless=True, use_undetected=True) as scraper:
            print("\nSearching Google Maps for 'hair salon' in 'Prague'...")
            result = scraper.search_google_maps("hair salon", "Prague")

            if result:
                print("\n✅ SeleniumScraper - Success!")
                print(f"   Name: {result.get('name', 'N/A')}")
                print(f"   Address: {result.get('address', 'N/A')}")
                print(f"   Phone: {result.get('phone', 'N/A')}")
                print(f"   Website: {result.get('website', 'N/A')}")
                print(f"   Rating: {result.get('rating', 'N/A')}")
                print(f"   Google Maps URL: {result.get('google_maps_url', 'N/A')}")
                return True
            else:
                print("\n⚠️  SeleniumScraper - No results returned")
                return False

    except ImportError as e:
        print(f"\n⚠️  SeleniumScraper - Not available: {e}")
        print("   Install with: python -m pip install selenium undetected-chromedriver")
        return False
    except Exception as e:
        print(f"\n❌ SeleniumScraper - Error: {e}")
        logger.exception("SeleniumScraper test failed")
        return False


async def test_multi_browser_scraper():
    """Test MultiBrowserScraper."""
    print("\n" + "=" * 60)
    print("Testing MultiBrowserScraper")
    print("=" * 60)

    try:
        from scripts.multi_browser_scraper import BrowserEngine, MultiBrowserScraper

        print("\nInitializing MultiBrowserScraper (auto engine selection)...")

        async with MultiBrowserScraper(engine=BrowserEngine.AUTO) as scraper:
            print(f"   Active engine: {scraper.active_engine}")
            print("\nSearching Google Maps for 'hair salon' in 'Prague'...")

            result = await scraper.search_google_maps("hair salon", "Prague")

            if result:
                print("\n✅ MultiBrowserScraper - Success!")
                print(
                    f"   Name: {result.get('name', result.get('business_name', 'N/A'))}"
                )
                print(f"   Address: {result.get('address', 'N/A')}")
                print(f"   Phone: {result.get('phone', 'N/A')}")
                print(f"   Website: {result.get('website', 'N/A')}")
                return True
            else:
                print("\n⚠️  MultiBrowserScraper - No results returned")
                return False

    except Exception as e:
        print(f"\n❌ MultiBrowserScraper - Error: {e}")
        logger.exception("MultiBrowserScraper test failed")
        return False


async def main():
    """Run all scraper tests."""
    print("\n" + "=" * 60)
    print("Browser Scrapers Test Suite")
    print("=" * 60)
    print("\nThis will test all available browser scrapers.")
    print("Note: Tests may take some time as they launch browsers.")
    print("\nPress Ctrl+C to cancel...")

    await asyncio.sleep(2)  # Give user time to read

    results = {}

    # Test 1: BrowserScraper
    try:
        results["BrowserScraper"] = await test_browser_scraper()
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        return
    except Exception as e:
        print(f"\n❌ BrowserScraper test crashed: {e}")
        results["BrowserScraper"] = False

    # Test 2: SeleniumScraper (synchronous)
    try:
        results["SeleniumScraper"] = test_selenium_scraper()
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        return
    except Exception as e:
        print(f"\n❌ SeleniumScraper test crashed: {e}")
        results["SeleniumScraper"] = False

    # Test 3: MultiBrowserScraper
    try:
        results["MultiBrowserScraper"] = await test_multi_browser_scraper()
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        return
    except Exception as e:
        print(f"\n❌ MultiBrowserScraper test crashed: {e}")
        results["MultiBrowserScraper"] = False

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for scraper_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{scraper_name:25} {status}")

    passed = sum(results.values())
    total = len(results)

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All scrapers are working correctly!")
    else:
        print(f"\n⚠️  {total - passed} scraper(s) need attention")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite crashed: {e}")
        logger.exception("Test suite failed")
