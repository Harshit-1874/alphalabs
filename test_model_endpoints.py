#!/usr/bin/env python3
"""
Test script to verify OpenRouter model endpoints API.
Tests different model ID formats to see which ones work.
"""
import os
import sys
from pathlib import Path
import requests
from dotenv import load_dotenv

# Load environment variables from backend/.env
backend_path = Path(__file__).parent / "backend"
env_path = backend_path / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try root .env
    load_dotenv()

# Use provided API key or try environment
API_KEY = "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"
if not API_KEY:
    API_KEY = os.getenv("OPENROUTER_API_KEY")
    if not API_KEY:
        print("[ERROR] OPENROUTER_API_KEY not found in environment")
        sys.exit(1)

BASE_URL = "https://openrouter.ai/api/v1"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "HTTP-Referer": "http://localhost:3000",
    "X-Title": "AlphaLab"
}

# Test models
TEST_MODELS = [
    "amazon/nova-2-lite-v1:free",
    "amazon/nova-2-lite-v1",
    "anthropic/claude-3.5-sonnet",
    "openai/gpt-4o",
    "google/gemma-3n-e2b-it:free",
]

def test_endpoints_endpoint(model_id: str):
    """Test the /models/{model_id}/endpoints endpoint"""
    # URL encode the model ID
    encoded_id = model_id.replace("/", "%2F").replace(":", "%3A")
    url = f"{BASE_URL}/models/{encoded_id}/endpoints"
    
    print(f"\n[TEST] Testing endpoints endpoint: {model_id}")
    print(f"   URL: {url}")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   [SUCCESS]")
            print(f"   Model ID: {data.get('id', 'N/A')}")
            print(f"   Model Name: {data.get('name', 'N/A')}")
            
            # Check architecture
            arch = data.get("architecture", {})
            if arch:
                context_length = arch.get("context_length")
                if context_length:
                    print(f"   Context Length: {context_length}")
            
            # Check endpoints
            endpoints = data.get("endpoints", [])
            if endpoints:
                print(f"   Endpoints: {len(endpoints)} found")
                first_endpoint = endpoints[0]
                if "context_length" in first_endpoint:
                    print(f"   First endpoint context_length: {first_endpoint['context_length']}")
        else:
            print(f"   [FAILED]: {response.text[:200]}")
            
    except Exception as e:
        print(f"   [ERROR]: {str(e)}")

def test_filter_models_list(model_id: str):
    """Test filtering /models list for a specific model"""
    print(f"\n[TEST] Testing filter from /models list: {model_id}")
    
    try:
        response = requests.get(f"{BASE_URL}/models", headers=HEADERS, timeout=10)
        if response.status_code != 200:
            print(f"   [FAILED] Could not fetch models list: {response.status_code}")
            return
        
        data = response.json()
        models = data.get("data", [])
        
        # Find the model
        model = next((m for m in models if m.get("id") == model_id), None)
        
        if model:
            print(f"   [SUCCESS] Found model in /models list")
            print(f"   Model ID: {model.get('id', 'N/A')}")
            print(f"   Model Name: {model.get('name', 'N/A')}")
            
            # Check context_length
            context_length = model.get("context_length")
            if context_length:
                print(f"   Context Length: {context_length}")
            
            # Check capabilities
            capabilities = model.get("capabilities", {})
            if capabilities:
                print(f"   Capabilities: {capabilities}")
                supports_structured = capabilities.get("function_calling", False) or capabilities.get("structured_outputs", False)
                print(f"   Supports Structured Outputs: {supports_structured}")
        else:
            print(f"   [NOT FOUND] Model not in /models list")
            
    except Exception as e:
        print(f"   [ERROR]: {str(e)}")

def test_models_list():
    """Test the /models endpoint to see what models are available"""
    print("\n" + "="*70)
    print("Testing /models endpoint (all models list)")
    print("="*70)
    
    url = f"{BASE_URL}/models"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            models = data.get("data", [])
            print(f"[SUCCESS] Found {len(models)} total models")
            
            # Search for nova models
            nova_models = [m for m in models if "nova" in m.get("id", "").lower()]
            print(f"\n[NOVA MODELS] Found: {len(nova_models)}")
            for model in nova_models[:5]:  # Show first 5
                print(f"   - {model.get('id')}")
            
            # Check if our test model exists
            test_model_ids = [m.get("id") for m in models]
            for test_model in TEST_MODELS:
                if test_model in test_model_ids:
                    print(f"\n[FOUND] '{test_model}' found in models list")
                else:
                    print(f"\n[NOT FOUND] '{test_model}' NOT found in models list")
        else:
            print(f"[FAILED]: {response.text[:200]}")
            
    except Exception as e:
        print(f"[ERROR]: {str(e)}")

if __name__ == "__main__":
    print("="*70)
    print("OpenRouter Model Endpoints API Test")
    print("="*70)
    
    # First, check what models are available
    test_models_list()
    
    # Then test the endpoints endpoint for each model
    print("\n" + "="*70)
    print("Testing /models/{model_id}/endpoints endpoint")
    print("="*70)
    
    for model_id in TEST_MODELS:
        test_endpoints_endpoint(model_id)
    
    # Also test filtering from /models list (this should work)
    print("\n" + "="*70)
    print("Testing filtering from /models list (should work)")
    print("="*70)
    
    for model_id in TEST_MODELS:
        test_filter_models_list(model_id)
    
    print("\n" + "="*70)
    print("Test Complete")
    print("="*70)

