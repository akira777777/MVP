"""
Асинхронный коллектор данных о бизнесах.

Использует приоритет: API -> MCP -> Scraper
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional

from .models import BusinessData, BusinessCreate
from .google_maps_api_client import GoogleMapsAPIClient
from .mcp_google_maps import MCPGoogleMapsClient
from .google_maps_scraper import GoogleMapsScraper
from utils.logging_config import setup_logging

logger = setup_logging(__name__)


@dataclass
class CollectionProgress:
    """Трекинг прогресса сбора."""
    total_queries: int
    completed_queries: int
    total_businesses_found: int
    total_businesses_saved: int
    errors: List[str]
    start_time: datetime

    @property
    def completion_percent(self) -> float:
        if self.total_queries == 0:
            return 0.0
        return (self.completed_queries / self.total_queries) * 100


class BusinessCollector:
    """
    Асинхронный коллектор данных о бизнесах.

    Использует приоритет: API -> MCP -> Scraper
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        batch_size: int = 50,
        max_concurrent: int = 5,
    ):
        """
        Initialize business collector.

        Args:
            api_key: Google Maps API key
            batch_size: Batch size for processing queries
            max_concurrent: Maximum concurrent requests
        """
        from .config import ScraperConfig
        
        config = ScraperConfig()
        if api_key:
            config.api_key = api_key
        
        self.api_client = GoogleMapsAPIClient(config) if (api_key or config.api_key) else None
        self.mcp_client = MCPGoogleMapsClient(config)
        self.scraper = None  # Инициализируется при необходимости
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.logger = logger
        self.progress = CollectionProgress(0, 0, 0, 0, [], datetime.now())
        
        # Database client will be imported when needed to avoid circular imports
        self._db_client = None

    def _get_db_client(self):
        """Get database client (lazy import to avoid circular dependencies)."""
        if self._db_client is None:
            import sys
            from pathlib import Path
            # Add parent directory to path
            sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
            from db.supabase_client import get_db_client
            self._db_client = get_db_client()
        return self._db_client

    async def collect_businesses(
        self,
        queries: List[Dict[str, any]],  # [{query, location, category, ...}]
        use_api: bool = True,
        use_mcp: bool = True,
        use_scraper: bool = False,
    ) -> CollectionProgress:
        """
        Собрать данные о бизнесах по списку запросов.

        Args:
            queries: Список запросов для выполнения
            use_api: Использовать Google Maps API
            use_mcp: Использовать MCP сервер
            use_scraper: Использовать браузерный скрапинг
        """
        self.progress.total_queries = len(queries)

        # Создаем семафор для ограничения параллелизма
        semaphore = asyncio.Semaphore(self.max_concurrent)

        # Группируем запросы в батчи
        for i in range(0, len(queries), self.batch_size):
            batch = queries[i:i + self.batch_size]
            tasks = [
                self._process_query(query, semaphore, use_api, use_mcp, use_scraper)
                for query in batch
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

        return self.progress

    async def _process_query(
        self,
        query: Dict,
        semaphore: asyncio.Semaphore,
        use_api: bool,
        use_mcp: bool,
        use_scraper: bool,
    ):
        """Обработать один запрос."""
        async with semaphore:
            try:
                businesses = await self._fetch_businesses(
                    query, use_api, use_mcp, use_scraper
                )

                # Сохранение в БД батчами
                if businesses:
                    await self._save_businesses(businesses, query.get('category'), query.get('data_source', 'api'))

                self.progress.completed_queries += 1
                self.progress.total_businesses_found += len(businesses)

            except Exception as e:
                self.logger.error(f"Error processing query {query}: {e}")
                self.progress.errors.append(str(e))

    async def _fetch_businesses(
        self,
        query: Dict,
        use_api: bool,
        use_mcp: bool,
        use_scraper: bool,
    ) -> List[BusinessData]:
        """Получить данные о бизнесах с fallback."""
        # Приоритет 1: API
        if use_api and self.api_client:
            try:
                location_tuple = None
                if query.get('location'):
                    loc = query['location']
                    if isinstance(loc, dict):
                        location_tuple = (loc.get('latitude', 50.0755), loc.get('longitude', 14.4378))
                    elif isinstance(loc, tuple):
                        location_tuple = loc
                
                location_dict = None
                if location_tuple:
                    location_dict = {'latitude': location_tuple[0], 'longitude': location_tuple[1]}
                
                businesses = await self.api_client.search_businesses(
                    query['query'],
                    location_dict,
                    query.get('max_results', 20)
                )
                if businesses:
                    return businesses
            except Exception as e:
                self.logger.warning(f"API failed, trying fallback: {e}")

        # Приоритет 2: MCP
        if use_mcp:
            try:
                mcp_available = await self.mcp_client.check_mcp_availability()
                if mcp_available:
                    location_dict = None
                    if query.get('location'):
                        loc = query['location']
                        if isinstance(loc, dict):
                            location_dict = loc
                        elif isinstance(loc, tuple):
                            location_dict = {'latitude': loc[0], 'longitude': loc[1]}
                    
                    businesses = await self.mcp_client.search_places(
                        query['query'],
                        location_dict,
                        query.get('radius')
                    )
                    if businesses:
                        return businesses
            except Exception as e:
                self.logger.warning(f"MCP failed, trying scraper: {e}")

        # Приоритет 3: Scraper
        if use_scraper:
            try:
                if not self.scraper:
                    from .config import ScraperConfig
                    config = ScraperConfig()
                    self.scraper = GoogleMapsScraper(config)
                    await self.scraper.__aenter__()

                location_str = query.get('location')
                if isinstance(location_str, dict):
                    location_str = f"Prague {query.get('district', '')}"
                elif isinstance(location_str, tuple):
                    location_str = "Prague"

                businesses = await self.scraper.search_businesses(
                    query['query'],
                    location_str or "Prague",
                    query.get('max_results', 20)
                )
                if businesses:
                    return businesses
            except Exception as e:
                self.logger.warning(f"Scraper failed: {e}")

        if not use_api and not use_mcp and not use_scraper:
            raise RuntimeError("All data sources disabled")
        
        return []

    async def _save_businesses(
        self,
        businesses: List[BusinessData],
        category: Optional[str],
        data_source: str = 'api',
    ):
        """Сохранить бизнесы в БД с дедупликацией."""
        try:
            db_client = self._get_db_client()
            
            business_creates = []
            for b in businesses:
                try:
                    # Ensure category is set
                    business_category = category or b.category or "unknown"
                    
                    business_create = BusinessCreate(
                        **b.model_dump(exclude_none=True),
                        category=business_category,
                        data_source=data_source
                    )
                    business_creates.append(business_create)
                except Exception as e:
                    self.logger.warning(f"Error creating BusinessCreate: {e}")
                    continue

            if business_creates:
                saved = await db_client.batch_create_businesses(business_creates)
                self.progress.total_businesses_saved += len(saved)
        except Exception as e:
            self.logger.error(f"Error saving businesses to DB: {e}")
            # Fallback: could save to CSV or log
            raise
