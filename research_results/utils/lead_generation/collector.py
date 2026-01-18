"""
Асинхронный коллектор данных о бизнесах.

Использует приоритет: API -> HERE -> MCP -> Scraper
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from utils.logging_config import setup_logging

from .business_repository import BusinessRepository
from .config import ScraperConfig
from .data_source_coordinator import DataSourceCoordinator

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

    Координирует сбор данных из различных источников с батчингом и параллелизмом.
    Использует приоритет: API -> HERE -> MCP -> Scraper
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        batch_size: int = 50,
        max_concurrent: int = 5,
        db_client=None,
    ):
        """
        Initialize business collector.

        Args:
            api_key: Google Maps API key
            batch_size: Batch size for processing queries
            max_concurrent: Maximum concurrent requests
            db_client: Optional database client (for dependency injection)
        """
        config = ScraperConfig()
        if api_key:
            config.api_key = api_key

        # Initialize components
        self.data_source_coordinator = DataSourceCoordinator(config)
        self.business_repository = BusinessRepository(db_client)

        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.logger = logger
        self.progress = CollectionProgress(0, 0, 0, 0, [], datetime.now())

    async def collect_businesses(
        self,
        queries: List[Dict[str, any]],  # [{query, location, category, ...}]
        use_api: bool = True,
        use_here: bool = False,
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
            batch = queries[i : i + self.batch_size]
            tasks = [
                self._process_query(
                    query, semaphore, use_api, use_here, use_mcp, use_scraper
                )
                for query in batch
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

        return self.progress

    async def _process_query(
        self,
        query: Dict,
        semaphore: asyncio.Semaphore,
        use_api: bool,
        use_here: bool,
        use_mcp: bool,
        use_scraper: bool,
    ):
        """Обработать один запрос."""
        async with semaphore:
            try:
                # Fetch businesses using coordinator
                businesses = await self.data_source_coordinator.fetch_businesses(
                    query, use_api, use_here, use_mcp, use_scraper
                )

                # Save businesses using repository
                if businesses:
                    saved_count = await self.business_repository.save_businesses(
                        businesses,
                        query.get("category"),
                        query.get("data_source", "api"),
                    )
                    self.progress.total_businesses_saved += saved_count

                self.progress.completed_queries += 1
                self.progress.total_businesses_found += len(businesses)

            except Exception as e:
                self.logger.error(f"Error processing query {query}: {e}")
                self.progress.errors.append(str(e))

    async def close(self):
        """Close all resources."""
        await self.data_source_coordinator.close()
