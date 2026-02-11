@echo off
title LoL Team Analytics - Setup
echo ============================================
echo   LoL Team Analytics - First Time Setup
echo ============================================
echo.

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo.
    echo Please install Python 3.9+ from:
    echo   https://www.python.org/downloads/
    echo.
    echo IMPORTANT: Check "Add Python to PATH" during installation!
    echo.
    pause
    exit /b 1
)

echo [OK] Python found:
python --version
echo.

:: Create virtual environment
if not exist ".venv" (
    echo [*] Creating virtual environment...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
) else (
    echo [OK] Virtual environment already exists.
)
echo.

:: Activate and install dependencies
echo [*] Installing dependencies (this may take a minute)...
call .venv\Scripts\activate.bat
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [OK] All dependencies installed.
echo.

:: Create data directories
if not exist "data" mkdir data
if not exist "data\exports" mkdir data\exports
echo [OK] Data directories ready.
echo.

echo ============================================
echo   Setup complete! Run 'run.bat' to start.
echo ============================================
pause
