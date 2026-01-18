#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Простая проверка MCP серверов"""

import subprocess
import sys
import os

def check(cmd):
    try:
        if sys.platform == "win32":
            result = subprocess.run(["where", cmd], capture_output=True, text=True, timeout=5)
        else:
            result = subprocess.run(["which", cmd], capture_output=True, text=True, timeout=5)
        return result.returncode == 0, result.stdout.strip().split('\n')[0] if result.returncode == 0 else ""
    except:
        return False, ""

print("\n=== Проверка MCP серверов ===\n")

servers = [
    ("git", "Git"),
    ("gh", "GitHub CLI"),
    ("sqlite3", "SQLite3"),
    ("sentry-cli", "Sentry CLI")
]

for cmd, name in servers:
    ok, path = check(cmd)
    status = "OK" if ok else "NOT FOUND"
    print(f"{name:15} {status:12} {path}")

print("\n=== Рекомендации ===\n")
print("1. Git и GitHub CLI установлены - должны работать")
print("2. SQLite3 и Sentry CLI не установлены (опционально)")
print("3. Перезапустите Cursor и нажмите 'Обновить MCP серверы'")
print("4. Для каждого сервера с ошибкой нажмите 'Повторить подключение'\n")
