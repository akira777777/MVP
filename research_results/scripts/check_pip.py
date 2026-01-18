#!/usr/bin/env python
"""
Диагностический скрипт для проверки установки pip и Python.
Запустите: python scripts/check_pip.py
"""

import sys
import subprocess
import os
from pathlib import Path


def run_command(cmd, description):
    """Выполнить команду и вернуть результат."""
    print(f"\n{'='*60}")
    print(f"Проверка: {description}")
    print(f"Команда: {cmd}")
    print('='*60)
    
    try:
        if isinstance(cmd, str):
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
        else:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
        
        if result.stdout:
            print("✅ Вывод:")
            print(result.stdout)
        if result.stderr:
            print("⚠️ Ошибки:")
            print(result.stderr)
        print(f"Код возврата: {result.returncode}")
        return result.returncode == 0
    except FileNotFoundError:
        print(f"❌ Команда не найдена: {cmd}")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def check_python():
    """Проверить установку Python."""
    print("\n" + "="*60)
    print("ПРОВЕРКА PYTHON")
    print("="*60)
    
    # Проверка версии Python
    print(f"\nТекущая версия Python: {sys.version}")
    print(f"Исполняемый файл: {sys.executable}")
    print(f"Версия: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # Проверка PATH
    print(f"\nPATH содержит:")
    python_dir = str(Path(sys.executable).parent)
    scripts_dir = str(Path(sys.executable).parent / "Scripts")
    
    path_env = os.environ.get("PATH", "")
    if python_dir in path_env:
        print(f"  ✅ {python_dir}")
    else:
        print(f"  ❌ {python_dir} (НЕ в PATH)")
    
    if scripts_dir in path_env:
        print(f"  ✅ {scripts_dir}")
    else:
        print(f"  ❌ {scripts_dir} (НЕ в PATH)")
    
    return True


def check_pip():
    """Проверить установку pip."""
    print("\n" + "="*60)
    print("ПРОВЕРКА PIP")
    print("="*60)
    
    results = {}
    
    # Проверка различных способов запуска pip
    commands = [
        ("pip --version", "pip напрямую"),
        ("python -m pip --version", "python -m pip"),
        ("python3 -m pip --version", "python3 -m pip"),
        ("py -m pip --version", "py -m pip"),
    ]
    
    for cmd, desc in commands:
        results[desc] = run_command(cmd, desc)
    
    # Проверка импорта pip
    print("\n" + "="*60)
    print("Проверка импорта pip")
    print("="*60)
    try:
        import pip
        print(f"✅ pip импортирован успешно")
        print(f"   Версия: {pip.__version__}")
        print(f"   Расположение: {pip.__file__}")
    except ImportError as e:
        print(f"❌ Не удалось импортировать pip: {e}")
        results["pip import"] = False
    
    return results


def check_pip_functionality():
    """Проверить функциональность pip."""
    print("\n" + "="*60)
    print("ПРОВЕРКА ФУНКЦИОНАЛЬНОСТИ PIP")
    print("="*60)
    
    commands = [
        (["python", "-m", "pip", "list"], "Список установленных пакетов"),
        (["python", "-m", "pip", "show", "pip"], "Информация о pip"),
        (["python", "-m", "pip", "--version"], "Версия pip"),
    ]
    
    results = {}
    for cmd, desc in commands:
        results[desc] = run_command(cmd, desc)
    
    return results


def main():
    """Главная функция."""
    print("\n" + "="*60)
    print("ДИАГНОСТИКА PIP И PYTHON")
    print("="*60)
    
    # Проверка Python
    python_ok = check_python()
    
    if not python_ok:
        print("\n❌ Python не установлен или не найден!")
        print("   Установите Python с https://www.python.org/downloads/")
        print("   Не забудьте отметить 'Add Python to PATH' при установке")
        return
    
    # Проверка pip
    pip_results = check_pip()
    
    # Проверка функциональности
    if any(pip_results.values()):
        check_pip_functionality()
    
    # Рекомендации
    print("\n" + "="*60)
    print("РЕКОМЕНДАЦИИ")
    print("="*60)
    
    if pip_results.get("python -m pip", False):
        print("\n✅ Используйте: python -m pip install package_name")
    elif pip_results.get("pip напрямую", False):
        print("\n✅ pip работает напрямую")
    else:
        print("\n❌ pip не найден. Попробуйте:")
        print("   1. python -m ensurepip --upgrade")
        print("   2. Скачайте get-pip.py и запустите: python get-pip.py")
        print("   3. Переустановите Python с опцией 'Add Python to PATH'")
    
    print("\n" + "="*60)
    print("ДИАГНОСТИКА ЗАВЕРШЕНА")
    print("="*60)


if __name__ == "__main__":
    main()
