"""MCP server integration for web search."""

import asyncio
import json
import logging
import subprocess
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class MCPSearchClient:
    """Client for MCP search servers (Brave Search, Tavily)."""

    def __init__(self):
        """Initialize MCP client."""
        self.brave_api_key = None  # Would be loaded from env

    async def brave_search(self, query: str, count: int = 20) -> List[Dict]:
        """
        Search using Brave Search API.
        
        In production, this would use MCP server directly.
        For now, uses direct API call if key available.
        """
        if not self.brave_api_key:
            logger.warning("Brave API key not configured, using fallback")
            return await self._fallback_search(query, count)

        try:
            import httpx
            async with httpx.AsyncClient() as client:
                url = "https://api.search.brave.com/res/v1/web/search"
                params = {
                    "q": query,
                    "count": min(count, 20),
                    "country": "CZ",
                    "search_lang": "cs",
                }
                headers = {"X-Subscription-Token": self.brave_api_key}

                response = await client.get(url, params=params, headers=headers, timeout=30.0)
                response.raise_for_status()
                data = response.json()

                results = []
                if "web" in data and "results" in data["web"]:
                    for item in data["web"]["results"]:
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "description": item.get("description", ""),
                            "snippet": item.get("description", ""),
                        })

                return results

        except Exception as e:
            logger.error(f"Brave search error: {e}")
            return await self._fallback_search(query, count)

    async def _fallback_search(self, query: str, count: int) -> List[Dict]:
        """
        Fallback search method.
        
        In production, this would trigger browser automation
        or use Tavily MCP server as alternative.
        """
        logger.info(f"Using fallback search for: {query}")
        # Return empty results - will be filled by browser automation
        return []

    async def local_search(self, query: str, location: str = "Prague, Czech Republic") -> List[Dict]:
        """
        Local business search using Brave Local Search API.
        
        This is better suited for finding businesses.
        """
        if not self.brave_api_key:
            logger.warning("Brave API key not configured for local search")
            return []

        try:
            import httpx
            async with httpx.AsyncClient() as client:
                url = "https://api.search.brave.com/res/v1/local/search"
                params = {
                    "q": query,
                    "location": location,
                    "count": 20,
                }
                headers = {"X-Subscription-Token": self.brave_api_key}

                response = await client.get(url, params=params, headers=headers, timeout=30.0)
                response.raise_for_status()
                data = response.json()

                results = []
                if "local" in data and "results" in data["local"]:
                    for item in data["local"]["results"]:
                        results.append({
                            "title": item.get("title", ""),
                            "address": item.get("address", ""),
                            "phone": item.get("phone", ""),
                            "url": item.get("url", ""),
                            "website": item.get("website", ""),
                            "rating": item.get("rating", ""),
                            "reviews": item.get("reviews", ""),
                        })

                return results

        except Exception as e:
            logger.error(f"Brave local search error: {e}")
            return []
