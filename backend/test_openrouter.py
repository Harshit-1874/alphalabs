"""
Quick test script to verify OpenRouter API integration.
Tests with a free model (google/gemini-flash-1.5-8b).
"""
import asyncio
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

# Load environment variables
load_dotenv()

async def test_openrouter():
    """Test OpenRouter API with a free model"""
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not found in .env file")
        return
    
    print(f"✓ API Key found: {api_key[:20]}...")
    print("\n" + "="*60)
    print("Testing OpenRouter API")
    print("Model: deepseek/deepseek-chat (free)")
    print("="*60 + "\n")
    
    # Initialize client
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost:3000"),
            "X-Title": os.getenv("OPENROUTER_X_TITLE", "AlphaLabs")
        }
    )
    
    try:
        print("📡 Making request to OpenRouter...")
        
        # Make a simple test request with timeout
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model="deepseek/deepseek-chat",  # Free model
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful AI assistant for a trading platform."
                    },
                    {
                        "role": "user",
                        "content": "Say hello and confirm you're working. Keep it brief."
                    }
                ],
                temperature=0.7,
                max_tokens=100
            ),
            timeout=30.0
        )
        
        # Extract response
        message = response.choices[0].message.content
        
        print("✅ Success! Response received:\n")
        print("-" * 60)
        print(message)
        print("-" * 60)
        print(f"\nModel used: {response.model}")
        print(f"Tokens used: {response.usage.total_tokens if response.usage else 'N/A'}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print(f"\nError type: {type(e).__name__}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_openrouter())
