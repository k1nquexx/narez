@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo   ShortsFactory - Windows 10/11 Setup (CUDA RTX 3060 Ready)
echo ============================================================
echo.

set "PY_CMD="
py -3.12 --version >nul 2>&1 && set "PY_CMD=py -3.12"
if not defined PY_CMD (
    py -3.11 --version >nul 2>&1 && set "PY_CMD=py -3.11"
)
if not defined PY_CMD (
    python --version >nul 2>&1 && set "PY_CMD=python"
)

if not defined PY_CMD (
    echo [ERROR] Python 3.11 or 3.12 was not found!
    echo Please install Python 3.12 from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/6] Using Python command: %PY_CMD%
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment in .venv...
    %PY_CMD% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create .venv.
        pause
        exit /b 1
    )
)

echo [2/6] Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip

echo [3/6] Installing PyTorch with CUDA 12.4 (for NVIDIA RTX GPU)...
".venv\Scripts\python.exe" -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
if errorlevel 1 (
    echo [WARN] CUDA 12.4 wheel install failed, trying CUDA 12.1...
    ".venv\Scripts\python.exe" -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
)

echo [4/6] Installing core Python dependencies (requirements.txt)...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install requirements.txt
    pause
    exit /b 1
)

echo [5/6] Installing GPU AI dependencies (requirements-gpu.txt)...
".venv\Scripts\python.exe" -m pip install -r requirements-gpu.txt
if errorlevel 1 (
    echo [WARN] Optional GPU packages failed to install. Gameplay mode will still work.
)

echo [6/6] Checking FFmpeg, fonts, and hardware acceleration...
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo.
    echo [WARNING] ffmpeg.exe not found on PATH!
    echo Install FFmpeg easily via PowerShell / CMD:
    echo   winget install -e --id Gyan.FFmpeg
    echo Then reopen this terminal and re-run setup_windows.bat.
    echo.
)

".venv\Scripts\python.exe" -m backend.scripts.ensure_assets
".venv\Scripts\python.exe" -m backend.core.hardware

if not exist "frontend\dist\index.html" (
    where npm >nul 2>&1
    if not errorlevel 1 (
        echo Building frontend UI...
        pushd frontend
        call npm install
        call npm run build
        popd
    ) else (
        echo [INFO] frontend\dist missing and npm not installed. Copy prebuilt frontend\dist from Linux.
    )
)

if not exist ".env" (
    if exist ".env.example" copy /Y ".env.example" ".env" >nul
)

echo.
echo ============================================================
echo   Setup complete! Run start_windows.bat to launch Studio.
echo ============================================================
pause
