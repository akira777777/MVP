# Запуск параллельных агентов для скрапинга бизнесов
# Агенты: barbershop, tetovani, restaurace, lounge, kavarna

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir

Set-Location $projectRoot

py scripts\collect_parallel_agents.py

Write-Host "Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
