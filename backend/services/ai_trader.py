"""
AI Trader Service for AlphaLab Trading Engine.

Purpose:
    Interface with OpenRouter API to get trading decisions from AI models.
    Handles prompt building, streaming responses, JSON parsing, and error handling.

Usage:
    from services.ai_trader import AITrader, AIDecision
    
    trader = AITrader(
        api_key="sk-...",
        model="anthropic/claude-3.5-sonnet",
        strategy_prompt="Trade based on RSI...",
        mode="monk"
    )
    
    decision = await trader.get_decision(candle, indicators, position, equity)
"""
import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from openai import AsyncOpenAI

from config import settings
from exceptions import OpenRouterAPIError, TimeoutError as AlphaLabTimeoutError
from utils.retry import retry_with_backoff, CircuitBreaker, with_timeout
from services.trading.position_manager import Position


logger = logging.getLogger(__name__)


@dataclass
class Candle:
    """Represents a single candlestick data point"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class AIDecision:
    """
    Represents a trading decision from the AI model.
    
    Attributes:
        action: Trading action - "LONG", "SHORT", "CLOSE", or "HOLD"
        reasoning: AI's explanation for the decision
        stop_loss_price: Absolute price level for stop loss (optional)
        take_profit_price: Absolute price level for take profit (optional)
        size_percentage: Percentage of capital to use (0.0 to 1.0)
        leverage: Leverage multiplier (1 to 5, default 1)
    """
    action: str
    reasoning: str
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    size_percentage: float = 0.0
    leverage: int = 1


class AITrader:
    """
    AI Trader service for getting trading decisions from OpenRouter API.
    
    Handles:
    - OpenRouter API integration with streaming
    - Prompt building with market context
    - JSON response parsing and validation
    - Retry logic and error handling
    - Circuit breaker for API failures
    """
    
    def __init__(
        self,
        api_key: str,
        model: str,
        strategy_prompt: str,
        mode: str
    ):
        """
        Initialize AI Trader.
        
        Args:
            api_key: OpenRouter API key
            model: Model identifier (e.g., "anthropic/claude-3.5-sonnet")
            strategy_prompt: Trading strategy instructions
            mode: Agent mode - "monk" or "omni"
        """
        self.api_key = api_key
        self.model = model
        self.strategy_prompt = strategy_prompt
        self.mode = mode
        
        # Initialize AsyncOpenAI client with OpenRouter base URL
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": settings.OPENROUTER_HTTP_REFERER,
                "X-Title": settings.OPENROUTER_X_TITLE
            }
        )
        
        # Initialize circuit breaker for API calls
        self.circuit_breaker = CircuitBreaker(
            service_name="openrouter",
            failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            timeout=settings.CIRCUIT_BREAKER_TIMEOUT
        )
        
        logger.info(
            f"AI Trader initialized",
            extra={
                "model": model,
                "mode": mode,
                "strategy_length": len(strategy_prompt)
            }
        )

    async def get_decision(
        self,
        candle: Candle,
        indicators: Dict[str, float],
        position_state: Optional[Position],
        equity: float
    ) -> AIDecision:
        """
        Get trading decision from AI model with retry logic.
        
        Implements exponential backoff retry (up to 3 attempts) and returns
        HOLD decision on failure with error reasoning.
        
        Args:
            candle: Current candle data
            indicators: Dictionary of calculated indicator values
            position_state: Current open position (if any)
            equity: Current account equity
            
        Returns:
            AIDecision object with action, reasoning, and order parameters.
            Returns HOLD decision if all retries fail.
        """
        try:
            # Build prompt with market context
            prompt = self._build_prompt(candle, indicators, position_state, equity)
            
            # Make API request with retry, timeout, and circuit breaker protection
            async def make_request_with_retry():
                async def make_request():
                    return await self._make_api_request(prompt)
                
                # Apply circuit breaker
                async def circuit_protected_request():
                    return await self.circuit_breaker.call(make_request)
                
                # Apply retry with exponential backoff
                return await retry_with_backoff(
                    circuit_protected_request,
                    max_retries=settings.MAX_RETRIES,
                    base_delay=settings.RETRY_BASE_DELAY,
                    max_delay=settings.RETRY_MAX_DELAY,
                    exceptions=(OpenRouterAPIError, AlphaLabTimeoutError),
                    operation_name="ai_decision"
                )
            
            response_text = await make_request_with_retry()
            
            # Parse and validate JSON response
            decision = self._parse_response(response_text)
            
            logger.info(
                f"AI decision received: {decision.action}",
                extra={
                    "action": decision.action,
                    "size_percentage": decision.size_percentage,
                    "leverage": decision.leverage,
                    "has_stop_loss": decision.stop_loss_price is not None,
                    "has_take_profit": decision.take_profit_price is not None
                }
            )
            
            return decision
            
        except Exception as e:
            logger.error(
                f"Error getting AI decision after retries: {str(e)}",
                extra={"error": str(e), "model": self.model}
            )
            # Return HOLD decision on failure with error reasoning
            return AIDecision(
                action="HOLD",
                reasoning=f"Failed to get AI decision after {settings.MAX_RETRIES} attempts: {str(e)}",
                size_percentage=0.0,
                leverage=1
            )
    
    def _build_prompt(
        self,
        candle: Candle,
        indicators: Dict[str, float],
        position_state: Optional[Position],
        equity: float
    ) -> str:
        """
        Build prompt with candle data, indicators, and position state.
        
        Args:
            candle: Current candle data
            indicators: Dictionary of calculated indicator values
            position_state: Current open position (if any)
            equity: Current account equity
            
        Returns:
            Formatted prompt string
        """
        # Format candle data
        candle_data = {
            "timestamp": candle.timestamp.isoformat(),
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume
        }
        
        # Format position state
        position_data = None
        if position_state:
            position_data = {
                "action": position_state.action,
                "entry_price": position_state.entry_price,
                "size": position_state.size,
                "stop_loss": position_state.stop_loss,
                "take_profit": position_state.take_profit,
                "leverage": position_state.leverage,
                "unrealized_pnl": position_state.unrealized_pnl
            }
        
        # Build market context
        market_context = {
            "candle": candle_data,
            "indicators": indicators,
            "position": position_data,
            "equity": equity
        }
        
        # Create user message
        user_message = f"""Current Market State:
{json.dumps(market_context, indent=2)}

Based on the current market state and your trading strategy, make a trading decision.

You must respond with a valid JSON object in the following format:
{{
    "action": "LONG" | "SHORT" | "CLOSE" | "HOLD",
    "reasoning": "Your detailed explanation for this decision",
    "stop_loss_price": <absolute price level for stop loss, optional>,
    "take_profit_price": <absolute price level for take profit, optional>,
    "size_percentage": <percentage of capital to use, 0.0 to 1.0>,
    "leverage": <leverage multiplier, 1 to 5, default 1>
}}

Rules:
- action: Must be one of LONG (buy), SHORT (sell), CLOSE (close position), or HOLD (do nothing)
- reasoning: Explain your decision based on indicators and market conditions
- stop_loss_price: Absolute price level (not percentage). For LONG, should be below entry. For SHORT, should be above entry.
- take_profit_price: Absolute price level (not percentage). For LONG, should be above entry. For SHORT, should be below entry.
- size_percentage: How much of your capital to use (0.0 to 1.0). For example, 0.5 means use 50% of capital.
- leverage: Multiplier for position size (1 to 5). Use 1 for no leverage.
- If you have an open position, you can only CLOSE or HOLD
- If you don't have a position, you can LONG, SHORT, or HOLD
"""
        
        return user_message
    
    async def _make_api_request(self, user_message: str) -> str:
        """
        Make streaming API request to OpenRouter with timeout and retry.
        
        Args:
            user_message: User message with market context
            
        Returns:
            Complete response text from AI
            
        Raises:
            OpenRouterAPIError: If API call fails
            AlphaLabTimeoutError: If request times out
        """
        async def make_request():
            try:
                # Build system message based on mode
                mode_description = "Monk Mode (limited indicators)" if self.mode == "monk" else "Omni Mode (all indicators)"
                system_message = f"""You are an AI trading agent operating in {mode_description}.

Your Strategy:
{self.strategy_prompt}

You must analyze the market data and make trading decisions based on your strategy.
Always respond with valid JSON in the exact format specified."""
                
                # Make streaming request
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_message}
                    ],
                    stream=True,
                    response_format={"type": "json_object"},
                    temperature=0.7,
                    max_tokens=1000
                )
                
                # Collect streaming response
                full_response = ""
                async for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                
                if not full_response:
                    raise OpenRouterAPIError("Empty response from API")
                
                return full_response
                
            except Exception as e:
                logger.error(
                    f"OpenRouter API request failed: {str(e)}",
                    extra={"error": str(e), "model": self.model}
                )
                raise OpenRouterAPIError(str(e))
        
        # Apply timeout
        return await with_timeout(
            make_request,
            timeout_seconds=settings.AI_DECISION_TIMEOUT,
            operation_name="ai_decision"
        )
    
    def _parse_response(self, response_text: str) -> AIDecision:
        """
        Parse and validate JSON response from AI.
        
        Args:
            response_text: Raw response text from AI
            
        Returns:
            AIDecision object
            
        Raises:
            OpenRouterAPIError: If response is invalid
        """
        try:
            # Parse JSON
            data = json.loads(response_text)
            
            # Validate required fields
            if "action" not in data:
                raise OpenRouterAPIError("Missing 'action' field in response")
            if "reasoning" not in data:
                raise OpenRouterAPIError("Missing 'reasoning' field in response")
            
            # Validate action
            action = data["action"].upper()
            if action not in ["LONG", "SHORT", "CLOSE", "HOLD"]:
                raise OpenRouterAPIError(f"Invalid action: {action}")
            
            # Extract optional fields with defaults
            stop_loss_price = data.get("stop_loss_price")
            take_profit_price = data.get("take_profit_price")
            size_percentage = data.get("size_percentage", 0.0)
            leverage = data.get("leverage", 1)
            
            # Validate size_percentage
            if not isinstance(size_percentage, (int, float)):
                raise OpenRouterAPIError(f"Invalid size_percentage type: {type(size_percentage)}")
            if size_percentage < 0.0 or size_percentage > 1.0:
                raise OpenRouterAPIError(f"size_percentage must be between 0.0 and 1.0, got {size_percentage}")
            
            # Validate leverage
            if not isinstance(leverage, int):
                leverage = int(leverage)
            if leverage < 1 or leverage > 5:
                raise OpenRouterAPIError(f"leverage must be between 1 and 5, got {leverage}")
            
            # Validate stop_loss_price and take_profit_price if provided
            if stop_loss_price is not None and not isinstance(stop_loss_price, (int, float)):
                raise OpenRouterAPIError(f"Invalid stop_loss_price type: {type(stop_loss_price)}")
            if take_profit_price is not None and not isinstance(take_profit_price, (int, float)):
                raise OpenRouterAPIError(f"Invalid take_profit_price type: {type(take_profit_price)}")
            
            # Create AIDecision
            return AIDecision(
                action=action,
                reasoning=data["reasoning"],
                stop_loss_price=float(stop_loss_price) if stop_loss_price is not None else None,
                take_profit_price=float(take_profit_price) if take_profit_price is not None else None,
                size_percentage=float(size_percentage),
                leverage=leverage
            )
            
        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to parse JSON response: {str(e)}",
                extra={"error": str(e), "response": response_text[:200]}
            )
            raise OpenRouterAPIError(f"Invalid JSON response: {str(e)}")
        except OpenRouterAPIError:
            raise
        except Exception as e:
            logger.error(
                f"Error parsing response: {str(e)}",
                extra={"error": str(e), "response": response_text[:200]}
            )
            raise OpenRouterAPIError(f"Error parsing response: {str(e)}")
