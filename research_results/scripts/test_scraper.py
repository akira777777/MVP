"""
Тестовый скрипт для проверки работы браузерного скрапера.
"""

import asyncio
import sys
from pathlib import Path

# Добавляем родительскую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.lead_generation import GoogleMapsScraper, ScraperConfig


async def test_scraper():
    """Тест браузерного скрапера."""
    print("=" * 60)
    print("Тест браузерного скрапера Google Maps")
    print("=" * 60)

    config = ScraperConfig(
        headless=True,
        max_results_per_query=5,  # Только 5 результатов для теста
        min_delay_seconds=2.0,
        max_delay_seconds=3.0,
    )

    print("\n1. Создание скрапера...")
    scraper = GoogleMapsScraper(config)

    try:
        print("2. Запуск браузера...")
        await scraper.start()
        print("   ✓ Браузер запущен")

        print("\n3. Поиск бизнесов (kavárna в Praha 1)...")
        businesses = await scraper.search_businesses(
            query="kavárna", location="Praha 1", max_results=5
        )

        print(f"\n4. Результаты: найдено {len(businesses)} бизнесов")

        for i, business in enumerate(businesses, 1):
            print(f"\n   Бизнес {i}:")
            print(f"   - Название: {business.name}")
            print(f"   - Адрес: {business.address}")
            if business.phone:
                print(f"   - Телефон: {business.phone}")
            if business.rating:
                print(f"   - Рейтинг: {business.rating}")

        print("\n" + "=" * 60)
        print("✓ Тест завершен успешно!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Ошибка: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("\n5. Закрытие браузера...")
        await scraper.close()
        print("   ✓ Браузер закрыт")


if __name__ == "__main__":
    print("Запуск теста...")
    asyncio.run(test_scraper())
