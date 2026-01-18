"""
Координатор источников данных с fallback логикой.

Отвечает за координацию различных источников данных (API, HERE, MCP, Scraper)
с автоматическим fallback при ошибках.
"""

import asyncio
import logging
from typing import Dict, List, Optional

from .config import ScraperConfig
from .google_maps_api_client import GoogleMapsAPIClient
from .google_maps_scraper import GoogleMapsScraper
from .here_places_client import HerePlacesClient
from .mcp_google_maps import MCPGoogleMapsClient
from .models import BusinessData
from .utils import normalize_location

logger = logging.getLogger(__name__)


class DataSourceCoordinator:
    """
    Координирует источники данных с fallback логикой.

    Приоритет источников: API -> HERE -> MCP -> Scraper
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        """
        Initialize data source coordinator.

        Args:
            config: Scraper configuration
        """
        self.config = config or ScraperConfig()
        self.logger = logger

        # Initialize clients
        self.api_client = (
            GoogleMapsAPIClient(self.config) if self.config.api_key else None
        )
        self.mcp_client = MCPGoogleMapsClient(self.config)
        self.scraper: Optional[GoogleMapsScraper] = None

        # Initialize HERE client if API key is available
        try:
            self.here_client = (
                HerePlacesClient(self.config) if self.config.here_api_key else None
            )
        except Exception as e:
            logger.warning(f"HERE client not available: {e}")
            self.here_client = None

    async def fetch_businesses(
        self,
        query: Dict,
        use_api: bool = True,
        use_here: bool = False,
        use_mcp: bool = True,
        use_scraper: bool = False,
    ) -> List[BusinessData]:
        """
        Получить данные о бизнесах с fallback между источниками.

        Args:
            query: Query dictionary with 'query', 'location', 'max_results', etc.
            use_api: Использовать Google Maps API
            use_here: Использовать HERE Places API
            use_mcp: Использовать MCP сервер
            use_scraper: Использовать браузерный скрапинг

        Returns:
            List of BusinessData objects
        """
        # Приоритет 1: Google Maps API
        if use_api and self.api_client:
            try:
                location_dict = normalize_location(query.get("location"))
                businesses = await self.api_client.search_businesses(
                    query["query"], location_dict, query.get("max_results", 20)
                )
                if businesses:
                    return businesses
            except Exception as e:
                self.logger.warning(f"Google Maps API failed, trying fallback: {e}")

        # Приоритет 2: HERE Places API
        if use_here and self.here_client:
            try:
                location_dict = normalize_location(query.get("location"))
                # HERE API is synchronous, run in executor
                loop = asyncio.get_event_loop()
                businesses = await loop.run_in_executor(
                    None,
                    self.here_client.search_businesses,
                    query["query"],
                    location_dict,
                    query.get("max_results", 20),
                    query.get("category"),
                )
                if businesses:
                    return businesses
            except Exception as e:
                self.logger.warning(f"HERE API failed, trying fallback: {e}")

        # Приоритет 3: MCP
        if use_mcp:
            try:
                mcp_available = await self.mcp_client.check_mcp_availability()
                if mcp_available:
                    location_dict = normalize_location(query.get("location"))
                    businesses = await self.mcp_client.search_places(
                        query["query"], location_dict, query.get("radius")
                    )
                    if businesses:
                        return businesses
            except Exception as e:
                self.logger.warning(f"MCP failed, trying scraper: {e}")

        # Приоритет 4: Scraper
        if use_scraper:
            try:
                if not self.scraper:
                    self.scraper = GoogleMapsScraper(self.config)
                    await self.scraper.__aenter__()

                location_str = query.get("location")
                if isinstance(location_str, dict):
                    location_str = f"Prague {query.get('district', '')}"
                elif isinstance(location_str, tuple):
                    location_str = "Prague"
                else:
                    location_str = location_str or "Prague"

                businesses = await self.scraper.search_businesses(
                    query["query"],
                    location_str,
                    query.get("max_results", 20),
                )
                if businesses:
                    return businesses
            except Exception as e:
                self.logger.warning(f"Scraper failed: {e}")

        if not use_api and not use_here and not use_mcp and not use_scraper:
            raise RuntimeError("All data sources disabled")

        return []

    async def close(self):
        """Close all resources."""
        if self.scraper:
            await self.scraper.__aexit__(None, None, None)
            self.scraper = None
