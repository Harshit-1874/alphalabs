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


AVAILABLE_MODELS: List[ModelInfo] = [
    ModelInfo(
        id="qwen/qwen3-235b-a22b",
        name="Qwen3 235B A22B",
        provider="qwen",
        description="235B-parameter MoE model (22B active) with switchable thinking modes for reasoning vs. fast conversation.",
        speed="fast",
        context_window="131K tokens",
        best_for="Advanced reasoning, multi-language support, tool-calling workflows",
        capabilities=["text", "reasoning", "tool-calling"],
    ),
    ModelInfo(
        id="qwen/qwen3-coder",
        name="Qwen3 Coder 480B A35B",
        provider="qwen",
        description="Agentic coding model optimized for tool use, function calling, and long-context code reasoning.",
        speed="medium",
        context_window="262K tokens",
        best_for="Code generation, tool orchestration, SWE-bench style tasks",
        capabilities=["text", "code", "tool-calling"],
    ),
    ModelInfo(
        id="qwen/qwen3-4b:free",
        name="Qwen3 4B",
        provider="qwen",
        description="4B dense model with dual thinking/non-thinking modes for reasoning and efficient dialogue generation.",
        speed="fast",
        context_window="41K tokens",
        best_for="Multi-turn chat, instruction following, agent workflows",
        capabilities=["text", "reasoning"],
    ),
    ModelInfo(
        id="openai/gpt-oss-20b",
        name="GPT-OSS-20B",
        provider="openai",
        description="Apache 2.0 MoE model (21B params / 3.6B active) tuned for low-latency consumer deployment.",
        speed="fast",
        context_window="131K tokens",
        best_for="Reasoning-level configurable assistants, tool use, structured outputs",
        capabilities=["text", "reasoning", "tool-calling"],
    ),
    ModelInfo(
        id="arcee-ai/trinity-mini",
        name="Trinity Mini",
        provider="arcee-ai",
        description="26B (3B active) sparse MoE optimized for 131K context with robust function calling.",
        speed="fast",
        context_window="131K tokens",
        best_for="Long-context agents, multi-step workflows",
        capabilities=["text", "reasoning", "tool-calling"],
    ),
    ModelInfo(
        id="amazon/nova-2-lite-v1",
        name="Amazon Nova 2 Lite",
        provider="amazon",
        description="Fast, cost-efficient reasoning model with multimodal (text/image/video) understanding.",
        speed="fast",
        context_window="1M tokens",
        best_for="Document/video intelligence, grounded QA, coding, multi-step agent workflows",
        capabilities=["text", "vision", "video"],
        is_multimodal=True,
    ),
    ModelInfo(
        id="nousresearch/hermes-3-llama-3.1-405b",
        name="Nous Hermes 3 405B",
        provider="nous",
        description="405B finetune emphasizing alignment, agentic abilities, and long-context coherence.",
        speed="medium",
        context_window="131K tokens",
        best_for="Reasoning, roleplay, agent coordination, structured outputs",
        capabilities=["text", "reasoning", "tool-calling"],
    ),
    ModelInfo(
        id="nvidia/nemotron-nano-12b-v2-vl",
        name="NVIDIA Nemotron Nano 2 VL",
        provider="nvidia",
        description="12B multimodal reasoning model for video/document intelligence (Transformer–Mamba).",
        speed="fast",
        context_window="128K tokens",
        best_for="Video understanding, OCR, charts, multimodal comprehension",
        capabilities=["text", "vision", "video"],
        is_multimodal=True,
    ),
    ModelInfo(
        id="nvidia/nemotron-nano-9b-v2",
        name="NVIDIA Nemotron Nano 9B v2",
        provider="nvidia",
        description="9B model trained from scratch for unified reasoning and non-reasoning tasks with controllable traces.",
        speed="fast",
        context_window="128K tokens",
        best_for="Reasoning traces on/off, structured Q&A",
        capabilities=["text", "reasoning"],
    ),
    ModelInfo(
        id="moonshotai/kimi-k2",
        name="Moonshot Kimi K2",
        provider="moonshot",
        description="1T-parameter MoE (32B active) optimized for reasoning, tool use, coding, and long-context tasks.",
        speed="medium",
        context_window="131K tokens",
        best_for="Complex reasoning, tool calling, coding, long-context agents",
        capabilities=["text", "code", "reasoning", "tool-calling"],
    ),
    ModelInfo(
        id="google/gemma-3-27b-it",
        name="Gemma 3 27B",
        provider="google",
        description="Multimodal Gemma variant supporting 128K context, 140+ languages, structured outputs.",
        speed="fast",
        context_window="131K tokens",
        best_for="Vision-language tasks, multilingual reasoning, function calling",
        capabilities=["text", "vision", "multilingual"],
        is_multimodal=True,
    ),
    ModelInfo(
        id="google/gemma-3n-e4b-it",
        name="Gemma 3n 4B",
        provider="google",
        description="On-device optimized multimodal model for low-resource devices with dynamic parameter loading.",
        speed="fast",
        context_window="8K tokens",
        best_for="On-device multimodal apps, speech/image analysis, translation",
        capabilities=["text", "vision", "audio"],
        is_multimodal=True,
    ),
    ModelInfo(
        id="google/gemma-3n-e2b-it:free",
        name="Gemma 3n 2B",
        provider="google",
        description="2B effective parameter model (6B arch) tuned for low-resource deployment with 32K context.",
        speed="fast",
        context_window="8K tokens",
        best_for="Low-resource multilingual assistants, reasoning on-device",
        capabilities=["text", "vision"],
        is_multimodal=True,
    ),
    ModelInfo(
        id="google/gemma-3-4b-it",
        name="Gemma 3 4B",
        provider="google",
        description="Lightweight multimodal model with 128K context and 140+ language support.",
        speed="fast",
        context_window="33K tokens",
        best_for="Multimodal assistants, multilingual tasks",
        capabilities=["text", "vision", "multilingual"],
        is_multimodal=True,
    ),
    ModelInfo(
        id="google/gemma-3-12b-it",
        name="Gemma 3 12B",
        provider="google",
        description="Higher capacity Gemma 3 variant with multimodal support.",
        speed="fast",
        context_window="33K tokens",
        best_for="Multimodal analysis, multilingual reasoning, structured outputs",
        capabilities=["text", "vision", "multilingual"],
        is_multimodal=True,
    ),
    ModelInfo(
        id="google/gemma-3-27b-it",
        name="Gemma 3 27B",
        provider="google",
        description="Multimodal Gemma 3 flagship model with 128K context and function calling.",
        speed="fast",
        context_window="131K tokens",
        best_for="Vision-language, function calling, multilingual assistants",
        capabilities=["text", "vision", "multilingual"],
        is_multimodal=True,
    ),
    ModelInfo(
        id="allenai/olmo-3-32b-think:free",
        name="Olmo 3 32B Think",
        provider="allenai",
        description="32B model purpose-built for deep reasoning, complex logic chains, and advanced instruction following.",
        speed="medium",
        context_window="66K tokens",
        best_for="Reasoning traces, transparent training, advanced conversational logic",
        capabilities=["text", "reasoning"],
    ),
    ModelInfo(
        id="mistralai/mistral-7b-instruct-v0.3",
        name="Mistral 7B Instruct",
        provider="mistral",
        description="7.3B parameter instruction-tuned model optimized for speed and long context.",
        speed="fast",
        context_window="33K tokens",
        best_for="General assistants, enterprise chat, long-context Q&A",
        capabilities=["text"],
    ),
    ModelInfo(
        id="meta-llama/llama-3.3-70b-instruct",
        name="Llama 3.3 70B Instruct",
        provider="meta",
        description="Multilingual instruction-tuned 70B model optimized for dialogue and structured outputs.",
        speed="medium",
        context_window="131K tokens",
        best_for="Multilingual assistants (EN/DE/FR/IT/PT/HI/ES/TH), structured outputs",
        capabilities=["text", "multilingual"],
    ),
]


@router.get("", response_model=List[ModelInfo])
async def list_models() -> List[ModelInfo]:
    """
    Return the curated list of AI models supported by the platform.

    Later this endpoint can fetch live data from OpenRouter, but for now
    it exposes the canonical list so the frontend no longer hardcodes models.
    """
    return AVAILABLE_MODELS

