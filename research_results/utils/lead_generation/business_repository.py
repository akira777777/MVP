"""
Репозиторий для сохранения бизнесов в БД.

Отвечает за сохранение бизнесов в базу данных с дедупликацией.
"""

import logging
from typing import List, Optional

from .models import BusinessCreate, BusinessData

logger = logging.getLogger(__name__)


class BusinessRepository:
    """
    Репозиторий для сохранения бизнесов в БД.

    Использует lazy import для избежания circular dependencies.
    """

    def __init__(self, db_client=None):
        """
        Initialize business repository.

        Args:
            db_client: Database client (optional, will be loaded lazily if not provided)
        """
        self._db_client = db_client
        self.logger = logger

    def _get_db_client(self):
        """Get database client (lazy import to avoid circular dependencies)."""
        if self._db_client is None:
            import sys
            from pathlib import Path

            # Add parent directory to path (go up to MVP root)
            current_file = Path(__file__)
            mvp_root = current_file.parent.parent.parent.parent
            if str(mvp_root) not in sys.path:
                sys.path.insert(0, str(mvp_root))
            try:
                from db.supabase_client import get_db_client

                self._db_client = get_db_client()
            except ImportError:
                self.logger.error(
                    "Could not import Supabase client. Make sure db/supabase_client.py exists."
                )
                raise
        return self._db_client

    async def save_businesses(
        self,
        businesses: List[BusinessData],
        category: Optional[str] = None,
        data_source: str = "api",
    ) -> int:
        """
        Сохранить бизнесы в БД с дедупликацией.

        Args:
            businesses: List of business data to save
            category: Optional category override
            data_source: Data source identifier (api, mcp, scraper)

        Returns:
            Number of businesses saved
        """
        if not businesses:
            return 0

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
                        data_source=data_source,
                    )
                    business_creates.append(business_create)
                except Exception as e:
                    self.logger.warning(f"Error creating BusinessCreate: {e}")
                    continue

            if business_creates:
                saved = await db_client.batch_create_businesses(business_creates)
                return len(saved)

            return 0
        except Exception as e:
            self.logger.error(f"Error saving businesses to DB: {e}")
            raise
