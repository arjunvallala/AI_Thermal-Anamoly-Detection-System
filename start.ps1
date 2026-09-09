# IndusFire AI - PowerShell Launcher
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " IndusFire AI - Industrial Fire Monitor" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Start backend
Write-Host "
Starting backend..." -ForegroundColor Yellow
 = Start-Process python -ArgumentList "main.py" -WorkingDirectory "\backend" -PassThru -WindowStyle Minimized
Write-Host "Backend PID: " -ForegroundColor Green

Start-Sleep -Seconds 3

# Test health
try {
     = Invoke-RestMethod http://localhost:8000/api/health
    Write-Host "Backend: ONLINE - " -ForegroundColor Green
} catch {
    Write-Host "Backend: Check if it started correctly" -ForegroundColor Red
}

# Open dashboard
Write-Host "
Opening dashboard in browser..." -ForegroundColor Yellow
Start-Process "\frontend\index.html"

Write-Host "
============================================" -ForegroundColor Cyan
Write-Host " Dashboard: Open frontend\index.html" -ForegroundColor White
Write-Host " API Docs:  http://localhost:8000/docs" -ForegroundColor White
Write-Host " Health:    http://localhost:8000/api/health" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "
Press Enter to stop the server..." -ForegroundColor Gray
Read-Host
 | Stop-Process -Force
Write-Host "Server stopped." -ForegroundColor Yellow
