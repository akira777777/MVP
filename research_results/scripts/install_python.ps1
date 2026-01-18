# Скрипт для правильной установки Python глобально
# Запускать от имени администратора!

Write-Host "=== Установка Python глобально ===" -ForegroundColor Green

# Проверка прав администратора
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ОШИБКА: Запустите скрипт от имени администратора!" -ForegroundColor Red
    Write-Host "Правый клик -> Запуск от имени администратора" -ForegroundColor Yellow
    exit 1
}

# URL для скачивания Python 3.12 (стабильная версия)
$pythonVersion = "3.12.7"
$pythonUrl = "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion-amd64.exe"
$installerPath = "$env:TEMP\python-installer.exe"
$installDir = "C:\Python312"

Write-Host "`nШаг 1: Удаление старых установок Python из PATH..." -ForegroundColor Cyan

# Удаляем старые пути Python из системного PATH
$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$pathsToRemove = @(
    "C:\Python314",
    "C:\Python314\Scripts",
    "C:\Users\-\AppData\Local\Programs\Python\Python314",
    "C:\Users\-\AppData\Local\Programs\Python\Python314\Scripts"
)

$newPath = $currentPath
foreach ($path in $pathsToRemove) {
    $newPath = $newPath -replace [regex]::Escape($path + ";"), ""
    $newPath = $newPath -replace [regex]::Escape(";" + $path), ""
    $newPath = $newPath -replace [regex]::Escape($path), ""
}

[Environment]::SetEnvironmentVariable("Path", $newPath, "Machine")
Write-Host "Старые пути удалены из PATH" -ForegroundColor Green

Write-Host "`nШаг 2: Скачивание Python $pythonVersion..." -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri $pythonUrl -OutFile $installerPath -UseBasicParsing
    Write-Host "Python скачан успешно" -ForegroundColor Green
}
catch {
    Write-Host "ОШИБКА при скачивании: $_" -ForegroundColor Red
    exit 1
}

Write-Host "`nШаг 3: Установка Python..." -ForegroundColor Cyan
Write-Host "ВНИМАНИЕ: В установщике обязательно выберите 'Add Python to PATH'!" -ForegroundColor Yellow

# Параметры установки
$installArgs = @(
    "/quiet",                    # Тихая установка
    "InstallAllUsers=1",         # Установка для всех пользователей
    "PrependPath=1",             # Добавить в PATH
    "Include_test=0",            # Не устанавливать тесты
    "Include_doc=0",             # Не устанавливать документацию
    "Include_pip=1",             # Установить pip
    "TargetDir=$installDir"      # Директория установки
)

Start-Process -FilePath $installerPath -ArgumentList $installArgs -Wait -NoNewWindow

Write-Host "`nШаг 4: Обновление переменных окружения..." -ForegroundColor Cyan
# Обновляем PATH в текущей сессии
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

Write-Host "`nШаг 5: Проверка установки..." -ForegroundColor Cyan
Start-Sleep -Seconds 2

# Проверяем Python
$pythonExe = "$installDir\python.exe"
if (Test-Path $pythonExe) {
    $version = & $pythonExe --version
    Write-Host "Python установлен: $version" -ForegroundColor Green
}
else {
    Write-Host "ОШИБКА: Python не найден в $installDir" -ForegroundColor Red
    exit 1
}

# Проверяем pip
$pipExe = "$installDir\Scripts\pip.exe"
if (Test-Path $pipExe) {
    $pipVersion = & $pipExe --version
    Write-Host "pip установлен: $pipVersion" -ForegroundColor Green
}
else {
    Write-Host "pip не найден, устанавливаем..." -ForegroundColor Yellow
    & $pythonExe -m ensurepip --upgrade
}

# Проверяем команды в PATH
Write-Host "`nШаг 6: Проверка команд в PATH..." -ForegroundColor Cyan
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
$pipCmd = Get-Command pip -ErrorAction SilentlyContinue

if ($pythonCmd) {
    Write-Host "✓ Команда 'python' работает: $($pythonCmd.Source)" -ForegroundColor Green
}
else {
    Write-Host "✗ Команда 'python' не найдена в PATH" -ForegroundColor Red
    Write-Host "  Добавьте вручную: $installDir" -ForegroundColor Yellow
}

if ($pipCmd) {
    Write-Host "✓ Команда 'pip' работает: $($pipCmd.Source)" -ForegroundColor Green
}
else {
    Write-Host "✗ Команда 'pip' не найдена в PATH" -ForegroundColor Red
    Write-Host "  Добавьте вручную: $installDir\Scripts" -ForegroundColor Yellow
}

Write-Host "`n=== Установка завершена ===" -ForegroundColor Green
Write-Host "`nВАЖНО: Перезапустите терминал/PowerShell для применения изменений PATH!" -ForegroundColor Yellow
Write-Host "После перезапуска проверьте:" -ForegroundColor Cyan
Write-Host "  python --version" -ForegroundColor White
Write-Host "  pip --version" -ForegroundColor White
