@echo off
REM Klar Search Engine - Windows Startup Script
REM Double-click this file to start the server

echo.
echo ================================================================
echo            KLAR SEARCH ENGINE - Starting Server
echo ================================================================
echo.

REM Check if Python 3.11+ available via py launcher
py -3.11 --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.11+ required ^(run 'py -3.11 --version'^)
    echo You have it—fix batch syntax if needed.
    pause
    exit /b 1
)





REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    py -3.11 -m venv venv

    echo.
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if dependencies are installed
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
    echo.
)

REM Check if index exists
if not exist "data\index\search_index.pkl" (
    echo.
    echo ================================================================
    echo WARNING: Search index not found!
    echo ================================================================
    echo.
    echo You must run initialization first:
    echo    python init_kse.py
    echo.
    echo This will take 2-4 hours but only needs to be done once.
    echo.
    set /p continue="Do you want to initialize now? (y/n): "
    if /i "%continue%"=="y" (
        python init_kse.py
    ) else (
        echo.
        echo Exiting. Please run init_kse.py first.
        pause
        exit /b 1
    )
)

REM Start the server
echo.
echo Starting Klar Search Engine Server...
echo.
echo Server will be available at:
echo   - Local:  http://localhost:5000
echo   - Network: http://YOUR_IP:5000
echo.
echo Press Ctrl+C to stop the server
echo.

python start_server.py

pause
