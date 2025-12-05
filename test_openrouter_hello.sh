#!/bin/bash

API_KEY="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"

curl https://openrouter.ai/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "openai/gpt-3.5-turbo",
    "messages": [
      {
        "role": "user",
        "content": "Hello! Say hi back in one sentence."
      }
    ]
  }'

