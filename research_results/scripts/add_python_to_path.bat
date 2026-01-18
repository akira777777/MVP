@echo off
REM Скрипт для добавления Python в PATH на Windows
REM Требует запуск от имени администратора для изменения системного PATH

echo ========================================
echo Добавление Python в PATH
echo ========================================
echo.

REM Проверяем права администратора
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ВНИМАНИЕ: Скрипт запущен без прав администратора.
    echo Изменения будут применены только для текущего пользователя.
    echo Для изменения системного PATH запустите скрипт от имени администратора.
    echo.
    pause
    set ADMIN_MODE=User
) else (
    echo Скрипт запущен с правами администратора.
    echo Изменения будут применены для всех пользователей.
    echo.
    set ADMIN_MODE=Machine
)

REM Пытаемся найти Python
echo Поиск Python...
where python >nul 2>&1
if %errorLevel% equ 0 (
    echo Python найден в PATH!
    for /f "tokens=*" %%i in ('where python') do set PYTHON_EXE=%%i
    for %%i in ("%PYTHON_EXE%") do set PYTHON_DIR=%%~dpi
    set PYTHON_DIR=%PYTHON_DIR:~0,-1%
    echo Путь к Python: %PYTHON_DIR%
) else (
    echo Python не найден в PATH.
    echo.
    echo Проверяем стандартные места установки...

    REM Проверяем стандартные пути
    if exist "C:\Python311\python.exe" (
        set PYTHON_DIR=C:\Python311
    ) else if exist "C:\Python310\python.exe" (
        set PYTHON_DIR=C:\Python310
    ) else if exist "C:\Python39\python.exe" (
        set PYTHON_DIR=C:\Python39
    ) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
        set PYTHON_DIR=%LOCALAPPDATA%\Programs\Python\Python311
    ) else if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
        set PYTHON_DIR=%LOCALAPPDATA%\Programs\Python\Python310
    ) else (
        echo Python не найден в стандартных местах.
        echo.
        set /p PYTHON_DIR="Введите путь к Python вручную (например, C:\Python311): "
    )
)

if not exist "%PYTHON_DIR%\python.exe" (
    echo ОШИБКА: Python не найден по пути: %PYTHON_DIR%
    echo Проверьте путь и попробуйте снова.
    pause
    exit /b 1
)

set SCRIPTS_DIR=%PYTHON_DIR%\Scripts

echo.
echo ========================================
echo Найденные пути:
echo ========================================
echo Python: %PYTHON_DIR%
echo Scripts: %SCRIPTS_DIR%
echo.

REM Проверяем, есть ли уже эти пути в PATH
echo %PATH% | findstr /C:"%PYTHON_DIR%" >nul
if %errorLevel% equ 0 (
    echo Python уже добавлен в PATH!
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
    echo Python добавлен в PATH.
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
