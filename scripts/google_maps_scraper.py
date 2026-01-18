"""
Google Maps Places API scraper for finding businesses in Prague.
Uses Google Places API to search for businesses by category and location.
"""

import logging
from typing import Optional

import httpx

from models.prospect import BusinessProspect

logger = logging.getLogger(__name__)


class GoogleMapsScraper:
    """Scraper for Google Maps Places API."""

    BASE_URL = "https://maps.googleapis.com/maps/api/place"
    PRAGUE_LOCATION = "50.0755,14.4378"  # Prague city center coordinates
    PRAGUE_RADIUS = 20000  # 20km radius

    def __init__(self, api_key: str):
        """
        Initialize Google Maps scraper.

        Args:
            api_key: Google Maps API key (requires Places API enabled)
        """
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def search_places(
        self,
        query: str,
        location: Optional[str] = None,
        radius: Optional[int] = None,
        category: Optional[str] = None,
        max_results: int = 20,
    ) -> list[BusinessProspect]:
        """
        Search for places using Google Places API.

        Args:
            query: Search query (e.g., "beauty salon", "kadeřnictví")
            location: Location coordinates (lat,lng). Defaults to Prague center.
            radius: Search radius in meters. Defaults to 20km.
            category: Place category filter (optional)
            max_results: Maximum number of results to return

        Returns:
            List of BusinessProspect objects
        """
        location = location or self.PRAGUE_LOCATION
        radius = radius or self.PRAGUE_RADIUS

        prospects = []
        next_page_token = None
        results_count = 0

        try:
            while results_count < max_results:
                # Build search URL
                params = {
                    "query": query,
                    "location": location,
                    "radius": radius,
                    "key": self.api_key,
                }

                if category:
                    params["type"] = category

                if next_page_token:
                    params["pagetoken"] = next_page_token

                # Search for places
                url = f"{self.BASE_URL}/textsearch/json"
                response = await self.client.get(url, params=params)
                response.raise_for_status()

                data = response.json()

                if data.get("status") != "OK":
                    logger.warning(f"Google Places API error: {data.get('status')}")
                    break

                # Process results
                for place in data.get("results", []):
                    if results_count >= max_results:
                        break

                    prospect = await self._place_to_prospect(place, query)
                    if prospect:
                        prospects.append(prospect)
                        results_count += 1

                # Check for next page
                next_page_token = data.get("next_page_token")
                if not next_page_token:
                    break

                # Wait before next page request (required by Google API)
                import asyncio
                await asyncio.sleep(2)

        except httpx.HTTPError as e:
            logger.error(f"HTTP error searching places: {e}")
        except Exception as e:
            logger.error(f"Error searching places: {e}", exc_info=True)

        return prospects

    async def search_by_category(
        self,
        category: str,
        location: Optional[str] = None,
        radius: Optional[int] = None,
        max_results: int = 20,
    ) -> list[BusinessProspect]:
        """
        Search for places by category.

        Common categories:
        - beauty_salon (kadeřnictví, kosmetika)
        - restaurant (restaurace)
        - spa (wellness, masáže)
        - store (obchod)
        - gym (fitness)

        Args:
            category: Place category
            location: Location coordinates
            radius: Search radius in meters
            max_results: Maximum number of results

        Returns:
            List of BusinessProspect objects
        """
        return await self.search_places(
            query=category,
            location=location,
            radius=radius,
            category=category,
            max_results=max_results,
        )

    async def get_place_details(self, place_id: str) -> Optional[BusinessProspect]:
        """
        Get detailed information about a place by place_id.

        Args:
            place_id: Google Places place_id

        Returns:
            BusinessProspect object or None if not found
        """
        try:
            params = {
                "place_id": place_id,
                "fields": "name,formatted_address,formatted_phone_number,website,url,rating,user_ratings_total,types",
                "key": self.api_key,
            }

            url = f"{self.BASE_URL}/details/json"
            response = await self.client.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            if data.get("status") != "OK":
                logger.warning(f"Google Places API error: {data.get('status')}")
                return None

            result = data.get("result")
            if not result:
                return None

            return await self._place_to_prospect(result, source="details")

        except httpx.HTTPError as e:
            logger.error(f"HTTP error getting place details: {e}")
        except Exception as e:
            logger.error(f"Error getting place details: {e}", exc_info=True)

        return None

    async def _place_to_prospect(
        self, place: dict, source: str = "search"
    ) -> Optional[BusinessProspect]:
        """
        Convert Google Places API result to BusinessProspect.

        Args:
            place: Place data from Google API
            source: Source of the data

        Returns:
            BusinessProspect object or None
        """
        try:
            # Extract basic info
            name = place.get("name", "")
            if not name:
                return None

            address = place.get("formatted_address")
            phone = place.get("formatted_phone_number") or place.get("international_phone_number")
            website = place.get("website")
            rating = place.get("rating")
            reviews_count = place.get("user_ratings_total", 0)

            # Build Google Maps URL
            place_id = place.get("place_id")
            google_maps_url = None
            if place_id:
                google_maps_url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"

            # Determine category from types
            types = place.get("types", [])
            category = None
            for t in types:
                if t in [
                    "beauty_salon",
                    "hair_care",
                    "spa",
                    "restaurant",
                    "cafe",
                    "store",
                    "gym",
                    "travel_agency",
                ]:
                    category = t
                    break

            prospect = BusinessProspect(
                name=name,
                address=address,
                phone=phone,
                website=website,
                google_maps_url=google_maps_url,
                category=category,
                rating=rating,
                reviews_count=reviews_count,
                source=source,
            )

            return prospect

        except Exception as e:
            logger.error(f"Error converting place to prospect: {e}", exc_info=True)
            return None

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
