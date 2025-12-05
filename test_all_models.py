#!/usr/bin/env python3
"""
Test script to verify all OpenRouter models in the backend.
Tests all models from AVAILABLE_MODELS and checks for issues.
"""
import requests
import time
import json
from typing import List, Dict, Any

API_KEY = "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"
TEST_PROMPT = "Say 'Hello, I am working!' in one sentence."

# All models from backend/api/models.py
MODELS = [
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
]

# Additional models found in codebase
ADDITIONAL_MODELS = [
    "amazon/nova-2-lite-v1:free",  # Free version mentioned by user
    "deepseek/deepseek-chat",      # Found in test files
    "anthropic/claude-3.5-sonnet"  # Found in examples
]

# Combine and deduplicate
ALL_MODELS = list(set(MODELS + ADDITIONAL_MODELS))

def test_model(model: str) -> Dict[str, Any]:
    """Test a single model with OpenRouter API."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": TEST_PROMPT
            }
        ]
    }
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            
            return {
                "model": model,
                "status": "[OK] SUCCESS",
                "response": content,
                "tokens": usage.get("total_tokens", 0),
                "error": None
            }
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            return {
                "model": model,
                "status": "[FAIL] FAILED",
                "response": None,
                "tokens": None,
                "error": error_msg
            }
            
    except Exception as e:
        return {
            "model": model,
            "status": "[FAIL] FAILED",
            "response": None,
            "tokens": None,
            "error": str(e)
        }

def main():
    print(f"\n[TEST] Testing {len(ALL_MODELS)} models with OpenRouter API...")
    print("=" * 80)
    
    results = []
    success_count = 0
    failure_count = 0
    
    for model in sorted(ALL_MODELS):
        print(f"\n[TEST] Testing: {model}")
        result = test_model(model)
        results.append(result)
        
        if result["status"] == "[OK] SUCCESS":
            print(f"  [OK] SUCCESS")
            preview = result["response"][:100] + "..." if len(result["response"]) > 100 else result["response"]
            print(f"  Response: {preview}")
            print(f"  Tokens: {result['tokens']}")
            success_count += 1
        else:
            print(f"  [FAIL] FAILED: {result['error']}")
            failure_count += 1
        
        # Small delay to avoid rate limits
        time.sleep(0.5)
    
    print("\n" + "=" * 80)
    print(f"\n[SUMMARY]")
    print(f"  Total Models: {len(ALL_MODELS)}")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {failure_count}")
    
    print(f"\n[DETAILED RESULTS]")
    print(f"{'Model':<50} {'Status':<15} {'Tokens':<10} {'Error':<30}")
    print("-" * 105)
    for r in results:
        error_preview = (r["error"][:27] + "...") if r["error"] and len(r["error"]) > 30 else (r["error"] or "")
        print(f"{r['model']:<50} {r['status']:<15} {str(r['tokens'] or ''):<10} {error_preview:<30}")
    
    # Check for potential issues
    print(f"\n[ISSUES FOUND]")
    
    # Check 1: Model ID mismatch in migration file
    print("  [WARN] Migration file maps 'llama-3.3-70b-instruct' to 'meta-llama/llama-3.1-70b-instruct'")
    print("         But models.py has 'meta-llama/llama-3.3-70b-instruct' - potential mismatch!")
    
    # Check 2: Missing :free suffix
    nova_models = [m for m in MODELS if "amazon/nova-2-lite" in m and ":free" not in m]
    if nova_models:
        print("  [WARN] Found 'amazon/nova-2-lite-v1' without :free suffix")
        print("         User mentioned 'amazon/nova-2-lite-v1:free' - check if both work")
    
    # Check 3: Old model formats still in code
    print("  [WARN] Found old model formats in test files:")
    print("         - 'deepseek-r1' (should be updated to OpenRouter format)")
    print("         - 'gpt-4' (test mock, but verify if used in production)")
    
    # Check 4: Duplicate gemma-3-27b-it
    gemma_27b_count = sum(1 for m in MODELS if m == "google/gemma-3-27b-it")
    if gemma_27b_count > 1:
        print(f"  [WARN] Found duplicate 'google/gemma-3-27b-it' in models list ({gemma_27b_count} times)")
    
    print("\n[COMPLETE] Test complete!")

if __name__ == "__main__":
    main()

