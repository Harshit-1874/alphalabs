#!/usr/bin/env python3
"""
Fetch model metadata from OpenRouter API and validate our models.
"""
import requests
import json
from typing import Dict, List, Any

API_KEY = "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"

# Our models from models.py
OUR_FREE_MODELS = [
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

def fetch_all_models() -> List[Dict[str, Any]]:
    """Fetch all models from OpenRouter API."""
    url = "https://openrouter.ai/api/v1/models"
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])
    except Exception as e:
        print(f"Error fetching models: {e}")
        return []

def find_model_in_openrouter(model_id: str, all_models: List[Dict]) -> Dict[str, Any]:
    """Find a specific model in the OpenRouter models list."""
    for model in all_models:
        if model.get("id") == model_id:
            return model
    return None

def main():
    print("=" * 80)
    print("Fetching all models from OpenRouter API...")
    print("=" * 80)
    
    all_models = fetch_all_models()
    
    if not all_models:
        print("Failed to fetch models!")
        return
    
    print(f"\nTotal models available on OpenRouter: {len(all_models)}")
    
    # Count free models
    free_models = [m for m in all_models if ":free" in m.get("id", "")]
    print(f"Free models available: {len(free_models)}")
    
    print("\n" + "=" * 80)
    print("Checking our models against OpenRouter API...")
    print("=" * 80)
    
    found_count = 0
    not_found_count = 0
    
    for our_model_id in OUR_FREE_MODELS:
        model_data = find_model_in_openrouter(our_model_id, all_models)
        
        if model_data:
            found_count += 1
            print(f"\n✅ FOUND: {our_model_id}")
            print(f"   Name: {model_data.get('name')}")
            print(f"   Context: {model_data.get('context_length')} tokens")
            
            # Pricing
            pricing = model_data.get('pricing', {})
            prompt_price = pricing.get('prompt', 0)
            completion_price = pricing.get('completion', 0)
            
            # Convert to float if string
            if isinstance(prompt_price, str):
                prompt_price = float(prompt_price)
            if isinstance(completion_price, str):
                completion_price = float(completion_price)
            
            print(f"   Pricing: ${prompt_price * 1_000_000:.2f}/M input, ${completion_price * 1_000_000:.2f}/M output")
            
            # Capabilities
            capabilities = model_data.get('capabilities', {})
            caps_list = []
            if capabilities.get('functions'): caps_list.append('functions')
            if capabilities.get('vision'): caps_list.append('vision')
            if capabilities.get('streaming'): caps_list.append('streaming')
            if caps_list:
                print(f"   Capabilities: {', '.join(caps_list)}")
            
            # Architecture
            arch = model_data.get('architecture', {})
            if arch:
                print(f"   Architecture: {json.dumps(arch, indent=6)}")
        else:
            not_found_count += 1
            print(f"\n❌ NOT FOUND: {our_model_id}")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Our models checked: {len(OUR_FREE_MODELS)}")
    print(f"Found in OpenRouter: {found_count}")
    print(f"Not found: {not_found_count}")
    
    # Sample model structure
    if all_models:
        print("\n" + "=" * 80)
        print("SAMPLE MODEL STRUCTURE (first free model):")
        print("=" * 80)
        sample = free_models[0] if free_models else all_models[0]
        print(json.dumps(sample, indent=2))
    
    # Save full response to file
    with open("/tmp/openrouter_models.json", "w") as f:
        json.dump({"total": len(all_models), "data": all_models}, f, indent=2)
    print(f"\n✅ Full response saved to: /tmp/openrouter_models.json")

if __name__ == "__main__":
    main()
