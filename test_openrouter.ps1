# PowerShell script to test OpenRouter API

# Get API key from environment variable
$apiKey = $env:OPENROUTER_API_KEY

if (-not $apiKey) {
    Write-Host "❌ ERROR: OPENROUTER_API_KEY not found in environment" -ForegroundColor Red
    Write-Host "ℹ️  INFO: Please set OPENROUTER_API_KEY environment variable or add it to backend/.env" -ForegroundColor Yellow
    Write-Host "" 
    Write-Host "To set it temporarily in PowerShell:" -ForegroundColor Cyan
    Write-Host '  $env:OPENROUTER_API_KEY = "your-api-key-here"' -ForegroundColor Gray
    exit 1
}

$headers = @{
    "Content-Type" = "application/json"
    "Authorization" = "Bearer $apiKey"
}

$body = @{
    model = "amazon/nova-2-lite-v1:free"
    messages = @(
        @{
            role = "user"
            content = "Hello! Can you tell me a short joke?"
        }
    )
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "https://openrouter.ai/api/v1/chat/completions" -Method POST -Headers $headers -Body $body
    $response | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Error: $_"
    Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)"
}

