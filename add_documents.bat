@echo off
REM ── Re-index every PDF in data\sample_docs (run after adding/removing PDFs) ──
title Knowledge Network - Add documents
cd /d "%~dp0"

docker info >nul 2>&1
if errorlevel 1 (
    echo Docker is not running. Start Docker Desktop first, then run this again.
    pause
    exit /b 1
)
docker compose up -d qdrant >nul 2>&1

echo Reading all PDFs in data\sample_docs ...
REM Start from a clean collection so removed PDFs disappear from search too.
curl -s -X DELETE http://localhost:6333/collections/enterprise_docs >nul 2>&1
set PYTHONIOENCODING=utf-8
".venv\Scripts\python.exe" scripts\02_ingest.py
echo.
echo Done. If the app is running, close its window and start it again with start.bat.
pause
