# Улучшения поиска бизнесов в Google Maps

## Обзор

Документ содержит рекомендации по улучшению системы сбора данных о бизнесах в Праге на основе исследования лучших практик Google Maps Places API и альтернативных подходов.

---

## 1. Оптимизация использования Google Maps Places API

### 1.1 Использование Places API (New) вместо Legacy

**Проблема**: Legacy API имеет ограничения и будет deprecated.

**Решение**: Перейти на Places API (New) с улучшенными возможностями:

```python
# Использовать новый Text Search вместо Legacy
url = "https://places.googleapis.com/v1/places:searchText"
headers = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": api_key,
    "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location"
}
```

**Преимущества**:

- Более гибкая система полей через FieldMask
- Лучшая производительность
- Поддержка пагинации через `nextPageToken`
- Более структурированные ответы

### 1.2 Правильная реализация пагинации

**Проблема**: Places API возвращает максимум 20 результатов за запрос, но можно получить до 60 используя `nextPageToken`.

**Решение**: Реализовать полную пагинацию:

```python
async def search_places_with_pagination(
    self,
    query: str,
    location: tuple[float, float],
    radius: int = 5000,
    max_results: int = 60  # Максимум для API
) -> List[BusinessData]:
    """Поиск с полной пагинацией до 60 результатов."""
    all_results = []
    next_page_token = None
    page_count = 0
    max_pages = 3  # API позволяет максимум 3 страницы (20*3=60)

    while page_count < max_pages and len(all_results) < max_results:
        # Rate limiting
        await self._wait_for_rate_limit()

        params = {
            "query": query,
            "location": f"{location[0]},{location[1]}",
            "radius": radius,
            "language": "cs"
        }

        # Добавляем токен пагинации если есть
        if next_page_token:
            params["pagetoken"] = next_page_token
            # Важно: нужно подождать несколько секунд перед использованием токена
            await asyncio.sleep(2)

        response = await self._make_api_request(params)

        if response.get("results"):
            all_results.extend(response["results"])

        # Получаем токен следующей страницы
        next_page_token = response.get("next_page_token")

        if not next_page_token:
            break  # Больше страниц нет

        page_count += 1

    return self._parse_api_response(all_results)
```

**Важно**:

- Токен пагинации становится валидным через несколько секунд после предыдущего запроса
- Максимум 3 страницы (60 результатов) на один запрос
- Для получения больше результатов нужно использовать другие стратегии

### 1.3 Использование FieldMask для оптимизации

**Проблема**: Запросы возвращают много ненужных данных, увеличивая время и стоимость.

**Решение**: Использовать FieldMask для запроса только нужных полей:

```python
# Для Places API (New)
field_mask = [
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.location",
    "places.nationalPhoneNumber",
    "places.websiteUri",
    "places.rating",
    "places.userRatingCount",
    "places.types"
]

# Для Legacy API используем параметр fields
fields = "place_id,name,formatted_address,geometry,formatted_phone_number,website,rating,user_ratings_total,types"
```

**Преимущества**:

- Меньше данных передается по сети
- Быстрее обработка
- Меньше стоимость запросов (если используется платный план)

### 1.4 Комбинирование методов поиска

**Проблема**: Один метод поиска не покрывает все случаи.

**Решение**: Использовать несколько методов поиска для максимального покрытия:

```python
async def comprehensive_search(
    self,
    query: str,
    location: tuple[float, float],
    radius: int = 5000
) -> List[BusinessData]:
    """Комплексный поиск используя несколько методов."""
    all_results = []
    seen_place_ids = set()

    # Метод 1: Text Search (лучше для текстовых запросов)
    text_results = await self.text_search(query, location, radius)
    for result in text_results:
        if result.google_place_id not in seen_place_ids:
            all_results.append(result)
            seen_place_ids.add(result.google_place_id)

    # Метод 2: Nearby Search (лучше для категорий)
    # Извлекаем категорию из запроса
    category = self._extract_category_from_query(query)
    if category:
        nearby_results = await self.nearby_search(
            location=location,
            radius=radius,
            type=category
        )
        for result in nearby_results:
            if result.google_place_id not in seen_place_ids:
                all_results.append(result)
                seen_place_ids.add(result.google_place_id)

    # Метод 3: Find Place (для точных совпадений)
    # Если запрос похож на название бизнеса
    if self._looks_like_business_name(query):
        find_results = await self.find_place(query, location)
        for result in find_results:
            if result.google_place_id not in seen_place_ids:
                all_results.append(result)
                seen_place_ids.add(result.google_place_id)

    return all_results
```

### 1.5 Оптимизация радиуса поиска

**Проблема**: Фиксированный радиус может пропускать результаты или возвращать слишком много.

**Решение**: Адаптивный радиус с разбиением на зоны:

```python
async def search_with_adaptive_radius(
    self,
    query: str,
    center: tuple[float, float],
    initial_radius: int = 2000,
    max_radius: int = 10000
) -> List[BusinessData]:
    """Поиск с адаптивным радиусом и разбиением на зоны."""
    all_results = []
    seen_place_ids = set()

    # Стратегия 1: Поиск от центра с увеличивающимся радиусом
    radius = initial_radius
    while radius <= max_radius:
        results = await self.search_places(query, center, radius)

        new_results = [
            r for r in results
            if r.google_place_id not in seen_place_ids
        ]

        if not new_results:
            break  # Больше результатов нет

        all_results.extend(new_results)
        seen_place_ids.update(r.google_place_id for r in new_results)

        radius += 2000  # Увеличиваем радиус

    # Стратегия 2: Разбиение на квадранты для больших радиусов
    if len(all_results) < 50:  # Если результатов мало
        quadrants = self._create_quadrants(center, max_radius)
        for quadrant_center in quadrants:
            results = await self.search_places(query, quadrant_center, max_radius // 2)
            for result in results:
                if result.google_place_id not in seen_place_ids:
                    all_results.append(result)
                    seen_place_ids.add(result.google_place_id)

    return all_results

def _create_quadrants(self, center: tuple[float, float], radius: int) -> List[tuple]:
    """Создать 4 квадранта вокруг центра."""
    lat, lng = center
    # Приблизительное преобразование метров в градусы (для Праги)
    lat_delta = radius / 111000  # ~111 км на градус широты
    lng_delta = radius / (111000 * abs(math.cos(math.radians(lat))))

    return [
        (lat + lat_delta/2, lng + lng_delta/2),  # Северо-восток
        (lat + lat_delta/2, lng - lng_delta/2),  # Северо-запад
        (lat - lat_delta/2, lng + lng_delta/2),  # Юго-восток
        (lat - lat_delta/2, lng - lng_delta/2),  # Юго-запад
    ]
```

---

## 2. Альтернативные источники данных

### 2.1 Чешский бизнес-реестр ARES

**Преимущество**: Официальный источник данных о чешских компаниях.

**Реализация**:

```python
class ARESScraper:
    """Скрапер чешского бизнес-реестра ARES."""

    BASE_URL = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty"

    async def search_businesses(
        self,
        name: Optional[str] = None,
        ico: Optional[str] = None,  # IČO - идентификационный номер компании
        location: Optional[str] = None
    ) -> List[BusinessData]:
        """Поиск в ARES."""
        # ARES API позволяет поиск по названию, IČO, адресу
        # Можно комбинировать с данными Google Maps для верификации
        pass
```

**Использование**:

- Верификация данных из Google Maps
- Получение дополнительной информации (IČO, дата регистрации)
- Поиск бизнесов, которых нет в Google Maps

### 2.2 Комбинирование источников

**Стратегия**: Использовать несколько источников для максимального покрытия:

```python
class MultiSourceCollector:
    """Коллектор использующий несколько источников данных."""

    async def collect_businesses(
        self,
        query: str,
        location: tuple[float, float]
    ) -> List[BusinessData]:
        """Сбор из всех доступных источников."""
        all_results = []
        seen_identifiers = set()

        # Источник 1: Google Maps Places API
        try:
            google_results = await self.google_maps_client.search_places(query, location)
            for result in google_results:
                identifier = result.google_place_id or result.name + result.address
                if identifier not in seen_identifiers:
                    all_results.append(result)
                    seen_identifiers.add(identifier)
        except Exception as e:
            self.logger.warning(f"Google Maps failed: {e}")

        # Источник 2: ARES (для чешских компаний)
        try:
            ares_results = await self.ares_scraper.search_businesses(name=query)
            for result in ares_results:
                identifier = result.ico or result.name + result.address
                if identifier not in seen_identifiers:
                    all_results.append(result)
                    seen_identifiers.add(identifier)
        except Exception as e:
            self.logger.warning(f"ARES failed: {e}")

        # Источник 3: MCP Google Maps (если доступен)
        try:
            mcp_results = await self.mcp_client.search_places(query, location)
            for result in mcp_results:
                identifier = result.google_place_id or result.name + result.address
                if identifier not in seen_identifiers:
                    all_results.append(result)
                    seen_identifiers.add(identifier)
        except Exception as e:
            self.logger.warning(f"MCP failed: {e}")

        return all_results
```

---

## 3. Оптимизация запросов

### 3.1 Локализованные запросы

**Проблема**: Запросы на английском могут давать меньше результатов для чешских бизнесов.

**Решение**: Использовать чешские термины и синонимы:

```python
CZECH_BUSINESS_TERMS = {
    "cafe": ["kavárna", "café", "kavárna", "kavárny"],
    "restaurant": ["restaurace", "restaurací", "jídlo", "oběd"],
    "beauty_salon": ["kadeřnictví", "kosmetika", "salon krásy", "manikúra"],
    "retail": ["obchod", "prodejna", "butik", "obchůdek"],
    "services": ["úklid", "opravy", "servis", "instalatér", "elektrikář"],
    "medical": ["lékař", "zubní lékař", "fyzioterapeut", "masáž", "ordinace"],
    "fitness": ["fitness", "posilovna", "yoga", "pilates", "sportovní centrum"]
}

def generate_localized_queries(category: str, district: str) -> List[str]:
    """Генерация локализованных запросов."""
    terms = CZECH_BUSINESS_TERMS.get(category, [])
    queries = []

    for term in terms:
        # Вариант 1: "термин район"
        queries.append(f"{term} {district}")
        # Вариант 2: "термин в районе"
        queries.append(f"{term} v {district}")
        # Вариант 3: "термин Прага район"
        queries.append(f"{term} Praha {district}")

    return queries
```

### 3.2 Использование типов мест (place types)

**Проблема**: Текстовые запросы могут быть неточными.

**Решение**: Комбинировать текстовые запросы с типами мест:

```python
PLACE_TYPES = {
    "cafe_restaurant": ["cafe", "restaurant", "food", "meal_takeaway"],
    "beauty_salon": ["beauty_salon", "hair_care", "spa"],
    "retail": ["store", "clothing_store", "shoe_store", "jewelry_store"],
    "services": ["plumber", "electrician", "general_contractor"],
    "medical": ["doctor", "dentist", "physiotherapist", "hospital"],
    "fitness": ["gym", "yoga_studio", "sports_club"]
}

async def search_by_type_and_query(
    self,
    query: str,
    location: tuple[float, float],
    category: str
) -> List[BusinessData]:
    """Поиск по типу места и текстовому запросу."""
    all_results = []
    seen_place_ids = set()

    # Поиск по типу места
    types = PLACE_TYPES.get(category, [])
    for place_type in types:
        results = await self.nearby_search(
            location=location,
            radius=5000,
            type=place_type
        )
        for result in results:
            if result.google_place_id not in seen_place_ids:
                all_results.append(result)
                seen_place_ids.add(result.google_place_id)

    # Поиск по текстовому запросу
    text_results = await self.text_search(query, location, 5000)
    for result in text_results:
        if result.google_place_id not in seen_place_ids:
            all_results.append(result)
            seen_place_ids.add(result.google_place_id)

    return all_results
```

### 3.3 Кеширование и дедупликация

**Улучшение**: Более умное кеширование:

```python
class SmartCache:
    """Умный кеш с учетом географии и времени."""

    def __init__(self, ttl_hours: int = 24):
        self.cache: Dict[str, Tuple[Any, datetime]] = {}
        self.ttl = timedelta(hours=ttl_hours)

    def get_cache_key(
        self,
        query: str,
        location: tuple[float, float],
        radius: int
    ) -> str:
        """Генерация ключа кеша с учетом географии."""
        # Округляем координаты для группировки близких запросов
        lat_rounded = round(location[0], 2)  # ~1.1 км точность
        lng_rounded = round(location[1], 2)
        radius_bucket = (radius // 1000) * 1000  # Округляем до километров

        return f"{query}:{lat_rounded}:{lng_rounded}:{radius_bucket}"

    def get(self, key: str) -> Optional[Any]:
        """Получить из кеша если не истек."""
        if key not in self.cache:
            return None

        data, cached_time = self.cache[key]
        if datetime.now() - cached_time > self.ttl:
            del self.cache[key]
            return None

        return data

    def set(self, key: str, value: Any):
        """Сохранить в кеш."""
        self.cache[key] = (value, datetime.now())
```

---

## 4. Обработка ограничений API

### 4.1 Распределение нагрузки по времени

**Проблема**: Rate limits ограничивают скорость сбора.

**Решение**: Распределить запросы по времени:

```python
class TimeDistributedCollector:
    """Коллектор распределяющий запросы по времени."""

    async def collect_over_time(
        self,
        queries: List[Dict],
        hours_per_day: int = 8,
        requests_per_hour: int = 50
    ):
        """Сбор данных распределенный по времени."""
        total_hours = len(queries) / requests_per_hour
        days_needed = math.ceil(total_hours / hours_per_day)

        queries_per_batch = requests_per_hour * hours_per_day

        for day in range(days_needed):
            start_idx = day * queries_per_batch
            end_idx = min(start_idx + queries_per_batch, len(queries))
            batch = queries[start_idx:end_idx]

            # Сбор батча в течение дня
            await self._collect_batch_over_hours(batch, hours_per_day)

            # Пауза между днями
            if day < days_needed - 1:
                await asyncio.sleep(3600 * (24 - hours_per_day))
```

### 4.2 Использование нескольких API ключей

**Решение**: Ротация ключей для увеличения лимитов:

```python
class MultiKeyAPIClient:
    """Клиент с поддержкой нескольких API ключей."""

    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys
        self.current_key_index = 0
        self.key_usage = {key: deque(maxlen=60) for key in api_keys}

    async def _get_available_key(self) -> str:
        """Получить доступный API ключ."""
        # Находим ключ с наименьшим использованием
        available_keys = [
            key for key in self.api_keys
            if len(self.key_usage[key]) < 60
        ]

        if not available_keys:
            # Все ключи на лимите, ждем
            await asyncio.sleep(60)
            return await self._get_available_key()

        # Выбираем ключ с наименьшим использованием
        return min(available_keys, key=lambda k: len(self.key_usage[k]))

    async def make_request(self, params: Dict) -> Dict:
        """Сделать запрос используя доступный ключ."""
        key = await self._get_available_key()
        params["key"] = key

        # Отслеживаем использование
        self.key_usage[key].append(datetime.now())

        return await self._make_api_request(params)
```

---

## 5. Мониторинг и оптимизация качества данных

### 5.1 Метрики качества данных

```python
@dataclass
class DataQualityMetrics:
    """Метрики качества собранных данных."""
    total_businesses: int
    businesses_with_phone: int
    businesses_with_website: int
    businesses_with_rating: int
    businesses_with_address: int
    duplicate_rate: float
    coverage_by_district: Dict[str, int]
    coverage_by_category: Dict[str, int]

    @property
    def phone_coverage(self) -> float:
        return (self.businesses_with_phone / self.total_businesses) * 100

    @property
    def website_coverage(self) -> float:
        return (self.businesses_with_website / self.total_businesses) * 100

    @property
    def data_completeness(self) -> float:
        """Общая полнота данных."""
        fields = [
            self.businesses_with_phone,
            self.businesses_with_website,
            self.businesses_with_rating,
            self.businesses_with_address
        ]
        return sum(fields) / (self.total_businesses * len(fields)) * 100
```

### 5.2 Автоматическое обновление данных

```python
class DataUpdater:
    """Автоматическое обновление данных о бизнесах."""

    async def update_stale_businesses(
        self,
        max_age_days: int = 30
    ):
        """Обновить данные старше указанного возраста."""
        stale_businesses = await self.db_client.get_stale_businesses(max_age_days)

        for business in stale_businesses:
            if business.google_place_id:
                # Обновляем через Place Details API
                updated_data = await self.api_client.get_place_details(
                    business.google_place_id
                )
                await self.db_client.update_business(business.id, updated_data)
```

---

## 6. Рекомендации по реализации

### Приоритет 1: Критичные улучшения

1. ✅ **Реализовать полную пагинацию** - получить до 60 результатов вместо 20
2. ✅ **Использовать Places API (New)** - более современный и эффективный API
3. ✅ **Добавить FieldMask** - оптимизация запросов и снижение стоимости
4. ✅ **Реализовать комбинированный поиск** - Text Search + Nearby Search

### Приоритет 2: Важные улучшения

1. ✅ **Адаптивный радиус поиска** - покрытие большей территории
2. ✅ **Локализованные запросы** - использование чешских терминов
3. ✅ **Умное кеширование** - снижение количества запросов
4. ✅ **Метрики качества данных** - отслеживание полноты данных

### Приоритет 3: Дополнительные улучшения

1. ✅ **Интеграция с ARES** - альтернативный источник данных
2. ✅ **Распределение нагрузки** - избежание rate limits
3. ✅ **Автоматическое обновление** - поддержание актуальности данных
4. ✅ **Мультиключевая ротация** - увеличение лимитов

---

## 7. Примеры кода для интеграции

### Полная реализация пагинации

```python
async def search_places_paginated(
    self,
    query: str,
    location: tuple[float, float],
    radius: int = 5000,
    max_results: int = 60
) -> List[BusinessData]:
    """Полный поиск с пагинацией до 60 результатов."""
    all_results = []
    next_page_token = None
    page = 0
    max_pages = 3

    while page < max_pages and len(all_results) < max_results:
        await self._wait_for_rate_limit()

        params = {
            "query": query,
            "location": f"{location[0]},{location[1]}",
            "radius": radius,
            "language": "cs",
            "key": self.api_key
        }

        if next_page_token:
            params["pagetoken"] = next_page_token
            # Важно: токен становится валидным через несколько секунд
            await asyncio.sleep(3)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://maps.googleapis.com/maps/api/place/textsearch/json",
                params=params
            )
            response.raise_for_status()
            data = response.json()

        if data.get("status") != "OK":
            self.logger.warning(f"API returned status: {data.get('status')}")
            break

        if data.get("results"):
            all_results.extend(data["results"])

        next_page_token = data.get("next_page_token")
        if not next_page_token:
            break

        page += 1

    return self._parse_api_response(all_results)
```

---

## Заключение

Реализация этих улучшений позволит:

1. **Увеличить покрытие** - получить больше результатов (до 60 вместо 20)
2. **Повысить качество** - использование нескольких источников и методов
3. **Оптимизировать затраты** - FieldMask и кеширование снижают стоимость
4. **Улучшить надежность** - fallback на несколько источников
5. **Масштабировать** - распределение нагрузки и ротация ключей

Рекомендуется начать с приоритета 1, затем постепенно внедрять улучшения из приоритетов 2 и 3.
