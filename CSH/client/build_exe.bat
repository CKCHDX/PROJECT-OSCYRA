@echo off
echo ================================================================================
echo Building SLP Client Windows Executable
echo ================================================================================
echo.

echo Installing PyInstaller...
pip install pyinstaller
echo.

echo Building executable...
pyinstaller --onefile --windowed --name=SLP_Client --icon=NONE slp_client_gui.py
echo.

if exist "dist\SLP_Client.exe" (
    echo ================================================================================
    echo Build Complete!
    echo ================================================================================
    echo.
    echo Executable location: dist\SLP_Client.exe
    echo Size: 
    dir dist\SLP_Client.exe | find "SLP_Client.exe"
    echo.
    echo You can now run: dist\SLP_Client.exe
    echo ================================================================================
) else (
    echo ================================================================================
    echo Build Failed!
    echo ================================================================================
    echo Check the output above for errors.
)

pause
