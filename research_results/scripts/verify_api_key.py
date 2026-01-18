"""
Скрипт для проверки Google Maps API ключа.

Проверяет валидность API ключа и доступность Places API.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional

import httpx

# Добавляем родительскую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_api_key() -> Optional[str]:
    """
    Загрузить API ключ из различных источников.

    Проверяет в следующем порядке:
    1. Переменная окружения GOOGLE_MAPS_API_KEY
    2. Файл .env в корне проекта
    3. Файл config.json в корне проекта
    4. Интерактивный ввод

    Returns:
        API ключ или None
    """
    # 1. Проверка переменной окружения
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if api_key:
        print("✓ API ключ найден в переменных окружения")
        return api_key

    # 2. Проверка .env файла
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GOOGLE_MAPS_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        print("✓ API ключ найден в .env файле")
                        return api_key
        except Exception as e:
            print(f"⚠ Ошибка чтения .env файла: {e}")

    # 3. Проверка config.json
    config_file = Path(__file__).parent.parent / "config.json"
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                api_key = config.get("google_maps_api_key") or config.get(
                    "GOOGLE_MAPS_API_KEY"
                )
                if api_key:
                    print("✓ API ключ найден в config.json")
                    return api_key
        except Exception as e:
            print(f"⚠ Ошибка чтения config.json: {e}")

    # 4. Интерактивный ввод
    print("\n⚠ API ключ не найден в конфигурации.")
    print("Введите API ключ вручную (или нажмите Enter для пропуска):")
    api_key = input("API ключ: ").strip()

    if api_key:
        return api_key

    return None


async def test_places_api_new(api_key: str) -> bool:
    """
    Тест Places API (New) - Text Search.

    Args:
        api_key: Google Maps API ключ

    Returns:
        True если API работает, False иначе
    """
    print("\n🔍 Тестирование Places API (New) - Text Search...")

    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location",
    }
    payload = {"textQuery": "restaurants in Prague", "maxResultCount": 1}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                data = response.json()
                if "places" in data and len(data["places"]) > 0:
                    place = data["places"][0]
                    print(
                        f"✓ API работает! Найден результат: {place.get('displayName', {}).get('text', 'N/A')}"
                    )
                    return True
                else:
                    print("⚠ API вернул пустой результат")
                    return False
            else:
                error_data = (
                    response.json()
                    if response.headers.get("content-type", "").startswith(
                        "application/json"
                    )
                    else {}
                )
                error_msg = error_data.get("error", {}).get("message", response.text)
                print(f"✗ Ошибка API: {response.status_code}")
                print(f"  Сообщение: {error_msg}")
                return False

    except httpx.TimeoutException:
        print("✗ Таймаут при запросе к API")
        return False
    except Exception as e:
        print(f"✗ Ошибка при запросе: {e}")
        return False


async def test_geocoding_api(api_key: str) -> bool:
    """
    Тест Geocoding API.

    Args:
        api_key: Google Maps API ключ

    Returns:
        True если API работает, False иначе
    """
    print("\n🔍 Тестирование Geocoding API...")

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": "Prague, Czech Republic", "key": api_key}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "OK" and data.get("results"):
                    result = data["results"][0]
                    print(
                        f"✓ Geocoding API работает! Адрес: {result.get('formatted_address', 'N/A')}"
                    )
                    return True
                else:
                    status = data.get("status", "UNKNOWN")
                    print(f"✗ Geocoding API вернул статус: {status}")
                    return False
            else:
                print(f"✗ Ошибка Geocoding API: {response.status_code}")
                return False

    except Exception as e:
        print(f"✗ Ошибка при запросе Geocoding API: {e}")
        return False


async def test_places_api_legacy(api_key: str) -> bool:
    """
    Тест Places API (Legacy) - Text Search.

    Args:
        api_key: Google Maps API ключ

    Returns:
        True если API работает, False иначе
    """
    print("\n🔍 Тестирование Places API (Legacy) - Text Search...")

    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {"query": "restaurants in Prague", "key": api_key}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "OK" and data.get("results"):
                    result = data["results"][0]
                    print(
                        f"✓ Legacy API работает! Найден результат: {result.get('name', 'N/A')}"
                    )
                    return True
                else:
                    status = data.get("status", "UNKNOWN")
                    error_msg = data.get("error_message", "")
                    print(f"✗ Legacy API вернул статус: {status}")
                    if error_msg:
                        print(f"  Сообщение: {error_msg}")
                    return False
            else:
                print(f"✗ Ошибка Legacy API: {response.status_code}")
                return False

    except Exception as e:
        print(f"✗ Ошибка при запросе Legacy API: {e}")
        return False


async def main():
    """Основная функция проверки."""
    print("=" * 60)
    print("Проверка Google Maps API ключа")
    print("=" * 60)

    # Загрузка API ключа
    api_key = load_api_key()

    if not api_key:
        print("\n✗ API ключ не найден!")
        print("\nДля получения API ключа следуйте инструкциям в GET_API_KEY.md")
        print("\nПосле получения ключа вы можете:")
        print(
            "1. Установить переменную окружения: export GOOGLE_MAPS_API_KEY='ваш_ключ'"
        )
        print("2. Создать файл .env с: GOOGLE_MAPS_API_KEY=ваш_ключ")
        print('3. Создать файл config.json с: {"google_maps_api_key": "ваш_ключ"}')
        return 1

    # Маскируем ключ для вывода
    masked_key = api_key[:10] + "..." + api_key[-4:] if len(api_key) > 14 else "***"
    print(f"\nИспользуемый API ключ: {masked_key}")

    # Тестирование API
    results = []

    # Тест 1: Places API (New)
    results.append(await test_places_api_new(api_key))

    # Тест 2: Geocoding API
    results.append(await test_geocoding_api(api_key))

    # Тест 3: Places API (Legacy) - для совместимости
    results.append(await test_places_api_legacy(api_key))

    # Итоговый результат
    print("\n" + "=" * 60)
    successful_tests = sum(results)
    total_tests = len(results)

    if successful_tests == total_tests:
        print(f"✓ Все тесты пройдены ({successful_tests}/{total_tests})")
        print(
            "\nAPI ключ работает корректно! Вы можете использовать его для сбора данных."
        )
        return 0
    elif successful_tests > 0:
        print(f"⚠ Частичный успех ({successful_tests}/{total_tests} тестов пройдено)")
        print("\nНекоторые API работают, но есть проблемы. Проверьте:")
        print("1. Включены ли все необходимые API в Google Cloud Console")
        print("2. Правильно ли настроены ограничения API ключа")
        print("3. Не превышены ли квоты запросов")
        return 1
    else:
        print(f"✗ Все тесты провалены ({successful_tests}/{total_tests})")
        print("\nAPI ключ не работает. Возможные причины:")
        print("1. Ключ неверный или неполный")
        print("2. Places API не включен в Google Cloud Console")
        print("3. API ключ имеет ограничения, которые блокируют запросы")
        print("4. Превышены квоты или лимиты")
        print("\nСледуйте инструкциям в GET_API_KEY.md для решения проблемы.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
