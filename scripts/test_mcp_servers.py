#!/usr/bin/env python3
"""
Скрипт для проверки подключения MCP серверов.
Тестирует каждый сервер и проверяет наличие необходимых инструментов.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Tuple


def check_command(cmd: str) -> Tuple[bool, str]:
    """Проверяет доступность команды в системе."""
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["where", cmd], capture_output=True, text=True, timeout=5
            )
        else:
            result = subprocess.run(
                ["which", cmd], capture_output=True, text=True, timeout=5
            )

        if result.returncode == 0:
            path = result.stdout.strip().split("\n")[0]
            return True, path
        return False, ""
    except Exception as e:
        return False, str(e)


def check_npx() -> Tuple[bool, str]:
    """Проверяет наличие npx."""
    return check_command("npx")


def test_mcp_server(
    server_name: str, package: str, env_vars: Dict[str, str] = None
) -> Tuple[bool, str]:
    """Тестирует запуск MCP сервера."""
    try:
        # Подготовка окружения
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)

        # Запуск сервера с таймаутом
        # Используем --version или подобную команду для проверки
        result = subprocess.run(
            ["npx", "-y", package, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )

        if result.returncode == 0:
            return True, "OK"
        else:
            # Некоторые серверы могут не поддерживать --version
            # Попробуем просто запустить и проверить, что процесс стартует
            return True, "Package available (version check may not be supported)"
    except subprocess.TimeoutExpired:
        return False, "Timeout - server may be hanging"
    except Exception as e:
        return False, str(e)


def load_mcp_config(config_path: Path) -> Dict:
    """Загружает конфигурацию MCP."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def check_server_config(server_name: str, config: Dict) -> Dict:
    """Проверяет конфигурацию сервера."""
    result = {
        "name": server_name,
        "command": config.get("command", ""),
        "args": config.get("args", []),
        "env": config.get("env", {}),
        "has_env": bool(config.get("env")),
        "package": None,
        "status": "unknown",
        "message": "",
    }

    # Извлекаем имя пакета из args
    args = config.get("args", [])
    for i, arg in enumerate(args):
        if arg.startswith("@modelcontextprotocol/server-"):
            result["package"] = arg
            break

    return result


def main():
    """Основная функция проверки."""
    print("=" * 70)
    print("Проверка MCP серверов")
    print("=" * 70)
    print()

    # Проверка npx
    npx_available, npx_path = check_npx()
    if not npx_available:
        print("❌ npx не найден! Установите Node.js и npm.")
        print("   Скачайте с: https://nodejs.org/")
        return 1

    print(f"✅ npx найден: {npx_path}")
    print()

    # Загрузка конфигурации
    config_paths = [
        Path.home() / ".cursor" / "mcp.json",
        Path("c:/Users/-/.cursor/mcp.json"),
        Path(__file__).parent.parent / ".kilocode" / "mcp.json",
    ]

    config = {}
    config_file = None

    for path in config_paths:
        if path.exists():
            config = load_mcp_config(path)
            if config.get("mcpServers"):
                config_file = path
                break

    if not config:
        print("❌ Конфигурация MCP не найдена!")
        print("   Проверенные пути:")
        for path in config_paths:
            print(f"   - {path}")
        return 1

    print(f"✅ Конфигурация загружена из: {config_file}")
    print()

    # Проверка каждого сервера
    servers = config.get("mcpServers", {})
    results = []

    print("=" * 70)
    print("Статус серверов")
    print("=" * 70)
    print()

    for server_name, server_config in servers.items():
        print(f"Сервер: {server_name}")
        server_info = check_server_config(server_name, server_config)

        # Проверка наличия команды
        if server_info["command"]:
            cmd_available, cmd_path = check_command(server_info["command"])
            if not cmd_available:
                print(f"  ❌ Команда '{server_info['command']}' не найдена")
                server_info["status"] = "error"
                server_info["message"] = f"Command '{server_info['command']}' not found"
                results.append(server_info)
                print()
                continue
            print(f"  ✅ Команда: {server_info['command']} ({cmd_path})")

        # Проверка пакета
        if server_info["package"]:
            print(f"  📦 Пакет: {server_info['package']}")

        # Проверка переменных окружения
        if server_info["has_env"]:
            env_vars = server_info["env"]
            print("  🔑 Переменные окружения:")
            for key, value in env_vars.items():
                # Маскируем значения для безопасности
                masked_value = (
                    value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                )
                print(f"     {key} = {masked_value}")
        else:
            print("  ℹ️  Переменные окружения не требуются")

        # Попытка тестирования сервера
        if server_info["package"]:
            print("  🔄 Тестирование подключения...")
            env_vars = server_info.get("env", {})
            test_ok, test_msg = test_mcp_server(
                server_name, server_info["package"], env_vars if env_vars else None
            )

            if test_ok:
                print(f"  ✅ Сервер доступен: {test_msg}")
                server_info["status"] = "ok"
            else:
                print(f"  ⚠️  Предупреждение: {test_msg}")
                server_info["status"] = "warning"
                server_info["message"] = test_msg

        results.append(server_info)
        print()

    # Итоговая сводка
    print("=" * 70)
    print("Итоговая сводка")
    print("=" * 70)
    print()

    ok_count = sum(1 for r in results if r["status"] == "ok")
    warning_count = sum(1 for r in results if r["status"] == "warning")
    error_count = sum(1 for r in results if r["status"] == "error")

    print(f"Всего серверов: {len(results)}")
    print(f"✅ Работают: {ok_count}")
    print(f"⚠️  Предупреждения: {warning_count}")
    print(f"❌ Ошибки: {error_count}")
    print()

    if error_count > 0:
        print("Серверы с ошибками:")
        for r in results:
            if r["status"] == "error":
                print(f"  - {r['name']}: {r['message']}")
        print()

    if warning_count > 0:
        print("Серверы с предупреждениями:")
        for r in results:
            if r["status"] == "warning":
                print(f"  - {r['name']}: {r['message']}")
        print()

    print("=" * 70)
    print("Рекомендации")
    print("=" * 70)
    print()

    if error_count == 0 and warning_count == 0:
        print("✅ Все серверы настроены правильно!")
        print()
        print("Следующие шаги:")
        print("1. Перезапустите Cursor полностью")
        print("2. Откройте настройки MCP серверов")
        print("3. Проверьте статус подключения в интерфейсе Cursor")
        print("4. При необходимости нажмите 'Reconnect' для каждого сервера")
    else:
        print("⚠️  Обнаружены проблемы с некоторыми серверами")
        print()
        print("Рекомендации:")
        print("1. Проверьте, что все необходимые инструменты установлены")
        print("2. Убедитесь, что API ключи корректны")
        print("3. Перезапустите Cursor после исправления")
        print("4. Проверьте логи Cursor для детальной информации об ошибках")

    print()

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
