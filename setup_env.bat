@echo off
REM Setup script for Windows environment
REM This script helps set up Python virtual environment correctly

echo Setting up Python environment...

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not found in PATH
    echo Please install Python 3.11+ or add it to PATH
    pause
    exit /b 1
)

REM Check if virtual environment exists
if exist .venv\Scripts\activate.bat (
    echo Virtual environment found. Activating...
    call .venv\Scripts\activate.bat
) else (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
)

REM Upgrade pip (important for Python 3.14 compatibility)
echo Upgrading pip...
python -m pip install --upgrade pip setuptools wheel

REM Install dependencies
echo Installing dependencies...
echo Note: This may take a few minutes, especially on first run...
pip install -r requirements.txt

if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo Setup complete!
echo.
echo To activate the environment in the future, run:
echo   .venv\Scripts\activate.bat
echo.
echo Or use: py -m venv .venv ^&^& .venv\Scripts\activate.bat
echo.
pause
