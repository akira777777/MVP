# PowerShell скрипт для запуска сбора данных о малом бизнесе в Праге

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir

Set-Location $projectRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "СБОР ДАННЫХ О МАЛОМ БИЗНЕСЕ В ПРАГЕ" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Проверка наличия Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python найден: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ОШИБКА: Python не найден!" -ForegroundColor Red
    Write-Host "Установите Python или добавьте его в PATH" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

Write-Host ""

# Запуск скрипта
python scripts\prague_small_businesses.py $args

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host "ОШИБКА ПРИ ВЫПОЛНЕНИИ СКРИПТА" -ForegroundColor Red
    Write-Host "============================================================" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "ГОТОВО!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Read-Host "Нажмите Enter для выхода"
