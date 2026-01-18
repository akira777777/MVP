"""
Unified Google Maps client wrapper for business lead generation scripts.

Provides a consistent interface that combines API client, MCP client, and scraper functionality.
"""

import logging
from typing import Any, Dict, List, Optional

from .config import ScraperConfig
from .google_maps_api_client import GoogleMapsAPIClient
from .mcp_google_maps import MCPGoogleMapsClient

logger = logging.getLogger(__name__)


class GoogleMapsClient:
    """
    Unified Google Maps client for business lead generation.
    
    Combines API client, MCP client, and provides methods needed by lead generation scripts.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        browser_scraper: Optional[Any] = None,
        config: Optional[ScraperConfig] = None,
    ):
        """
        Initialize Google Maps client.

        Args:
            api_key: Google Maps API key (optional, uses config if not provided)
            browser_scraper: Optional browser scraper for fallback (not used currently)
            config: Optional ScraperConfig (creates new one if not provided)
        """
        # Create config with API key if provided
        if config is None:
            config = ScraperConfig()
            if api_key:
                config.api_key = api_key

        self.config = config
        self.browser_scraper = browser_scraper

        # Try MCP client first, fallback to API client
        self._mcp_client = MCPGoogleMapsClient(config)
        self._api_client = GoogleMapsAPIClient(config)

        # Use API client as primary (MCP is not fully implemented yet)
        self._primary_client = self._api_client

    async def search_businesses(
        self,
        query: str,
        location: str = "Prague, Czech Republic",
        max_results: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Search for businesses and return raw place data dictionaries.

        Args:
            query: Search query (e.g., "kadeřnictví")
            location: Location string (e.g., "Prague, Czech Republic")
            max_results: Maximum number of results

        Returns:
            List of place data dictionaries
        """
        # Convert location string to dict if needed
        location_dict = None
        if isinstance(location, str):
            # Try to extract coordinates from location string
            # For now, use default Prague coordinates
            location_dict = {"latitude": 50.0755, "longitude": 14.4378}

        # Search using API client
        places = await self._api_client.search_places(
            query=query,
            location=location_dict,
            max_results=max_results,
        )

        return places

    def parse_place_data(self, place_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse place data from API response to extract business information.

        Args:
            place_data: Raw place data dictionary from API

        Returns:
            Dictionary with parsed business information
        """
        geometry = place_data.get("geometry", {})
        location = geometry.get("location", {})

        return {
            "business_name": place_data.get("name", ""),
            "google_address": place_data.get("formatted_address", ""),
            "google_phone": place_data.get("formatted_phone_number"),
            "google_website": place_data.get("website"),
            "google_maps_id": place_data.get("place_id"),
            "google_maps_url": f"https://www.google.com/maps/place/?q=place_id:{place_data.get('place_id', '')}",
            "latitude": location.get("lat"),
            "longitude": location.get("lng"),
            "rating": place_data.get("rating"),
            "review_count": place_data.get("user_ratings_total"),
            "types": place_data.get("types", []),
        }

    async def get_place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a place.

        Args:
            place_id: Google Places place_id

        Returns:
            Place details dictionary or None if not found
        """
        return await self._api_client.get_place_details(place_id)

    async def close(self):
        """Close all clients and cleanup resources."""
        # API client doesn't need explicit close, but MCP client might
        if hasattr(self._mcp_client, "close"):
            await self._mcp_client.close()
        logger.info("Google Maps client closed")
