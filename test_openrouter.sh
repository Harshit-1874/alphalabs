#!/bin/bash
# Bash cURL command to test OpenRouter API

curl -X POST https://openrouter.ai/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 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" \
  -d '{
    "model": "amazon/nova-2-lite-v1:free",
    "messages": [
      {
        "role": "user",
        "content": "Hello! Can you tell me a short joke?"
      }
    ]
  }'

