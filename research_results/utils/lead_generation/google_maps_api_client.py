"""
Direct Google Maps Places API client.

Uses Google Maps Places API directly when MCP is not available but API key is configured.
"""

import asyncio
import logging
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .config import ScraperConfig
from .models import BusinessData

logger = logging.getLogger(__name__)


class GoogleMapsAPIClient:
    """
    Клиент для Google Maps Places API с rate limiting и кешированием.

    Приоритетный источник данных - официальный API.
    """

    def __init__(
        self,
        config: Optional[ScraperConfig] = None,
        rate_limit_per_minute: int = 60,
    ):
        """
        Initialize Google Maps API client.

        Args:
            config: Scraper configuration with API key
            rate_limit_per_minute: Rate limit per minute (default 60)
        """
        self.config = config or ScraperConfig()
        self.api_key = self.config.api_key
        self.rate_limit = rate_limit_per_minute
        self.request_times = deque(maxlen=rate_limit_per_minute)
        self.cache: Dict[str, Tuple[Any, datetime]] = {}
        self.cache_ttl = timedelta(hours=24)

        if not self.api_key:
            logger.warning("No API key configured. API client will not work.")
        else:
            masked_key = (
                self.api_key[:10] + "..." + self.api_key[-4:]
                if len(self.api_key) > 14
                else "***"
            )
            logger.info(f"Google Maps API client initialized with key: {masked_key}")

    async def _wait_for_rate_limit(self):
        """Ожидание для соблюдения rate limit."""
        now = datetime.now()
        # Удаляем старые записи
        while self.request_times and (now - self.request_times[0]).total_seconds() >= 60:
            self.request_times.popleft()

        if len(self.request_times) >= self.rate_limit:
            sleep_time = 60 - (now - self.request_times[0]).total_seconds()
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        self.request_times.append(datetime.now())

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Получить данные из кеша если не истек TTL."""
        if cache_key not in self.cache:
            return None
        data, cached_time = self.cache[cache_key]
        if datetime.now() - cached_time > self.cache_ttl:
            del self.cache[cache_key]
            return None
        return data

    def _set_cache(self, cache_key: str, data: Any):
        """Сохранить данные в кеш."""
        self.cache[cache_key] = (data, datetime.now())

    async def search_places(
        self,
        query: str,
        location: Optional[Dict[str, float]] = None,
        radius: Optional[int] = None,
        max_results: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Поиск мест через Places API.

        Args:
            query: Search query (e.g., "kavárna Praha 1")
            location: Optional location dict with 'latitude' and 'longitude'
            radius: Optional search radius in meters
            max_results: Maximum number of results to return

        Returns:
            List of place data dictionaries
        """
        if not self.api_key:
            logger.error("API key not configured")
            return []

        # Rate limiting
        await self._wait_for_rate_limit()

        # Проверка кеша
        cache_key = f"{query}:{location}:{radius}:{max_results}"
        if cached := self._get_from_cache(cache_key):
            logger.debug(f"Returning cached results for query: {query}")
            return cached

        # Try Places API (New) first
        results = await self._search_places_new(query, location, radius, max_results)

        # Fallback to Legacy API if New API fails
        if not results:
            logger.info("Places API (New) failed, trying Legacy API")
            results = await self._search_places_legacy(
                query, location, radius, max_results
            )

        # Cache results
        if results:
            self._set_cache(cache_key, results)

        return results

    async def _search_places_new(
        self,
        query: str,
        location: Optional[Dict[str, float]] = None,
        radius: Optional[int] = None,
        max_results: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search using Places API (New)."""
        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "places.id,places.displayName,places.formattedAddress,"
                "places.location,places.nationalPhoneNumber,places.websiteUri,"
                "places.rating,places.userRatingCount,places.types"
            ),
        }

        payload: Dict[str, Any] = {
            "textQuery": query,
            "maxResultCount": min(max_results, 20),  # API limit
        }

        if location:
            payload["locationBias"] = {
                "circle": {
                    "center": {
                        "latitude": location.get("latitude", 50.0755),
                        "longitude": location.get("longitude", 14.4378),
                    },
                    "radius": radius or self.config.default_radius_meters,
                }
            }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, headers=headers, json=payload)

                if response.status_code == 200:
                    data = response.json()
                    places = data.get("places", [])

                    # Convert to legacy format for compatibility
                    converted = []
                    for place in places:
                        converted.append(self._convert_new_to_legacy_format(place))

                    logger.info(f"Found {len(converted)} places using Places API (New)")
                    return converted
                else:
                    error_data = (
                        response.json()
                        if response.headers.get("content-type", "").startswith(
                            "application/json"
                        )
                        else {}
                    )
                    error_msg = error_data.get("error", {}).get(
                        "message", response.text
                    )
                    logger.warning(
                        f"Places API (New) error: {response.status_code} - {error_msg}"
                    )
                    return []

        except Exception as e:
            logger.error(f"Error calling Places API (New): {e}")
            return []

    async def _search_places_legacy(
        self,
        query: str,
        location: Optional[Dict[str, float]] = None,
        radius: Optional[int] = None,
        max_results: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search using Places API (Legacy)."""
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params: Dict[str, Any] = {"query": query, "key": self.api_key, "language": "cs"}

        if location:
            params["location"] = (
                f"{location.get('latitude', 50.0755)},{location.get('longitude', 14.4378)}"
            )
            params["radius"] = radius or self.config.default_radius_meters

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)

                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "OK":
                        results = data.get("results", [])
                        logger.info(f"Found {len(results)} places using Legacy API")
                        return results[:max_results]
                    else:
                        status = data.get("status", "UNKNOWN")
                        error_msg = data.get("error_message", "")
                        logger.warning(
                            f"Legacy API returned status: {status} - {error_msg}"
                        )
                        return []
                else:
                    logger.warning(f"Legacy API error: {response.status_code}")
                    return []

        except Exception as e:
            logger.error(f"Error calling Legacy API: {e}")
            return []

    def _convert_new_to_legacy_format(self, place: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Places API (New) format to Legacy format for compatibility."""
        display_name = place.get("displayName", {})
        location = place.get("location", {})

        return {
            "place_id": place.get("id", ""),
            "name": display_name.get("text", ""),
            "formatted_address": place.get("formattedAddress", ""),
            "geometry": {
                "location": {
                    "lat": location.get("latitude", 0),
                    "lng": location.get("longitude", 0),
                }
            },
            "formatted_phone_number": place.get("nationalPhoneNumber", ""),
            "website": place.get("websiteUri", ""),
            "rating": place.get("rating"),
            "user_ratings_total": place.get("userRatingCount"),
            "types": place.get("types", []),
        }

    async def get_place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение детальной информации о месте.

        Args:
            place_id: Google Places place_id

        Returns:
            Place details dictionary or None if not found
        """
        if not self.api_key:
            return None

        # Rate limiting
        await self._wait_for_rate_limit()

        # Проверка кеша
        cache_key = f"details:{place_id}"
        if cached := self._get_from_cache(cache_key):
            logger.debug(f"Returning cached details for place_id: {place_id}")
            return cached

        # Try Legacy API (more reliable for place details)
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": place_id,
            "key": self.api_key,
            "fields": "name,formatted_address,formatted_phone_number,website,rating,user_ratings_total,geometry,types",
            "language": "cs",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)

                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "OK":
                        result = data.get("result", {})
                        self._set_cache(cache_key, result)
                        return result
                    else:
                        logger.warning(
                            f"Place details API returned status: {data.get('status')}"
                        )
                        return None
                else:
                    logger.warning(f"Place details API error: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching place details: {e}")
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
        places = await self.search_places(
            query, location, self.config.default_radius_meters, max_results
        )

        businesses = []
        for place in places:
            try:
                business = self._convert_place_to_business(place)
                if business:
                    businesses.append(business)
            except Exception as e:
                logger.warning(f"Error converting place to business: {e}")
                continue

        return businesses

    def _convert_place_to_business(
        self, place_data: Dict[str, Any]
    ) -> Optional[BusinessData]:
        """
        Convert API place data to BusinessData model.

        Args:
            place_data: Place data from API

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
                rating=Decimal(str(place_data.get("rating"))) if place_data.get("rating") else None,
                review_count=place_data.get("user_ratings_total"),
                latitude=Decimal(str(location.get("lat"))) if location.get("lat") else None,
                longitude=Decimal(str(location.get("lng"))) if location.get("lng") else None,
            )
        except Exception as e:
            logger.error(f"Error converting place data: {e}")
            return None

    def clear_cache(self):
        """Clear the API results cache."""
        self.cache.clear()
        logger.info("API cache cleared")
