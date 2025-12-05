# Test script to verify all OpenRouter models in the backend
# Tests all models from AVAILABLE_MODELS and checks for issues

$apiKey = "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"
$testPrompt = "Say 'Hello, I am working!' in one sentence."

# All models from backend/api/models.py
$models = @(
    "qwen/qwen3-235b-a22b",
    "qwen/qwen3-coder",
    "qwen/qwen3-4b:free",
    "openai/gpt-oss-20b",
    "arcee-ai/trinity-mini",
    "amazon/nova-2-lite-v1",
    "nousresearch/hermes-3-llama-3.1-405b",
    "nvidia/nemotron-nano-12b-v2-vl",
    "nvidia/nemotron-nano-9b-v2",
    "moonshotai/kimi-k2",
    "google/gemma-3-27b-it",
    "google/gemma-3n-e4b-it",
    "google/gemma-3n-e2b-it:free",
    "google/gemma-3-4b-it",
    "google/gemma-3-12b-it",
    "google/gemma-3-27b-it",
    "allenai/olmo-3-32b-think:free",
    "mistralai/mistral-7b-instruct-v0.3",
    "meta-llama/llama-3.3-70b-instruct"
)

# Additional models found in codebase
$additionalModels = @(
    "amazon/nova-2-lite-v1:free",
    "deepseek/deepseek-chat",
    "anthropic/claude-3.5-sonnet"
)

# Combine and get unique models
$allModelsList = New-Object System.Collections.ArrayList
foreach ($m in $models) { [void]$allModelsList.Add($m) }
foreach ($m in $additionalModels) { 
    if (-not $allModelsList.Contains($m)) { [void]$allModelsList.Add($m) }
}
$allModels = $allModelsList.ToArray()

$headers = @{
    "Content-Type" = "application/json"
    "Authorization" = "Bearer $apiKey"
}

Write-Host ""
Write-Host "🧪 Testing $($allModels.Count) models with OpenRouter API..." -ForegroundColor Cyan
Write-Host ("=" * 80) -ForegroundColor Gray

$results = @()
$successCount = 0
$failureCount = 0

foreach ($model in $allModels) {
    Write-Host ""
    Write-Host "📡 Testing: $model" -ForegroundColor Yellow
    
    $body = @{
        model = $model
        messages = @(
            @{
                role = "user"
                content = $testPrompt
            }
        )
    } | ConvertTo-Json -Depth 10
    
    try {
        $response = Invoke-RestMethod -Uri "https://openrouter.ai/api/v1/chat/completions" -Method POST -Headers $headers -Body $body -ErrorAction Stop
        
        $content = $response.choices[0].message.content
        $usage = $response.usage
        
        Write-Host "  ✅ SUCCESS" -ForegroundColor Green
        $preview = if ($content.Length -gt 100) { $content.Substring(0, 100) + "..." } else { $content }
        Write-Host "  Response: $preview" -ForegroundColor Gray
        Write-Host "  Tokens: $($usage.total_tokens) (prompt: $($usage.prompt_tokens), completion: $($usage.completion_tokens))" -ForegroundColor Gray
        
        $results += [PSCustomObject]@{
            Model = $model
            Status = "✅ SUCCESS"
            Response = $content
            Tokens = $usage.total_tokens
            Error = $null
        }
        $successCount++
        
    } catch {
        $errorMsg = $_.Exception.Message
        if ($_.Exception.Response) {
            $statusCode = $_.Exception.Response.StatusCode.value__
            $errorMsg = "HTTP $statusCode : $errorMsg"
        }
        
        Write-Host "  ❌ FAILED: $errorMsg" -ForegroundColor Red
        
        $results += [PSCustomObject]@{
            Model = $model
            Status = "❌ FAILED"
            Response = $null
            Tokens = $null
            Error = $errorMsg
        }
        $failureCount++
    }
    
    # Small delay to avoid rate limits
    Start-Sleep -Milliseconds 500
}

Write-Host ""
Write-Host ("=" * 80) -ForegroundColor Gray
Write-Host ""
Write-Host "📊 SUMMARY" -ForegroundColor Cyan
Write-Host "  Total Models: $($allModels.Count)" -ForegroundColor White
Write-Host "  ✅ Successful: $successCount" -ForegroundColor Green
Write-Host "  ❌ Failed: $failureCount" -ForegroundColor Red

Write-Host ""
Write-Host "📋 DETAILED RESULTS:" -ForegroundColor Cyan
$results | Format-Table -AutoSize

# Check for potential issues
Write-Host ""
Write-Host "🔍 POTENTIAL ISSUES FOUND:" -ForegroundColor Yellow

# Check 1: Model ID mismatch in migration file
Write-Host "  ⚠️  Migration file maps 'llama-3.3-70b-instruct' to 'meta-llama/llama-3.1-70b-instruct'" -ForegroundColor Yellow
Write-Host "     But models.py has 'meta-llama/llama-3.3-70b-instruct' - potential mismatch!" -ForegroundColor Yellow

# Check 2: Missing :free suffix
$modelsWithoutFree = $models | Where-Object { $_ -notmatch ":free" -and $_ -match "amazon/nova-2-lite" }
if ($modelsWithoutFree) {
    Write-Host "  ⚠️  Found 'amazon/nova-2-lite-v1' without :free suffix" -ForegroundColor Yellow
    Write-Host "     User mentioned 'amazon/nova-2-lite-v1:free' - check if both work" -ForegroundColor Yellow
}

# Check 3: Old model formats still in code
Write-Host "  ⚠️  Found old model formats in test files:" -ForegroundColor Yellow
Write-Host "     - 'deepseek-r1' (should be updated to OpenRouter format)" -ForegroundColor Yellow
Write-Host "     - 'gpt-4' (test mock, but verify if used in production)" -ForegroundColor Yellow

Write-Host ""
Write-Host "✅ Test complete!" -ForegroundColor Green
