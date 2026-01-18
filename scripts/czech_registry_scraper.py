"""
Scraper for Czech business registries (ARES and Obchodní rejstřík).
Finds company owners and legal information from official Czech registries.
"""

import logging
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from models.prospect import BusinessProspect, CompanyOwner

logger = logging.getLogger(__name__)


class CzechRegistryScraper:
    """Scraper for Czech business registries."""

    ARES_BASE_URL = "https://ares.gov.cz"
    OBCHODNI_REJSTRIK_BASE_URL = "https://or.justice.cz"

    def __init__(self):
        """Initialize Czech registry scraper."""
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
        )

    async def search_by_name(self, name: str) -> Optional[BusinessProspect]:
        """
        Search for company by name in ARES registry.

        Args:
            name: Company name to search

        Returns:
            BusinessProspect with registry data or None
        """
        try:
            # ARES search
            search_url = f"{self.ARES_BASE_URL}/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/vyhledat"
            params = {"obchodniJmeno": name, "pocet": 10, "strana": 1}

            response = await self.client.get(search_url, params=params)
            response.raise_for_status()

            data = response.json()

            if not data.get("ekonomickeSubjekty"):
                logger.debug(f"No results found for name: {name}")
                return None

            # Get first result
            company = data["ekonomickeSubjekty"][0]
            return await self._parse_ares_company(company)

        except httpx.HTTPError as e:
            logger.error(f"HTTP error searching ARES by name: {e}")
        except Exception as e:
            logger.error(f"Error searching ARES by name: {e}", exc_info=True)

        return None

    async def search_by_ico(self, ico: str) -> Optional[BusinessProspect]:
        """
        Search for company by IČO (company ID) in ARES registry.

        Args:
            ico: Company IČO (8 digits)

        Returns:
            BusinessProspect with registry data or None
        """
        try:
            # Validate IČO format
            ico_clean = re.sub(r"\D", "", ico)
            if len(ico_clean) != 8:
                logger.warning(f"Invalid IČO format: {ico}")
                return None

            # ARES search by IČO
            search_url = f"{self.ARES_BASE_URL}/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/{ico_clean}"

            response = await self.client.get(search_url)
            response.raise_for_status()

            company = response.json()

            if not company:
                logger.debug(f"No results found for IČO: {ico_clean}")
                return None

            return await self._parse_ares_company(company)

        except httpx.HTTPError as e:
            logger.error(f"HTTP error searching ARES by IČO: {e}")
        except Exception as e:
            logger.error(f"Error searching ARES by IČO: {e}", exc_info=True)

        return None

    async def get_owners_from_rejstrik(self, ico: str) -> list[CompanyOwner]:
        """
        Get company owners from Obchodní rejstřík.

        Args:
            ico: Company IČO

        Returns:
            List of CompanyOwner objects
        """
        owners = []

        try:
            ico_clean = re.sub(r"\D", "", ico)
            if len(ico_clean) != 8:
                return owners

            # Search in Obchodní rejstřík
            search_url = f"{self.OBCHODNI_REJSTRIK_BASE_URL}/ias/ui/rejstrik-$firma"
            params = {"ico": ico_clean}

            response = await self.client.get(search_url, params=params)
            response.raise_for_status()

            # Parse HTML response
            soup = BeautifulSoup(response.text, "html.parser")

            # Find company details section
            # Note: This is a simplified parser - actual structure may vary
            detail_sections = soup.find_all("div", class_="detail")

            for section in detail_sections:
                text = section.get_text(strip=True)

                # Look for statutární orgán (director)
                if "statutární orgán" in text.lower() or "jednatel" in text.lower():
                    # Extract name (simplified - may need refinement)
                    name_match = re.search(r"([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+(?:\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+)+)", text)
                    if name_match:
                        owners.append(
                            CompanyOwner(
                                name=name_match.group(1),
                                role="statutární orgán",
                                ico=ico_clean,
                            )
                        )

                # Look for společníci (partners/owners)
                if "společník" in text.lower() or "vlastník" in text.lower():
                    name_match = re.search(r"([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+(?:\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+)+)", text)
                    if name_match:
                        owners.append(
                            CompanyOwner(
                                name=name_match.group(1),
                                role="společník",
                                ico=ico_clean,
                            )
                        )

        except httpx.HTTPError as e:
            logger.error(f"HTTP error getting owners from rejstřík: {e}")
        except Exception as e:
            logger.error(f"Error getting owners from rejstřík: {e}", exc_info=True)

        return owners

    async def enrich_prospect(
        self, prospect: BusinessProspect
    ) -> BusinessProspect:
        """
        Enrich prospect with registry data.

        Args:
            prospect: BusinessProspect to enrich

        Returns:
            Enriched BusinessProspect
        """
        try:
            # Try to find by name first
            registry_data = None

            if prospect.name:
                registry_data = await self.search_by_name(prospect.name)

            # If found, merge data
            if registry_data:
                prospect.ico = registry_data.ico or prospect.ico
                prospect.legal_name = registry_data.legal_name or prospect.legal_name
                prospect.status = registry_data.status or prospect.status
                prospect.registration_date = (
                    registry_data.registration_date or prospect.registration_date
                )

                # Get owners if we have IČO
                if prospect.ico:
                    owners = await self.get_owners_from_rejstrik(prospect.ico)
                    if owners:
                        prospect.owners = owners

        except Exception as e:
            logger.error(f"Error enriching prospect: {e}", exc_info=True)

        return prospect

    async def _parse_ares_company(self, company: dict) -> BusinessProspect:
        """
        Parse ARES API response to BusinessProspect.

        Args:
            company: Company data from ARES API

        Returns:
            BusinessProspect object
        """
        try:
            ico = company.get("ico")
            legal_name = company.get("obchodniJmeno") or company.get("nazev")
            status = company.get("stav") or company.get("stavSubjektu")

            # Parse registration date if available
            registration_date = None
            if company.get("datumVzniku"):
                try:
                    from datetime import datetime
                    registration_date = datetime.fromisoformat(
                        company["datumVzniku"].replace("Z", "+00:00")
                    )
                except Exception:
                    pass

            prospect = BusinessProspect(
                name=legal_name or "",
                ico=ico,
                legal_name=legal_name,
                status=status,
                registration_date=registration_date,
                source="ares",
            )

            return prospect

        except Exception as e:
            logger.error(f"Error parsing ARES company: {e}", exc_info=True)
            return BusinessProspect(name="", source="ares")

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
