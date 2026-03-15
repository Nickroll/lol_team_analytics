@echo off
title LoL Team Analytics
echo ============================================
echo   LoL Team Analytics
echo ============================================
echo.

:: Check if setup has been run
if not exist ".venv" (
    echo [!] First time? Run setup.bat first!
    echo.
    pause
    exit /b 1
)

:: Check activate script exists
if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment is broken. Delete the .venv folder and run setup.bat again.
    echo.
    pause
    exit /b 1
)

:: Activate virtual environment
call .venv\Scripts\activate.bat

:: Launch Streamlit
echo [*] Starting app... (your browser will open automatically)
echo [*] Press Ctrl+C in this window to stop the app.
echo.
streamlit run main.py --server.headless false --browser.gatherUsageStats false
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] App exited unexpectedly. Check the output above for details.
    pause
)
