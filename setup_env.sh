#!/bin/bash
# Setup script for Git Bash / Linux / macOS
# This script helps set up Python virtual environment correctly

set -e

echo "Setting up Python environment..."

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "ERROR: Python is not found in PATH"
    echo "Please install Python 3.11+ or add it to PATH"
    exit 1
fi

# Check if virtual environment exists
if [ -d ".venv" ]; then
    echo "Virtual environment found. Activating..."
    source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate
else
    echo "Creating virtual environment..."
    python -m venv .venv
    echo "Activating virtual environment..."
    source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate
fi

# Upgrade pip (important for Python 3.14 compatibility)
echo "Upgrading pip..."
python -m pip install --upgrade pip setuptools wheel

# Install dependencies
echo "Installing dependencies..."
echo "Note: This may take a few minutes, especially on first run..."
pip install -r requirements.txt

echo ""
echo "Setup complete!"
echo ""
echo "To activate the environment in the future, run:"
echo "  source .venv/Scripts/activate  # Windows Git Bash"
echo "  source .venv/bin/activate      # Linux/macOS"
echo ""
