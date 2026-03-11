@echo off
echo ============================================
echo RESTARTING AEGIS TRADER BACKEND
echo ============================================
echo.

echo Step 1: Stopping existing Python processes...
taskkill /F /IM python.exe /T 2>nul
timeout /t 2 /nobreak >nul

echo.
echo Step 2: Starting backend server...
echo Command: python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
echo.
echo NOTE: Backend will start in this window.
echo       Keep this window open while using the mobile app.
echo       Press Ctrl+C to stop the backend.
echo.
echo ============================================
echo.

python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
