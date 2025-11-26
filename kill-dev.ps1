# Kill all dev processes
Write-Host "Killing all dev processes..." -ForegroundColor Yellow

# Kill Node/Next.js processes
Get-Process | Where-Object {$_.ProcessName -like "*node*" -or $_.ProcessName -like "*next*"} | Stop-Process -Force -ErrorAction SilentlyContinue

# Kill Python processes
Get-Process | Where-Object {$_.ProcessName -like "*python*"} | Stop-Process -Force -ErrorAction SilentlyContinue

# Remove lock files
Remove-Item -Path "frontend\.next\dev\lock" -Force -ErrorAction SilentlyContinue

Write-Host "All processes killed!" -ForegroundColor Green

