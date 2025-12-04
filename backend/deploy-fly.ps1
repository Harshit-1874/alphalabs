# Fly.io Deployment Script for AlphaLabs Backend
# Run this script from the backend directory

Write-Host "AlphaLabs Backend - Fly.io Deployment" -ForegroundColor Cyan
Write-Host ""

# Check if flyctl is installed
if (-not (Get-Command flyctl -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Fly.io CLI not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Install it with:" -ForegroundColor Yellow
    Write-Host '  powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"' -ForegroundColor White
    Write-Host ""
    Write-Host "Or download from: https://fly.io/docs/getting-started/installing-flyctl/" -ForegroundColor White
    exit 1
}

Write-Host "OK: Fly.io CLI found" -ForegroundColor Green
Write-Host ""

# Check if logged in
Write-Host "Checking authentication..." -ForegroundColor Cyan
$authCheck = flyctl auth whoami 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: Not logged in. Please login first:" -ForegroundColor Yellow
    Write-Host "  flyctl auth login" -ForegroundColor White
    exit 1
}

Write-Host "OK: Authenticated as: $($authCheck)" -ForegroundColor Green
Write-Host ""

# Check if app exists
Write-Host "Checking if app 'alphalabs-backend' exists..." -ForegroundColor Cyan
$appCheck = flyctl apps list 2>&1 | Select-String "alphalabs-backend"
if (-not $appCheck) {
    Write-Host "WARNING: App not found. Creating app..." -ForegroundColor Yellow
    flyctl apps create alphalabs-backend --org personal
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to create app" -ForegroundColor Red
        exit 1
    }
    Write-Host "OK: App created" -ForegroundColor Green
} else {
    Write-Host "OK: App exists" -ForegroundColor Green
}

Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Set environment variables (secrets):" -ForegroundColor Yellow
Write-Host "   Run: .\set-fly-secrets.ps1" -ForegroundColor White
Write-Host "   Or manually set each secret:" -ForegroundColor White
Write-Host "   flyctl secrets set OPENROUTER_API_KEY=your_key" -ForegroundColor Gray
Write-Host "   flyctl secrets set SUPABASE_URL=https://your-project.supabase.co" -ForegroundColor Gray
Write-Host "   flyctl secrets set SUPABASE_KEY=your_key" -ForegroundColor Gray
Write-Host "   flyctl secrets set DATABASE_URL=postgresql://user:pass@host:5432/dbname" -ForegroundColor Gray
Write-Host "   flyctl secrets set CLERK_SECRET_KEY=sk_test_..." -ForegroundColor Gray
Write-Host "   flyctl secrets set CLERK_WEBHOOK_SECRET=whsec_..." -ForegroundColor Gray
Write-Host "   flyctl secrets set ENCRYPTION_KEY=your_fernet_key" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Deploy:" -ForegroundColor Yellow
Write-Host "   flyctl deploy" -ForegroundColor White
Write-Host ""
Write-Host "3. Check status:" -ForegroundColor Yellow
Write-Host "   flyctl status" -ForegroundColor White
Write-Host "   flyctl logs" -ForegroundColor White
Write-Host ""
Write-Host "4. Get your app URL:" -ForegroundColor Yellow
Write-Host "   flyctl info" -ForegroundColor White
Write-Host ""
