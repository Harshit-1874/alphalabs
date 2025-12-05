# AlphaLabs AI Models - Final Configuration
**Date:** December 5, 2025  
**Status:** ✅ Production Ready

---

## Summary

**Total Models:** 42  
**Free Models:** 18 (consistently working)  
**Paid Models:** 24 (require OpenRouter credits)

---

## Free Models (18 total)

All these models work without credits. They have been tested and verified:

### 🏆 Premium Free Models (Large Context/Parameters)
1. **`nousresearch/hermes-3-llama-3.1-405b:free`** - 405B params, 131K context
   - Best for: Reasoning, roleplay, agent coordination

2. **`meta-llama/llama-3.3-70b-instruct:free`** - 70B params, 131K context  
   - Best for: Multilingual assistants, structured outputs

3. **`qwen/qwen3-coder:free`** - 480B MoE (35B active), 262K context
   - Best for: Code generation, tool orchestration

### 💻 Coding Specialists
4. **`kwaipilot/kat-coder-pro:free`** - 256K context
   - Best for: Software development, debugging

5. **`tngtech/deepseek-r1t2-chimera:free`** - 164K context
   - Best for: Complex reasoning, code analysis

6. **`tngtech/deepseek-r1t-chimera:free`** - 164K context
   - Best for: Reasoning tasks, problem solving

### 🎨 Multimodal Models
7. **`amazon/nova-2-lite-v1:free`** - 1M context, vision+video
   - Best for: Document/video intelligence

8. **`nvidia/nemotron-nano-12b-v2-vl:free`** - 128K context, multimodal
   - Best for: Video understanding, OCR, charts

9. **`google/gemma-3-27b-it:free`** - 131K context, vision+multilingual
   - Best for: Vision-language tasks

### ⚡ Fast & Efficient
10. **`mistralai/mistral-small-3.1-24b-instruct:free`** - 24B params, 128K context, multimodal
    - Best for: Conversational agents, function calling

11. **`mistralai/mistral-7b-instruct:free`** - 7.3B params, 33K context
    - Best for: General assistants, chat

12. **`openai/gpt-oss-20b:free`** - 21B MoE (3.6B active), 131K context
    - Best for: Tool use, structured outputs

### 🔬 Google Gemma Family
13. **`google/gemma-3-4b-it:free`** - 33K context, multilingual
14. **`google/gemma-3-12b-it:free`** - 33K context, multilingual
15. **`google/gemma-3n-e2b-it:free`** - 8K context, on-device
16. **`google/gemma-3n-e4b-it:free`** - 8K context, multimodal on-device

### 🤖 NVIDIA Reasoning
17. **`nvidia/nemotron-nano-9b-v2:free`** - 128K context
    - Best for: Reasoning traces, structured Q&A

### 🔹 Trinity MoE
18. **`arcee-ai/trinity-mini:free`** - 26B MoE (3B active), 131K context
    - Best for: Long-context agents, multi-step workflows

---

## Paid Models (24 total)

Premium models requiring OpenRouter credits:

### 🏅 Top Tier (Flagship Models)
- **`anthropic/claude-opus-4.5`** - $5/M in, $25/M out
- **`openai/gpt-5.1`** - $1.25/M in, $10/M out, 400K tokens
- **`google/gemini-3-pro-preview`** - $2/M in, $12/M out, 1M tokens
- **`anthropic/claude-sonnet-4.5`** - $3/M in, $15/M out, 1M tokens

### 🧠 Reasoning Specialists
- **`openai/o3`** - $2/M in, $8/M out
- **`openai/o3-deep-research`** - $10/M in, $40/M out (premium research)
- **`deepseek/deepseek-r1`** - $0.30/M in, $1.20/M out
- **`deepseek/deepseek-r1-0528`** - $0.20/M in, $4.50/M out

### 🚀 Google Gemini Production
- **`google/gemini-2.5-pro`** - $1.25/M in, $10/M out, 1M tokens
- **`google/gemini-2.5-flash`** - $0.30/M in, $2.50/M out, 1M tokens

### 🧪 Experimental/Specialized
- **`deepseek/deepseek-v3.2-exp`** - $0.21/M in, $0.32/M out
- **`deepseek/deepseek-v3.2-speciale`** - $0.27/M in, $0.41/M out
- **`deepseek/deepseek-v3.1-terminus`** - $0.21/M in, $0.79/M out

### 📊 Qwen Family (Premium)
- **`qwen/qwen3-max`** - $1.20/M in, $6/M out, 256K tokens
- **`qwen/qwen3-next-80b-a3b-thinking`** - $0.12/M in, $1.20/M out
- **`qwen/qwen3-235b-a22b-thinking-2507`** - $0.11/M in, $0.60/M out, 262K tokens

### 🦙 Meta Llama
- **`meta-llama/llama-4-maverick`** - $0.136/M in, $0.68/M out, 1M tokens
- **`meta-llama/llama-3.3-70b-instruct`** (paid version)

### 🔧 Other Premium
- **`z-ai/glm-4.6`** - $0.40/M in, $1.75/M out
- **`tngtech/deepseek-r1t2-chimera`** (paid version)
- **`openai/gpt-5-chat`** - $1.25/M in, $10/M out, 128K tokens
- **`mistralai/mistral-7b-instruct-v0.3`** (paid version)
- **`google/gemma-3-27b-it`** (paid version)
- **`nvidia/nemotron-nano-9b-v2`** (paid version)

---

## Rate Limits

**Free Tier Limits (OpenRouter):**
- 50 requests/day
- 20 requests/minute

**Solutions if you hit limits:**
- Wait for daily reset
- Users can add their own API keys
- Implement exponential backoff retry logic

---

## Removed Models

The following models were removed from the original list:

### Invalid Models (HTTP 404/400):
- ❌ `moonshotai/kimi-k2:free` - Model doesn't exist
- ❌ `qwen/qwen3-4b:free` - Invalid parameters

### Rate-Limited Models (too unreliable):
- ❌ `allenai/olmo-3-32b-think:free`
- ❌ `meta-llama/llama-3.2-3b-instruct:free`
- ❌ `z-ai/glm-4.5-air:free`
- ❌ `tngtech/tng-r1t-chimera:free`
- ❌ `meituan/longcat-flash-chat:free`
- ❌ `qwen/qwen3-235b-a22b:free`
- ❌ `google/gemini-2.0-flash-exp:free`
- ❌ `alibaba/tongyi-deepresearch-30b-a3b:free`
- ❌ `cognitivecomputations/dolphin-mistral-24b-venice-edition:free`

---

## Recommendations

### For Free Tier Users:
Use these top models:
- **Best Overall:** `nousresearch/hermes-3-llama-3.1-405b:free`
- **Best Coding:** `qwen/qwen3-coder:free`, `kwaipilot/kat-coder-pro:free`
- **Best Balanced:** `mistralai/mistral-small-3.1-24b-instruct:free`
- **Best Multimodal:** `amazon/nova-2-lite-v1:free` (1M context!)

### For Paid Users:
- **Best Premium:** `anthropic/claude-opus-4.5`
- **Best Value:** `meta-llama/llama-4-maverick` ($0.136/M in)
- **Best Research:** `openai/o3-deep-research`

---

## Files Updated

1. ✅ `backend/api/models.py` - 42 models (18 free + 24 paid)
2. ✅ `backend/tests/test_all_openrouter_models.py` - Updated test script
3. ✅ `frontend/hooks/use-models.ts` - TypeScript interfaces with `isFree` field

---

**Platform is production-ready with 42 high-quality models!** 🎉
