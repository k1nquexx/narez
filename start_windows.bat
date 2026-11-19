@echo off
setlocal EnableExtensions
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Please run setup_windows.bat first!
    pause
    exit /b 1
)

echo ============================================================
echo   Starting ShortsFactory Studio on http://127.0.0.1:8000
echo   Close this window to stop the background worker and server.
echo ============================================================
echo.

start "" "http://127.0.0.1:8000"
".venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

pause
