# Использование BusinessCollector с HERE API

## Обзор

`BusinessCollector` - это универсальный асинхронный коллектор данных о бизнесах, который поддерживает несколько источников данных с автоматическим fallback.

## Поддерживаемые источники

1. **Google Maps API** (`use_api=True`)
2. **HERE Places API** (`use_here=True`) ✅
3. **MCP Google Maps** (`use_mcp=True`)
4. **Browser Scraper** (`use_scraper=True`)

## Базовое использование

### Пример 1: Только HERE API

```python
import asyncio
from utils.lead_generation import BusinessCollector

async def main():
    collector = BusinessCollector()

    progress = await collector.collect_businesses(
        queries=[
            {
                "query": "kavárna",
                "location": (50.0755, 14.4378),  # Prague center
                "category": "cafe",
                "max_results": 20,
            }
        ],
        use_api=False,      # Отключить Google Maps API
        use_here=True,      # Использовать HERE API
        use_mcp=False,
        use_scraper=False
    )

    print(f"Найдено: {progress.total_businesses_found}")
    print(f"Сохранено: {progress.total_businesses_saved}")

asyncio.run(main())
```

### Пример 2: Множественные запросы

```python
queries = [
    {"query": "kavárna", "location": (50.0755, 14.4378), "category": "cafe"},
    {"query": "kadeřnictví", "location": (50.0755, 14.4378), "category": "hair_salon"},
    {"query": "kosmetika", "location": (50.0755, 14.4378), "category": "beauty"},
]

progress = await collector.collect_businesses(
    queries=queries,
    use_api=False,
    use_here=True,
    use_mcp=False,
    use_scraper=False
)
```

### Пример 3: Fallback цепочка (приоритет)

```python
# Попробует источники в порядке приоритета:
# 1. Google Maps API (если use_api=True)
# 2. HERE API (если use_here=True и API #1 не сработал)
# 3. MCP (если use_mcp=True и предыдущие не сработали)
# 4. Scraper (если use_scraper=True и предыдущие не сработали)

progress = await collector.collect_businesses(
    queries=[{"query": "restaurace", "location": (50.0755, 14.4378)}],
    use_api=True,      # Попробовать сначала Google Maps API
    use_here=True,     # Fallback на HERE API
    use_mcp=True,      # Fallback на MCP
    use_scraper=False  # Не использовать scraper
)
```

## Формат запросов

Каждый запрос в списке `queries` может содержать:

```python
{
    "query": str,              # Поисковый запрос (обязательно)
    "location": tuple | dict,  # Координаты или адрес
    "category": str,           # Категория бизнеса (опционально)
    "max_results": int,        # Максимум результатов (по умолчанию 20)
    "radius": int,             # Радиус поиска в метрах (для некоторых источников)
    "data_source": str,        # Источник данных для метаданных
}
```

### Форматы location

**Tuple (широта, долгота):**

```python
"location": (50.0755, 14.4378)
```

**Dict:**

```python
"location": {"latitude": 50.0755, "longitude": 14.4378}
```

## Настройка

### 1. HERE API ключ

Установите переменную окружения или добавьте в `.env`:

```
HERE_API_KEY=your_api_key_here
```

### 2. Параметры коллектора

```python
collector = BusinessCollector(
    api_key=None,           # Google Maps API key (опционально)
    batch_size=50,          # Размер батча для обработки
    max_concurrent=5,       # Максимум параллельных запросов
)
```

## Результаты

`collect_businesses` возвращает объект `CollectionProgress`:

```python
@dataclass
class CollectionProgress:
    total_queries: int           # Всего запросов
    completed_queries: int        # Завершено запросов
    total_businesses_found: int   # Найдено бизнесов
    total_businesses_saved: int   # Сохранено в БД
    errors: List[str]            # Список ошибок
    start_time: datetime         # Время начала

    @property
    def completion_percent(self) -> float:
        # Процент завершения
```

## Сохранение данных

По умолчанию `BusinessCollector` сохраняет данные в Supabase базу данных через `db_client.batch_create_businesses()`.

Если база данных недоступна, будет выброшено исключение. В будущем можно добавить fallback на CSV файл.

## Тестирование

Запустите тестовый скрипт:

```bash
python scripts\test_business_collector.py
```

## Обработка ошибок

Коллектор обрабатывает ошибки автоматически:

- Если один источник не работает, пробует следующий в цепочке приоритетов
- Ошибки логируются и добавляются в `progress.errors`
- Сбор данных продолжается даже при ошибках в отдельных запросах

## Пример полного использования

```python
import asyncio
from utils.lead_generation import BusinessCollector

async def collect_prague_businesses():
    """Собрать данные о бизнесах в Праге используя HERE API."""

    collector = BusinessCollector()

    # Категории для поиска
    categories = [
        ("kavárna", "cafe"),
        ("kadeřnictví", "hair_salon"),
        ("kosmetika", "beauty"),
        ("restaurace", "restaurant"),
    ]

    # Prague center coordinates
    prague_center = (50.0755, 14.4378)

    # Формируем запросы
    queries = [
        {
            "query": query,
            "location": prague_center,
            "category": category,
            "max_results": 20,
        }
        for query, category in categories
    ]

    # Собираем данные
    progress = await collector.collect_businesses(
        queries=queries,
        use_api=False,      # Отключить Google Maps API
        use_here=True,      # Использовать HERE API
        use_mcp=False,
        use_scraper=False
    )

    # Выводим результаты
    print(f"\n{'='*70}")
    print("РЕЗУЛЬТАТЫ СБОРА")
    print(f"{'='*70}")
    print(f"Запросов: {progress.completed_queries}/{progress.total_queries}")
    print(f"Найдено бизнесов: {progress.total_businesses_found}")
    print(f"Сохранено в БД: {progress.total_businesses_saved}")
    print(f"Ошибок: {len(progress.errors)}")

    return progress

if __name__ == "__main__":
    asyncio.run(collect_prague_businesses())
```

## Преимущества BusinessCollector

- ✅ **Асинхронность**: Параллельная обработка запросов
- ✅ **Fallback**: Автоматический переход между источниками
- ✅ **Батчинг**: Эффективная обработка больших объемов данных
- ✅ **Дедупликация**: Автоматическое удаление дубликатов при сохранении
- ✅ **Прогресс**: Трекинг прогресса сбора данных
- ✅ **Гибкость**: Легко включать/отключать источники

## Сравнение с прямым использованием клиентов

| Метод | Преимущества | Недостатки |
|-------|-------------|------------|
| **BusinessCollector** | Fallback, батчинг, прогресс, БД | Более сложный API |
| **Прямой клиент** | Простота, контроль | Нет fallback, ручная обработка |

Используйте `BusinessCollector` для production-сборов данных, прямые клиенты - для тестирования и простых случаев.
