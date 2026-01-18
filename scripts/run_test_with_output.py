"""
Run test scrapers and save output to file.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Output file
OUTPUT_FILE = Path("scraper_test_output.txt")


def log(message, to_console=True):
    """Log message to file and optionally console."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{timestamp}] {message}"

    if to_console:
        print(msg)
        sys.stdout.flush()

    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
        f.flush()


async def test_browser_scraper():
    """Test BrowserScraper."""
    log("\n" + "=" * 60)
    log("Test 1: BrowserScraper")
    log("=" * 60)

    try:
        from scripts.browser_scraper import BrowserScraper

        scraper = BrowserScraper()
        log("\nSearching Google Maps for 'hair salon' in 'Prague'...")

        result = await scraper.search_google_maps("hair salon", "Prague")

        if result:
            log("\n✅ Success!")
            log(f"   Name: {result.get('business_name', result.get('name', 'N/A'))}")
            log(f"   Address: {result.get('address', 'N/A')}")
            log(f"   Phone: {result.get('phone', 'N/A')}")
            log(f"   Website: {result.get('website', 'N/A')}")
            return True
        else:
            log("\n⚠️  No result (may be normal if browser not available)")
            return False
    except Exception as e:
        log(f"\n❌ Error: {e}")
        import traceback

        log(traceback.format_exc())
        return False


def test_selenium_scraper():
    """Test SeleniumScraper."""
    log("\n" + "=" * 60)
    log("Test 2: SeleniumScraper")
    log("=" * 60)

    try:
        from scripts.selenium_scraper import SeleniumScraper

        log("\nStarting browser (this may take a moment)...")

        with SeleniumScraper(headless=True, use_undetected=True) as scraper:
            log("Browser started!")
            log("\nSearching Google Maps for 'hair salon' in 'Prague'...")

            result = scraper.search_google_maps("hair salon", "Prague")

            if result:
                log("\n✅ Success!")
                log(f"   Name: {result.get('name', 'N/A')}")
                log(f"   Address: {result.get('address', 'N/A')}")
                log(f"   Phone: {result.get('phone', 'N/A')}")
                log(f"   Website: {result.get('website', 'N/A')}")
                return True
            else:
                log("\n⚠️  No result")
                return False

    except ImportError:
        log("\n⚠️  Selenium not installed")
        log("   Install with: python -m pip install selenium undetected-chromedriver")
        return False
    except Exception as e:
        log(f"\n❌ Error: {e}")
        import traceback

        log(traceback.format_exc())
        return False


async def main():
    """Run all tests."""
    # Clear output file
    OUTPUT_FILE.write_text("")

    log("=" * 60)
    log("Browser Scrapers Test Example")
    log("=" * 60)
    log("\nThis will test BrowserScraper and SeleniumScraper")
    log("Note: Tests may take 10-30 seconds each")
    log(f"\nOutput will be saved to: {OUTPUT_FILE}")

    results = {}

    # Test BrowserScraper
    try:
        results["BrowserScraper"] = await test_browser_scraper()
    except Exception as e:
        log(f"\n❌ BrowserScraper test crashed: {e}")
        results["BrowserScraper"] = False

    # Test SeleniumScraper
    try:
        results["SeleniumScraper"] = test_selenium_scraper()
    except Exception as e:
        log(f"\n❌ SeleniumScraper test crashed: {e}")
        results["SeleniumScraper"] = False

    # Summary
    log("\n" + "=" * 60)
    log("Test Summary")
    log("=" * 60)

    for name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        log(f"{name:25} {status}")

    passed = sum(results.values())
    total = len(results)
    log(f"\nTotal: {passed}/{total} tests passed")

    log("\n" + "=" * 60)
    log("Tests complete!")
    log("=" * 60)
    log(f"\nCheck {OUTPUT_FILE} for full output")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("\n\n⚠️  Tests interrupted")
    except Exception as e:
        log(f"\n❌ Fatal error: {e}")
        import traceback

        log(traceback.format_exc())
        sys.exit(1)
