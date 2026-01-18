"""
Параллельный запуск 5 агентов для скрапинга бизнесов по разным запросам.

Каждый агент работает независимо со своим поисковым запросом:
- barbershop
- tetovani
- restaurace
- lounge
- kavarna (дополнительный запрос)
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List

# Add current directory to path (research_results)
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

from utils.lead_generation.collector import BusinessCollector, CollectionProgress
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
    log_file="collect_parallel_agents.log",
)


# Поисковые запросы для каждого агента
AGENT_QUERIES = [
    {
        "name": "barbershop",
        "query": "barbershop",
        "category": "barbershop",
    },
    {
        "name": "tetovani",
        "query": "tetovani",
        "category": "tattoo",
    },
    {
        "name": "restaurace",
        "query": "restaurace",
        "category": "restaurant",
    },
    {
        "name": "lounge",
        "query": "lounge",
        "category": "lounge",
    },
    {
        "name": "kavarna",
        "query": "kavarna",
        "category": "cafe",
    },
]

# Центр Праги (координаты)
PRAGUE_CENTER = (50.0755, 14.4378)

# Районы Праги для поиска
PRAGUE_DISTRICTS = [
    "Prague 1",
    "Prague 2",
    "Prague 3",
    "Prague 4",
    "Prague 5",
    "Prague 6",
    "Prague 7",
    "Prague 8",
    "Prague 9",
    "Prague 10",
]


def generate_queries_for_agent(agent_config: Dict) -> List[Dict]:
    """
    Генерация запросов для одного агента.

    Args:
        agent_config: Конфигурация агента с query и category

    Returns:
        Список запросов для выполнения
    """
    queries = []
    base_query = agent_config["query"]
    category = agent_config["category"]

    # Генерируем запросы для каждого района
    for district in PRAGUE_DISTRICTS:
        queries.append(
            {
                "query": f"{base_query} {district}",
                "location": PRAGUE_CENTER,
                "category": category,
                "radius": 5000,
                "district": district,
                "max_results": 20,
            }
        )

    # Также добавляем общий запрос по Праге
    queries.append(
        {
            "query": f"{base_query} Prague",
            "location": PRAGUE_CENTER,
            "category": category,
            "radius": 10000,
            "district": None,
            "max_results": 50,
        }
    )

    return queries


async def run_agent(
    agent_config: Dict,
    agent_id: int,
    use_api: bool = True,
    use_mcp: bool = True,
    use_scraper: bool = False,
) -> CollectionProgress:
    """
    Запуск одного агента для сбора данных.

    Args:
        agent_config: Конфигурация агента
        agent_id: ID агента (для логирования)
        use_api: Использовать Google Maps API
        use_mcp: Использовать MCP сервер
        use_scraper: Использовать браузерный скрапинг

    Returns:
        Прогресс сбора данных
    """
    agent_name = agent_config["name"]
    logger.info(f"[Agent {agent_id}] Starting agent: {agent_name}")

    # Генерация запросов для агента
    queries = generate_queries_for_agent(agent_config)
    logger.info(f"[Agent {agent_id}] Generated {len(queries)} queries for {agent_name}")

    # Создание коллектора для агента
    collector = BusinessCollector(
        api_key=settings.google_maps_api_key,
        batch_size=getattr(settings, "lead_generation_batch_size", 50),
        max_concurrent=3,  # По 3 параллельных запроса на агента
    )

    try:
        # Сбор данных
        progress = await collector.collect_businesses(
            queries,
            use_api=use_api,
            use_mcp=use_mcp,
            use_scraper=use_scraper,
        )

        # Логирование результатов
        logger.info(
            f"[Agent {agent_id}] {agent_name} completed: "
            f"{progress.completion_percent:.1f}%"
        )
        logger.info(
            f"[Agent {agent_id}] {agent_name} found: "
            f"{progress.total_businesses_found} businesses"
        )
        logger.info(
            f"[Agent {agent_id}] {agent_name} saved: "
            f"{progress.total_businesses_saved} businesses"
        )

        if progress.errors:
            logger.warning(
                f"[Agent {agent_id}] {agent_name} errors: {len(progress.errors)}"
            )
            for error in progress.errors[:5]:  # Show first 5 errors
                logger.warning(f"[Agent {agent_id}]   - {error}")

        return progress

    except Exception as e:
        logger.error(f"[Agent {agent_id}] {agent_name} failed: {e}", exc_info=True)
        # Возвращаем пустой прогресс при ошибке
        from datetime import datetime

        return CollectionProgress(0, 0, 0, 0, [str(e)], datetime.now())


async def main():
    """Главная функция параллельного запуска агентов."""
    logger.info("=" * 80)
    logger.info("Starting parallel agents collection")
    logger.info(f"Total agents: {len(AGENT_QUERIES)}")
    logger.info("=" * 80)

    # Настройки источников данных
    use_api = getattr(settings, "lead_generation_use_api", True)
    use_mcp = getattr(settings, "lead_generation_use_mcp", True)
    use_scraper = getattr(settings, "lead_generation_use_scraper", False)

    logger.info(
        f"Data sources - API: {use_api}, MCP: {use_mcp}, Scraper: {use_scraper}"
    )

    # Запуск всех агентов параллельно
    tasks = [
        run_agent(
            agent_config,
            agent_id=i + 1,
            use_api=use_api,
            use_mcp=use_mcp,
            use_scraper=use_scraper,
        )
        for i, agent_config in enumerate(AGENT_QUERIES)
    ]

    # Ожидание завершения всех агентов
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Подсчет итоговых результатов
    total_found = 0
    total_saved = 0
    total_errors = 0

    logger.info("=" * 80)
    logger.info("Collection Summary")
    logger.info("=" * 80)

    for i, (agent_config, result) in enumerate(zip(AGENT_QUERIES, results)):
        agent_name = agent_config["name"]
        if isinstance(result, Exception):
            logger.error(
                f"[Agent {i + 1}] {agent_name} failed with exception: {result}"
            )
            total_errors += 1
        elif isinstance(result, CollectionProgress):
            total_found += result.total_businesses_found
            total_saved += result.total_businesses_saved
            total_errors += len(result.errors)
            logger.info(
                f"[Agent {i + 1}] {agent_name}: "
                f"Found={result.total_businesses_found}, "
                f"Saved={result.total_businesses_saved}, "
                f"Errors={len(result.errors)}"
            )

    logger.info("=" * 80)
    logger.info(f"Total businesses found: {total_found}")
    logger.info(f"Total businesses saved: {total_saved}")
    logger.info(f"Total errors: {total_errors}")
    logger.info("=" * 80)
    logger.info("Parallel agents collection completed")


if __name__ == "__main__":
    asyncio.run(main())
