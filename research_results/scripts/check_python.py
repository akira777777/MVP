"""
Скрипт для проверки установки Python.
"""

import os
import sys

print("=" * 60)
print("Проверка установки Python")
print("=" * 60)
print()

# Информация о текущем Python
print("1. Текущий Python:")
print(f"   Версия: {sys.version}")
print(f"   Исполняемый файл: {sys.executable}")
print(f"   Директория: {os.path.dirname(sys.executable)}")
print()

# Проверка pip
try:
    import pip

    print("2. pip:")
    print(f"   Версия: {pip.__version__}")
    print(f"   Расположение: {pip.__file__}")
except ImportError:
    print("2. pip: НЕ УСТАНОВЛЕН")
print()

# Проверка PATH
print("3. Python в PATH:")
python_in_path = False
path_dirs = os.environ.get("PATH", "").split(os.pathsep)
python_dirs = [d for d in path_dirs if "Python" in d or "python" in d.lower()]

if python_dirs:
    print("   Найдены пути с Python:")
    for dir_path in python_dirs:
        marker = " ← ТЕКУЩИЙ" if dir_path in os.path.dirname(sys.executable) else ""
        print(f"   - {dir_path}{marker}")
    python_in_path = True
else:
    print("   Python НЕ найден в PATH")

if not python_in_path:
    python_dir = os.path.dirname(sys.executable)
    scripts_dir = os.path.join(python_dir, "Scripts")
    print()
    print("4. Рекомендация:")
    print("   Добавьте в PATH:")
    print(f"   - {python_dir}")
    print(f"   - {scripts_dir}")
    print()
    print("   Или запустите:")
    print("   scripts\\add_python314_to_path.bat")
else:
    print()
    print("4. Статус: ✓ Python уже в PATH")

print()
print("=" * 60)
