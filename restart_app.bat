@echo off
echo ============================================================
echo Restarting Gruha Alankar Flask Application
echo ============================================================
echo.

REM Kill any existing Flask/Python processes for this app
echo Stopping existing Flask processes...
for /f "tokens=2" %%a in ('tasklist ^| findstr /i "python.exe"') do (
    taskkill /F /PID %%a 2>nul
)

echo.
echo Waiting for processes to stop...
timeout /t 2 /nobreak >nul

echo.
echo ============================================================
echo Starting Flask Application
echo ============================================================
echo.

REM Start Flask app
python app_minimal.py

pause
