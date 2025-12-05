"""
AI Council Trader Service for Collaborative Trading Decisions.

Purpose:
    Extends the standard AITrader to use multiple LLMs in a 3-stage deliberation
    process for more robust trading decisions.

Usage:
    from services.ai_council_trader import AICouncilTrader
    
    trader = AICouncilTrader(
        api_key="sk-...",
        council_models=["anthropic/claude-3.5-sonnet", "openai/gpt-4o"],
        chairman_model="google/gemini-2.0-flash-001",
        strategy_prompt="Trade based on RSI...",
        mode="monk"
    )
    
    decision = await trader.get_decision(candle, indicators, position, equity)
"""

import json
import logging
from typing import Optional, Dict, Any, List

from services.ai_trader import AITrader, AIDecision, Candle
from services.trading.position_manager import Position
from services.llm_council import run_trading_council
from services.llm_council.config import CouncilConfig
from config import settings

logger = logging.getLogger(__name__)


class AICouncilTrader(AITrader):
    """
    AI Council Trader that uses multiple LLMs for collaborative trading decisions.
    
    Extends AITrader with council deliberation:
    1. Stage 1: Multiple models independently analyze market and provide decisions
    2. Stage 2: Models rank each other's decisions
    3. Stage 3: Chairman synthesizes final decision
    
    The get_decision() method returns an AIDecision object (same as AITrader)
    plus council deliberation metadata for frontend visualization.
    """
    
    def __init__(
        self,
        api_key: str,
        council_models: List[str],
        chairman_model: str,
        strategy_prompt: str,
        mode: str,
        model_timeout: float = 30.0,
        total_timeout: float = 60.0
    ):
        """
        Initialize AI Council Trader.
        
        Args:
            api_key: OpenRouter API key
            council_models: List of model identifiers for council members
            chairman_model: Model identifier for chairman/synthesizer
            strategy_prompt: Trading strategy instructions
            mode: Agent mode - "monk" or "omni"
            model_timeout: Timeout per model request (seconds)
            total_timeout: Total timeout for entire council process (seconds)
        """
        # Initialize parent AITrader with chairman model
        # (for compatibility with existing code that expects self.model)
        super().__init__(
            api_key=api_key,
            model=chairman_model,
            strategy_prompt=strategy_prompt,
            mode=mode
        )
        
        # Council configuration
        self.council_config = CouncilConfig(
            council_models=council_models,
            chairman_model=chairman_model,
            api_key=api_key,
            model_timeout=model_timeout,
            total_timeout=total_timeout
        )
        
        # Store last deliberation metadata for frontend
        self.last_deliberation: Optional[Dict[str, Any]] = None
        
        logger.info(
            f"AI Council Trader initialized with {len(council_models)} models",
            extra={
                "council_models": council_models,
                "chairman_model": chairman_model,
                "mode": mode
            }
        )
    
    async def initialize(self) -> None:
        """
        Initialize model metadata for chairman model.
        
        Note: We don't initialize all council models individually since
        they're queried through the council service.
        """
        await super().initialize()
    
    async def get_decision(
        self,
        candle: Candle,
        indicators: Dict[str, float],
        position_state: Optional[Position],
        equity: float,
        recent_candles: Optional[List[Dict[str, Any]]] = None,
        recent_indicators: Optional[List[Dict[str, Any]]] = None,
        decision_context: Optional[Dict[str, Any]] = None,
    ) -> AIDecision:
        """
        Get trading decision from AI council with full 3-stage deliberation.
        
        Runs the council process and returns a standard AIDecision object
        compatible with existing trading engine code.
        
        Args:
            candle: Current candle data
            indicators: Dictionary of calculated indicator values
            position_state: Current open position (if any)
            equity: Current account equity
            recent_candles: Recent candle history
            recent_indicators: Recent indicator history
            decision_context: Additional context (mode, interval, etc.)
            
        Returns:
            AIDecision object with action, reasoning, and order parameters.
            Includes council deliberation metadata in decision_context.
        """
        try:
            # Build the trading prompt using parent class method
            trading_prompt = self._build_prompt(
                candle,
                indicators,
                position_state,
                equity,
                recent_candles=recent_candles,
                recent_indicators=recent_indicators,
                decision_context=decision_context,
            )
            
            logger.info("Starting council deliberation for trading decision")
            
            # Run the 3-stage council process
            final_decision_text, deliberation = await run_trading_council(
                self.council_config,
                trading_prompt
            )
            
            # Store deliberation for frontend access
            self.last_deliberation = deliberation
            
            logger.info(
                f"Council deliberation complete: "
                f"Stage1={len(deliberation.get('stage1', []))} responses, "
                f"Stage2={len(deliberation.get('stage2', []))} rankings"
            )
            
            # Parse the chairman's final decision
            decision = self._parse_response(final_decision_text)
            
            # Add council metadata to decision context
            if decision_context is None:
                decision_context = {}
            
            decision_context['council_deliberation'] = deliberation
            decision.decision_context = decision_context
            
            logger.info(
                f"Council decision: {decision.action}",
                extra={
                    "action": decision.action,
                    "size_percentage": decision.size_percentage,
                    "leverage": decision.leverage,
                    "num_council_members": len(self.council_config.council_models)
                }
            )
            
            return decision
            
        except Exception as e:
            logger.error(
                f"Error in council deliberation: {str(e)}",
                extra={"error": str(e)}
            )
            
            # Fallback to HOLD decision
            return AIDecision(
                action="HOLD",
                reasoning=f"Council deliberation failed: {str(e)}",
                size_percentage=0.0,
                leverage=1,
                decision_context={
                    "council_error": str(e),
                    "council_deliberation": {
                        "stage1": [],
                        "stage2": [],
                        "stage3": {"model": "error", "response": ""},
                        "aggregate_rankings": []
                    }
                }
            )
    
    def get_last_deliberation(self) -> Optional[Dict[str, Any]]:
        """
        Get the most recent council deliberation metadata.
        
        Returns:
            Dictionary with stage1, stage2, stage3 results and aggregate rankings,
            or None if no deliberation has been performed yet.
        """
        return self.last_deliberation

