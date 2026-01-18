"""
Тестовый скрипт для демонстрации использования BusinessCollector с HERE API.
"""

import asyncio
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.lead_generation import BusinessCollector


async def main():
    """Демонстрация использования BusinessCollector с HERE API."""

    print("=" * 70)
    print("ТЕСТ BusinessCollector с HERE API")
    print("=" * 70)
    print()

    # Создаем коллектор
    collector = BusinessCollector()

    # Проверяем доступность HERE клиента
    if collector.here_client:
        print("✓ HERE API клиент инициализирован")
    else:
        print("⚠ HERE API клиент недоступен (проверьте HERE_API_KEY)")
        print("  Продолжаем без HERE API...")

    # Пример запросов
    queries = [
        {
            "query": "kavárna",
            "location": (50.0755, 14.4378),  # Prague center
            "category": "cafe",
            "max_results": 10,
        },
        {
            "query": "kadeřnictví",
            "location": (50.0755, 14.4378),
            "category": "hair_salon",
            "max_results": 10,
        },
    ]

    print(f"\nЗапросов для обработки: {len(queries)}")
    print(f"Категории: {', '.join([q['query'] for q in queries])}")
    print()

    # Собираем данные используя только HERE API
    print("Запуск сбора данных...")
    print("  use_api=False (отключен Google Maps API)")
    print("  use_here=True (используется HERE API)")
    print("  use_mcp=False")
    print("  use_scraper=False")
    print()

    try:
        progress = await collector.collect_businesses(
            queries=queries,
            use_api=False,  # Отключить Google Maps API
            use_here=True,  # Использовать HERE API
            use_mcp=False,
            use_scraper=False,
        )

        print("\n" + "=" * 70)
        print("РЕЗУЛЬТАТЫ")
        print("=" * 70)
        print(
            f"Запросов обработано: {progress.completed_queries}/{progress.total_queries}"
        )
        print(f"Прогресс: {progress.completion_percent:.1f}%")
        print(f"Найдено бизнесов: {progress.total_businesses_found}")
        print(f"Сохранено в БД: {progress.total_businesses_saved}")

        if progress.errors:
            print(f"\nОшибки ({len(progress.errors)}):")
            for error in progress.errors[:5]:  # Показываем первые 5
                print(f"  - {error}")

    except Exception as e:
        print(f"\n✗ Ошибка при сборе данных: {e}")
        import traceback

        traceback.print_exc()

    # Закрываем скрапер если был открыт
    if collector.scraper:
        try:
            await collector.scraper.__aexit__(None, None, None)
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())
