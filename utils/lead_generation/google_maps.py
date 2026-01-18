"""
Google Maps Places API client for finding businesses.
"""

import asyncio
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import httpx
from urllib.parse import urlencode

from config import settings
from utils.logging_config import setup_logging

logger = setup_logging(
    name=__name__, log_level="INFO", log_file="lead_generation.log", log_dir="logs"
)

# Retry configuration
_MAX_RETRIES = 3
_RETRY_DELAY = 1.0  # seconds
_RETRY_BACKOFF = 2.0  # exponential backoff multiplier
_API_TIMEOUT = 30.0  # seconds

# Google Maps API endpoints
_PLACES_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
_PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
_PLACES_NEXT_PAGE_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"


class GoogleMapsClient:
    """
    Client for Google Maps Places API.
    
    Features:
    - Automatic fallback to browser scraping when API quota is exceeded
    - Result caching to avoid duplicate API calls
    - Retry logic with exponential backoff
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        browser_scraper: Optional[Any] = None,
        cache_ttl: timedelta = timedelta(hours=24),
    ):
        """
        Initialize Google Maps client.

        Args:
            api_key: Google Maps API key (defaults to GOOGLE_MAPS_API_KEY from settings)
            browser_scraper: Optional BrowserScraper instance for fallback
            cache_ttl: Cache TTL for search results (default: 24 hours)
        """
        self.api_key = api_key or getattr(settings, "google_maps_api_key", None)
        if not self.api_key:
            raise ValueError(
                "Google Maps API key is required. Set GOOGLE_MAPS_API_KEY in .env"
            )
        self.client = httpx.AsyncClient(timeout=_API_TIMEOUT)
        self.browser_scraper = browser_scraper
        
        # Cache for search results: {cache_key: (results, expiry_time)}
        self._cache: Dict[str, tuple[List[Dict[str, Any]], datetime]] = {}
        self.cache_ttl = cache_ttl

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
    
    def _get_cache_key(self, query: str, location: str) -> str:
        """Generate cache key for search query."""
        cache_string = f"{query}:{location}".lower().strip()
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Get results from cache if not expired."""
        if cache_key not in self._cache:
            return None
        
        results, expiry = self._cache[cache_key]
        if datetime.utcnow() > expiry:
            del self._cache[cache_key]
            return None
        
        logger.debug(f"Cache hit for query: {cache_key[:16]}...")
        return results
    
    def _set_cache(self, cache_key: str, results: List[Dict[str, Any]]) -> None:
        """Store results in cache."""
        expiry = datetime.utcnow() + self.cache_ttl
        self._cache[cache_key] = (results, expiry)
        logger.debug(f"Cached results for query: {cache_key[:16]}...")
    
    def _cleanup_expired_cache(self) -> None:
        """Remove expired cache entries."""
        now = datetime.utcnow()
        expired_keys = [
            k for k, (_, expiry) in self._cache.items()
            if now > expiry
        ]
        for k in expired_keys:
            del self._cache[k]

    async def search_businesses(
        self,
        query: str,
        location: str = "Prague, Czech Republic",
        max_results: int = 20,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Search for businesses using Google Maps Places API.
        
        Automatically falls back to browser scraping if API quota is exceeded.

        Args:
            query: Search query (e.g., "beauty salon", "kavárna", "restaurant")
            location: Location to search in (default: Prague)
            max_results: Maximum number of results to return
            use_cache: Whether to use cached results (default: True)

        Returns:
            List of business place data dictionaries

        Raises:
            ValueError: If query is empty
            RuntimeError: If API call fails after retries and no fallback available
        """
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        # Check cache first
        cache_key = self._get_cache_key(query, location)
        if use_cache:
            cached_results = self._get_from_cache(cache_key)
            if cached_results is not None:
                return cached_results[:max_results]
        
        # Cleanup expired cache entries periodically
        self._cleanup_expired_cache()

        # Build search query
        search_query = f"{query} in {location}"

        results = []
        next_page_token = None
        delay = _RETRY_DELAY

        while len(results) < max_results:
            try:
                # Prepare request parameters
                params = {
                    "query": search_query,
                    "key": self.api_key,
                    "language": "cs",  # Czech language
                }

                if next_page_token:
                    params["pagetoken"] = next_page_token

                # Make API request with retry logic
                for attempt in range(_MAX_RETRIES):
                    try:
                        response = await self.client.get(_PLACES_SEARCH_URL, params=params)
                        response.raise_for_status()

                        data = response.json()

                        if data.get("status") == "OK":
                            places = data.get("results", [])
                            results.extend(places)

                            # Check for next page
                            next_page_token = data.get("next_page_token")
                            if not next_page_token or len(results) >= max_results:
                                break

                            # Wait before requesting next page (Google requires delay)
                            await asyncio.sleep(2)

                        elif data.get("status") == "ZERO_RESULTS":
                            logger.info(f"No results found for query: {search_query}")
                            break

                        elif data.get("status") == "OVER_QUERY_LIMIT":
                            logger.warning("Google Maps API quota exceeded, trying browser fallback")
                            # Try browser fallback
                            if self.browser_scraper:
                                try:
                                    browser_results = await self._search_with_browser_fallback(query, location, max_results)
                                    if browser_results:
                                        # Cache browser results
                                        self._set_cache(cache_key, browser_results)
                                        return browser_results[:max_results]
                                except Exception as e:
                                    logger.error(f"Browser fallback failed: {e}")
                            
                            raise RuntimeError("Google Maps API quota exceeded and browser fallback unavailable")

                        else:
                            error_msg = data.get("error_message", "Unknown error")
                            logger.warning(
                                f"Google Maps API error: {data.get('status')} - {error_msg}"
                            )
                            if attempt < _MAX_RETRIES - 1:
                                await asyncio.sleep(delay)
                                delay *= _RETRY_BACKOFF
                                continue
                            break

                    except httpx.HTTPStatusError as e:
                        if attempt < _MAX_RETRIES - 1:
                            logger.warning(
                                f"HTTP error (attempt {attempt + 1}/{_MAX_RETRIES}): {e}. Retrying..."
                            )
                            await asyncio.sleep(delay)
                            delay *= _RETRY_BACKOFF
                        else:
                            raise RuntimeError(f"HTTP error calling Google Maps API: {e}") from e

                    except httpx.RequestError as e:
                        if attempt < _MAX_RETRIES - 1:
                            logger.warning(
                                f"Request error (attempt {attempt + 1}/{_MAX_RETRIES}): {e}. Retrying..."
                            )
                            await asyncio.sleep(delay)
                            delay *= _RETRY_BACKOFF
                        else:
                            raise RuntimeError(
                                f"Request error calling Google Maps API: {e}"
                            ) from e

                if not next_page_token:
                    break

            except RuntimeError as e:
                # Re-raise quota exceeded errors (already handled fallback)
                if "quota exceeded" in str(e).lower():
                    raise
                logger.error(f"Error searching businesses: {e}", exc_info=True)
                raise RuntimeError(f"Failed to search businesses: {e}") from e
            except Exception as e:
                logger.error(f"Error searching businesses: {e}", exc_info=True)
                # Try browser fallback on any error
                if self.browser_scraper:
                    try:
                        logger.info("Attempting browser fallback due to API error")
                        browser_results = await self._search_with_browser_fallback(query, location, max_results)
                        if browser_results:
                            self._set_cache(cache_key, browser_results)
                            return browser_results[:max_results]
                    except Exception as fallback_error:
                        logger.error(f"Browser fallback also failed: {fallback_error}")
                
                raise RuntimeError(f"Failed to search businesses: {e}") from e

        # Cache successful results
        if results:
            self._set_cache(cache_key, results)
        
        return results[:max_results]
    
    async def _search_with_browser_fallback(
        self,
        query: str,
        location: str,
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """
        Fallback to browser scraping when API is unavailable.
        
        Args:
            query: Search query
            location: Location string
            max_results: Maximum results to return
            
        Returns:
            List of business data dictionaries
        """
        if not self.browser_scraper:
            return []
        
        logger.info(f"Using browser fallback for query: {query} in {location}")
        
        try:
            # Search using browser scraper
            browser_result = await self.browser_scraper.search_google_maps(query, location)
            
            if not browser_result:
                return []
            
            # Convert browser result to API-like format
            result_dict = {
                "place_id": None,  # Not available from browser scraping
                "name": browser_result.get("business_name") or query,
                "formatted_address": browser_result.get("address"),
                "formatted_phone_number": browser_result.get("phone"),
                "website": browser_result.get("website"),
                "rating": browser_result.get("rating"),
                "user_ratings_total": browser_result.get("reviews_count"),
                "url": browser_result.get("google_maps_url"),
                "types": [],  # Not easily extractable from browser
            }
            
            return [result_dict]
            
        except Exception as e:
            logger.error(f"Browser fallback error: {e}", exc_info=True)
            return []

    async def get_place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a place.

        Args:
            place_id: Google Maps Place ID

        Returns:
            Place details dictionary or None if not found

        Raises:
            ValueError: If place_id is empty
        """
        if not place_id:
            raise ValueError("Place ID cannot be empty")

        params = {
            "place_id": place_id,
            "key": self.api_key,
            "language": "cs",
            "fields": "name,formatted_address,formatted_phone_number,website,rating,user_ratings_total,types,url",
        }

        delay = _RETRY_DELAY

        for attempt in range(_MAX_RETRIES):
            try:
                response = await self.client.get(_PLACES_DETAILS_URL, params=params)
                response.raise_for_status()

                data = response.json()

                if data.get("status") == "OK":
                    return data.get("result")

                elif data.get("status") == "NOT_FOUND":
                    logger.debug(f"Place {place_id} not found")
                    return None

                elif data.get("status") == "OVER_QUERY_LIMIT":
                    logger.warning("Google Maps API quota exceeded for place details")
                    # Try browser fallback if available
                    if self.browser_scraper:
                        try:
                            browser_result = await self.browser_scraper.extract_business_details(
                                f"https://www.google.com/maps/place/?q=place_id:{place_id}"
                            )
                            if browser_result:
                                return browser_result
                        except Exception as e:
                            logger.error(f"Browser fallback for place details failed: {e}")
                    raise RuntimeError("Google Maps API quota exceeded")

                else:
                    error_msg = data.get("error_message", "Unknown error")
                    logger.warning(
                        f"Google Maps API error: {data.get('status')} - {error_msg}"
                    )
                    if attempt < _MAX_RETRIES - 1:
                        await asyncio.sleep(delay)
                        delay *= _RETRY_BACKOFF
                    else:
                        return None

            except httpx.HTTPStatusError as e:
                if attempt < _MAX_RETRIES - 1:
                    logger.warning(
                        f"HTTP error (attempt {attempt + 1}/{_MAX_RETRIES}): {e}. Retrying..."
                    )
                    await asyncio.sleep(delay)
                    delay *= _RETRY_BACKOFF
                else:
                    logger.error(f"HTTP error getting place details: {e}", exc_info=True)
                    return None

            except httpx.RequestError as e:
                if attempt < _MAX_RETRIES - 1:
                    logger.warning(
                        f"Request error (attempt {attempt + 1}/{_MAX_RETRIES}): {e}. Retrying..."
                    )
                    await asyncio.sleep(delay)
                    delay *= _RETRY_BACKOFF
                else:
                    logger.error(f"Request error getting place details: {e}", exc_info=True)
                    return None

        return None

    def parse_place_data(self, place_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Google Maps place data into standardized format.

        Args:
            place_data: Raw place data from Google Maps API

        Returns:
            Parsed business information dictionary
        """
        return {
            "google_maps_id": place_data.get("place_id"),
            "business_name": place_data.get("name", ""),
            "google_address": place_data.get("formatted_address"),
            "google_phone": place_data.get("formatted_phone_number"),
            "google_website": place_data.get("website"),
            "google_rating": place_data.get("rating"),
            "google_reviews_count": place_data.get("user_ratings_total"),
            "category": ", ".join(place_data.get("types", [])) if place_data.get("types") else None,
            "google_maps_url": place_data.get("url"),
        }
