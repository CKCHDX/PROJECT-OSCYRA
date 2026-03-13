@echo off
REM ============================================================================
REM KLAR SEARCH ENGINE - MASTER DEPLOYMENT SCRIPT
REM ============================================================================
REM One-click deployment: Crawl -> Index -> Configure -> Deploy -> Launch
REM This script handles EVERYTHING from start to production
REM ============================================================================

setlocal enabledelayedexpansion
color 0A

echo.
echo ================================================================================
echo    KLAR SEARCH ENGINE - AUTOMATED DEPLOYMENT
echo    Sweden's National Search Infrastructure
echo ================================================================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.8+ first.
    pause
    exit /b 1
)

echo [OK] Python detected
echo.

REM ============================================================================
REM STEP 1: CONFIGURATION CHECK
REM ============================================================================
echo ================================================================================
echo STEP 1: Checking Configuration
echo ================================================================================
echo.

if not exist "kse_settings.ini" (
    echo [INFO] Creating default settings file...
    python load_settings.py
    echo [OK] Settings file created: kse_settings.ini
    echo.
    echo You can edit kse_settings.ini to change:
    echo   - MAX_PAGES_PER_DOMAIN (default: 1000)
    echo   - MAX_CONCURRENT_CRAWLS (default: 10)
    echo   - API_PORT (default: 5000)
    echo.
    set /p CONTINUE="Continue with default settings? (Y/N): "
    if /i not "!CONTINUE!"=="Y" (
        echo.
        echo Edit kse_settings.ini and run this script again.
        pause
        exit /b 0
    )
) else (
    echo [OK] Configuration file found
    type kse_settings.ini
    echo.
)

REM ============================================================================
REM STEP 2: DEPENDENCY CHECK & INSTALLATION
REM ============================================================================
echo.
echo ================================================================================
echo STEP 2: Installing Dependencies
echo ================================================================================
echo.

echo [INFO] Checking and installing required packages...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo [OK] All dependencies installed
echo.

REM ============================================================================
REM STEP 3: NLTK DATA DOWNLOAD
REM ============================================================================
echo ================================================================================
echo STEP 3: Validating Optimization Components
echo ================================================================================
echo.

echo [INFO] Running optimization validation tests...
python test_optimizations.py

if errorlevel 1 (
    echo [WARNING] Optimization tests had issues, but continuing...
) else (
    echo [OK] All optimization components validated
)

echo.

REM ============================================================================
REM STEP 4: NLTK DATA DOWNLOAD
REM ============================================================================
echo ================================================================================
echo STEP 4: Downloading NLP Data
echo ================================================================================
echo.

python -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('stopwords', quiet=True)"
echo [OK] NLP data downloaded
echo.

REM ============================================================================
REM STEP 5: DIRECTORY STRUCTURE & DATA CHECK
REM ============================================================================
echo ================================================================================
echo STEP 5: Checking Existing Data
echo ================================================================================
echo.

if not exist "data" mkdir data
if not exist "data\crawled" mkdir data\crawled
if not exist "data\index" mkdir data\index
if not exist "logs" mkdir logs
if not exist ".cache" mkdir .cache

REM Check for existing crawled data
set CRAWLED_SIZE=0
set CRAWLED_COUNT=0
set INDEX_EXISTS=0
set SKIP_CRAWL=0
set SKIP_INDEX=0

REM Count files and sum sizes explicitly
for %%F in ("data\crawled\*.json") do (
    set /a CRAWLED_COUNT+=1
    set /a CRAWLED_SIZE+=%%~zF
)

REM Detect index by the real persisted file from indexer_standalone.py
if exist "data\index\search_index.pkl" (
    set INDEX_EXISTS=1
)


REM Display current data status
echo [STATUS] Current Data:
if not "!CRAWLED_COUNT!"=="0" (
    set /a CRAWLED_MB=CRAWLED_SIZE / 1048576
    echo   - Crawled pages: !CRAWLED_COUNT! files
    echo   - Storage used: !CRAWLED_SIZE! bytes (^~!CRAWLED_MB! MB^)
) else (
    echo   - Crawled pages: None
)

if !INDEX_EXISTS! EQU 1 (
    echo   - Search index: EXISTS
) else (
    echo   - Search index: NOT FOUND
)
echo.


REM Ask user what to do if data exists
if not "!CRAWLED_COUNT!"=="0" (
    echo ================================================================================
    echo EXISTING DATA FOUND!
    echo ================================================================================
    echo.
    echo You have existing crawled data. What would you like to do?
    echo.
    echo   [1] DELETE ALL and start fresh crawl (will take 30-60 min)
    echo   [2] KEEP DATA and skip crawling (use existing data)
    echo   [3] RESUME crawling (continue from last position)
    echo   [4] JUST START SERVER (skip crawl and index if ready)
    echo.
    set /p USER_CHOICE="Enter choice (1-4): "
    
    if "!USER_CHOICE!"=="1" (
        echo.
        echo [WARNING] This will DELETE all crawled data and search index!
        set /p CONFIRM="Are you sure? Type YES to confirm: "
        if /i "!CONFIRM!"=="YES" (
            echo.
            echo [INFO] Deleting all data...
            rmdir /s /q "data\crawled" 2>nul
            rmdir /s /q "data\index" 2>nul
            mkdir "data\crawled"
            mkdir "data\index"
            echo [OK] Data deleted. Starting fresh.
            set SKIP_CRAWL=0
            set SKIP_INDEX=0
        ) else (
            echo.
            echo [INFO] Delete cancelled. Keeping existing data.
            set SKIP_CRAWL=1
        )
    )
    
    if "!USER_CHOICE!"=="2" (
        echo [INFO] Keeping existing data. Skipping crawl.
        set SKIP_CRAWL=1
        if !INDEX_EXISTS! EQU 1 (
            echo [INFO] Search index found. Skipping index build too.
            set SKIP_INDEX=1
        ) else (
            echo [INFO] No index found. Will build index from existing data.
            set SKIP_INDEX=0
        )
    )
    
    if "!USER_CHOICE!"=="3" (
        echo [INFO] Will resume crawling from last position.
        set SKIP_CRAWL=0
        if !INDEX_EXISTS! EQU 1 (
            echo [INFO] Search index found. Skipping index build.
            set SKIP_INDEX=1
        ) else (
            echo [INFO] Will rebuild index after crawling.
            set SKIP_INDEX=0
        )
    )
    
    if "!USER_CHOICE!"=="4" (
        if !INDEX_EXISTS! EQU 1 (
            echo [INFO] Skipping to server launch.
            set SKIP_CRAWL=1
            set SKIP_INDEX=1
        ) else (
            echo [WARNING] Search index not found! Must build index first.
            set SKIP_CRAWL=1
            set SKIP_INDEX=0
        )
    )
    echo.
) else (
    echo [INFO] No existing data found. Will start fresh crawl.
    echo.
)

REM ============================================================================
REM STEP 6: WEB CRAWLING (conditional)
REM ============================================================================
if !SKIP_CRAWL! EQU 0 (
    echo ================================================================================
    echo STEP 6: Crawling Swedish Web
    echo ================================================================================
    echo.
    
    if exist "data\crawled\crawler_state.json" (
        echo [INFO] Found previous crawl state - resuming from last position
    ) else (
        echo [INFO] Starting fresh crawl
    )
    
    echo [INFO] This may take 30-60 minutes depending on settings...
    echo [INFO] You can safely close and restart - progress is saved automatically
    echo.
    
    python crawler.py
    
    if errorlevel 1 (
        echo.
        echo [WARNING] Crawling encountered errors but may have partial data
        set /p CONTINUE="Continue to indexing? (Y/N): "
        if /i not "!CONTINUE!"=="Y" (
            echo.
            echo Run this script again to resume crawling.
            pause
            exit /b 0
        )
    ) else (
        echo.
        echo [OK] Crawling completed successfully
    )
    
    REM Check if any pages were crawled
    dir /b /a "data\crawled\*.json" >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] No pages crawled! Check logs\crawler.log for details.
        pause
        exit /b 1
    )
    
    echo.
) else (
    echo ================================================================================
    echo STEP 6: Crawling - SKIPPED (using existing data)
    echo ================================================================================
    echo.
)

REM ============================================================================
REM STEP 7: BUILDING SEARCH INDEX (conditional)
REM ============================================================================
if !SKIP_INDEX! EQU 0 (
    echo ================================================================================
    echo STEP 7: Building Inverted Index
    echo ================================================================================
    echo.
    echo [INFO] Processing crawled pages and building search index...
    echo [INFO] This may take 10-30 minutes...
    echo.
    
    python indexer_standalone.py
    
    if errorlevel 1 (
        echo [ERROR] Indexing failed! Check logs\indexer.log for details.
        pause
        exit /b 1
    )
    
    echo.
    echo [OK] Search index built successfully
    echo.
) else (
    echo ================================================================================
    echo STEP 7: Indexing - SKIPPED (using existing index)
    echo ================================================================================
    echo.
)

REM ============================================================================
REM STEP 8: CALCULATING PAGERANK
REM ============================================================================
echo ================================================================================
echo STEP 8: Calculating PageRank
echo ================================================================================
echo.
echo [INFO] Running PageRank algorithm on link graph...
echo.

python -c "from ranker import calculate_pagerank; calculate_pagerank()"

if errorlevel 1 (
    echo [WARNING] PageRank calculation failed, continuing with default scores
) else (
    echo [OK] PageRank calculated
)

echo.

REM ============================================================================
REM STEP 9: SYSTEM HEALTH CHECK
REM ============================================================================
echo ================================================================================
echo STEP 9: Running System Health Check
echo ================================================================================
echo.

python -c "from health_check import run_health_check; run_health_check()"

echo.

REM ============================================================================
REM STEP 10: NETWORK CONFIGURATION & DNS INFORMATION
REM ============================================================================
echo ================================================================================
echo STEP 10: Network Configuration & IP Change Detection
echo ================================================================================
echo.

echo [INFO] Detecting IP addresses for DNS configuration...
echo.

REM Get local IP address
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set LOCAL_IP=%%a
    goto :found_local
)
:found_local
set LOCAL_IP=%LOCAL_IP:~1%

REM Get public IP address
for /f "delims=" %%a in ('powershell -Command "(Invoke-WebRequest -Uri 'https://api.ipify.org' -UseBasicParsing).Content" 2^>nul') do (
    set PUBLIC_IP=%%a
)

REM Check for previous IP address
set IP_CHANGED=0
set LAST_IP=
if exist ".cache\last_public_ip.txt" (
    set /p LAST_IP=<.cache\last_public_ip.txt
    if not "!LAST_IP!"=="%PUBLIC_IP%" (
        set IP_CHANGED=1
    )
) else (
    set IP_CHANGED=1
)

REM Save current IP
if defined PUBLIC_IP (
    echo %PUBLIC_IP%>.cache\last_public_ip.txt
    echo %date% %time%>.cache\last_ip_check.txt
)

echo ================================================================================
echo DNS CONFIGURATION INFORMATION
echo ================================================================================
echo.

REM Alert if IP changed
if !IP_CHANGED! EQU 1 (
    if defined LAST_IP (
        echo *** WARNING: PUBLIC IP ADDRESS HAS CHANGED! ***
        echo.
        echo   Previous IP: !LAST_IP!
        echo   Current IP:  %PUBLIC_IP%
        echo.
        echo   ACTION REQUIRED: Update your DNS A record!
        echo.
        echo ================================================================================
        echo.
    )
)

echo For DNS A Record Configuration:
echo.
if defined LOCAL_IP (
    echo   Local Network IP:  %LOCAL_IP%
    echo   ^(Use this for local network access^)
    echo.
)
if defined PUBLIC_IP (
    echo   Public IP Address: %PUBLIC_IP%
    if !IP_CHANGED! EQU 1 (
        if defined LAST_IP (
            echo   [CHANGED FROM: !LAST_IP!]
        ) else (
            echo   [FIRST TIME DETECTED]
        )
    ) else (
        echo   [NO CHANGE SINCE LAST RUN]
    )
    echo   ^(Use this for internet DNS records^)
    echo.
) else (
    echo   Public IP Address: Unable to detect
    echo   ^(Check manually at: https://whatismyip.com^)
    echo.
)
echo Server will listen on:
echo   - Local: http://localhost:5000
echo   - Network: http://%LOCAL_IP%:5000
if defined PUBLIC_IP (
    echo   - Public: http://%PUBLIC_IP%:5000
)
echo.
echo DNS Record Example:
echo   Type: A
echo   Name: search.yourdomain.com ^(or @ for root^)
if defined PUBLIC_IP (
    echo   Value: %PUBLIC_IP%
) else (
    echo   Value: ^[Your Public IP^]
)
echo   TTL: 3600
echo.
echo ================================================================================
echo.
if !IP_CHANGED! EQU 1 (
    if defined LAST_IP (
        echo.
        echo [!!!] IMPORTANT: Your public IP has changed!
        echo [!!!] Update your DNS records to point to: %PUBLIC_IP%
        echo.
        pause
    )
)
pause

REM ============================================================================
REM STEP 11: LAUNCH SERVER
REM ============================================================================
echo ================================================================================
echo STEP 11: Launching Search API Server
echo ================================================================================
echo.

echo [INFO] Starting Klar Search Engine API...
echo [INFO] The server will run on http://localhost:5000
echo.
echo Available endpoints:
echo   - POST /search - Search query endpoint
echo   - GET  /health - Health check
echo   - GET  /stats  - System statistics
echo.
echo ================================================================================
echo    DEPLOYMENT COMPLETE - SERVER STARTING
echo ================================================================================
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start server (this will run indefinitely)
python api_server.py

REM If server stops, show message
echo.
echo ================================================================================
echo Server stopped.
echo Run this script again to restart, or use: python api_server.py
echo ================================================================================
pause
