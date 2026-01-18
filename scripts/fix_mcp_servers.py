#!/usr/bin/env python3
"""
Скрипт для диагностики и исправления проблем с MCP серверами.
Проверяет доступность необходимых инструментов и предоставляет инструкции по исправлению.
"""

import subprocess
import sys
import json
import os
from pathlib import Path


def check_command(cmd: str) -> tuple[bool, str]:
    """Проверяет доступность команды в системе."""
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["where", cmd],
                capture_output=True,
                text=True,
                timeout=5
            )
        else:
            result = subprocess.run(
                ["which", cmd],
                capture_output=True,
                text=True,
                timeout=5
            )

        if result.returncode == 0:
            path = result.stdout.strip().split('\n')[0]
            return True, path
        return False, ""
    except Exception as e:
        return False, str(e)


def check_mcp_server_status():
    """Проверяет статус MCP серверов."""
    servers = {
        "git": {
            "command": "git",
            "required": True,
            "description": "Git для управления версиями"
        },
        "github": {
            "command": "gh",
            "required": True,
            "description": "GitHub CLI для работы с GitHub"
        },
        "sqlite": {
            "command": "sqlite3",
            "required": False,
            "description": "SQLite CLI (может использоваться через Python)"
        },
        "sentry": {
            "command": "sentry-cli",
            "required": False,
            "description": "Sentry CLI для мониторинга ошибок"
        }
    }

    results = {}
    print("=" * 60)
    print("Диагностика MCP серверов")
    print("=" * 60)
    print()

    for server_name, config in servers.items():
        print(f"Проверка {server_name}...")
        available, path = check_command(config["command"])
        results[server_name] = {
            "available": available,
            "path": path,
            "required": config["required"],
            "description": config["description"]
        }

        if available:
            print(f"  ✅ {config['description']} найден: {path}")
        else:
            status = "❌ ОТСУТСТВУЕТ" if config["required"] else "⚠️  ОТСУТСТВУЕТ (опционально)"
            print(f"  {status} {config['description']} не найден")
        print()

    return results


def generate_fix_instructions(results: dict):
    """Генерирует инструкции по исправлению проблем."""
    print("=" * 60)
    print("Инструкции по исправлению")
    print("=" * 60)
    print()

    fixes_needed = []

    for server_name, result in results.items():
        if not result["available"]:
            if result["required"]:
                fixes_needed.append(server_name)
                print(f"🔴 {server_name.upper()} - ТРЕБУЕТСЯ УСТАНОВКА")
                print(f"   Описание: {result['description']}")

                if server_name == "git":
                    print("   Решение: Git уже должен быть установлен, проверьте PATH")
                    print("   Путь: C:\\Program Files\\Git\\cmd\\git.exe")
                elif server_name == "github":
                    print("   Решение: GitHub CLI уже должен быть установлен, проверьте PATH")
                    print("   Путь: C:\\Program Files\\GitHub CLI\\gh.exe")
                elif server_name == "sqlite":
                    print("   Решение: SQLite может работать через Python")
                    print("   Альтернатива: Установите через pip: pip install pysqlite3")
                elif server_name == "sentry":
                    print("   Решение: Установите Sentry CLI:")
                    print("   npm install -g @sentry/cli")
                    print("   или скачайте с https://github.com/getsentry/sentry-cli/releases")
                print()

    if not fixes_needed:
        print("✅ Все необходимые инструменты установлены!")
        print()
        print("Если проблемы с подключением остаются:")
        print("1. Перезапустите Cursor")
        print("2. Проверьте настройки MCP в Cursor:")
        print("   - Откройте настройки Cursor")
        print("   - Найдите раздел MCP Servers")
        print("   - Убедитесь, что пути к инструментам указаны правильно")
        print("3. Попробуйте переподключить серверы через интерфейс")
        print()

    return fixes_needed


def check_cursor_mcp_config():
    """Проверяет возможные пути к конфигурации MCP в Cursor."""
    print("=" * 60)
    print("Пути к конфигурации MCP")
    print("=" * 60)
    print()

    if sys.platform == "win32":
        appdata = os.getenv("APPDATA")
        if appdata:
            cursor_config_path = Path(appdata) / "Cursor" / "User" / "globalStorage" / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json"
            print(f"Возможный путь к глобальной конфигурации:")
            print(f"  {cursor_config_path}")
            print()

            if cursor_config_path.exists():
                print("✅ Файл конфигурации найден!")
                try:
                    with open(cursor_config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    print(f"Конфигурация содержит {len(config)} серверов")
                except Exception as e:
                    print(f"⚠️  Не удалось прочитать конфигурацию: {e}")
            else:
                print("⚠️  Файл конфигурации не найден по этому пути")
                print("   Конфигурация может храниться в другом месте")
    else:
        home = Path.home()
        cursor_config_path = home / ".config" / "Cursor" / "User" / "globalStorage" / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json"
        print(f"Возможный путь к конфигурации:")
        print(f"  {cursor_config_path}")
        print()

    print()


def main():
    """Основная функция."""
    print()
    results = check_mcp_server_status()
    fixes_needed = generate_fix_instructions(results)
    check_cursor_mcp_config()

    print("=" * 60)
    print("Рекомендации")
    print("=" * 60)
    print()
    print("1. Если инструменты установлены, но серверы не работают:")
    print("   - Перезапустите Cursor полностью")
    print("   - Нажмите кнопку 'Обновить MCP серверы' в интерфейсе")
    print("   - Попробуйте переподключить каждый сервер вручную")
    print()
    print("2. Для серверов с ошибкой 'Connection closed':")
    print("   - Проверьте логи Cursor")
    print("   - Убедитесь, что пути к исполняемым файлам правильные")
    print("   - Проверьте права доступа к файлам")
    print()
    print("3. Если проблема сохраняется:")
    print("   - Проверьте конфигурацию MCP в настройках Cursor")
    print("   - Убедитесь, что все переменные окружения установлены")
    print()

    return 0 if not fixes_needed else 1


if __name__ == "__main__":
    sys.exit(main())
