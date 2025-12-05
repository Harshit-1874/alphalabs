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

# ✅ ALL MODELS - Free and Paid (Updated Dec 2025)
# Testing all models from backend/api/models.py

# FREE MODELS (18 models - removed rate-limited ones)
FREE_MODELS = [
    # Verified working free models only
    "amazon/nova-2-lite-v1:free",
    "google/gemma-3n-e2b-it:free",
    "arcee-ai/trinity-mini:free",
    "google/gemma-3-4b-it:free",
    "google/gemma-3-12b-it:free",
    "google/gemma-3n-e4b-it:free",
    "tngtech/deepseek-r1t2-chimera:free",
    "kwaipilot/kat-coder-pro:free",
    "tngtech/deepseek-r1t-chimera:free",
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "qwen/qwen3-coder:free",
    "google/gemma-3-27b-it:free",
    "openai/gpt-oss-20b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
]

# PAID MODELS (24 models)
PAID_MODELS = [
    # Basic paid models
    "nvidia/nemotron-nano-9b-v2",
    "google/gemma-3-27b-it",
    "mistralai/mistral-7b-instruct-v0.3",
    "meta-llama/llama-3.3-70b-instruct",
    
    # Premium paid models
    "anthropic/claude-opus-4.5",
    "openai/gpt-5.1",
    "google/gemini-3-pro-preview",
    "anthropic/claude-sonnet-4.5",
    "openai/gpt-5-chat",
    "deepseek/deepseek-r1",
    "deepseek/deepseek-r1-0528",
    "tngtech/deepseek-r1t2-chimera",
    "qwen/qwen3-next-80b-a3b-thinking",
    "qwen/qwen3-235b-a22b-thinking-2507",
    "google/gemini-2.5-pro",
    "openai/o3",
    "openai/o3-deep-research",
    "deepseek/deepseek-v3.2-exp",
    "deepseek/deepseek-v3.2-speciale",
    "deepseek/deepseek-v3.1-terminus",
    "google/gemini-2.5-flash",
    "z-ai/glm-4.6",
    "meta-llama/llama-4-maverick",
    "qwen/qwen3-max",
]

# Combine all models for testing
ALL_MODELS = FREE_MODELS + PAID_MODELS

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
    print(f"  Free Models: {len(FREE_MODELS)}")
    print(f"  Paid Models: {len(PAID_MODELS)}")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {failure_count}")
    print(f"  Success Rate: {(success_count/len(ALL_MODELS)*100):.1f}%")
    
    print(f"\n[DETAILED RESULTS]")
    print(f"{'Model':<50} {'Status':<15} {'Tokens':<10} {'Error':<30}")
    print("-" * 105)
    for r in results:
        error_preview = (r["error"][:27] + "...") if r["error"] and len(r["error"]) > 30 else (r["error"] or "")
        print(f"{r['model']:<50} {r['status']:<15} {str(r['tokens'] or ''):<10} {error_preview:<30}")
    
    # Check for potential issues
    print(f"\n[ISSUES FOUND]")
    
    failed_models = [r for r in results if r["status"] == "[FAIL] FAILED"]
    
    if failed_models:
        print(f"  [INFO] {len(failed_models)} models failed:")
        for r in failed_models:
            if "rate-limited" in r["error"].lower():
                print(f"    - {r['model']}: Rate limited (try again later)")
            elif "402" in r["error"]:
                print(f"    - {r['model']}: Needs credits (should have :free suffix)")
            elif "400" in r["error"] or "404" in r["error"]:
                print(f"    - {r['model']}: Invalid model ID")
            else:
                print(f"    - {r['model']}: {r['error'][:60]}...")
    else:
        print("  [OK] No issues found! All free models working.")
    
    print("\n[COMPLETE] Test complete!")

if __name__ == "__main__":
    main()
