@echo off
REM Upsum Project Nexus — Quick Start
REM Automated setup for Wikipedia-integrated Swedish knowledge platform

REM Check for admin privileges and elevate if needed
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs -ArgumentList '%cd%'"
    exit /b
)

REM Change to script directory (important when running as admin)
cd /d "%~dp0"

echo ===============================================
echo   Upsum — Project Nexus
echo   Starting backend and frontend...
echo   Running as Administrator for port 80 access
echo ===============================================
echo.

REM Backend setup
echo [1/3] Setting up backend...
cd backend
if not exist .venv (
    echo Creating Python virtual environment...
    python -m venv .venv
)
echo Activating virtual environment...
call .venv\Scripts\activate.bat
echo Installing dependencies (FastAPI, uvicorn, requests)...
pip install -q -r requirements.txt

echo.
echo [2/3] Starting backend server on http://0.0.0.0:80
echo Note: Using port 80 for standard HTTP access (no :8000 needed)

REM Get full path to uvicorn in venv
set VENV_PATH=%cd%\.venv\Scripts
set UVICORN=%VENV_PATH%\uvicorn.exe

REM Start backend with full path to uvicorn
start "Upsum Backend" cmd /k "cd /d "%cd%" && echo Upsum Backend Server && echo ==================== && echo Running on port 80 (HTTP) && echo. && "%UVICORN%" main:app --reload --host 0.0.0.0 --port 80"
cd ..

REM Wait for backend to start
echo Waiting for backend to initialize...
timeout /t 4 /nobreak > nul

REM Frontend setup
echo.
echo [3/3] Opening frontend interface...

REM Check if React/Vite frontend exists
if exist frontend\package.json (
    cd frontend
    echo Found npm project, installing dependencies...
    call npm install
    start "Upsum Frontend" cmd /k "echo Upsum Frontend Server && echo ==================== && echo. && npm run dev"
    cd ..
    timeout /t 2 /nobreak > nul
    start http://localhost:5173
) else (
    REM Use standalone HTML frontend served by backend
    echo Using standalone HTML frontend served by backend
    start http://localhost
)

echo.
echo ===============================================
echo   Upsum is now running!
echo ===============================================
echo   Frontend:  http://localhost
echo   Remote:    http://upsum.oscyra.solutions
echo   Public IP: http://188.149.38.55
echo   API Docs:  http://localhost/api/docs
echo   Health:    http://localhost/health
echo ===============================================
echo.
echo Note: Backend running on port 80 (standard HTTP)
echo This allows access without specifying :8000
echo.
echo Press any key to open API documentation...
pause > nul
start http://localhost/api/docs

echo.
echo Upsum is ready! Close this window when done.
echo Backend and frontend will continue running in separate windows.
pause
