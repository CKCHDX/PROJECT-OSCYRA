@echo off
REM Sverkan (fresh) backend launcher

echo ========================================
echo Starting Sverkan (fresh)
echo ========================================
echo.

if not exist "venv\Scripts\python.exe" (
	echo Creating virtual environment...
	python -m venv venv
)

call venv\Scripts\activate.bat

echo Installing dependencies...
python -m pip install -r requirements.txt

echo.
echo Starting backend server...
start "Sverkan Server" cmd /k "python server\server.py"

echo Waiting for server...
timeout /t 2 /nobreak >nul

echo Starting client...
start "Sverkan Client" cmd /k "python client\qt_client.py"

echo.
echo ========================================
echo Sverkan has exited
echo ========================================
pause
