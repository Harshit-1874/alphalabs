#!/bin/bash
# Bash cURL command to test OpenRouter API

# Check if OPENROUTER_API_KEY is set
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "❌ ERROR: OPENROUTER_API_KEY environment variable is not set"
    echo "ℹ️  INFO: Please set OPENROUTER_API_KEY environment variable or add it to backend/.env"
    echo ""
    echo "To set it temporarily in bash:"
    echo '  export OPENROUTER_API_KEY="your-api-key-here"'
    exit 1
fi

curl -X POST https://openrouter.ai/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -d '{
    "model": "amazon/nova-2-lite-v1:free",
    "messages": [
      {
        "role": "user",
        "content": "Hello! Can you tell me a short joke?"
      }
    ]
  }'

