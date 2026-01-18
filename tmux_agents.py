#!/usr/bin/env python3
"""
TMUX Agents Manager - имитация tmux сессии для Windows
Управляет запуском различных агентов в отдельных процессах
"""

import subprocess
import sys
import time
import signal
import os
from pathlib import Path

class AgentsManager:
    def __init__(self):
        self.processes = {}
        self.session_name = "agents"

    def create_window(self, name, command, cwd=None):
        """Создает 'окно' - запускает процесс в фоне"""
        print(f"Создание окна '{name}' с командой: {command}")

        try:
            if isinstance(command, str):
                # Для Windows используем shell=True для поддержки команд
                process = subprocess.Popen(
                    command,
                    shell=True,
                    cwd=cwd or os.getcwd(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
                )
            else:
                # command как список
                process = subprocess.Popen(
                    command,
                    cwd=cwd or os.getcwd(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
                )

            self.processes[name] = process
            print(f"Окно '{name}' запущено (PID: {process.pid})")
            return True

        except Exception as e:
            print(f"Ошибка запуска окна '{name}': {e}")
            return False

    def setup_agents_session(self):
        """Настраивает все окна агентов"""
        print(f"Создание tmux сессии '{self.session_name}'...")

        # Окно 1: Telegram боты (aiogram)
        self.create_window(
            "telegram-bots",
            "python -c \"print('Telegram bots window - waiting for bot scripts...'); import time; time.sleep(3600)\"",
            cwd="."
        )

        # Окно 2: Планировщик задач (apscheduler)
        self.create_window(
            "scheduler",
            "python -c \"print('Task scheduler window - waiting for scheduler scripts...'); import time; time.sleep(3600)\"",
            cwd="."
        )

        # Окно 3: Мониторинг и HTTP сервисы (aiohttp)
        self.create_window(
            "monitoring",
            "python -c \"print('Monitoring & HTTP services window - waiting for aiohttp scripts...'); import time; time.sleep(3600)\"",
            cwd="."
        )

        # Окно 4: Автоматизация браузера (playwright)
        self.create_window(
            "browser-automation",
            "python -c \"print('Browser automation window - waiting for playwright scripts...'); import time; time.sleep(3600)\"",
            cwd="."
        )

        # Окно 5: MCP серверы
        self.create_window(
            "mcp-servers",
            "python -c \"print('MCP servers window - waiting for server startup scripts...'); import time; time.sleep(3600)\"",
            cwd="."
        )

    def list_windows(self):
        """Показывает список активных окон"""
        print(f"\nАктивные окна в сессии '{self.session_name}':")
        for name, process in self.processes.items():
            status = "running" if process.poll() is None else "stopped"
            pid = process.pid if process.pid else "N/A"
            print(f"  {name}: {status} (PID: {pid})")

    def kill_window(self, name):
        """Останавливает конкретное окно"""
        if name in self.processes:
            process = self.processes[name]
            if process.poll() is None:
                if os.name == 'nt':
                    process.terminate()
                else:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                print(f"Окно '{name}' остановлено")
            else:
                print(f"Окно '{name}' уже остановлено")
        else:
            print(f"Окно '{name}' не найдено")

    def cleanup(self):
        """Останавливает все процессы"""
        print("\nОстановка всех окон...")
        for name, process in self.processes.items():
            if process.poll() is None:
                try:
                    if os.name == 'nt':
                        process.terminate()
                        process.wait(timeout=5)
                    else:
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    print(f"Окно '{name}' остановлено")
                except Exception as e:
                    print(f"Ошибка остановки окна '{name}': {e}")
                    try:
                        process.kill()
                    except:
                        pass

    def run_interactive(self):
        """Запускает интерактивный режим управления"""
        print(f"TMUX Agents Manager - сессия '{self.session_name}'")
        print("Команды:")
        print("  list - показать активные окна")
        print("  kill <name> - остановить окно")
        print("  restart <name> - перезапустить окно")
        print("  exit - выйти и остановить все")

        try:
            while True:
                cmd = input("\nagents> ").strip().split()
                if not cmd:
                    continue

                if cmd[0] == "list":
                    self.list_windows()

                elif cmd[0] == "kill" and len(cmd) > 1:
                    self.kill_window(cmd[1])

                elif cmd[0] == "restart" and len(cmd) > 1:
                    self.kill_window(cmd[1])
                    # Здесь можно добавить логику перезапуска конкретного окна

                elif cmd[0] == "exit":
                    break

                else:
                    print("Неизвестная команда. Используйте: list, kill <name>, restart <name>, exit")

        except KeyboardInterrupt:
            print("\nПолучен сигнал прерывания...")
        finally:
            self.cleanup()

def main():
    manager = AgentsManager()

    # Обработка сигналов для корректного завершения
    def signal_handler(signum, frame):
        print(f"\nПолучен сигнал {signum}, завершение...")
        manager.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Создание сессии
    manager.setup_agents_session()

    # Небольшая пауза для инициализации
    time.sleep(2)

    # Показываем статус
    manager.list_windows()

    # Запуск интерактивного режима
    manager.run_interactive()

if __name__ == "__main__":
    main()