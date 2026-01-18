# Lead Generation Module

Модуль для сбора информации о малых бизнесах в Праге через Google Maps.

## Компоненты

### Модели данных (`models.py`)
- `BusinessData` - Pydantic модель для представления данных о бизнесе
- Валидация телефонных номеров (чешский формат)
- Нормализация адресов Праги

### Конфигурация (`config.py`)
- `ScraperConfig` - настройки скрапинга (задержки, таймауты, rate limiting)
- Список районов Праги для систематического поиска
- Категории бизнесов для поиска

### Утилиты (`utils.py`)
- Нормализация адресов Праги
- Валидация чешских телефонных номеров
- Дедупликация бизнесов
- Форматирование данных для CSV

### MCP интеграция (`mcp_google_maps.py`)
- `MCPGoogleMapsClient` - клиент для работы с Google Maps MCP сервером
- Автоматический fallback на браузерный скрапинг
- Кеширование результатов

### Браузерный скрапер (`google_maps_scraper.py`)
- `GoogleMapsScraper` - скрапер на основе Playwright
- Извлечение данных со страниц Google Maps
- Обработка пагинации и прокрутки
- Rate limiting для избежания блокировок

## Использование

### Базовое использование

```python
from utils.lead_generation import ScraperConfig, GoogleMapsScraper

config = ScraperConfig(headless=True)
async with GoogleMapsScraper(config) as scraper:
    businesses = await scraper.search_businesses(
        query="kavárna",
        location="Praha 1",
        max_results=20
    )
```

### Использование MCP клиента

```python
from utils.lead_generation import MCPGoogleMapsClient, ScraperConfig

config = ScraperConfig()
client = MCPGoogleMapsClient(config)
mcp_available = await client.check_mcp_availability()

if mcp_available:
    businesses = await client.search_businesses(
        query="kavárna Praha 1",
        location={"latitude": 50.0755, "longitude": 14.4378},
        max_results=20
    )
```

### Запуск основного скрипта

```bash
python scripts/collect_prague_businesses.py
```

Скрипт автоматически:
- Проверяет доступность MCP сервера
- Использует MCP если доступен, иначе браузерный скрапер
- Систематически собирает данные по всем категориям и районам
- Сохраняет прогресс для возможности возобновления
- Экспортирует результаты в CSV

## Выходные данные

Результаты сохраняются в `research_results/prague_businesses.csv` со следующими полями:
- name - название бизнеса
- address - адрес
- phone - телефон
- website - веб-сайт
- category - категория
- rating - рейтинг
- review_count - количество отзывов
- place_id - Google Places ID
- latitude - широта
- longitude - долгота

## Важные замечания

1. **Юридические ограничения**: Google Maps Terms of Service запрещают массовый скрапинг. Рекомендуется использовать официальный Google Maps Places API.

2. **Rate Limiting**: Модуль включает механизмы rate limiting для избежания блокировок. Настройки можно изменить в `ScraperConfig`.

3. **GDPR**: Сбор персональных данных (телефоны) требует соблюдения GDPR.

4. **Возобновление**: Скрипт сохраняет прогресс в `.progress.json` файл, что позволяет возобновить сбор с места остановки.

5. **Дедупликация**: Автоматическое удаление дубликатов на основе названия и адреса.
