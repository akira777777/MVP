"""
MCP Google Maps integration for structured place data retrieval.
"""

import logging
from typing import Any, Dict, List, Optional

from .config import ScraperConfig
from .google_maps_api_client import GoogleMapsAPIClient
from .models import BusinessData

logger = logging.getLogger(__name__)


class MCPGoogleMapsClient:
    """
    Клиент для Google Maps через MCP сервер.

    Используется как альтернатива API если доступен.
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        """
        Initialize MCP Google Maps client.

        Args:
            config: Scraper configuration
        """
        self.config = config or ScraperConfig()
        self.logger = logger
        self._mcp_available = self._check_mcp_availability()
        self._cache: Dict[str, Any] = {}
        # Fallback to direct API client if MCP unavailable but API key is configured
        self._api_client: Optional[GoogleMapsAPIClient] = None
        if self.config.api_key:
            self._api_client = GoogleMapsAPIClient(self.config)

    def _check_mcp_availability(self) -> bool:
        """Проверка доступности MCP сервера."""
        # Try to import MCP tools or check MCP server availability
        try:
            # This would be replaced with actual MCP client check
            # For now, we'll check if MCP tools are available
            # In a real implementation, this would check the MCP server connection
            self._mcp_available = False  # Default to False until properly configured
            return False
        except Exception as e:
            self.logger.warning(f"MCP Google Maps server not available: {e}")
            return False

    async def check_mcp_availability(self) -> bool:
        """
        Check if Google Maps MCP server is available (async version).

        Returns:
            True if MCP server is available, False otherwise
        """
        return self._mcp_available

    async def search_places(
        self,
        query: str,
        location: Optional[Dict[str, float]] = None,
        radius: Optional[int] = None,
    ) -> List[BusinessData]:
        """
        Поиск мест через MCP.

        Args:
            query: Search query (e.g., "kavárna Praha 1")
            location: Optional location dict with 'latitude' and 'longitude'
            radius: Optional search radius in meters

        Returns:
            List of BusinessData objects
        """
        if not self._mcp_available:
            raise RuntimeError("MCP Google Maps server not available")

        # Check cache
        cache_key = f"{query}_{location}_{radius}"
        if cache_key in self._cache:
            self.logger.debug(f"Returning cached results for query: {query}")
            return self._cache[cache_key]

        # Использование MCP инструментов
        # Пример вызова (зависит от конкретной реализации MCP)
        # results = await mcp_client.call("google-maps/search_places", {...})
        # return self._parse_mcp_response(results)

        # For now, fallback to API client if available
        if self._api_client:
            self.logger.info(f"Using direct API client for query: {query}")
            businesses = await self._api_client.search_businesses(
                query, location, self.config.max_results_per_query
            )
            if businesses:
                self._cache[cache_key] = businesses
                return businesses

        return []

    async def get_place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a place using MCP.
        Falls back to direct API client if MCP unavailable but API key is configured.

        Args:
            place_id: Google Places place_id

        Returns:
            Place details dictionary or None if not found
        """
        # Check cache
        if place_id in self._cache:
            logger.debug(f"Returning cached details for place_id: {place_id}")
            return self._cache[place_id]

        # Try MCP first if available
        if self._mcp_available:
            try:
                # This would use actual MCP tools when available
                # TODO: Implement actual MCP tool calls
                logger.info(f"Fetching place details via MCP: {place_id}")
            except Exception as e:
                logger.warning(f"Error using MCP, falling back to API: {e}")

        # Fallback to direct API client
        if self._api_client:
            logger.info(f"Using direct API client for place_id: {place_id}")
            details = await self._api_client.get_place_details(place_id)
            if details:
                self._cache[place_id] = details
                return details

        if not self._mcp_available and not self._api_client:
            logger.warning("Neither MCP nor API client available")
            return None

        return None

    async def search_businesses(
        self,
        query: str,
        location: Optional[Dict[str, float]] = None,
        max_results: int = 20,
    ) -> List[BusinessData]:
        """
        Search for businesses and convert to BusinessData models.

        Args:
            query: Search query
            location: Optional location dict
            max_results: Maximum number of results to return

        Returns:
            List of BusinessData objects
        """
        return await self.search_places(
            query, location, self.config.default_radius_meters
        )

    def _convert_place_to_business(
        self, place_data: Dict[str, Any]
    ) -> Optional[BusinessData]:
        """
        Convert MCP place data to BusinessData model.

        Note: This method is reserved for future MCP implementation.
        Currently, search_places uses API client directly.

        Args:
            place_data: Place data from MCP API

        Returns:
            BusinessData object or None if conversion fails
        """
        try:
            from decimal import Decimal

            geometry = place_data.get("geometry", {})
            location = geometry.get("location", {})
            types_list = place_data.get("types", [])

            # Extract district from address if possible
            address = place_data.get("formatted_address", "")
            district = None
            for i in range(1, 11):
                if f"Praha {i}" in address or f"Prague {i}" in address:
                    district = f"Prague {i}"
                    break

            return BusinessData(
                name=place_data.get("name", ""),
                address=address,
                city="Prague",
                district=district,
                phone=place_data.get("formatted_phone_number"),
                website=place_data.get("website"),
                category=", ".join(types_list[:3]) if types_list else "unknown",
                subcategory=", ".join(types_list[3:]) if len(types_list) > 3 else None,
                google_place_id=place_data.get("place_id"),
                place_id=place_data.get("place_id"),  # Keep for backward compatibility
                rating=Decimal(str(place_data.get("rating")))
                if place_data.get("rating")
                else None,
                review_count=place_data.get("user_ratings_total"),
                latitude=Decimal(str(location.get("lat")))
                if location.get("lat")
                else None,
                longitude=Decimal(str(location.get("lng")))
                if location.get("lng")
                else None,
            )
        except Exception as e:
            logger.error(f"Error converting place data: {e}")
            return None

    def clear_cache(self):
        """Clear the MCP results cache."""
        self._cache.clear()
        logger.info("MCP cache cleared")
