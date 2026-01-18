# Настройка MCP Google Maps сервера с API ключом

## Что такое MCP?

MCP (Model Context Protocol) - это протокол для интеграции языковых моделей с внешними сервисами. MCP Google Maps сервер позволяет использовать Google Maps API через стандартизированный интерфейс.

## Предварительные требования

1. Установлен Node.js (версия 18 или выше)
2. Получен Google Maps API ключ (см. `GET_API_KEY.md`)
3. Настроен MCP клиент (например, Cursor, Claude Desktop, или другой)

## Установка MCP Google Maps сервера

### Шаг 1: Установка через npm

MCP Google Maps сервер устанавливается автоматически при первом использовании через `npx`, но вы можете установить его глобально:

```bash
npm install -g @modelcontextprotocol/server-google-maps
```

### Шаг 2: Настройка конфигурации MCP

Конфигурация MCP зависит от вашего клиента. Ниже приведены примеры для популярных клиентов.

#### Для Cursor IDE

Создайте или обновите файл `.mcp.json` в корне проекта или `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "google-maps": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-google-maps"
      ],
      "env": {
        "GOOGLE_MAPS_API_KEY": "ваш_api_ключ_здесь"
      }
    }
  }
}
```

#### Для Claude Desktop

Откройте файл конфигурации Claude Desktop:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Добавьте конфигурацию:

```json
{
  "mcpServers": {
    "google-maps": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-google-maps"
      ],
      "env": {
        "GOOGLE_MAPS_API_KEY": "ваш_api_ключ_здесь"
      }
    }
  }
}
```

#### Для других MCP клиентов

Используйте аналогичную структуру конфигурации с указанием:

- `command`: команда для запуска сервера (обычно `npx`)
- `args`: аргументы команды
- `env`: переменные окружения, включая `GOOGLE_MAPS_API_KEY`

### Шаг 3: Использование переменных окружения (альтернатива)

Вместо хранения ключа в конфигурации MCP, вы можете использовать переменные окружения системы:

**Windows (PowerShell):**

```powershell
$env:GOOGLE_MAPS_API_KEY = "ваш_api_ключ"
```

**Windows (CMD):**

```cmd
set GOOGLE_MAPS_API_KEY=ваш_api_ключ
```

**macOS/Linux:**

```bash
export GOOGLE_MAPS_API_KEY="ваш_api_ключ"
```

Затем в конфигурации MCP уберите секцию `env` или оставьте её пустой:

```json
{
  "mcpServers": {
    "google-maps": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-google-maps"
      ]
    }
  }
}
```

### Шаг 4: Перезапуск MCP клиента

После изменения конфигурации:

1. **Cursor IDE**: Перезапустите Cursor или перезагрузите окно (Ctrl+R / Cmd+R)
2. **Claude Desktop**: Перезапустите приложение
3. **Другие клиенты**: Следуйте инструкциям для вашего клиента

### Шаг 5: Проверка подключения

Используйте скрипт проверки:

```bash
python scripts/verify_api_key.py
```

Или проверьте в вашем MCP клиенте, что сервер Google Maps доступен и отвечает на запросы.

## Использование в коде

После настройки MCP сервера, вы можете использовать его в вашем Python коде:

```python
from utils.lead_generation import MCPGoogleMapsClient, ScraperConfig

config = ScraperConfig()
client = MCPGoogleMapsClient(config)

# Проверка доступности
mcp_available = await client.check_mcp_availability()

if mcp_available:
    # Поиск мест
    businesses = await client.search_businesses(
        query="kavárna Praha 1",
        location={"latitude": 50.0755, "longitude": 14.4378},
        max_results=20
    )
    print(f"Найдено бизнесов: {len(businesses)}")
else:
    print("MCP сервер недоступен, используйте браузерный скрапер")
```

## Безопасность

⚠️ **ВАЖНО**:

1. **Никогда не коммитьте API ключи в git!**
   - Добавьте `.env`, `config.json` и файлы конфигурации MCP в `.gitignore`
   - Используйте переменные окружения или секретные менеджеры для продакшена

2. **Ограничьте API ключ в Google Cloud Console:**
   - Установите ограничения по IP адресам
   - Ограничьте доступные API только необходимыми
   - Установите квоты и лимиты бюджета

3. **Регулярно ротируйте ключи:**
   - Создавайте новые ключи периодически
   - Отзывайте старые неиспользуемые ключи

## Устранение проблем

### MCP сервер не запускается

1. Проверьте, что Node.js установлен: `node --version`
2. Проверьте, что npm доступен: `npm --version`
3. Попробуйте запустить сервер вручную:

   ```bash
   npx -y @modelcontextprotocol/server-google-maps
   ```

### Ошибка "API key not found"

1. Проверьте, что переменная окружения `GOOGLE_MAPS_API_KEY` установлена
2. Проверьте конфигурацию MCP на наличие секции `env`
3. Убедитесь, что ключ скопирован полностью без лишних пробелов

### Ошибка "API key not valid"

1. Проверьте ключ через `verify_api_key.py`
2. Убедитесь, что Places API включен в Google Cloud Console
3. Проверьте ограничения API ключа

### MCP сервер не отвечает

1. Проверьте логи MCP клиента
2. Убедитесь, что порты не заблокированы файрволом
3. Попробуйте перезапустить MCP клиент

## Дополнительные ресурсы

- [MCP Documentation](https://modelcontextprotocol.io/)
- [Google Maps MCP Server](https://github.com/modelcontextprotocol/servers/tree/main/src/google-maps)
- [GET_API_KEY.md](./GET_API_KEY.md) - инструкция по получению API ключа
