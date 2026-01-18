#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Простая проверка конфигурации MCP серверов"""

import json
import sys
from pathlib import Path


def check_config(config_path):
    """Проверяет конфигурацию MCP."""
    print(f"\nПроверка: {config_path}")
    print("=" * 70)

    if not config_path.exists():
        print("❌ Файл не найден")
        return False

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ Ошибка чтения: {e}")
        return False

    servers = config.get("mcpServers", {})
    print(f"✅ Найдено серверов: {len(servers)}\n")

    for name, server_config in servers.items():
        print(f"Сервер: {name}")
        print(f"  Команда: {server_config.get('command', 'N/A')}")

        args = server_config.get("args", [])
        package = None
        for arg in args:
            if arg.startswith("@modelcontextprotocol/server-"):
                package = arg
                break

        if package:
            print(f"  Пакет: {package}")

        env = server_config.get("env", {})
        if env:
            print("  Переменные окружения:")
            for key, value in env.items():
                # Показываем первые и последние символы
                if len(value) > 12:
                    masked = value[:8] + "..." + value[-4:]
                else:
                    masked = "***"
                print(f"    {key}: {masked}")
        else:
            print("  Переменные окружения: не требуются")

        print()

    return True


def main():
    """Основная функция."""
    print("=" * 70)
    print("Проверка конфигурации MCP серверов")
    print("=" * 70)

    configs = [
        Path("c:/Users/-/.cursor/mcp.json"),
        Path(__file__).parent.parent / ".kilocode" / "mcp.json",
    ]

    all_ok = True
    for config_path in configs:
        if not check_config(config_path):
            all_ok = False

    print("=" * 70)
    print("Рекомендации:")
    print("=" * 70)
    print("1. Убедитесь, что все ключи API корректны")
    print("2. Перезапустите Cursor полностью")
    print("3. Проверьте статус серверов в настройках Cursor")
    print("4. При ошибках подключения нажмите 'Reconnect' для каждого сервера")
    print()

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
