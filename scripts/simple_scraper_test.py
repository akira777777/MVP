"""
Simple test script that saves results to file.
"""

import asyncio
import sys
from datetime import datetime


def log(message):
    """Log message to console and file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{timestamp}] {message}"
    print(msg)
    with open("scraper_test_results.txt", "a", encoding="utf-8") as f:
        f.write(msg + "\n")


async def main():
    """Run simple scraper tests."""
    log("=" * 60)
    log("Browser Scrapers Test")
    log("=" * 60)

    # Test BrowserScraper import
    log("\n[1] Testing BrowserScraper import...")
    try:
        from scripts.browser_scraper import BrowserScraper

        log("   ✅ BrowserScraper imported")

        scraper = BrowserScraper()
        log("   ✅ BrowserScraper initialized")

        log("   ⏳ Testing search_google_maps...")
        result = await scraper.search_google_maps("hair salon", "Prague")

        if result:
            log(f"   ✅ Result received: {list(result.keys())}")
        else:
            log("   ⚠️  No result (may be normal)")

    except Exception as e:
        log(f"   ❌ Error: {type(e).__name__}: {e}")

    # Test SeleniumScraper import
    log("\n[2] Testing SeleniumScraper import...")
    try:
        from scripts.selenium_scraper import SeleniumScraper

        log("   ✅ SeleniumScraper imported")

        log("   ⏳ Testing SeleniumScraper initialization...")
        scraper = SeleniumScraper(headless=True, use_undetected=True)
        log("   ✅ SeleniumScraper initialized")
        scraper.stop()  # Clean up

    except ImportError as e:
        log(f"   ⚠️  Import error: {e}")
    except Exception as e:
        log(f"   ❌ Error: {type(e).__name__}: {e}")

    log("\n" + "=" * 60)
    log("Test complete! Check scraper_test_results.txt for details.")
    log("=" * 60)


if __name__ == "__main__":
    # Clear previous results
    with open("scraper_test_results.txt", "w", encoding="utf-8") as f:
        f.write("")

    try:
        asyncio.run(main())
    except Exception as e:
        log(f"Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
