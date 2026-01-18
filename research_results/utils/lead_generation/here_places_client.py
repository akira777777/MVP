"""
HERE Technologies Places API client for business data collection.

Alternative to Google Maps API with good coverage in Europe.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

try:
    from herepy import GeocoderApi, PlacesApi

    HERE_AVAILABLE = True
except ImportError:
    HERE_AVAILABLE = False

from .config import ScraperConfig
from .models import BusinessData

logger = logging.getLogger(__name__)


class HerePlacesClient:
    """
    Client for HERE Technologies Places API.

    Provides alternative to Google Maps API with good European coverage.
    """

    def __init__(
        self, config: Optional[ScraperConfig] = None, api_key: Optional[str] = None
    ):
        """
        Initialize HERE Places client.

        Args:
            config: Scraper configuration
            api_key: HERE API key (if not provided, tries to load from config)
        """
        if not HERE_AVAILABLE:
            raise ImportError(
                "herepy is not installed. Install it with: pip install herepy"
            )

        self.config = config or ScraperConfig()
        self.api_key = api_key or getattr(self.config, "here_api_key", None)

        if not self.api_key:
            # Try to load from environment
            import os

            self.api_key = os.getenv("HERE_API_KEY")

        if not self.api_key:
            raise ValueError(
                "HERE API key is required. Set HERE_API_KEY environment variable "
                "or provide api_key parameter."
            )

        self.places_api = PlacesApi(self.api_key)
        self.geocoder_api = GeocoderApi(self.api_key)
        logger.info("HERE Places client initialized")

    def search_businesses(
        self,
        query: str,
        location: Optional[Dict[str, float]] = None,
        max_results: int = 20,
        category: Optional[str] = None,
    ) -> List[BusinessData]:
        """
        Search for businesses using HERE Places API.

        Args:
            query: Search query (e.g., "kavárna")
            location: Dictionary with 'latitude' and 'longitude' (defaults to Prague center)
            max_results: Maximum number of results to return
            category: Business category for tagging

        Returns:
            List of BusinessData objects
        """
        if not location:
            # Default to Prague center
            location = {"latitude": 50.0755, "longitude": 14.4378}

        try:
            # HERE API uses "at" parameter as "lat,lon"
            at_coords = f"{location['latitude']},{location['longitude']}"

            # Search places
            response = self.places_api.search(
                query=query,
                at=at_coords,
                limit=min(max_results, 100),  # HERE API max is 100
            )

            if not response or not hasattr(response, "as_dict"):
                logger.warning(f"No response from HERE API for query: {query}")
                return []

            response_dict = response.as_dict()
            items = response_dict.get("items", [])

            businesses = []
            for item in items[:max_results]:
                try:
                    business = self._parse_here_item(item, category or query)
                    if business:
                        businesses.append(business)
                except Exception as e:
                    logger.debug(f"Error parsing HERE item: {e}")
                    continue

            logger.info(
                f"Found {len(businesses)} businesses via HERE API for query: {query}"
            )
            return businesses

        except Exception as e:
            logger.error(f"Error searching HERE Places API: {e}", exc_info=True)
            return []

    def _parse_here_item(
        self, item: Dict[str, Any], category: str
    ) -> Optional[BusinessData]:
        """
        Parse HERE API response item into BusinessData.

        Args:
            item: HERE API response item
            category: Business category

        Returns:
            BusinessData object or None
        """
        try:
            # Extract basic information
            title = item.get("title", "").strip()
            if not title:
                return None

            # Extract address
            address_info = item.get("address", {})
            address_parts = []

            if address_info.get("street"):
                address_parts.append(address_info["street"])
            if address_info.get("houseNumber"):
                address_parts.append(address_info["houseNumber"])

            address = (
                ", ".join(address_parts)
                if address_parts
                else address_info.get("label", "")
            )

            # Extract city and district
            city = address_info.get("city", "Prague")
            district = None
            postal_code = address_info.get("postalCode")

            # Try to extract Prague district
            if "Praha" in city or "Prague" in city:
                # Check if district is in address
                for i in range(1, 11):
                    if f"Praha {i}" in address or f"Prague {i}" in address:
                        district = f"Prague {i}"
                        break

            # Extract coordinates
            position = item.get("position", {})
            latitude = (
                Decimal(str(position.get("lat", 0))) if position.get("lat") else None
            )
            longitude = (
                Decimal(str(position.get("lng", 0))) if position.get("lng") else None
            )

            # Extract contact information
            contacts = item.get("contacts", [])
            phone = None
            website = None

            for contact in contacts:
                if contact.get("phone"):
                    phone_list = contact.get("phone", [])
                    if phone_list:
                        phone = phone_list[0].get("value")
                if contact.get("www"):
                    www_list = contact.get("www", [])
                    if www_list:
                        website = www_list[0].get("value")

            # Extract rating (if available)
            rating = None
            if "averageRating" in item:
                rating = Decimal(str(item["averageRating"]))

            # Create business data
            business = BusinessData(
                name=title,
                address=address or "Unknown",
                city=city or "Prague",
                district=district,
                postal_code=postal_code,
                latitude=latitude,
                longitude=longitude,
                phone=phone,
                website=website,
                category=category,
                rating=rating,
                review_count=item.get("userRatingsTotal"),
            )

            return business

        except Exception as e:
            logger.debug(f"Error parsing HERE item: {e}")
            return None

    def geocode_address(self, address: str) -> Optional[Dict[str, float]]:
        """
        Geocode an address to get coordinates.

        Args:
            address: Address string

        Returns:
            Dictionary with 'latitude' and 'longitude' or None
        """
        try:
            response = self.geocoder_api.free_form(address)
            if response and hasattr(response, "as_dict"):
                response_dict = response.as_dict()
                items = response_dict.get("items", [])
                if items:
                    position = items[0].get("position", {})
                    return {
                        "latitude": position.get("lat"),
                        "longitude": position.get("lng"),
                    }
        except Exception as e:
            logger.debug(f"Error geocoding address {address}: {e}")
        return None
