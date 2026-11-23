@echo off
REM ── One-click start: Docker -> Qdrant -> (ingest if needed) -> web app ──
title Knowledge Network
cd /d "%~dp0"

echo.
echo  [1/4] Checking Docker...
docker info >nul 2>&1
if not errorlevel 1 goto dockerready
echo        Docker is not running - starting Docker Desktop...
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
:waitdocker
timeout /t 3 /nobreak >nul
docker info >nul 2>&1
if errorlevel 1 goto waitdocker
:dockerready
echo        Docker is ready.

echo  [2/4] Starting the Qdrant database...
docker compose up -d qdrant >nul 2>&1
if errorlevel 1 (
    echo        ERROR: could not start Qdrant. Open Docker Desktop and try again.
    pause
    exit /b 1
)
echo        Qdrant is running.

if not exist ".venv\Scripts\python.exe" (
    echo        ERROR: .venv not found. See HOW_TO_USE.pdf, "First-time setup".
    pause
    exit /b 1
)

echo  [3/4] Checking documents...
if not exist "data\docstore.jsonl" (
    echo        No index yet - reading the PDFs in data\sample_docs...
    set PYTHONIOENCODING=utf-8
    ".venv\Scripts\python.exe" scripts\02_ingest.py
)
echo        Documents are indexed.

REM `start.bat share` = also reachable from other devices on the same Wi-Fi.
set HOST=127.0.0.1
if /i "%~1"=="share" set HOST=0.0.0.0

echo  [4/4] Starting the app at http://localhost:8080
if "%HOST%"=="0.0.0.0" (
    echo.
    echo        SHARING ON WI-FI. Others on the same network can open:
    powershell -NoProfile -Command "Get-NetIPConfiguration | Where-Object IPv4DefaultGateway | ForEach-Object { '         http://' + $_.IPv4Address.IPAddress + ':8080' }"
    echo        If Windows asks about the firewall, click "Allow".
)
echo.
echo  ===========================================================
echo   Keep this window OPEN while you use the app.
echo   The browser opens by itself in about a minute.
echo   To stop the app: close this window (or press Ctrl+C).
echo  ===========================================================
echo.
REM Use the keys from .env, not any placeholder set in Windows.
set OPENAI_API_KEY=
set PYTHONIOENCODING=utf-8
start "" /min powershell -NoProfile -WindowStyle Hidden -Command "while (-not (Test-NetConnection 127.0.0.1 -Port 8080 -InformationLevel Quiet -WarningAction SilentlyContinue)) { Start-Sleep 2 }; Start-Process http://localhost:8080"
".venv\Scripts\python.exe" -m uvicorn src.api:app --host %HOST% --port 8080
pause
