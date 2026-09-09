@echo off
echo ============================================
echo  IndusFire AI - Industrial Fire Monitor
echo ============================================
echo.
echo Starting backend server...
cd /d "%~dp0backend"
start "IndusFire Backend" python main.py
echo.
echo Backend starting on http://localhost:8000
echo.
timeout /t 3 /nobreak > nul
echo Opening dashboard...
start "" "%~dp0frontend\index.html"
echo.
echo ============================================
echo  Dashboard: frontend\index.html
echo  API Docs:  http://localhost:8000/docs
echo  Health:    http://localhost:8000/api/health
echo ============================================
echo.
echo Press any key to stop the server...
pause > nul
taskkill /FI "WINDOWTITLE eq IndusFire Backend*" /T /F
