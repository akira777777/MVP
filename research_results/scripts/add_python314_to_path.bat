@echo off
REM Скрипт для добавления Python 3.14 в PATH на Windows
REM Требует запуск от имени администратора для изменения системного PATH

echo ========================================
echo Добавление Python 3.14 в PATH
echo ========================================
echo.

set PYTHON_DIR=C:\Python314
set SCRIPTS_DIR=C:\Python314\Scripts

REM Проверяем существование Python
if not exist "%PYTHON_DIR%\python.exe" (
    echo ОШИБКА: Python не найден по пути: %PYTHON_DIR%
    echo Проверьте путь и попробуйте снова.
    pause
    exit /b 1
)

echo Python найден: %PYTHON_DIR%
echo Scripts: %SCRIPTS_DIR%
echo.

REM Проверяем права администратора
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ВНИМАНИЕ: Скрипт запущен без прав администратора.
    echo Изменения будут применены только для текущего пользователя.
    echo Для изменения системного PATH запустите скрипт от имени администратора.
    echo.
    set ADMIN_MODE=User
) else (
    echo Скрипт запущен с правами администратора.
    echo Изменения будут применены для всех пользователей.
    echo.
    set ADMIN_MODE=Machine
)

REM Проверяем, есть ли уже эти пути в PATH
echo %PATH% | findstr /C:"%PYTHON_DIR%" >nul
if %errorLevel% equ 0 (
    echo Python уже добавлен в PATH!
    echo.
    echo Проверка:
    where python
    where pip
) else (
    echo Добавление Python в PATH...

    if "%ADMIN_MODE%"=="Machine" (
        REM Для всех пользователей
        for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH') do set SYSTEM_PATH=%%B
        setx PATH "%SYSTEM_PATH%;%PYTHON_DIR%;%SCRIPTS_DIR%" /M
        echo Изменения применены для всех пользователей.
    ) else (
        REM Для текущего пользователя
        setx PATH "%PATH%;%PYTHON_DIR%;%SCRIPTS_DIR%"
        echo Изменения применены для текущего пользователя.
    )

    echo.
    echo ========================================
    echo Готово!
    echo ========================================
    echo.
    echo Python добавлен в PATH:
    echo   - %PYTHON_DIR%
    echo   - %SCRIPTS_DIR%
    echo.
    echo ВАЖНО: Закройте и откройте командную строку заново,
    echo чтобы изменения вступили в силу.
    echo.
    echo После перезапуска проверьте:
    echo   python --version
    echo   pip --version
    echo.
)

pause
