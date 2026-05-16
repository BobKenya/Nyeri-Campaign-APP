@echo off
echo ============================================
echo  Nyeri Campaign App - Windows Setup
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Download from https://www.python.org/downloads/
    echo IMPORTANT: Check "Add Python to PATH" during install!
    pause
    exit /b 1
)

echo [1/3] Creating virtual environment...
python -m venv .venv
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

echo [2/3] Activating and installing dependencies...
call .venv\Scripts\activate.bat
pip install -r requirements.txt --quiet

echo [3/3] Seeding database with Nyeri County data...
python scripts/seed.py

echo.
echo ============================================
echo  Setup complete!
echo  Run the app with:  run.bat
echo  Then open:  http://localhost:8000/docs
echo ============================================
pause
