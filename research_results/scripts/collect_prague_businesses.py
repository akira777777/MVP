"""
Главная функция сбора данных о бизнесах Праги.

Использует приоритет: API -> MCP -> Scraper
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path (research_results)
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

# Import from local utils.lead_generation module
from utils.lead_generation.collector import BusinessCollector
from utils.lead_generation.utils import generate_prague_queries
from utils.logging_config import setup_logging

# Try to import config from parent directory
try:
    from config import settings
except ImportError:
    # Fallback to environment variables
    import os

    class Settings:
        google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        lead_generation_batch_size = int(os.getenv("LEAD_GENERATION_BATCH_SIZE", "50"))
        lead_generation_use_api = (
            os.getenv("LEAD_GENERATION_USE_API", "true").lower() == "true"
        )
        lead_generation_use_mcp = (
            os.getenv("LEAD_GENERATION_USE_MCP", "true").lower() == "true"
        )
        lead_generation_use_scraper = (
            os.getenv("LEAD_GENERATION_USE_SCRAPER", "false").lower() == "true"
        )

    settings = Settings()

# Setup logging
logger = setup_logging(
    __name__,
    log_level="INFO",
    log_file="collect_prague_businesses.log",
)


async def main():
    """Главная функция сбора данных."""
    logger.info("Starting business data collection for Prague")

    # Генерация запросов для Праги
    queries = generate_prague_queries()
    logger.info(f"Generated {len(queries)} queries")

    # Создание коллектора
    collector = BusinessCollector(
        api_key=settings.google_maps_api_key,
        batch_size=getattr(settings, "lead_generation_batch_size", 50),
        max_concurrent=5,
    )

    # Сбор данных
    progress = await collector.collect_businesses(
        queries,
        use_api=getattr(settings, "lead_generation_use_api", True),
        use_mcp=getattr(settings, "lead_generation_use_mcp", True),
        use_scraper=getattr(settings, "lead_generation_use_scraper", False),
    )

    # Логирование результатов
    logger.info(f"Collection completed: {progress.completion_percent:.1f}%")
    logger.info(f"Total businesses found: {progress.total_businesses_found}")
    logger.info(f"Total businesses saved: {progress.total_businesses_saved}")

    if progress.errors:
        logger.warning(f"Errors encountered: {len(progress.errors)}")
        for error in progress.errors[:10]:  # Show first 10 errors
            logger.warning(f"  - {error}")

    logger.info("Business data collection completed")


if __name__ == "__main__":
    asyncio.run(main())
