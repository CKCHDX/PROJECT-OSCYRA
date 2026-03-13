@echo off
REM Build Sverkan Qt Client into a standalone EXE
call C:\Users\akoj2\Desktop\Sverkan\sverkan\venv\Scripts\activate.bat
REM Ensure Python and PyInstaller are installed
python -m pip install --upgrade pip
python -m pip install pyinstaller

REM Build the EXE
pyinstaller --onefile --windowed qt_client.py --name SverkanQtClient

REM Output location
if exist dist\SverkanQtClient.exe (
    echo Build successful! EXE located at dist\SverkanQtClient.exe
) else (
    echo Build failed. Check for errors above.
)
pause
