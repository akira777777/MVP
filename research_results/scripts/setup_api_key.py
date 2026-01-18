"""
Скрипт для настройки Google Maps API ключа.

Интерактивно помогает настроить API ключ в различных форматах конфигурации.
"""

import json
import os
import sys
from pathlib import Path

# Добавляем родительскую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))


def create_env_file(api_key: str, env_path: Path) -> bool:
    """
    Создать или обновить .env файл.

    Args:
        api_key: API ключ
        env_path: Путь к .env файлу

    Returns:
        True если успешно
    """
    try:
        # Читаем существующий файл если есть
        existing_lines = []
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                existing_lines = f.readlines()

        # Обновляем или добавляем GOOGLE_MAPS_API_KEY
        updated = False
        new_lines = []
        for line in existing_lines:
            if line.strip().startswith("GOOGLE_MAPS_API_KEY="):
                new_lines.append(f'GOOGLE_MAPS_API_KEY="{api_key}"\n')
                updated = True
            else:
                new_lines.append(line)

        if not updated:
            new_lines.append(f'GOOGLE_MAPS_API_KEY="{api_key}"\n')

        # Записываем файл
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        return True
    except Exception as e:
        print(f"✗ Ошибка при создании .env файла: {e}")
        return False


def create_config_json(api_key: str, config_path: Path) -> bool:
    """
    Создать или обновить config.json файл.

    Args:
        api_key: API ключ
        config_path: Путь к config.json файлу

    Returns:
        True если успешно
    """
    try:
        # Читаем существующий конфиг если есть
        config = {}
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

        # Обновляем API ключ
        config["google_maps_api_key"] = api_key

        # Записываем файл
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        return True
    except Exception as e:
        print(f"✗ Ошибка при создании config.json: {e}")
        return False


def setup_mcp_config(api_key: str) -> bool:
    """
    Показать инструкции по настройке MCP сервера.

    Args:
        api_key: API ключ

    Returns:
        True если инструкции показаны
    """
    print("\n" + "=" * 60)
    print("Настройка MCP Google Maps сервера")
    print("=" * 60)

    print("\nДля использования API ключа с MCP сервером:")
    print(
        "\n1. Найдите файл конфигурации MCP (обычно ~/.config/mcp/settings.json или .mcp.json)"
    )
    print("\n2. Добавьте или обновите конфигурацию Google Maps сервера:")
    print(
        "\n"
        + json.dumps(
            {
                "mcpServers": {
                    "google-maps": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-google-maps"],
                        "env": {"GOOGLE_MAPS_API_KEY": api_key},
                    }
                }
            },
            indent=2,
        )
    )

    print("\n3. Перезапустите MCP сервер или приложение, использующее MCP")

    return True


def main():
    """Основная функция настройки."""
    print("=" * 60)
    print("Настройка Google Maps API ключа")
    print("=" * 60)

    # Проверяем, есть ли уже ключ
    existing_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if existing_key:
        masked_key = (
            existing_key[:10] + "..." + existing_key[-4:]
            if len(existing_key) > 14
            else "***"
        )
        print(f"\n⚠ Найден существующий API ключ в переменных окружения: {masked_key}")
        use_existing = input("Использовать существующий ключ? (y/n): ").strip().lower()
        if use_existing == "y":
            api_key = existing_key
        else:
            api_key = input("\nВведите новый API ключ: ").strip()
    else:
        print("\nВведите ваш Google Maps API ключ.")
        print("Если у вас его нет, следуйте инструкциям в GET_API_KEY.md")
        api_key = input("\nAPI ключ: ").strip()

    if not api_key:
        print("\n✗ API ключ не введен. Выход.")
        return 1

    # Проверяем формат ключа (базовая валидация)
    if len(api_key) < 20:
        print("\n⚠ Предупреждение: API ключ кажется слишком коротким.")
        continue_anyway = input("Продолжить? (y/n): ").strip().lower()
        if continue_anyway != "y":
            return 1

    print("\n" + "=" * 60)
    print("Выберите способ сохранения API ключа:")
    print("=" * 60)
    print("1. Создать/обновить .env файл (рекомендуется)")
    print("2. Создать/обновить config.json")
    print("3. Показать инструкции для MCP сервера")
    print("4. Все вышеперечисленное")
    print("5. Только показать инструкции (не сохранять)")

    choice = input("\nВаш выбор (1-5): ").strip()

    project_root = Path(__file__).parent.parent
    success_count = 0

    if choice in ["1", "4"]:
        env_path = project_root / ".env"
        if create_env_file(api_key, env_path):
            print(f"✓ .env файл создан/обновлен: {env_path}")
            success_count += 1
        else:
            print("✗ Не удалось создать .env файл")

    if choice in ["2", "4"]:
        config_path = project_root / "config.json"
        if create_config_json(api_key, config_path):
            print(f"✓ config.json создан/обновлен: {config_path}")
            success_count += 1
        else:
            print("✗ Не удалось создать config.json")

    if choice in ["3", "4", "5"]:
        setup_mcp_config(api_key)
        success_count += 1

    if choice == "5":
        print("\n✓ Инструкции показаны (файлы не сохранены)")
        return 0

    print("\n" + "=" * 60)
    if success_count > 0:
        print("✓ Настройка завершена успешно!")
        print("\nСледующие шаги:")
        print("1. Запустите verify_api_key.py для проверки ключа:")
        print("   python scripts/verify_api_key.py")
        print("\n2. Если используете .env файл, убедитесь, что он не добавлен в git:")
        print("   Добавьте .env в .gitignore")
        print("\n3. Начните использовать API в вашем коде!")
    else:
        print("✗ Не удалось сохранить конфигурацию")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
