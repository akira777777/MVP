"""Quick test script to verify scraper installations."""

import sys


def test_imports():
    """Test if all scraper packages can be imported."""
    results = {}

    # Test Selenium
    try:
        import selenium

        results["selenium"] = f"✅ {selenium.__version__}"
    except ImportError as e:
        results["selenium"] = f"❌ {e}"

    # Test undetected-chromedriver
    try:
        import undetected_chromedriver as uc

        results["undetected-chromedriver"] = "✅ installed"
    except ImportError as e:
        results["undetected-chromedriver"] = f"❌ {e}"

    # Test Scrapy
    try:
        import scrapy

        results["scrapy"] = f"✅ {scrapy.__version__}"
    except ImportError as e:
        results["scrapy"] = f"❌ {e}"

    # Test requests-html
    try:
        import requests_html

        results["requests-html"] = "✅ installed"
    except ImportError as e:
        results["requests-html"] = f"❌ {e}"

    # Test Playwright
    try:
        import playwright

        results["playwright"] = "✅ installed"
    except ImportError as e:
        results["playwright"] = f"❌ {e}"

    return results


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Browser Scraper Dependencies")
    print("=" * 60)
    print()

    results = test_imports()

    for package, status in results.items():
        print(f"{package:25} {status}")

    print()
    print("=" * 60)

    all_ok = all("✅" in status for status in results.values())

    if all_ok:
        print("✅ All packages are installed and ready to use!")
        sys.exit(0)
    else:
        print("⚠️  Some packages are missing. Run install_scrapers.bat")
        sys.exit(1)
