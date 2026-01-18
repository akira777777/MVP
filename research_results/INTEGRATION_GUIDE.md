# Руководство по интеграции новых библиотек

Документ описывает интеграцию новых библиотек для веб-скрапинга и сбора данных.

## Интегрированные библиотеки

### 1. playwright-stealth ✅

**Интеграция**: Автоматически применяется в `GoogleMapsScraper` при запуске браузера.

**Использование**:

```python
from utils.lead_generation import GoogleMapsScraper, ScraperConfig

config = ScraperConfig(use_stealth=True)  # По умолчанию True
async with GoogleMapsScraper(config) as scraper:
    businesses = await scraper.search_businesses("kavárna", "Prague")
```

**Конфигурация**:

- `use_stealth` в `ScraperConfig` (по умолчанию `True`)
- Автоматически отключается, если библиотека не установлена

---

### 2. phone-email-extractor ✅

**Интеграция**: Автоматически извлекает email и телефоны с веб-сайтов бизнесов.

**Использование**:

```python
from utils.lead_generation import GoogleMapsScraper, ScraperConfig

config = ScraperConfig(extract_contacts_from_website=True)  # По умолчанию True
async with GoogleMapsScraper(config) as scraper:
    businesses = await scraper.search_businesses("kavárna", "Prague")
    # businesses будут содержать email и phone, если найдены на сайте
```

**Конфигурация**:

- `extract_contacts_from_website` в `ScraperConfig` (по умолчанию `True`)
- Автоматически отключается, если библиотека не установлена

**Что извлекается**:

- Email адреса с веб-сайтов бизнесов
- Телефонные номера с веб-сайтов
- Фильтрация невалидных email (example.com, test.com и т.д.)
- Приоритет чешским телефонным номерам

---

### 3. herepy (HERE Places API) ✅

**Интеграция**: Новый клиент `HerePlacesClient` как альтернатива Google Maps API.

**Использование**:

```python
from utils.lead_generation import HerePlacesClient, ScraperConfig

config = ScraperConfig()
config.here_api_key = "YOUR_HERE_API_KEY"  # или через HERE_API_KEY env var

client = HerePlacesClient(config)
businesses = client.search_businesses(
    query="kavárna",
    location={"latitude": 50.0755, "longitude": 14.4378},
    max_results=20
)
```

**Интеграция в коллектор**:

```python
from utils.lead_generation import BusinessCollector

collector = BusinessCollector()
progress = await collector.collect_businesses(
    queries=[{"query": "kavárna", "location": (50.0755, 14.4378)}],
    use_api=False,      # Отключить Google Maps API
    use_here=True,      # Использовать HERE API
    use_mcp=False,
    use_scraper=False
)
```

**Конфигурация**:

- Установите переменную окружения `HERE_API_KEY`
- Или установите `config.here_api_key` в коде
- Или добавьте в `.env` файл: `HERE_API_KEY=your_key`

**Преимущества HERE API**:

- Хорошее покрытие в Европе
- Альтернатива Google Maps при проблемах с API ключом
- Бесплатный лимит: 250,000 запросов/месяц

---

## Обновления моделей данных

### BusinessData

Добавлено новое поле:

- `email: Optional[str]` - Email адрес бизнеса

**Пример**:

```python
from utils.lead_generation import BusinessData

business = BusinessData(
    name="Kavárna U Zlatého lva",
    address="Václavské náměstí 1, Praha 1",
    phone="+420 123 456 789",
    email="info@kavarna.cz",  # Новое поле
    website="https://kavarna.cz",
    category="kavárna"
)
```

---

## Обновления конфигурации

### ScraperConfig

Новые параметры:

```python
@dataclass
class ScraperConfig:
    # ... существующие параметры ...

    # Stealth mode для обхода антибот-защиты
    use_stealth: bool = True

    # Извлечение контактов с веб-сайтов
    extract_contacts_from_website: bool = True

    # HERE API ключ (альтернатива Google Maps)
    here_api_key: Optional[str] = None  # Автоматически загружается из env
```

---

## Примеры использования

### Пример 1: Использование скрапера с stealth и извлечением контактов

```python
import asyncio
from utils.lead_generation import GoogleMapsScraper, ScraperConfig

async def main():
    config = ScraperConfig(
        use_stealth=True,
        extract_contacts_from_website=True,
        headless=True
    )

    async with GoogleMapsScraper(config) as scraper:
        businesses = await scraper.search_businesses(
            query="kadeřnictví",
            location="Prague 1",
            max_results=10
        )

        for business in businesses:
            print(f"{business.name}")
            print(f"  Phone: {business.phone}")
            print(f"  Email: {business.email}")  # Новое поле
            print(f"  Website: {business.website}")
            print()

if __name__ == "__main__":
    asyncio.run(main())
```

### Пример 2: Использование HERE API через коллектор

```python
import asyncio
from utils.lead_generation import BusinessCollector, ScraperConfig

async def main():
    config = ScraperConfig()
    # HERE_API_KEY должен быть установлен в env или config

    collector = BusinessCollector()

    queries = [
        {
            "query": "kavárna",
            "location": {"latitude": 50.0755, "longitude": 14.4378},
            "category": "cafe",
            "max_results": 20
        }
    ]

    progress = await collector.collect_businesses(
        queries=queries,
        use_api=False,      # Отключить Google Maps
        use_here=True,      # Использовать HERE
        use_mcp=False,
        use_scraper=False
    )

    print(f"Найдено бизнесов: {progress.total_businesses_found}")
    print(f"Сохранено: {progress.total_businesses_saved}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Пример 3: Комбинированное использование всех источников

```python
import asyncio
from utils.lead_generation import BusinessCollector

async def main():
    collector = BusinessCollector()

    queries = [
        {"query": "restaurace", "location": (50.0755, 14.4378), "max_results": 20}
    ]

    # Приоритет: Google Maps API -> HERE API -> MCP -> Scraper
    progress = await collector.collect_businesses(
        queries=queries,
        use_api=True,      # Попробовать Google Maps API
        use_here=True,     # Fallback на HERE API
        use_mcp=True,      # Fallback на MCP
        use_scraper=True  # Последний fallback - скрапер
    )

    print(f"Прогресс: {progress.completion_percent:.1f}%")
    print(f"Найдено: {progress.total_businesses_found}")
    print(f"Сохранено: {progress.total_businesses_saved}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Переменные окружения

Добавьте в `.env` файл:

```bash
# Google Maps API (существующий)
GOOGLE_MAPS_API_KEY=your_google_maps_api_key

# HERE API (новый)
HERE_API_KEY=your_here_api_key
```

---

## Проверка установки

Проверьте, что все библиотеки установлены:

```python
# Проверка playwright-stealth
try:
    import playwright_stealth
    print("✅ playwright-stealth установлен")
except ImportError:
    print("❌ playwright-stealth не установлен")

# Проверка phone-email-extractor
try:
    from phone_email_extractor import extract_emails, extract_phones
    print("✅ phone-email-extractor установлен")
except ImportError:
    print("❌ phone-email-extractor не установлен")

# Проверка herepy
try:
    import herepy
    print("✅ herepy установлен")
except ImportError:
    print("❌ herepy не установлен")
```

---

## Примечания

1. **playwright-stealth**: Автоматически применяется, если установлен. Не требует дополнительной настройки.
2. **phone-email-extractor**: Извлечение контактов может замедлить скрапинг, так как требует загрузки веб-сайтов бизнесов. Можно отключить через `extract_contacts_from_website=False`.
3. **HERE API**: Синхронный API, но интегрирован асинхронно через `run_in_executor`. Не требует изменений в коде коллектора.
4. **Обратная совместимость**: Все изменения обратно совместимы. Существующий код продолжит работать без изменений.

---

**Последнее обновление**: Январь 2025
