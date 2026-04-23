@echo off
REM Setup script for site-analysis project
REM This script creates and activates the virtual environment, then installs dependencies

echo ========================================
echo Setting up site-analysis environment
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.6+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created successfully.
) else (
    echo Virtual environment already exists.
)

echo.
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Verify activation
where python | findstr ".venv" >nul
if errorlevel 1 (
    echo WARNING: Virtual environment may not be activated properly
)

echo.
echo Installing/updating dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ========================================
echo Setup complete!
echo ========================================
echo.
echo You can now run the analysis script:
echo   python analyze-pages.py
echo.
echo To activate the environment in future sessions:
echo   .venv\Scripts\activate
echo.
pause
