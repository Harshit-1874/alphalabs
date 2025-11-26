# PowerShell script to run both frontend and backend
Write-Host "Starting AlphaLabs development servers..." -ForegroundColor Green

# Start backend in background
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; python app.py" -WindowStyle Normal

# Start frontend
Write-Host "Starting frontend on http://localhost:3000" -ForegroundColor Cyan
bun run --filter @alphalabs/frontend dev

