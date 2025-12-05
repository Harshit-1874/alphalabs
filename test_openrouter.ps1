# PowerShell script to test OpenRouter API
$headers = @{
    "Content-Type" = "application/json"
    "Authorization" = "Bearer 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"
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

