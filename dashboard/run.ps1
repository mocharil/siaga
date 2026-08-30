# ==============================================================================
# SIAGA Dashboard Runner for Windows PowerShell (D4)
# Binds strictly to 127.0.0.1:8000 for local access.
# ==============================================================================

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

$env:PYTHONPATH = "$ProjectRoot;$env:PYTHONPATH"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "Starting SIAGA Security Monitoring Dashboard" -ForegroundColor Green
Write-Host "URL: http://127.0.0.1:8000" -ForegroundColor Yellow
Write-Host "Security: Strictly Read-Only Mode (SQLite ?mode=ro, localhost only)" -ForegroundColor Gray
Write-Host "=================================================================" -ForegroundColor Cyan

Set-Location -Path $ProjectRoot
python -m uvicorn dashboard.api:app --host 127.0.0.1 --port 8000 --log-level info
