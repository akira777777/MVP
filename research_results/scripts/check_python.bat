@echo off
echo ========================================
echo Проверка установки Python
echo ========================================
echo.

echo 1. Проверка Python по пути C:\Python314:
if exist "C:\Python314\python.exe" (
    echo    [OK] Python найден
    C:\Python314\python.exe --version
    echo    Путь: C:\Python314\python.exe
) else (
    echo    [ОШИБКА] Python не найден по пути C:\Python314
)
echo.

echo 2. Проверка pip:
if exist "C:\Python314\Scripts\pip.exe" (
    echo    [OK] pip найден
    C:\Python314\Scripts\pip.exe --version
) else (
    echo    [ПРЕДУПРЕЖДЕНИЕ] pip не найден в C:\Python314\Scripts\
)
echo.

echo 3. Проверка Python в PATH:
where python >nul 2>&1
if %errorLevel% equ 0 (
    echo    [OK] Python найден в PATH
    where python
    python --version
) else (
    echo    [ОШИБКА] Python НЕ найден в PATH
    echo    Нужно добавить Python в PATH!
    echo.
    echo    Запустите: scripts\add_python314_to_path.bat
)
echo.

echo 4. Проверка pip в PATH:
where pip >nul 2>&1
if %errorLevel% equ 0 (
    echo    [OK] pip найден в PATH
    where pip
    pip --version
) else (
    echo    [ОШИБКА] pip НЕ найден в PATH
    echo    Нужно добавить Python\Scripts в PATH!
)
echo.

echo ========================================
echo Проверка завершена
echo ========================================
pause
