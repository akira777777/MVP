# Скрипт для добавления Python в PATH
# Запускать от имени администратора!

Write-Host "=== Добавление Python в PATH ===" -ForegroundColor Green

# Проверка прав администратора
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ОШИБКА: Запустите скрипт от имени администратора!" -ForegroundColor Red
    Write-Host "Правый клик -> Запуск от имени администратора" -ForegroundColor Yellow
    exit 1
}

$pythonDir = "C:\Python314"
$scriptsDir = "$pythonDir\Scripts"

if (-not (Test-Path "$pythonDir\python.exe")) {
    Write-Host "ОШИБКА: Python не найден в $pythonDir" -ForegroundColor Red
    exit 1
}

Write-Host "`nДобавление Python в системный PATH..." -ForegroundColor Cyan

# Получаем текущий системный PATH
$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")

# Проверяем, не добавлен ли уже
if ($currentPath -notlike "*$pythonDir*") {
    $newPath = "$pythonDir;$scriptsDir;$currentPath"
    [Environment]::SetEnvironmentVariable("Path", $newPath, "Machine")
    Write-Host "✓ Python добавлен в системный PATH" -ForegroundColor Green
}
else {
    Write-Host "✓ Python уже в PATH" -ForegroundColor Yellow
}

# Обновляем PATH пользователя тоже
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$pythonDir*") {
    if ($userPath) {
        $newUserPath = "$pythonDir;$scriptsDir;$userPath"
    }
    else {
        $newUserPath = "$pythonDir;$scriptsDir"
    }
    [Environment]::SetEnvironmentVariable("Path", $newUserPath, "User")
    Write-Host "✓ Python добавлен в пользовательский PATH" -ForegroundColor Green
}

# Обновляем PATH в текущей сессии
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

Write-Host "`nПроверка установки..." -ForegroundColor Cyan

# Проверяем Python
try {
    $pythonVersion = & "$pythonDir\python.exe" --version
    Write-Host "✓ Python: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "✗ Python не работает" -ForegroundColor Red
}

# Проверяем pip
if (Test-Path "$scriptsDir\pip.exe") {
    try {
        $pipVersion = & "$scriptsDir\pip.exe" --version
        Write-Host "✓ pip: $pipVersion" -ForegroundColor Green
    }
    catch {
        Write-Host "✗ pip не работает" -ForegroundColor Red
    }
}
else {
    Write-Host "pip не найден, устанавливаем..." -ForegroundColor Yellow
    & "$pythonDir\python.exe" -m ensurepip --upgrade
    if (Test-Path "$scriptsDir\pip.exe") {
        Write-Host "✓ pip установлен" -ForegroundColor Green
    }
    else {
        Write-Host "✗ Не удалось установить pip" -ForegroundColor Red
    }
}

Write-Host "`n=== Готово ===" -ForegroundColor Green
Write-Host "`nВАЖНО: Перезапустите терминал/PowerShell для применения изменений!" -ForegroundColor Yellow
Write-Host "После перезапуска проверьте:" -ForegroundColor Cyan
Write-Host "  python --version" -ForegroundColor White
Write-Host "  pip --version" -ForegroundColor White
