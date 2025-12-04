# Fly.io Secrets Setup Script
# Reads .env file and sets secrets on Fly.io
# Run this from the backend directory

Write-Host "Setting Fly.io Secrets from .env file" -ForegroundColor Cyan
Write-Host ""

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "ERROR: .env file not found!" -ForegroundColor Red
    Write-Host "Please create a .env file with your environment variables." -ForegroundColor Yellow
    exit 1
}

Write-Host "OK: Found .env file" -ForegroundColor Green
Write-Host ""

# Read .env file and parse key-value pairs
$envVars = @{}
Get-Content ".env" | ForEach-Object {
    $line = $_.Trim()
    # Skip empty lines and comments
    if ($line -and -not $line.StartsWith("#")) {
        if ($line -match "^([^=]+)=(.*)$") {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            # Remove quotes if present
            if ($value.StartsWith('"') -and $value.EndsWith('"')) {
                $value = $value.Substring(1, $value.Length - 2)
            }
            if ($value.StartsWith("'") -and $value.EndsWith("'")) {
                $value = $value.Substring(1, $value.Length - 2)
            }
            $envVars[$key] = $value
        }
    }
}

# List of required secrets to set
$requiredSecrets = @(
    "OPENROUTER_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "DATABASE_URL",
    "CLERK_SECRET_KEY",
    "CLERK_WEBHOOK_SECRET",
    "ENCRYPTION_KEY"
)

# Additional database secrets (fallback options)
$databaseSecrets = @(
    "DB_CONNECTION_STRING",
    "SUPABASE_DB_HOST",
    "SUPABASE_DB_PORT",
    "SUPABASE_DB_NAME",
    "SUPABASE_DB_USER",
    "SUPABASE_DB_PASSWORD"
)

# Optional secrets (will be set if found)
$optionalSecrets = @(
    "CERTIFICATE_SHARE_BASE_URL",
    "WEBSOCKET_BASE_URL",
    "OPENROUTER_HTTP_REFERER",
    "OPENROUTER_X_TITLE"
)

Write-Host "Found environment variables:" -ForegroundColor Cyan
$envVars.Keys | ForEach-Object { Write-Host "  - $_" -ForegroundColor Gray }
Write-Host ""

# Check for required secrets
$missing = @()
foreach ($secret in $requiredSecrets) {
    if (-not $envVars.ContainsKey($secret) -or [string]::IsNullOrWhiteSpace($envVars[$secret])) {
        $missing += $secret
    }
}

if ($missing.Count -gt 0) {
    Write-Host "WARNING: Missing required environment variables:" -ForegroundColor Yellow
    $missing | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Host ""
    Write-Host "Please add these to your .env file before running this script." -ForegroundColor Yellow
    exit 1
}

# Build the flyctl secrets set command
$secretsToSet = @{}
foreach ($secret in ($requiredSecrets + $optionalSecrets + $databaseSecrets)) {
    if ($envVars.ContainsKey($secret) -and -not [string]::IsNullOrWhiteSpace($envVars[$secret])) {
        $secretsToSet[$secret] = $envVars[$secret]
    }
}

# Validate DATABASE_URL format if present
if ($secretsToSet.ContainsKey("DATABASE_URL")) {
    $dbUrl = $secretsToSet["DATABASE_URL"]
    if (-not $dbUrl.StartsWith("postgresql://") -and -not $dbUrl.StartsWith("postgresql+asyncpg://")) {
        Write-Host "WARNING: DATABASE_URL should start with 'postgresql://'" -ForegroundColor Yellow
        Write-Host "  Current value starts with: $($dbUrl.Substring(0, [Math]::Min(20, $dbUrl.Length)))..." -ForegroundColor Gray
    }
}

# Check if flyctl is available
if (-not (Get-Command flyctl -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Fly.io CLI not found!" -ForegroundColor Red
    Write-Host "Install it with: powershell -Command `"iwr https://fly.io/install.ps1 -useb | iex`"" -ForegroundColor Yellow
    exit 1
}

# Check authentication
Write-Host "Checking authentication..." -ForegroundColor Cyan
$authCheck = flyctl auth whoami 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Not authenticated. Please login first:" -ForegroundColor Red
    Write-Host "  flyctl auth login" -ForegroundColor Yellow
    exit 1
}

Write-Host "OK: Authenticated" -ForegroundColor Green
Write-Host ""

# Set secrets
Write-Host "Setting secrets on Fly.io..." -ForegroundColor Cyan
Write-Host ""

$secretArgs = @()
foreach ($key in $secretsToSet.Keys) {
    $value = $secretsToSet[$key]
    $secretArgs += "$key=$value"
    Write-Host "  Setting $key..." -ForegroundColor Gray
}

# Set all secrets at once
$secretString = $secretArgs -join " "
flyctl secrets set $secretString

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "OK: Successfully set all secrets!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Set secrets:" -ForegroundColor Cyan
    foreach ($key in $secretsToSet.Keys) {
        Write-Host "  OK: $key" -ForegroundColor Green
    }
    Write-Host ""
    Write-Host "Next step: Run 'flyctl deploy' to deploy your app" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "ERROR: Failed to set secrets" -ForegroundColor Red
    Write-Host "You may need to set them individually:" -ForegroundColor Yellow
    foreach ($key in $secretsToSet.Keys) {
        $value = $secretsToSet[$key]
        Write-Host "  flyctl secrets set $key=$value" -ForegroundColor White
    }
    exit 1
}


