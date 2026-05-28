# start.ps1 - Universal Paperclips Agent Launcher
# Starts relay.py in a new terminal window, then runs agent.py here.
# Usage: right-click -> "Run with PowerShell"  OR  powershell -File start.ps1

Write-Host ""
Write-Host "  Universal Paperclips - Agent Launcher" -ForegroundColor Cyan
Write-Host "  ----------------------------------------" -ForegroundColor DarkCyan
Write-Host ""

$relay = Join-Path $PSScriptRoot "relay.py"
$agent = Join-Path $PSScriptRoot "agent.py"

if (-not (Test-Path $relay) -or -not (Test-Path $agent)) {
    Write-Host "  ERROR: relay.py or agent.py not found." -ForegroundColor Red
    Write-Host "  Run this script from the project folder." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "  [1/3] Starting relay in new window..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'RELAY SERVER' -ForegroundColor Cyan; python `"$relay`""

Write-Host "  [2/3] Waiting 2s for relay to start..." -ForegroundColor DarkGray
Start-Sleep -Seconds 2

Write-Host "  [3/3] Starting agent  (Ctrl+C to stop)" -ForegroundColor Green
Write-Host "        Dashboard -> http://localhost:5000" -ForegroundColor DarkCyan
Write-Host ""
python $agent
