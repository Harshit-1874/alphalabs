"""
LLM Council Service for collaborative AI decision-making.

This package provides a multi-stage deliberation system where multiple LLMs:
1. Independently analyze trading scenarios
2. Rank each other's decisions
3. Synthesize a final consensus decision

Usage:
    from services.llm_council import run_trading_council
    
    decision, deliberation = await run_trading_council(
        api_key=api_key,
        models=["anthropic/claude-3.5-sonnet", "openai/gpt-4o"],
        chairman_model="google/gemini-2.0-flash-001",
        trading_context=context
    )
"""

from .council import run_trading_council
from .config import CouncilConfig

__all__ = ["run_trading_council", "CouncilConfig"]

