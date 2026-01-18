# Полная переустановка Python
# Запускать от имени администратора!

Write-Host "=== Переустановка Python ===" -ForegroundColor Green

# Проверка прав администратора
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ОШИБКА: Запустите скрипт от имени администратора!" -ForegroundColor Red
    Write-Host "Правый клик -> Запуск от имени администратора" -ForegroundColor Yellow
    exit 1
}

# Параметры
$pythonVersion = "3.12.7"
$pythonUrl = "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion-amd64.exe"
$installerPath = "$env:TEMP\python-$pythonVersion-installer.exe"
$installDir = "C:\Python312"

Write-Host "`nШаг 1: Удаление старой установки из PATH..." -ForegroundColor Cyan
$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$pathsToRemove = @(
    "C:\Python314",
    "C:\Python314\Scripts"
)

$newPath = $currentPath
foreach ($path in $pathsToRemove) {
    $newPath = $newPath -replace [regex]::Escape($path + ";"), ""
    $newPath = $newPath -replace [regex]::Escape(";" + $path), ""
    $newPath = $newPath -replace [regex]::Escape($path), ""
}

[Environment]::SetEnvironmentVariable("Path", $newPath, "Machine")
Write-Host "✓ Старые пути удалены" -ForegroundColor Green

Write-Host "`nШаг 2: Скачивание Python $pythonVersion..." -ForegroundColor Cyan
try {
    if (Test-Path $installerPath) {
        Write-Host "Установщик уже скачан" -ForegroundColor Yellow
    }
    else {
        Invoke-WebRequest -Uri $pythonUrl -OutFile $installerPath -UseBasicParsing
        Write-Host "✓ Python скачан" -ForegroundColor Green
    }
}
catch {
    Write-Host "ОШИБКА при скачивании: $_" -ForegroundColor Red
    Write-Host "Скачайте вручную с https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

Write-Host "`nШаг 3: Запуск установщика..." -ForegroundColor Cyan
Write-Host "ВНИМАНИЕ: В окне установщика обязательно отметьте 'Add Python to PATH'!" -ForegroundColor Yellow -BackgroundColor DarkRed
Write-Host "Нажмите Enter когда будете готовы продолжить..." -ForegroundColor Cyan
Read-Host

# Параметры установки
$installArgs = @(
    "/quiet",
    "InstallAllUsers=1",
    "PrependPath=1",           # Добавить в PATH
    "Include_test=0",
    "Include_doc=0",
    "Include_pip=1",           # Установить pip
    "Include_launcher=1",      # Установить py launcher
    "TargetDir=$installDir"
)

Write-Host "Устанавливаю Python..." -ForegroundColor Cyan
$process = Start-Process -FilePath $installerPath -ArgumentList $installArgs -Wait -PassThru -NoNewWindow

if ($process.ExitCode -eq 0) {
    Write-Host "✓ Python установлен" -ForegroundColor Green
}
else {
    Write-Host "⚠ Код выхода: $($process.ExitCode)" -ForegroundColor Yellow
}

Write-Host "`nШаг 4: Обновление переменных окружения..." -ForegroundColor Cyan
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
Start-Sleep -Seconds 2

Write-Host "`nШаг 5: Проверка установки..." -ForegroundColor Cyan

# Проверяем Python
$pythonExe = "$installDir\python.exe"
if (Test-Path $pythonExe) {
    $version = & $pythonExe --version 2>&1
    Write-Host "✓ Python: $version" -ForegroundColor Green
}
else {
    Write-Host "✗ Python не найден в $installDir" -ForegroundColor Red
    Write-Host "Проверьте установку вручную" -ForegroundColor Yellow
    exit 1
}

# Проверяем pip
$pipExe = "$installDir\Scripts\pip.exe"
if (Test-Path $pipExe) {
    $pipVersion = & $pipExe --version 2>&1
    Write-Host "✓ pip: $pipVersion" -ForegroundColor Green
}
else {
    Write-Host "pip не найден, устанавливаем..." -ForegroundColor Yellow
    & $pythonExe -m ensurepip --upgrade
    if (Test-Path $pipExe) {
        Write-Host "✓ pip установлен" -ForegroundColor Green
    }
}

# Проверяем команды
Write-Host "`nШаг 6: Проверка команд в PATH..." -ForegroundColor Cyan
$env:Path = "$installDir;$installDir\Scripts;" + $env:Path

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
$pipCmd = Get-Command pip -ErrorAction SilentlyContinue

if ($pythonCmd) {
    Write-Host "✓ Команда 'python' работает: $($pythonCmd.Source)" -ForegroundColor Green
}
else {
    Write-Host "✗ Команда 'python' не найдена" -ForegroundColor Red
    Write-Host "  Добавьте вручную в PATH: $installDir" -ForegroundColor Yellow
}

if ($pipCmd) {
    Write-Host "✓ Команда 'pip' работает: $($pipCmd.Source)" -ForegroundColor Green
}
else {
    Write-Host "✗ Команда 'pip' не найдена" -ForegroundColor Red
    Write-Host "  Добавьте вручную в PATH: $installDir\Scripts" -ForegroundColor Yellow
}

Write-Host "`n=== Установка завершена ===" -ForegroundColor Green
Write-Host "`nВАЖНО: Перезапустите терминал для применения изменений PATH!" -ForegroundColor Yellow
Write-Host "После перезапуска проверьте:" -ForegroundColor Cyan
Write-Host "  python --version" -ForegroundColor White
Write-Host "  pip --version" -ForegroundColor White
