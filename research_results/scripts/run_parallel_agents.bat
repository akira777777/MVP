@echo off
REM Запуск параллельных агентов для скрапинга бизнесов
REM Агенты: barbershop, tetovani, restaurace, lounge, kavarna

cd /d "%~dp0\.."
py scripts\collect_parallel_agents.py

pause
