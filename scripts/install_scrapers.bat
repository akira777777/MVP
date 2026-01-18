@echo off
REM Script to install browser scraper dependencies
REM Uses python -m pip instead of pip directly to avoid launcher issues

echo Installing browser scraper dependencies...
echo.

python -m pip install --upgrade pip
python -m pip install selenium==4.27.1
python -m pip install undetected-chromedriver==3.5.5
python -m pip install scrapy==2.11.2
python -m pip install requests-html==0.10.0

echo.
echo Installation complete!
echo.
echo Verifying installation...
python scripts/check_scrapers_installation.py

pause
