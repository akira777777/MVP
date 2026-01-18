"""
Example: How to test browser scrapers.

Run this script to test both BrowserScraper and SeleniumScraper.
"""

import asyncio
import sys

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)


async def test_browser_scraper():
    """Test BrowserScraper."""
    print("\n" + "=" * 60)
    print("Test 1: BrowserScraper")
    print("=" * 60)

    from scripts.browser_scraper import BrowserScraper

    scraper = BrowserScraper()
    print("\nSearching Google Maps for 'hair salon' in 'Prague'...")
    sys.stdout.flush()

    result = await scraper.search_google_maps("hair salon", "Prague")

    if result:
        print("\n✅ Success!")
        print(f"   Name: {result.get('business_name', result.get('name', 'N/A'))}")
        print(f"   Address: {result.get('address', 'N/A')}")
        print(f"   Phone: {result.get('phone', 'N/A')}")
        print(f"   Website: {result.get('website', 'N/A')}")
    else:
        print("\n⚠️  No result (may be normal if browser not available)")


def test_selenium_scraper():
    """Test SeleniumScraper."""
    print("\n" + "=" * 60)
    print("Test 2: SeleniumScraper")
    print("=" * 60)

    try:
        from scripts.selenium_scraper import SeleniumScraper

        print("\nStarting browser (this may take a moment)...")
        sys.stdout.flush()
        with SeleniumScraper(headless=True, use_undetected=True) as scraper:
            print("Browser started!")
            sys.stdout.flush()
            print("\nSearching Google Maps for 'hair salon' in 'Prague'...")
            sys.stdout.flush()

            result = scraper.search_google_maps("hair salon", "Prague")

            if result:
                print("\n✅ Success!")
                print(f"   Name: {result.get('name', 'N/A')}")
                print(f"   Address: {result.get('address', 'N/A')}")
                print(f"   Phone: {result.get('phone', 'N/A')}")
                print(f"   Website: {result.get('website', 'N/A')}")
            else:
                print("\n⚠️  No result")

    except ImportError:
        print("\n⚠️  Selenium not installed")
        print("   Install with: python -m pip install selenium undetected-chromedriver")
    except Exception as e:
        print(f"\n❌ Error: {e}")


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Browser Scrapers Test Example")
    print("=" * 60)
    print("\nThis will test BrowserScraper and SeleniumScraper")
    print("Note: Tests may take 10-30 seconds each")

    # Test BrowserScraper
    await test_browser_scraper()

    # Test SeleniumScraper
    test_selenium_scraper()

    print("\n" + "=" * 60)
    print("Tests complete!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
