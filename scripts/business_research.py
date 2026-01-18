"""
Business research script for finding business owners in Czech Republic.
Helps automate the process of finding company owners via Google Maps → ARES/Obchodní rejstřík.

Usage:
    python scripts/business_research.py --category "beauty salon" --location "Prague"
    python scripts/business_research.py --csv input.csv --output results.json
"""

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class BusinessInfo:
    """Business information from Google Maps."""

    name: str
    address: str
    phone: Optional[str] = None
    website: Optional[str] = None
    google_maps_url: Optional[str] = None
    category: Optional[str] = None


@dataclass
class CompanyRegistryInfo:
    """Company information from ARES/Obchodní rejstřík."""

    ico: Optional[str] = None  # IČO - Company ID
    name: Optional[str] = None
    address: Optional[str] = None
    director: Optional[str] = None  # Statutární orgán
    owners: Optional[List[str]] = None  # Společníci
    registry_url: Optional[str] = None


@dataclass
class ResearchResult:
    """Complete research result combining business and registry info."""

    business: BusinessInfo
    registry: Optional[CompanyRegistryInfo] = None
    found: bool = False
    research_date: str = datetime.now().isoformat()
    notes: Optional[str] = None


class BusinessResearchTool:
    """Tool for researching businesses in Czech Republic."""

    ARES_URL = "https://ares.gov.cz"
    OBCHODNI_REJSTRIK_URL = "https://or.justice.cz"

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize research tool.

        Args:
            output_dir: Directory to save results (default: ./research_results)
        """
        self.output_dir = output_dir or Path(__file__).parent.parent / "research_results"
        self.output_dir.mkdir(exist_ok=True)

    def generate_ares_search_url(self, business: BusinessInfo) -> str:
        """
        Generate ARES search URL for a business.

        Args:
            business: Business information

        Returns:
            ARES search URL
        """
        # ARES allows searching by name, address, or IČO
        # This is a template - actual search requires manual interaction or API
        search_params = []
        if business.name:
            search_params.append(f"name={business.name}")
        if business.address:
            search_params.append(f"address={business.address}")

        # Note: ARES doesn't have a simple URL-based search API
        # This would require web scraping or official API access
        return f"{self.ARES_URL}/ekonomicke-subjekty-v-cr/"

    def generate_registry_search_url(self, business: BusinessInfo) -> str:
        """
        Generate Obchodní rejstřík search URL.

        Args:
            business: Business information

        Returns:
            Registry search URL
        """
        return f"{self.OBCHODNI_REJSTRIK_URL}/ias/ui/vyhledavani"

    async def search_registry(
        self, business: BusinessInfo
    ) -> Optional[CompanyRegistryInfo]:
        """
        Search ARES/Obchodní rejstřík for company information.

        Note: This is a placeholder. Real implementation would require:
        - Web scraping (with proper rate limiting and ToS compliance)
        - Official API access (if available)
        - Manual verification

        Args:
            business: Business information to search

        Returns:
            Company registry information if found
        """
        # TODO: Implement actual search logic
        # This could use:
        # - requests/httpx for HTTP requests
        # - BeautifulSoup for HTML parsing
        # - Selenium/Playwright for JavaScript-heavy sites
        # - Official APIs if available

        print(f"🔍 Searching registry for: {business.name}")
        print(f"   Address: {business.address}")
        print(f"   ARES URL: {self.generate_ares_search_url(business)}")
        print(f"   Registry URL: {self.generate_registry_search_url(business)}")
        print("   ⚠️  Manual search required - see BUSINESS_RESEARCH_PRAGUE.md")

        return None

    def parse_business_from_csv(self, csv_path: Path) -> List[BusinessInfo]:
        """
        Parse business information from CSV file.

        Expected CSV format:
        name,address,phone,website,category
        "Salon Beauty","Prague 1, Wenceslas Square 1","+420123456789","https://example.com","beauty"

        Args:
            csv_path: Path to CSV file

        Returns:
            List of BusinessInfo objects
        """
        import csv

        businesses = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                business = BusinessInfo(
                    name=row.get("name", "").strip(),
                    address=row.get("address", "").strip(),
                    phone=row.get("phone", "").strip() or None,
                    website=row.get("website", "").strip() or None,
                    category=row.get("category", "").strip() or None,
                )
                if business.name and business.address:
                    businesses.append(business)

        return businesses

    async def research_business(self, business: BusinessInfo) -> ResearchResult:
        """
        Research a single business.

        Args:
            business: Business information

        Returns:
            Research result with registry information
        """
        registry_info = await self.search_registry(business)

        result = ResearchResult(
            business=business,
            registry=registry_info,
            found=registry_info is not None,
        )

        return result

    async def research_multiple(
        self, businesses: List[BusinessInfo]
    ) -> List[ResearchResult]:
        """
        Research multiple businesses.

        Args:
            businesses: List of business information

        Returns:
            List of research results
        """
        results = []
        for i, business in enumerate(businesses, 1):
            print(f"\n[{i}/{len(businesses)}] Processing: {business.name}")
            result = await self.research_business(business)
            results.append(result)

            # Rate limiting - be respectful
            if i < len(businesses):
                await asyncio.sleep(1)

        return results

    def save_results(
        self, results: List[ResearchResult], output_file: Optional[Path] = None
    ):
        """
        Save research results to JSON file.

        Args:
            results: List of research results
            output_file: Output file path (default: research_results_YYYYMMDD_HHMMSS.json)
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f"research_results_{timestamp}.json"

        # Convert to dict for JSON serialization
        results_dict = [asdict(result) for result in results]

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results_dict, f, ensure_ascii=False, indent=2)

        print(f"\n✅ Results saved to: {output_file}")

    def generate_cold_email_template(
        self, result: ResearchResult, language: str = "cs"
    ) -> str:
        """
        Generate cold email template for a business owner.

        Args:
            result: Research result with business and owner info
            language: Language code ('cs' for Czech, 'en' for English)

        Returns:
            Email template text
        """
        owner_name = "Vážený pane/paní"
        if result.registry and result.registry.director:
            owner_name = result.registry.director

        if language == "cs":
            template = f"""Dobrý den, {owner_name},

Viděl jsem, že {result.business.name} nabízí služby v oblasti {result.business.category or 'vašeho oboru'}.
Pracuji na automatizaci pro malé firmy v Praze — pomáhám s rezervacemi, chatboty a integracemi s Google Maps/WhatsApp.

Mohli bychom si domluvit krátkou 15minutovou demo?
Ukážu vám, jak by to mohlo fungovat pro váš business.

S pozdravem,
[Vaše jméno]
"""
        else:  # English
            template = f"""Hello {owner_name},

I noticed that {result.business.name} offers services in {result.business.category or 'your industry'}.
I work on automation solutions for small businesses in Prague — helping with bookings, chatbots, and integrations with Google Maps/WhatsApp.

Could we schedule a quick 15-minute demo?
I'll show you how it could work for your business.

Best regards,
[Your name]
"""

        return template


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Research businesses in Czech Republic via ARES/Obchodní rejstřík"
    )
    parser.add_argument(
        "--csv",
        type=Path,
        help="Input CSV file with business information",
    )
    parser.add_argument(
        "--category",
        type=str,
        help="Business category to search (e.g., 'beauty salon', 'cafe')",
    )
    parser.add_argument(
        "--location",
        type=str,
        default="Prague",
        help="Location to search (default: Prague)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON file path",
    )
    parser.add_argument(
        "--email-template",
        action="store_true",
        help="Generate cold email templates",
    )
    parser.add_argument(
        "--language",
        choices=["cs", "en"],
        default="cs",
        help="Language for email templates (default: cs)",
    )

    args = parser.parse_args()

    tool = BusinessResearchTool()

    businesses: List[BusinessInfo] = []

    if args.csv:
        print(f"📄 Reading businesses from CSV: {args.csv}")
        businesses = tool.parse_business_from_csv(args.csv)
        print(f"✅ Found {len(businesses)} businesses in CSV")
    elif args.category:
        print(f"🔍 Category search not yet implemented")
        print(f"   Please use --csv option with manually collected data from Google Maps")
        print(f"   See BUSINESS_RESEARCH_PRAGUE.md for manual collection process")
        sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    if not businesses:
        print("❌ No businesses to research")
        sys.exit(1)

    # Research businesses
    print(f"\n🚀 Starting research for {len(businesses)} businesses...")
    results = await tool.research_multiple(businesses)

    # Save results
    tool.save_results(results, args.output)

    # Generate email templates if requested
    if args.email_template:
        email_dir = tool.output_dir / "email_templates"
        email_dir.mkdir(exist_ok=True)

        for i, result in enumerate(results, 1):
            if result.registry and result.registry.director:
                email_text = tool.generate_cold_email_template(result, args.language)
                email_file = email_dir / f"email_{i}_{result.business.name.replace(' ', '_')}.txt"
                with open(email_file, "w", encoding="utf-8") as f:
                    f.write(email_text)
                print(f"📧 Generated email template: {email_file}")

    # Summary
    found_count = sum(1 for r in results if r.found)
    print(f"\n📊 Summary:")
    print(f"   Total businesses: {len(results)}")
    print(f"   Found in registry: {found_count}")
    print(f"   Not found: {len(results) - found_count}")


if __name__ == "__main__":
    asyncio.run(main())
