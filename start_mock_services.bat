@echo off
REM Start all mock AI services for testing

echo ============================================================
echo Starting Mock AI Services for Testing
echo ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please install Python 3.8+ and add to PATH
    pause
    exit /b 1
)

echo Installing dependencies if needed...
pip install fastapi uvicorn pillow --quiet

echo.
echo Starting services on ports 8001-8004...
echo Press Ctrl+C in each window to stop services
echo.

REM Start each service in a new window
start "Florence2 Mock (8001)" cmd /k "python quick_start_minimal_ai.py 8001"
timeout /t 2 /nobreak >nul

start "YOLO Mock (8002)" cmd /k "python quick_start_minimal_ai.py 8002"
timeout /t 2 /nobreak >nul

start "SAM2 Mock (8003)" cmd /k "python quick_start_minimal_ai.py 8003"
timeout /t 2 /nobreak >nul

start "SDXL Mock (8004)" cmd /k "python quick_start_minimal_ai.py 8004"
timeout /t 2 /nobreak >nul

echo.
echo ============================================================
echo All mock services started!
echo ============================================================
echo.
echo Services running on:
echo   - Florence2 (Vision): http://localhost:8001
echo   - YOLO (Detection):   http://localhost:8002
echo   - SAM2 (Segment):     http://localhost:8003
echo   - SDXL (Generation):  http://localhost:8004
echo.
echo Check service status:
echo   python check_services.py
echo.
echo These are MOCK services for testing only!
echo For production, use real AI models.
echo.
echo Press any key to exit (services will keep running)...
pause >nul
