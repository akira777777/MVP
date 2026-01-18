"""
ARES (Administrativní registr ekonomických subjektů) client.
Official Czech business registry: https://ares.gov.cz
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
import httpx

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

# ARES API endpoints
_ARES_BASE_URL = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty"
_ARES_DETAIL_URL = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/{ico}"


class ARESClient:
    """Client for ARES (Czech business registry) API."""

    def __init__(self):
        """Initialize ARES client."""
        self.client = httpx.AsyncClient(timeout=_API_TIMEOUT, follow_redirects=True)

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def search_by_name(
        self, company_name: str, max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for companies by name in ARES.

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

        params = {
            "obchodniJmeno": company_name.strip(),
            "pocet": max_results,
            "stranka": 1,
        }

        delay = _RETRY_DELAY

        for attempt in range(_MAX_RETRIES):
            try:
                response = await self.client.get(_ARES_BASE_URL, params=params)
                response.raise_for_status()

                data = response.json()

                if isinstance(data, dict) and "ekonomickeSubjekty" in data:
                    return data["ekonomickeSubjekty"]

                return []

            except httpx.HTTPStatusError as e:
                if attempt < _MAX_RETRIES - 1:
                    logger.warning(
                        f"HTTP error (attempt {attempt + 1}/{_MAX_RETRIES}): {e}. Retrying..."
                    )
                    await asyncio.sleep(delay)
                    delay *= _RETRY_BACKOFF
                else:
                    logger.error(f"HTTP error searching ARES: {e}", exc_info=True)
                    return []

            except httpx.RequestError as e:
                if attempt < _MAX_RETRIES - 1:
                    logger.warning(
                        f"Request error (attempt {attempt + 1}/{_MAX_RETRIES}): {e}. Retrying..."
                    )
                    await asyncio.sleep(delay)
                    delay *= _RETRY_BACKOFF
                else:
                    logger.error(f"Request error searching ARES: {e}", exc_info=True)
                    return []

            except Exception as e:
                logger.error(f"Error searching ARES: {e}", exc_info=True)
                return []

        return []

    async def search_by_ico(self, ico: str) -> Optional[Dict[str, Any]]:
        """
        Get company details by IČO.

        Args:
            ico: IČO (8-digit company ID)

        Returns:
            Company data dictionary or None if not found

        Raises:
            ValueError: If IČO is invalid
        """
        if not ico or not ico.isdigit() or len(ico) != 8:
            raise ValueError("IČO must be 8 digits")

        url = _ARES_DETAIL_URL.format(ico=ico)

        delay = _RETRY_DELAY

        for attempt in range(_MAX_RETRIES):
            try:
                response = await self.client.get(url)
                response.raise_for_status()

                data = response.json()

                if isinstance(data, dict) and data.get("ico"):
                    return data

                return None

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.debug(f"Company with IČO {ico} not found in ARES")
                    return None

                if attempt < _MAX_RETRIES - 1:
                    logger.warning(
                        f"HTTP error (attempt {attempt + 1}/{_MAX_RETRIES}): {e}. Retrying..."
                    )
                    await asyncio.sleep(delay)
                    delay *= _RETRY_BACKOFF
                else:
                    logger.error(f"HTTP error getting ARES details: {e}", exc_info=True)
                    return None

            except httpx.RequestError as e:
                if attempt < _MAX_RETRIES - 1:
                    logger.warning(
                        f"Request error (attempt {attempt + 1}/{_MAX_RETRIES}): {e}. Retrying..."
                    )
                    await asyncio.sleep(delay)
                    delay *= _RETRY_BACKOFF
                else:
                    logger.error(f"Request error getting ARES details: {e}", exc_info=True)
                    return None

            except Exception as e:
                logger.error(f"Error getting ARES details: {e}", exc_info=True)
                return None

        return None

    async def search_by_address(self, address: str) -> List[Dict[str, Any]]:
        """
        Search for companies by address.

        Args:
            address: Address to search for

        Returns:
            List of company data dictionaries
        """
        if not address or not address.strip():
            raise ValueError("Address cannot be empty")

        # ARES API supports address search via 'sidlo' parameter
        params = {
            "sidlo": address.strip(),
            "pocet": 10,
            "stranka": 1,
        }

        delay = _RETRY_DELAY

        for attempt in range(_MAX_RETRIES):
            try:
                response = await self.client.get(_ARES_BASE_URL, params=params)
                response.raise_for_status()

                data = response.json()

                if isinstance(data, dict) and "ekonomickeSubjekty" in data:
                    return data["ekonomickeSubjekty"]

                return []

            except httpx.HTTPStatusError as e:
                if attempt < _MAX_RETRIES - 1:
                    logger.warning(
                        f"HTTP error (attempt {attempt + 1}/{_MAX_RETRIES}): {e}. Retrying..."
                    )
                    await asyncio.sleep(delay)
                    delay *= _RETRY_BACKOFF
                else:
                    logger.error(f"HTTP error searching ARES by address: {e}", exc_info=True)
                    return []

            except httpx.RequestError as e:
                if attempt < _MAX_RETRIES - 1:
                    logger.warning(
                        f"Request error (attempt {attempt + 1}/{_MAX_RETRIES}): {e}. Retrying..."
                    )
                    await asyncio.sleep(delay)
                    delay *= _RETRY_BACKOFF
                else:
                    logger.error(f"Request error searching ARES by address: {e}", exc_info=True)
                    return []

        return []

    def parse_company_data(self, data: Dict[str, Any]) -> CompanyInfo:
        """
        Parse ARES API response into CompanyInfo model.

        Args:
            data: Raw ARES API response

        Returns:
            CompanyInfo object
        """
        # Extract address components
        address_parts = []
        if data.get("sidlo", {}).get("ulice"):
            address_parts.append(data["sidlo"]["ulice"])
        if data.get("sidlo", {}).get("cisloPopisne"):
            address_parts.append(data["sidlo"]["cisloPopisne"])
        if data.get("sidlo", {}).get("mesto"):
            address_parts.append(data["sidlo"]["mesto"])
        if data.get("sidlo", {}).get("psc"):
            address_parts.append(data["sidlo"]["psc"])

        address = ", ".join(address_parts) if address_parts else None

        # Parse registration date
        registration_date = None
        if data.get("datumVzniku"):
            try:
                registration_date = datetime.fromisoformat(
                    data["datumVzniku"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        return CompanyInfo(
            ico=str(data.get("ico", "")),
            name=data.get("obchodniJmeno", ""),
            address=address,
            legal_form=data.get("pravniForma", {}).get("nazev") if data.get("pravniForma") else None,
            status=data.get("stav"),
            registration_date=registration_date,
            source="ARES",
        )
