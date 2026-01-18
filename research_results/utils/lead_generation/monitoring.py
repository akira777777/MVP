"""
Мониторинг и метрики сбора данных.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict


@dataclass
class CollectionMetrics:
    """Метрики сбора данных."""
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    total_businesses_found: int = 0
    total_businesses_saved: int = 0
    duplicates_skipped: int = 0
    errors_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    businesses_by_category: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    businesses_by_district: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        if self.total_queries == 0:
            return 0.0
        return (self.successful_queries / self.total_queries) * 100

    @property
    def duration(self) -> Optional[float]:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def to_dict(self) -> Dict:
        """Экспорт метрик в словарь."""
        return {
            'total_queries': self.total_queries,
            'successful_queries': self.successful_queries,
            'failed_queries': self.failed_queries,
            'success_rate': f"{self.success_rate:.2f}%",
            'total_businesses_found': self.total_businesses_found,
            'total_businesses_saved': self.total_businesses_saved,
            'duplicates_skipped': self.duplicates_skipped,
            'duration_seconds': self.duration,
            'businesses_by_category': dict(self.businesses_by_category),
            'businesses_by_district': dict(self.businesses_by_district),
            'errors': dict(self.errors_by_type),
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
        }

    def record_success(self, businesses_found: int = 0, businesses_saved: int = 0):
        """Записать успешный запрос."""
        self.total_queries += 1
        self.successful_queries += 1
        self.total_businesses_found += businesses_found
        self.total_businesses_saved += businesses_saved

    def record_failure(self, error_type: str, error_message: str = ""):
        """Записать неудачный запрос."""
        self.total_queries += 1
        self.failed_queries += 1
        self.errors_by_type[error_type] += 1

    def record_business(self, category: str, district: Optional[str] = None):
        """Записать найденный бизнес."""
        self.businesses_by_category[category] += 1
        if district:
            self.businesses_by_district[district] += 1

    def record_duplicate(self):
        """Записать пропущенный дубликат."""
        self.duplicates_skipped += 1

    def finish(self):
        """Завершить сбор метрик."""
        self.end_time = datetime.now()
