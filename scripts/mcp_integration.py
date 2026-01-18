"""
Integration module for MCP servers.
Provides wrappers for web search and browser automation.
"""

import os
import json
import logging
from typing import List, Dict, Optional, Any
import httpx

logger = logging.getLogger(__name__)


class MCPSearchClient:
    """
    Client for web search via MCP servers (Brave Search, Tavily).
    Falls back to direct API calls if MCP not available.
    """
    
    def __init__(self):
        """Initialize search client."""
        self.brave_api_key = os.getenv('BRAVE_API_KEY')
        self.tavily_api_key = os.getenv('TAVILY_API_KEY')
    
    async def search(
        self,
        query: str,
        count: int = 10,
        use_mcp: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search the web using Brave Search or Tavily.
        
        Args:
            query: Search query
            count: Number of results
            use_mcp: Whether to try MCP first (requires Cursor environment)
            
        Returns:
            List of search results
        """
        # Try MCP first if available (in Cursor environment)
        if use_mcp:
            try:
                # In Cursor, MCP functions are available via tools
                # This would be called by the AI assistant, not directly
                # For now, fall through to direct API
                pass
            except Exception as e:
                logger.debug(f"MCP search not available: {e}")
        
        # Fallback to direct API calls
        if self.brave_api_key:
            return await self._brave_search(query, count)
        elif self.tavily_api_key:
            return await self._tavily_search(query, count)
        else:
            logger.warning(
                "No API keys configured. Set BRAVE_API_KEY or TAVILY_API_KEY "
                "for web search functionality."
            )
            return []
    
    async def _brave_search(
        self,
        query: str,
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """Search using Brave Search API."""
        if not self.brave_api_key:
            return []
        
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.brave_api_key,
        }
        params = {
            "q": query,
            "count": min(count, 20),  # Brave limit
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get('web', {}).get('results', [])[:count]:
                    results.append({
                        'title': item.get('title', ''),
                        'url': item.get('url', ''),
                        'description': item.get('description', ''),
                    })
                
                return results
        except Exception as e:
            logger.error(f"Brave Search API error: {e}")
            return []
    
    async def _tavily_search(
        self,
        query: str,
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """Search using Tavily API."""
        if not self.tavily_api_key:
            return []
        
        url = "https://api.tavily.com/search"
        headers = {
            "Content-Type": "application/json",
        }
        data = {
            "api_key": self.tavily_api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": min(count, 10),  # Tavily limit
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
                
                results = []
                for item in result.get('results', [])[:count]:
                    results.append({
                        'title': item.get('title', ''),
                        'url': item.get('url', ''),
                        'description': item.get('content', ''),
                    })
                
                return results
        except Exception as e:
            logger.error(f"Tavily API error: {e}")
            return []


class MCPBrowserClient:
    """
    Client for browser automation via MCP Puppeteer server.
    Falls back to Playwright if MCP not available.
    """
    
    def __init__(self):
        """Initialize browser client."""
        self.use_playwright = True  # Fallback option
    
    async def navigate(self, url: str) -> bool:
        """
        Navigate to URL.
        
        Args:
            url: URL to navigate to
            
        Returns:
            True if successful
        """
        # In Cursor environment, this would use MCP browser tools
        # For standalone script, use Playwright
        if self.use_playwright:
            try:
                from playwright.async_api import async_playwright
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    await page.goto(url, wait_until='networkidle')
                    await browser.close()
                    return True
            except Exception as e:
                logger.error(f"Playwright navigation error: {e}")
                return False
        
        return False
    
    async def get_page_content(self, url: str) -> Optional[str]:
        """
        Get HTML content of a page.
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content or None
        """
        if self.use_playwright:
            try:
                from playwright.async_api import async_playwright
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    await page.goto(url, wait_until='networkidle')
                    content = await page.content()
                    await browser.close()
                    return content
            except Exception as e:
                logger.error(f"Playwright content fetch error: {e}")
                return None
        
        return None
    
    async def extract_google_maps_data(self, maps_url: str) -> Optional[Dict]:
        """
        Extract data from Google Maps page.
        
        Args:
            maps_url: Google Maps URL
            
        Returns:
            Dictionary with business data
        """
        content = await self.get_page_content(maps_url)
        if not content:
            return None
        
        from bs4 import BeautifulSoup
        import re
        
        soup = BeautifulSoup(content, 'html.parser')
        data = {}
        
        # Method 1: Look for JSON-LD structured data
        json_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_scripts:
            try:
                json_data = json.loads(script.string)
                if isinstance(json_data, dict):
                    if '@type' in json_data and 'LocalBusiness' in str(json_data.get('@type')):
                        data['name'] = json_data.get('name', '')
                        addr = json_data.get('address', {})
                        if isinstance(addr, dict):
                            address_parts = [
                                addr.get('streetAddress', ''),
                                addr.get('addressLocality', ''),
                                addr.get('postalCode', ''),
                            ]
                            data['address'] = ', '.join(filter(None, address_parts))
                        elif isinstance(addr, str):
                            data['address'] = addr
                        data['phone'] = json_data.get('telephone', '')
                        data['website'] = json_data.get('url', '')
                        # Try to get rating
                        if 'aggregateRating' in json_data:
                            rating_data = json_data['aggregateRating']
                            data['rating'] = rating_data.get('ratingValue')
                            data['reviews_count'] = rating_data.get('reviewCount')
                        break
            except Exception:
                continue
        
        # Method 2: Extract from inline JSON data (Google Maps specific)
        inline_scripts = soup.find_all('script')
        for script in inline_scripts:
            if script.string and 'window.APP_INITIALIZATION_STATE' in script.string:
                # Try to extract business data from Google Maps initialization
                try:
                    # Look for patterns like [null,null,"Business Name"]
                    name_match = re.search(r'\[null,null,"([^"]+)"\]', script.string)
                    if name_match:
                        data['name'] = name_match.group(1)
                    
                    # Look for phone patterns
                    phone_match = re.search(r'\+?\d{1,3}[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{3}', script.string)
                    if phone_match:
                        data['phone'] = phone_match.group(0)
                except Exception:
                    pass
        
        # Method 3: Extract from meta tags and title
        if not data.get('name'):
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.get_text().strip()
                # Remove " - Google Maps" suffix
                data['name'] = title_text.replace(' - Google Maps', '').strip()
        
        # Method 4: Try to find address in content
        if not data.get('address'):
            # Look for address patterns
            address_patterns = [
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*Praha\s*\d+',
                r'Praha\s*\d+[^,]*',
            ]
            for pattern in address_patterns:
                match = re.search(pattern, content)
                if match:
                    data['address'] = match.group(0)
                    break
        
        # Extract rating if available in text
        if not data.get('rating'):
            rating_match = re.search(r'(\d+\.?\d*)\s*(?:stars?|⭐)', content, re.IGNORECASE)
            if rating_match:
                try:
                    data['rating'] = float(rating_match.group(1))
                except ValueError:
                    pass
        
        return data if data.get('name') else None
