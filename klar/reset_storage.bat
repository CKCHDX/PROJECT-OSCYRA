@echo off
REM ============================================================================
REM KLAR Search Engine - Reset Storage & Logs
REM Deletes crawled data, indexes, and logs for clean initialization
REM ============================================================================

setlocal enabledelayedexpansion

echo.
echo ============================================================================
echo KLAR Storage Reset - Deleting data, indexes, and logs
echo ============================================================================
echo.

REM Delete data directory
if exist "data" (
    echo Deleting data directory...
    rmdir /s /q data
    if !errorlevel! equ 0 (
        echo [OK] data/ deleted
    ) else (
        echo [ERROR] Failed to delete data/
    )
) else (
    echo [SKIP] data/ does not exist
)

REM Delete logs directory
if exist "logs" (
    echo Deleting logs directory...
    rmdir /s /q logs
    if !errorlevel! equ 0 (
        echo [OK] logs/ deleted
    ) else (
        echo [ERROR] Failed to delete logs/
    )
) else (
    echo [SKIP] logs/ does not exist
)

REM Delete cache files if present
if exist ".cache" (
    echo Deleting cache directory...
    rmdir /s /q .cache
    echo [OK] .cache/ deleted
)

echo.
echo ============================================================================
echo Storage reset complete. Ready for fresh initialization.
echo Run: python init_kse.py
echo ============================================================================
echo.

pause
