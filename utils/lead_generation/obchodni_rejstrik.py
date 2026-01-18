"""
Obchodní rejstřík (Trade Registry) client.
Official Czech trade registry: https://or.justice.cz
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
import re

from utils.logging_config import setup_logging
from utils.lead_generation.models import CompanyInfo, OwnerInfo

logger = setup_logging(
    name=__name__, log_level="INFO", log_file="lead_generation.log", log_dir="logs"
)

# Retry configuration
_MAX_RETRIES = 3
_RETRY_DELAY = 1.0  # seconds
_RETRY_BACKOFF = 2.0  # exponential backoff multiplier
_API_TIMEOUT = 30.0  # seconds

# Obchodní rejstřík endpoints
_OR_SEARCH_URL = "https://or.justice.cz/ias/ui/rejstrik"
_OR_DETAIL_URL = "https://or.justice.cz/ias/ui/rejstrik-$firma"


class ObchodniRejstrikClient:
    """Client for Obchodní rejstřík (Czech Trade Registry) web scraping."""

    def __init__(self):
        """Initialize Obchodní rejstřík client."""
        self.client = httpx.AsyncClient(
            timeout=_API_TIMEOUT,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
        )

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def search_by_name(
        self, company_name: str, max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for companies by name in Obchodní rejstřík.

        Note: This uses web scraping as the registry doesn't have a public API.
        Be respectful with rate limiting.

        Args:
            company_name: Company name to search for
            max_results: Maximum number of results

        Returns:
            List of company data dictionaries

        Raises:
            ValueError: If company_name is empty
        """
        if not company_name or not company_name.strip():
            raise ValueError("Company name cannot be empty")

        # Search form parameters
        params = {
            "nazev": company_name.strip(),
            "typ": "subjekt",
        }

        delay = _RETRY_DELAY

        for attempt in range(_MAX_RETRIES):
            try:
                response = await self.client.post(_OR_SEARCH_URL, data=params)
                response.raise_for_status()

                # Parse HTML response
                soup = BeautifulSoup(response.text, "html.parser")

                # Extract company links and basic info
                companies = []
                results_table = soup.find("table", class_="result")

                if results_table:
                    rows = results_table.find_all("tr")[1:]  # Skip header
                    for row in rows[:max_results]:
                        cells = row.find_all("td")
                        if len(cells) >= 2:
                            name_cell = cells[0]
                            ico_cell = cells[1]

                            name_link = name_cell.find("a")
                            if name_link:
                                company_name_found = name_link.get_text(strip=True)
                                detail_url = name_link.get("href", "")
                                ico = ico_cell.get_text(strip=True)

                                if company_name_found and ico:
                                    companies.append(
                                        {
                                            "name": company_name_found,
                                            "ico": ico,
                                            "detail_url": detail_url,
                                        }
                                    )

                return companies

            except httpx.HTTPStatusError as e:
                if attempt < _MAX_RETRIES - 1:
                    logger.warning(
                        f"HTTP error (attempt {attempt + 1}/{_MAX_RETRIES}): {e}. Retrying..."
                    )
                    await asyncio.sleep(delay)
                    delay *= _RETRY_BACKOFF
                else:
                    logger.error(
                        f"HTTP error searching Obchodní rejstřík: {e}", exc_info=True
                    )
                    return []

            except httpx.RequestError as e:
                if attempt < _MAX_RETRIES - 1:
                    logger.warning(
                        f"Request error (attempt {attempt + 1}/{_MAX_RETRIES}): {e}. Retrying..."
                    )
                    await asyncio.sleep(delay)
                    delay *= _RETRY_BACKOFF
                else:
                    logger.error(
                        f"Request error searching Obchodní rejstřík: {e}", exc_info=True
                    )
                    return []

            except Exception as e:
                logger.error(f"Error searching Obchodní rejstřík: {e}", exc_info=True)
                return []

        return []

    async def get_company_details(self, ico: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed company information including owners.

        Args:
            ico: IČO (8-digit company ID)

        Returns:
            Company details dictionary with owners or None if not found

        Raises:
            ValueError: If IČO is invalid
        """
        if not ico or not ico.isdigit() or len(ico) != 8:
            raise ValueError("IČO must be 8 digits")

        # Build detail URL
        url = f"{_OR_DETAIL_URL.replace('$firma', ico)}"

        delay = _RETRY_DELAY

        for attempt in range(_MAX_RETRIES):
            try:
                response = await self.client.get(url)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")

                # Extract company information
                company_data = {"ico": ico, "owners": []}

                # Find company name
                name_elem = soup.find("h1") or soup.find("div", class_="nazev")
                if name_elem:
                    company_data["name"] = name_elem.get_text(strip=True)

                # Find address
                address_elem = soup.find("div", class_="sidlo") or soup.find(
                    "span", string=re.compile("Sídlo")
                )
                if address_elem:
                    # Try to find address in next sibling or parent
                    address_text = address_elem.get_text(strip=True)
                    if "Sídlo" in address_text:
                        # Extract address after "Sídlo:"
                        address_match = re.search(r"Sídlo:\s*(.+)", address_text)
                        if address_match:
                            company_data["address"] = address_match.group(1).strip()

                # Find statutární orgán (director)
                statutarni_section = soup.find(
                    "div", string=re.compile("Statutární orgán", re.I)
                ) or soup.find("h3", string=re.compile("Statutární orgán", re.I))

                if statutarni_section:
                    # Find parent container
                    container = statutarni_section.find_parent("div") or statutarni_section.find_next_sibling("div")
                    if container:
                        # Extract names
                        name_elements = container.find_all("strong") or container.find_all("span", class_="jmeno")
                        for elem in name_elements:
                            name = elem.get_text(strip=True)
                            if name:
                                company_data["owners"].append(
                                    {
                                        "name": name,
                                        "role": "Statutární orgán",
                                    }
                                )

                # Find společníci (partners/owners)
                spolecnici_section = soup.find(
                    "div", string=re.compile("Společníci", re.I)
                ) or soup.find("h3", string=re.compile("Společníci", re.I))

                if spolecnici_section:
                    container = spolecnici_section.find_parent("div") or spolecnici_section.find_next_sibling("div")
                    if container:
                        name_elements = container.find_all("strong") or container.find_all("span", class_="jmeno")
                        for elem in name_elements:
                            name = elem.get_text(strip=True)
                            if name:
                                company_data["owners"].append(
                                    {
                                        "name": name,
                                        "role": "Společník",
                                    }
                                )

                return company_data if company_data.get("name") else None

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.debug(f"Company with IČO {ico} not found in Obchodní rejstřík")
                    return None

                if attempt < _MAX_RETRIES - 1:
                    logger.warning(
                        f"HTTP error (attempt {attempt + 1}/{_MAX_RETRIES}): {e}. Retrying..."
                    )
                    await asyncio.sleep(delay)
                    delay *= _RETRY_BACKOFF
                else:
                    logger.error(
                        f"HTTP error getting Obchodní rejstřík details: {e}", exc_info=True
                    )
                    return None

            except httpx.RequestError as e:
                if attempt < _MAX_RETRIES - 1:
                    logger.warning(
                        f"Request error (attempt {attempt + 1}/{_MAX_RETRIES}): {e}. Retrying..."
                    )
                    await asyncio.sleep(delay)
                    delay *= _RETRY_BACKOFF
                else:
                    logger.error(
                        f"Request error getting Obchodní rejstřík details: {e}", exc_info=True
                    )
                    return None

            except Exception as e:
                logger.error(f"Error getting Obchodní rejstřík details: {e}", exc_info=True)
                return None

        return None

    def parse_company_data(self, data: Dict[str, Any]) -> CompanyInfo:
        """
        Parse Obchodní rejstřík data into CompanyInfo model.

        Args:
            data: Raw data from web scraping

        Returns:
            CompanyInfo object
        """
        return CompanyInfo(
            ico=str(data.get("ico", "")),
            name=data.get("name", ""),
            address=data.get("address"),
            source="Obchodní rejstřík",
        )

    def parse_owners(self, data: Dict[str, Any]) -> List[OwnerInfo]:
        """
        Parse owners from Obchodní rejstřík data.

        Args:
            data: Raw data containing owners list

        Returns:
            List of OwnerInfo objects
        """
        owners = []
        for owner_data in data.get("owners", []):
            owners.append(
                OwnerInfo(
                    name=owner_data.get("name", ""),
                    role=owner_data.get("role"),
                )
            )
        return owners
