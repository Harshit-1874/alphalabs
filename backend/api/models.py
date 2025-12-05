from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/models", tags=["models"])


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    description: str
    speed: str
    context_window: str
    best_for: str
    capabilities: List[str] = []
    is_multimodal: bool = False
    is_free: bool = False  # True for free tier models, False for paid models
    structured_data: dict = {}  # Raw OpenRouter API data (pricing, architecture, etc.)


# ✅ ALL MODELS - Free and Paid (Updated Dec 2025)
# Free models have :free suffix and is_free=True
# Paid models require OpenRouter credits (users can add their own API keys)
AVAILABLE_MODELS: List[ModelInfo] = [
    # ==========================================
    # FREE TIER MODELS (Verified Working)
    # ==========================================
    ModelInfo(
        id="amazon/nova-2-lite-v1:free",
        name="Amazon Nova 2 Lite (Free)",
        provider="amazon",
        description="Fast, cost-efficient reasoning model with multimodal (text/image/video) understanding.",
        speed="fast",
        context_window="1M tokens",
        best_for="Document/video intelligence, grounded QA, coding, multi-step agent workflows",
        capabilities=["text", "vision", "video"],
        is_multimodal=True,
        is_free=True,
    ),
    ModelInfo(
        id="google/gemma-3n-e2b-it:free",
        name="Gemma 3n 2B (Free)",
        provider="google",
        description="2B effective parameter model (6B arch) tuned for low-resource deployment with 32K context.",
        speed="fast",
        context_window="8K tokens",
        best_for="Low-resource multilingual assistants, reasoning on-device",
        capabilities=["text", "vision"],
        is_multimodal=True,
        is_free=True,
    ),
    ModelInfo(
        id="arcee-ai/trinity-mini:free",
        name="Trinity Mini (Free)",
        provider="arcee-ai",
        description="26B (3B active) sparse MoE optimized for 131K context with robust function calling.",
        speed="fast",
        context_window="131K tokens",
        best_for="Long-context agents, multi-step workflows",
        capabilities=["text", "reasoning", "tool-calling"],
        is_free=True,
    ),
    ModelInfo(
        id="google/gemma-3-4b-it:free",
        name="Gemma 3 4B (Free)",
        provider="google",
        description="Lightweight multimodal model with 128K context and 140+ language support.",
        speed="fast",
        context_window="33K tokens",
        best_for="Multimodal assistants, multilingual tasks",
        capabilities=["text", "vision", "multilingual"],
        is_multimodal=True,
        is_free=True,
    ),
    ModelInfo(
        id="google/gemma-3-12b-it:free",
        name="Gemma 3 12B (Free)",
        provider="google",
        description="Higher capacity Gemma 3 variant with multimodal support.",
        speed="fast",
        context_window="33K tokens",
        best_for="Multimodal analysis, multilingual reasoning, structured outputs",
        capabilities=["text", "vision", "multilingual"],
        is_multimodal=True,
        is_free=True,
    ),
    ModelInfo(
        id="google/gemma-3n-e4b-it:free",
        name="Gemma 3n 4B (Free)",
        provider="google",
        description="On-device optimized multimodal model for low-resource devices with dynamic parameter loading.",
        speed="fast",
        context_window="8K tokens",
        best_for="On-device multimodal apps, speech/image analysis, translation",
        capabilities=["text", "vision", "audio"],
        is_multimodal=True,
        is_free=True,
    ),
    
    # ==========================================
    # NEW FREE MODELS - Added Dec 2025
    # ==========================================
    ModelInfo(
        id="tngtech/deepseek-r1t2-chimera:free",
        name="TNG DeepSeek R1T2 Chimera (Free)",
        provider="tngtech",
        description="Advanced reasoning model with chimera architecture for complex problem solving.",
        speed="medium",
        context_window="164K tokens",
        best_for="Complex reasoning, code analysis, research tasks",
        capabilities=["text", "reasoning", "code"],
        is_free=True,
    ),
    ModelInfo(
        id="kwaipilot/kat-coder-pro:free",
        name="KAT-Coder-Pro V1 (Free)",
        provider="kwaipilot",
        description="Specialized coding model optimized for software development tasks.",
        speed="fast",
        context_window="256K tokens",
        best_for="Code generation, debugging, software engineering",
        capabilities=["text", "code"],
        is_free=True,
    ),
    ModelInfo(
        id="tngtech/deepseek-r1t-chimera:free",
        name="TNG DeepSeek R1T Chimera (Free)",
        provider="tngtech",
        description="Reasoning-focused model with chimera architecture.",
        speed="medium",
        context_window="164K tokens",
        best_for="Reasoning tasks, problem solving, analysis",
        capabilities=["text", "reasoning"],
        is_free=True,
    ),

    ModelInfo(
        id="nvidia/nemotron-nano-12b-v2-vl:free",
        name="NVIDIA Nemotron Nano 12B 2 VL (Free)",
        provider="nvidia",
        description="12B multimodal reasoning model for video/document intelligence.",
        speed="fast",
        context_window="128K tokens",
        best_for="Video understanding, OCR, charts, multimodal comprehension",
        capabilities=["text", "vision", "video"],
        is_multimodal=True,
        is_free=True,
    ),

    ModelInfo(
        id="qwen/qwen3-coder:free",
        name="Qwen3 Coder 480B A35B (Free)",
        provider="qwen",
        description="Agentic coding model optimized for tool use and long-context code reasoning.",
        speed="medium",
        context_window="262K tokens",
        best_for="Code generation, tool orchestration, SWE-bench style tasks",
        capabilities=["text", "code", "tool-calling"],
        is_free=True,
    ),
    ModelInfo(
        id="google/gemma-3-27b-it:free",
        name="Gemma 3 27B (Free)",
        provider="google",
        description="Multimodal Gemma variant supporting 131K context, 140+ languages.",
        speed="fast",
        context_window="131K tokens",
        best_for="Vision-language tasks, multilingual reasoning, function calling",
        capabilities=["text", "vision", "multilingual"],
        is_multimodal=True,
        is_free=True,
    ),
    ModelInfo(
        id="openai/gpt-oss-20b:free",
        name="GPT-OSS-20B (Free)",
        provider="openai",
        description="Apache 2.0 MoE model tuned for low-latency consumer deployment.",
        speed="fast",
        context_window="131K tokens",
        best_for="Reasoning-level configurable assistants, tool use, structured outputs",
        capabilities=["text", "reasoning", "tool-calling"],
        is_free=True,
    ),

    ModelInfo(
        id="meta-llama/llama-3.3-70b-instruct:free",
        name="Llama 3.3 70B Instruct (Free)",
        provider="meta",
        description="Multilingual instruction-tuned 70B model optimized for dialogue.",
        speed="medium",
        context_window="131K tokens",
        best_for="Multilingual assistants, structured outputs, complex reasoning",
        capabilities=["text", "multilingual", "reasoning"],
        is_free=True,
    ),




    ModelInfo(
        id="mistralai/mistral-7b-instruct:free",
        name="Mistral 7B Instruct (Free)",
        provider="mistral",
        description="7.3B parameter instruction-tuned model optimized for speed.",
        speed="fast",
        context_window="33K tokens",
        best_for="General assistants, enterprise chat, long-context Q&A",
        capabilities=["text"],
        is_free=True,
    ),
    ModelInfo(
        id="nvidia/nemotron-nano-9b-v2:free",
        name="NVIDIA Nemotron Nano 9B V2 (Free)",
        provider="nvidia",
        description="9B model for unified reasoning and non-reasoning tasks.",
        speed="fast",
        context_window="128K tokens",
        best_for="Reasoning traces on/off, structured Q&A",
        capabilities=["text", "reasoning"],
        is_free=True,
    ),
    ModelInfo(
        id="nousresearch/hermes-3-llama-3.1-405b:free",
        name="Nous Hermes 3 405B Instruct (Free)",
        provider="nous",
        description="405B finetune emphasizing alignment and agentic abilities.",
        speed="medium",
        context_window="131K tokens",
        best_for="Reasoning, roleplay, agent coordination, structured outputs",
        capabilities=["text", "reasoning", "tool-calling"],
        is_free=True,
    ),
    ModelInfo(
        id="mistralai/mistral-small-3.1-24b-instruct:free",
        name="Mistral Small 3.1 24B Instruct (Free)",
        provider="mistral",
        description="24B model with advanced multimodal capabilities and multilingual support.",
        speed="fast",
        context_window="128K tokens",
        best_for="Conversational agents, function calling, long-document comprehension",
        capabilities=["text", "vision", "code", "multilingual"],
        is_multimodal=True,
        is_free=True,
    ),
    
    # ==========================================
    # PAID MODELS (Require OpenRouter Credits)
    # ==========================================
    # Note: Some models below may also have free versions (with :free suffix)
    # These are the paid versions for users who want guaranteed availability
    
    ModelInfo(
        id="nvidia/nemotron-nano-9b-v2",
        name="NVIDIA Nemotron Nano 9B v2 (Paid)",
        provider="nvidia",
        description="Paid version - 9B model trained from scratch for unified reasoning and non-reasoning tasks.",
        speed="fast",
        context_window="128K tokens",
        best_for="Reasoning traces on/off, structured Q&A, guaranteed availability",
        capabilities=["text", "reasoning"],
        is_free=False,
    ),
    ModelInfo(
        id="google/gemma-3-27b-it",
        name="Gemma 3 27B (Paid)",
        provider="google",
        description="Paid version - Multimodal Gemma 3 flagship model with 128K context and function calling.",
        speed="fast",
        context_window="131K tokens",
        best_for="Vision-language, function calling, multilingual assistants, guaranteed availability",
        capabilities=["text", "vision", "multilingual"],
        is_multimodal=True,
        is_free=False,
    ),
    ModelInfo(
        id="mistralai/mistral-7b-instruct-v0.3",
        name="Mistral 7B Instruct v0.3 (Paid)",
        provider="mistral",
        description="Paid version - 7.3B parameter instruction-tuned model optimized for speed and long context.",
        speed="fast",
        context_window="33K tokens",
        best_for="General assistants, enterprise chat, long-context Q&A, guaranteed availability",
        capabilities=["text"],
        is_free=False,
    ),
    ModelInfo(
        id="meta-llama/llama-3.3-70b-instruct",
        name="Llama 3.3 70B Instruct (Paid)",
        provider="meta",
        description="Paid version - Multilingual instruction-tuned 70B model optimized for dialogue and structured outputs.",
        speed="medium",
        context_window="131K tokens",
        best_for="Multilingual assistants (EN/DE/FR/IT/PT/HI/ES/TH), structured outputs, guaranteed availability",
        capabilities=["text", "multilingual"],
        is_free=False,
    ),
    
    # ==========================================
    # PREMIUM PAID MODELS - High-tier models
    # ==========================================
    ModelInfo(
        id="anthropic/claude-opus-4.5",
        name="Claude Opus 4.5",
        provider="anthropic",
        description="Anthropic's most powerful model ($5/M input, $25/M output). Superior reasoning, analysis, and creative tasks.",
        speed="medium",
        context_window="200K tokens",
        best_for="Complex reasoning, research, long-form content, advanced analysis",
        capabilities=["text", "reasoning", "analysis"],
        is_free=False,
    ),
    ModelInfo(
        id="openai/gpt-5.1",
        name="GPT-5.1",
        provider="openai",
        description="OpenAI's next-generation model ($1.25/M input, $10/M output). Advanced reasoning and multimodal capabilities.",
        speed="fast",
        context_window="400K tokens",
        best_for="Advanced reasoning, coding, research, multimodal tasks",
        capabilities=["text", "reasoning", "code", "vision"],
        is_multimodal=True,
        is_free=False,
    ),
    ModelInfo(
        id="google/gemini-3-pro-preview",
        name="Gemini 3 Pro Preview",
        provider="google",
        description="Google's experimental flagship model ($2/M input, $12/M output) with 1M+ context window.",
        speed="medium",
        context_window="1M tokens",
        best_for="Ultra-long context, multimodal reasoning, experimental features",
        capabilities=["text", "vision", "reasoning", "multilingual"],
        is_multimodal=True,
        is_free=False,
    ),
    ModelInfo(
        id="anthropic/claude-sonnet-4.5",
        name="Claude Sonnet 4.5",
        provider="anthropic",
        description="Balanced Claude model ($3/M input, $15/M output) with 1M context. Great reasoning with efficiency.",
        speed="fast",
        context_window="1M tokens",
        best_for="Balanced reasoning, long documents, coding, general tasks",
        capabilities=["text", "reasoning", "code"],
        is_free=False,
    ),
    ModelInfo(
        id="openai/gpt-5-chat",
        name="GPT-5 Chat",
        provider="openai",
        description="Optimized GPT-5 for conversations ($1.25/M input, $10/M output). Enhanced dialogue capabilities.",
        speed="fast",
        context_window="128K tokens",
        best_for="Conversational AI, chat applications, interactive assistants",
        capabilities=["text", "reasoning", "dialogue"],
        is_free=False,
    ),
    ModelInfo(
        id="deepseek/deepseek-r1",
        name="DeepSeek R1",
        provider="deepseek",
        description="DeepSeek's reasoning model ($0.30/M input, $1.20/M output). Cost-effective advanced reasoning.",
        speed="medium",
        context_window="164K tokens",
        best_for="Reasoning, problem-solving, research at lower cost",
        capabilities=["text", "reasoning"],
        is_free=False,
    ),
    ModelInfo(
        id="deepseek/deepseek-r1-0528",
        name="DeepSeek R1 0528",
        provider="deepseek",
        description="Updated DeepSeek R1 variant ($0.20/M input, $4.50/M output). Enhanced reasoning capabilities.",
        speed="medium",
        context_window="164K tokens",
        best_for="Advanced reasoning, research, analytical tasks",
        capabilities=["text", "reasoning"],
        is_free=False,
    ),
    ModelInfo(
        id="tngtech/deepseek-r1t2-chimera",
        name="TNG DeepSeek R1T2 Chimera",
        provider="tngtech",
        description="Paid version ($0.30/M input, $1.20/M output). Advanced chimera architecture for complex reasoning.",
        speed="medium",
        context_window="164K tokens",
        best_for="Complex reasoning, code analysis, research tasks, guaranteed availability",
        capabilities=["text", "reasoning", "code"],
        is_free=False,
    ),
    ModelInfo(
        id="qwen/qwen3-next-80b-a3b-thinking",
        name="Qwen3 Next 80B A3B Thinking",
        provider="qwen",
        description="Qwen's thinking-optimized model ($0.12/M input, $1.20/M output). Cost-effective reasoning.",
        speed="fast",
        context_window="131K tokens",
        best_for="Reasoning tasks, problem-solving, analytical work",
        capabilities=["text", "reasoning", "thinking"],
        is_free=False,
    ),
    ModelInfo(
        id="qwen/qwen3-235b-a22b-thinking-2507",
        name="Qwen3 235B A22B Thinking 2507",
        provider="qwen",
        description="Large-scale Qwen model ($0.11/M input, $0.60/M output). Premium reasoning at competitive pricing.",
        speed="fast",
        context_window="262K tokens",
        best_for="Large-scale reasoning, research, complex analysis",
        capabilities=["text", "reasoning", "tool-calling"],
        is_free=False,
    ),
    ModelInfo(
        id="google/gemini-2.5-pro",
        name="Gemini 2.5 Pro",
        provider="google",
        description="Google's production-ready model ($1.25/M input, $10/M output) with 1M+ context.",
        speed="fast",
        context_window="1M tokens",
        best_for="Production multimodal apps, long-context tasks, enterprise use",
        capabilities=["text", "vision", "reasoning", "multilingual"],
        is_multimodal=True,
        is_free=False,
    ),
    ModelInfo(
        id="openai/o3",
        name="OpenAI o3",
        provider="openai",
        description="OpenAI's reasoning-focused model ($2/M input, $8/M output). Optimized for complex problem-solving.",
        speed="medium",
        context_window="200K tokens",
        best_for="Complex reasoning, mathematical problems, logic puzzles",
        capabilities=["text", "reasoning", "mathematics"],
        is_free=False,
    ),
    ModelInfo(
        id="openai/o3-deep-research",
        name="OpenAI o3 Deep Research",
        provider="openai",
        description="Premium research model ($10/M input, $40/M output). Optimized for deep analytical work.",
        speed="slow",
        context_window="200K tokens",
        best_for="Academic research, deep analysis, comprehensive investigations",
        capabilities=["text", "reasoning", "research"],
        is_free=False,
    ),
    ModelInfo(
        id="deepseek/deepseek-v3.2-exp",
        name="DeepSeek V3.2 Exp",
        provider="deepseek",
        description="Experimental DeepSeek variant ($0.21/M input, $0.32/M output). Cutting-edge features.",
        speed="fast",
        context_window="164K tokens",
        best_for="Experimental features, cost-effective reasoning",
        capabilities=["text", "reasoning"],
        is_free=False,
    ),
    ModelInfo(
        id="deepseek/deepseek-v3.2-speciale",
        name="DeepSeek V3.2 Speciale",
        provider="deepseek",
        description="Specialized DeepSeek model ($0.27/M input, $0.41/M output). Enhanced for specific tasks.",
        speed="fast",
        context_window="164K tokens",
        best_for="Specialized reasoning, tailored applications",
        capabilities=["text", "reasoning"],
        is_free=False,
    ),
    ModelInfo(
        id="deepseek/deepseek-v3.1-terminus",
        name="DeepSeek V3.1 Terminus",
        provider="deepseek",
        description="DeepSeek's optimized variant ($0.21/M input, $0.79/M output). Balanced performance.",
        speed="fast",
        context_window="164K tokens",
        best_for="General reasoning, cost-effective solutions",
        capabilities=["text", "reasoning"],
        is_free=False,
    ),
    ModelInfo(
        id="google/gemini-2.5-flash",
        name="Gemini 2.5 Flash",
        provider="google",
        description="Fast Gemini variant ($0.30/M input, $2.50/M output) with 1M+ context. Speed optimized.",
        speed="fast",
        context_window="1M tokens",
        best_for="Fast multimodal tasks, real-time applications, high-throughput",
        capabilities=["text", "vision", "multilingual"],
        is_multimodal=True,
        is_free=False,
    ),
    ModelInfo(
        id="z-ai/glm-4.6",
        name="Z.AI GLM 4.6",
        provider="z-ai",
        description="Z.AI's enhanced model ($0.40/M input, $1.75/M output). Improved capabilities over free version.",
        speed="fast",
        context_window="203K tokens",
        best_for="General tasks, guaranteed performance",
        capabilities=["text", "reasoning"],
        is_free=False,
    ),
    ModelInfo(
        id="meta-llama/llama-4-maverick",
        name="Llama 4 Maverick",
        provider="meta",
        description="Meta's next-gen Llama ($0.136/M input, $0.68/M output) with 1M+ context. Excellent value.",
        speed="fast",
        context_window="1M tokens",
        best_for="Cost-effective reasoning, long-context tasks, multilingual",
        capabilities=["text", "reasoning", "multilingual"],
        is_free=False,
    ),
    ModelInfo(
        id="qwen/qwen3-max",
        name="Qwen3 Max",
        provider="qwen",
        description="Qwen's flagship model ($1.20/M input, $6/M output). Maximum capabilities.",
        speed="medium",
        context_window="256K tokens",
        best_for="Advanced reasoning, complex tasks, tool-calling workflows",
        capabilities=["text", "reasoning", "tool-calling", "code"],
        is_free=False,
    ),
]


@router.get("", response_model=List[ModelInfo])
async def list_models() -> List[ModelInfo]:
    """
    Return the curated list of AI models supported by the platform.
    
    Models are marked with is_free=True for free tier (no credits required)
    or is_free=False for paid models (require OpenRouter credits or user's own API key).
    
    Free models have :free suffix in their ID.
    Paid models require credits but offer more capabilities.
    """
    return AVAILABLE_MODELS
