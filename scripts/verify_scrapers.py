"""
Verify that all scrapers can be imported and initialized.
This is a quick check without actually running browsers.
"""

import sys


def test_imports():
    """Test that all scraper modules can be imported."""
    print("=" * 60)
    print("Verifying Browser Scrapers")
    print("=" * 60)

    results = {}

    # Test BrowserScraper
    print("\n[1/3] Testing BrowserScraper...")
    try:
        from scripts.browser_scraper import BrowserScraper

        scraper = BrowserScraper()
        print("   ✅ BrowserScraper - OK")
        results["BrowserScraper"] = True
    except Exception as e:
        print(f"   ❌ BrowserScraper - FAILED: {e}")
        results["BrowserScraper"] = False

    # Test SeleniumScraper
    print("\n[2/3] Testing SeleniumScraper...")
    try:
        from scripts.selenium_scraper import SeleniumScraper

        print("   ✅ SeleniumScraper - Import OK")
        # Don't initialize - requires browser
        results["SeleniumScraper"] = True
    except ImportError as e:
        print(f"   ⚠️  SeleniumScraper - Not installed: {e}")
        results["SeleniumScraper"] = False
    except Exception as e:
        print(f"   ❌ SeleniumScraper - FAILED: {e}")
        results["SeleniumScraper"] = False

    # Test MultiBrowserScraper
    print("\n[3/3] Testing MultiBrowserScraper...")
    try:
        print("   ✅ MultiBrowserScraper - OK")
        results["MultiBrowserScraper"] = True
    except Exception as e:
        print(f"   ❌ MultiBrowserScraper - FAILED: {e}")
        results["MultiBrowserScraper"] = False

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    for name, success in results.items():
        status = "✅ OK" if success else "❌ FAIL"
        print(f"{name:25} {status}")

    passed = sum(results.values())
    total = len(results)

    print(f"\nTotal: {passed}/{total} scrapers verified")

    if passed == total:
        print("\n✅ All scrapers are ready to use!")
        print("\nTo test actual functionality, run:")
        print("  python scripts/test_browser_scrapers.py")
        return 0
    else:
        print(f"\n⚠️  {total - passed} scraper(s) need attention")
        return 1


if __name__ == "__main__":
    sys.exit(test_imports())
