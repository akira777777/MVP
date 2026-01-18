"""
Quick test for browser scrapers - simplified version.
"""

import asyncio
import sys


async def quick_test():
    """Quick test of scrapers."""
    print("=" * 60)
    print("Quick Browser Scrapers Test")
    print("=" * 60)

    # Test 1: BrowserScraper
    print("\n[1/2] Testing BrowserScraper...")
    try:
        from scripts.browser_scraper import BrowserScraper

        scraper = BrowserScraper()
        print("   ✅ BrowserScraper imported successfully")
        print("   ⏳ Searching Google Maps (this may take a moment)...")
        result = await scraper.search_google_maps("hair salon", "Prague")
        if result:
            print(
                f"   ✅ Found result: {result.get('business_name', result.get('name', 'Unknown'))}"
            )
        else:
            print("   ⚠️  No result returned (may be normal if browser not available)")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 2: SeleniumScraper
    print("\n[2/2] Testing SeleniumScraper...")
    try:
        from scripts.selenium_scraper import SeleniumScraper

        print("   ✅ SeleniumScraper imported successfully")
        print("   ⏳ Starting browser (this may take a moment)...")
        with SeleniumScraper(headless=True, use_undetected=True) as scraper:
            print("   ✅ Browser started")
            print("   ⏳ Searching Google Maps...")
            result = scraper.search_google_maps("hair salon", "Prague")
            if result:
                print(f"   ✅ Found result: {result.get('name', 'Unknown')}")
            else:
                print("   ⚠️  No result returned")
    except ImportError as e:
        print(f"   ⚠️  Selenium not available: {e}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(quick_test())
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
