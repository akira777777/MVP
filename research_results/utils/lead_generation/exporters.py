"""
Экспорт бизнесов в различные форматы.
"""

from typing import List, Optional
from pathlib import Path
import csv
import json
from datetime import datetime

from .models import Business
from utils.logging_config import setup_logging

logger = setup_logging(__name__)


class BusinessExporter:
    """Экспорт бизнесов в различные форматы."""

    def __init__(self):
        """Initialize exporter."""
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

    async def export_to_csv(
        self,
        output_path: Path,
        category: Optional[str] = None,
        district: Optional[str] = None,
    ):
        """
        Экспорт в CSV.

        Args:
            output_path: Path to output CSV file
            category: Optional category filter
            district: Optional district filter
        """
        db_client = self._get_db_client()
        businesses = await db_client.search_businesses(
            category=category,
            district=district
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'name', 'address', 'city', 'district', 'postal_code',
                'phone', 'website', 'category', 'subcategory',
                'rating', 'review_count', 'google_place_id',
                'latitude', 'longitude', 'data_source', 'verified',
                'collected_at', 'updated_at'
            ])
            writer.writeheader()
            for b in businesses:
                writer.writerow({
                    'name': b.name,
                    'address': b.address,
                    'city': b.city or '',
                    'district': b.district or '',
                    'postal_code': b.postal_code or '',
                    'phone': b.phone or '',
                    'website': str(b.website) if b.website else '',
                    'category': b.category,
                    'subcategory': b.subcategory or '',
                    'rating': float(b.rating) if b.rating else '',
                    'review_count': b.review_count or '',
                    'google_place_id': b.google_place_id or '',
                    'latitude': float(b.latitude) if b.latitude else '',
                    'longitude': float(b.longitude) if b.longitude else '',
                    'data_source': b.data_source,
                    'verified': b.verified,
                    'collected_at': b.collected_at.isoformat() if b.collected_at else '',
                    'updated_at': b.updated_at.isoformat() if b.updated_at else '',
                })

        logger.info(f"Exported {len(businesses)} businesses to {output_path}")

    async def export_to_json(
        self,
        output_path: Path,
        category: Optional[str] = None,
        district: Optional[str] = None,
    ):
        """
        Экспорт в JSON.

        Args:
            output_path: Path to output JSON file
            category: Optional category filter
            district: Optional district filter
        """
        db_client = self._get_db_client()
        businesses = await db_client.search_businesses(
            category=category,
            district=district
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = [b.model_dump() for b in businesses]
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"Exported {len(businesses)} businesses to {output_path}")

    async def export_to_excel(
        self,
        output_path: Path,
        category: Optional[str] = None,
        district: Optional[str] = None,
    ):
        """
        Экспорт в Excel.

        Args:
            output_path: Path to output Excel file
            category: Optional category filter
            district: Optional district filter
        """
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas and openpyxl required for Excel export. Install with: pip install pandas openpyxl")
            raise

        db_client = self._get_db_client()
        businesses = await db_client.search_businesses(
            category=category,
            district=district
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to DataFrame
        data = []
        for b in businesses:
            data.append({
                'name': b.name,
                'address': b.address,
                'city': b.city or '',
                'district': b.district or '',
                'postal_code': b.postal_code or '',
                'phone': b.phone or '',
                'website': str(b.website) if b.website else '',
                'category': b.category,
                'subcategory': b.subcategory or '',
                'rating': float(b.rating) if b.rating else None,
                'review_count': b.review_count or None,
                'google_place_id': b.google_place_id or '',
                'latitude': float(b.latitude) if b.latitude else None,
                'longitude': float(b.longitude) if b.longitude else None,
                'data_source': b.data_source,
                'verified': b.verified,
                'collected_at': b.collected_at.isoformat() if b.collected_at else '',
                'updated_at': b.updated_at.isoformat() if b.updated_at else '',
            })

        df = pd.DataFrame(data)
        df.to_excel(output_path, index=False, engine='openpyxl')

        logger.info(f"Exported {len(businesses)} businesses to {output_path}")
