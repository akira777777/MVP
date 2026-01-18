"""
Script to check if all browser scraper dependencies are installed.
"""

import sys


def check_package(package_name, import_name=None):
    """Check if a package is installed."""
    if import_name is None:
        import_name = package_name

    try:
        __import__(import_name)
        print(f"✅ {package_name} - installed")
        return True
    except ImportError as e:
        print(f"❌ {package_name} - NOT installed: {e}")
        return False


def main():
    """Check all scraper dependencies."""
    print("Checking browser scraper dependencies...\n")

    packages = [
        ("selenium", "selenium"),
        ("undetected-chromedriver", "undetected_chromedriver"),
        ("scrapy", "scrapy"),
        ("requests-html", "requests_html"),
        ("playwright", "playwright"),
        ("beautifulsoup4", "bs4"),
        ("lxml", "lxml"),
    ]

    results = []
    for package_name, import_name in packages:
        result = check_package(package_name, import_name)
        results.append(result)

    print("\n" + "=" * 50)
    installed_count = sum(results)
    total_count = len(results)

    if installed_count == total_count:
        print(f"✅ All {total_count} packages are installed!")
        return 0
    else:
        print(f"⚠️  {installed_count}/{total_count} packages installed")
        print("\nTo install missing packages, run:")
        print("python -m pip install -r requirements.txt")
        print("\nOr install individually:")
        missing = [pkg[0] for pkg, result in zip(packages, results) if not result]
        for pkg in missing:
            print(f"  python -m pip install {pkg}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
