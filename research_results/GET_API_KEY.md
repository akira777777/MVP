# Как получить API ключ от Google Maps Places API

## Пошаговая инструкция

### Шаг 1: Создайте аккаунт Google Cloud

1. Перейдите на [Google Cloud Console](https://console.cloud.google.com/)
2. Войдите в свой Google аккаунт (или создайте новый)
3. Если у вас еще нет проекта, нажмите на выпадающий список проектов вверху и выберите **"New Project"**

### Шаг 2: Создайте новый проект (если нужно)

1. Нажмите **"New Project"**
2. Введите название проекта (например, "Prague Business Search")
3. Нажмите **"Create"**
4. Дождитесь создания проекта (обычно несколько секунд)

### Шаг 3: Включите Places API

1. В меню слева выберите **"APIs & Services"** → **"Library"**
2. В поиске введите **"Places API"**
3. Выберите **"Places API (New)"** или **"Places API"**
4. Нажмите кнопку **"Enable"** (Включить)
5. Дождитесь активации API

**Важно**: Включите также следующие API для полной функциональности:

- **Places API (New)** - основной API для поиска мест
- **Geocoding API** - для преобразования адресов в координаты
- **Maps JavaScript API** - может потребоваться для некоторых функций

### Шаг 4: Создайте API ключ

1. В меню слева выберите **"APIs & Services"** → **"Credentials"**
2. Нажмите кнопку **"+ CREATE CREDENTIALS"** вверху страницы
3. Выберите **"API key"**
4. Скопируйте созданный API ключ (он будет показан в модальном окне)

**⚠️ ВАЖНО**: Не закрывайте это окно, пока не скопируете ключ! После закрытия вы не сможете увидеть полный ключ снова.

### Шаг 5: Ограничьте API ключ (рекомендуется)

Для безопасности рекомендуется ограничить использование ключа:

1. В списке API ключей нажмите на только что созданный ключ
2. В разделе **"API restrictions"** выберите **"Restrict key"**
3. Выберите только нужные API:
   - Places API (New)
   - Geocoding API
   - Maps JavaScript API
4. В разделе **"Application restrictions"** выберите:
   - **"IP addresses (web servers, cron jobs, etc.)"** - если используете с сервера
   - **"None"** - для тестирования (не рекомендуется для продакшена)
5. Нажмите **"Save"**

### Шаг 6: Сохраните API ключ

Сохраните ваш API ключ в безопасном месте. Вы можете:

**Вариант 1: Использовать переменные окружения (рекомендуется)**

Создайте файл `.env` в корне проекта:

```bash
GOOGLE_MAPS_API_KEY=ваш_api_ключ_здесь
```

**Вариант 2: Использовать файл конфигурации**

Создайте файл `config.json`:

```json
{
  "google_maps_api_key": "ваш_api_ключ_здесь"
}
```

**Вариант 3: Настроить MCP сервер**

Если вы используете MCP сервер, добавьте ключ в конфигурацию MCP (см. `SETUP_MCP.md`)

### Шаг 7: Проверьте API ключ

Запустите скрипт проверки:

```bash
python scripts/verify_api_key.py
```

Или проверьте вручную через curl:

```bash
curl "https://places.googleapis.com/v1/places:searchText" \
  -H "Content-Type: application/json" \
  -H "X-Goog-Api-Key: ВАШ_API_КЛЮЧ" \
  -d '{
    "textQuery": "restaurants in Prague"
  }'
```

## Бесплатный лимит

Google предоставляет **$200 бесплатных кредитов** каждый месяц, что включает:

- **Places API (New)**:
  - Text Search: $32 за 1000 запросов
  - Place Details: $17 за 1000 запросов
  - Autocomplete: $2.83 за 1000 запросов

- **Geocoding API**: $5 за 1000 запросов

**Пример**: С $200 кредитами вы можете сделать примерно:

- ~6,250 Text Search запросов
- ~11,700 Place Details запросов
- ~70,600 Autocomplete запросов

## Настройка биллинга (опционально)

Если вы планируете использовать больше бесплатного лимита:

1. В меню слева выберите **"Billing"**
2. Нажмите **"Link a billing account"**
3. Добавьте способ оплаты (карта)
4. Установите лимиты бюджета для предотвращения неожиданных расходов

**Рекомендация**: Установите лимит бюджета на $10-20 в месяц для начала.

## Устранение проблем

### Ошибка "API key not valid"

1. Проверьте, что вы скопировали ключ полностью
2. Убедитесь, что Places API включен в проекте
3. Проверьте ограничения API ключа (должны включать Places API)

### Ошибка "This API project is not authorized to use this API"

1. Перейдите в **"APIs & Services"** → **"Library"**
2. Найдите **"Places API"** и убедитесь, что он включен
3. Если не включен, нажмите **"Enable"**

### Ошибка "REQUEST_DENIED"

1. Проверьте ограничения IP-адресов в настройках ключа
2. Убедитесь, что ваш IP-адрес добавлен в список разрешенных
3. Для тестирования можно временно установить "None" в Application restrictions

### Ошибка "OVER_QUERY_LIMIT"

1. Вы превысили квоту запросов
2. Подождите или увеличьте квоту в настройках проекта
3. Проверьте биллинг аккаунт

## Дополнительные ресурсы

- [Документация Places API (New)](https://developers.google.com/maps/documentation/places/web-service)
- [Цены на Google Maps Platform](https://developers.google.com/maps/billing-and-pricing/pricing)
- [Руководство по безопасности API ключей](https://developers.google.com/maps/api-security-best-practices)

## Быстрая ссылка

- [Google Cloud Console](https://console.cloud.google.com/)
- [Places API Library](https://console.cloud.google.com/apis/library/places-backend.googleapis.com)
- [Credentials Page](https://console.cloud.google.com/apis/credentials)
