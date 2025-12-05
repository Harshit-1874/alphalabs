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
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List
from openai import AsyncOpenAI

from config import settings
from exceptions import OpenRouterAPIError, TimeoutError as AlphaLabTimeoutError, CircuitBreakerOpenError, RateLimitError
from utils.retry import retry_with_backoff, CircuitBreaker, with_timeout
from services.trading.position_manager import Position
from services.model_inspector import ModelInspector


logger = logging.getLogger(__name__)


# Global request throttling
_last_request_time: float = 0
_request_lock = asyncio.Lock()


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
    # Optional entry price for limit-like behavior. If provided, the engine
    # will treat this as a pending order to be filled when price reaches this
    # level; otherwise it is treated as a market-at-close decision.
    entry_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    size_percentage: float = 0.0
    leverage: int = 1
    candle_index: Optional[int] = None
    decision_context: Optional[Dict[str, Any]] = None
    candle_index: Optional[int] = None


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
        
        # Initialize model inspector for metadata and validation
        self.model_inspector = ModelInspector(api_key)
        
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
        
        # Cache for model metadata (lazy-loaded on first use)
        self._model_max_tokens: Optional[int] = None
        self._model_supports_structured: Optional[bool] = None
        
        logger.info(
            f"AI Trader initialized",
            extra={
                "model": model,
                "mode": mode,
                "strategy_length": len(strategy_prompt)
            }
        )
    
    async def initialize(self) -> None:
        """
        Eagerly initialize model metadata.
        
        This should be called after creating AITrader to pre-load model
        information (max_tokens, structured outputs support) so it doesn't
        happen during trading decisions.
        """
        if self._model_max_tokens is None or self._model_supports_structured is None:
            logger.debug(f"Initializing model metadata for {self.model}")
            # Eagerly load both values to avoid fetching during trading decisions
            self._model_max_tokens = await self.model_inspector.get_optimal_max_tokens(
                self.model,
                default=2048,
                min_tokens=512,
                max_tokens=8192
            )
            self._model_supports_structured = await self.model_inspector.supports_structured_outputs(
                self.model
            )
            logger.debug(
                f"Model metadata initialized: max_tokens={self._model_max_tokens}, "
                f"supports_structured={self._model_supports_structured}"
            )
    
    async def _get_optimal_max_tokens(self) -> int:
        """Get optimal max_tokens for the current model (lazy-loaded)"""
        if self._model_max_tokens is None:
            self._model_max_tokens = await self.model_inspector.get_optimal_max_tokens(
                self.model,
                default=2048,
                min_tokens=512,
                max_tokens=8192
            )
        return self._model_max_tokens
    
    async def _supports_structured_outputs(self) -> bool:
        """Check if current model supports structured outputs (lazy-loaded)"""
        if self._model_supports_structured is None:
            self._model_supports_structured = await self.model_inspector.supports_structured_outputs(
                self.model
            )
        return self._model_supports_structured

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
            prompt = self._build_prompt(
                candle,
                indicators,
                position_state,
                equity,
                recent_candles=recent_candles,
                recent_indicators=recent_indicators,
                decision_context=decision_context,
            )
            
            # Make API request with retry, timeout, and circuit breaker protection
            async def make_request_with_retry():
                async def make_request():
                    return await self._make_api_request(prompt)
                
                # Apply circuit breaker
                async def circuit_protected_request():
                    return await self.circuit_breaker.call(make_request)
                
                # Apply retry with exponential backoff.
                # Retry API errors and rate limits (rate limits handled with reset-time-aware backoff).
                # We keep retries low (1-2) to avoid freezing backtests.
                return await retry_with_backoff(
                    circuit_protected_request,
                    max_retries=settings.MAX_RETRIES,
                    base_delay=settings.RETRY_BASE_DELAY,
                    max_delay=settings.RETRY_MAX_DELAY,
                    # Retry API errors and rate limits (rate limits handled specially in retry logic)
                    exceptions=(OpenRouterAPIError, RateLimitError),
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
            
        except CircuitBreakerOpenError as e:
            # Circuit breaker is open - service is temporarily unavailable
            # Log as warning (not error) since this is expected behavior when service is down
            logger.warning(
                f"AI decision skipped: {str(e)}",
                extra={"error": str(e), "model": self.model}
            )
            # Return HOLD decision with brief reasoning
            return AIDecision(
                action="HOLD",
                reasoning=f"AI service temporarily unavailable (circuit breaker open)",
                size_percentage=0.0,
                leverage=1
            )
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
        equity: float,
        recent_candles: Optional[List[Dict[str, Any]]] = None,
        recent_indicators: Optional[List[Dict[str, Any]]] = None,
        decision_context: Optional[Dict[str, Any]] = None,
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
            "equity": equity,
            "recent_candles": recent_candles or [],
            "recent_indicators": recent_indicators or [],
            "decision_context": decision_context or {},
        }
        constraints = market_context["decision_context"]
        allow_leverage = constraints.get("allow_leverage", False) if constraints else False
        max_leverage = constraints.get("max_leverage", 1) if constraints else 1
        
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
- leverage: Multiplier for position size. Leverage is {'allowed up to ' + str(max_leverage) + 'x' if allow_leverage else 'locked at 1x (no leverage allowed)'}.
- If you have an open position, you can only CLOSE or HOLD
- If you don't have a position, you can LONG, SHORT, or HOLD
"""
        
        return user_message
    
    async def _make_api_request(self, user_message: str) -> str:
        """
        Make API request to OpenRouter with timeout and retry.
        
        Implements request throttling to prevent rate limit errors by ensuring
        a minimum delay between consecutive API calls.
        
        We intentionally use the non-streaming API with OpenRouter structured
        outputs so the model is constrained to emit JSON that matches our
        trading decision schema. This keeps parsing simple and avoids most
        hallucinated or malformed responses.
        
        Args:
            user_message: User message with market context
            
        Returns:
            Complete response text from AI (JSON string)
            
        Raises:
            OpenRouterAPIError: If API call fails
            AlphaLabTimeoutError: If request times out
        """
        # Throttle requests globally to respect rate limits
        global _last_request_time, _request_lock
        
        async with _request_lock:
            current_time = time.time()
            time_since_last_request = current_time - _last_request_time
            
            if time_since_last_request < settings.API_REQUEST_DELAY:
                wait_time = settings.API_REQUEST_DELAY - time_since_last_request
                logger.debug(f"Throttling API request: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
            
            _last_request_time = time.time()
        
        async def make_request():
            try:
                # Build system message based on mode
                mode_description = "Monk Mode (limited indicators)" if self.mode == "monk" else "Omni Mode (all indicators)"
                system_message = f"""You are an AI trading agent operating in {mode_description}.

Your Strategy:
{self.strategy_prompt}

You must analyze the market data and make trading decisions based on your strategy.
Always respond with valid JSON in the exact format specified. Your response must be a JSON object with these fields:
- action: one of "LONG", "SHORT", "CLOSE", or "HOLD"
- reasoning: explanation for your decision
- size_percentage: number between 0.0 and 1.0 (fraction of capital to use)
- leverage: integer between 1 and 5
- entry_price: (optional) desired entry price
- stop_loss_price: (optional) stop loss price
- take_profit_price: (optional) take profit price"""
                
                # Get optimal max_tokens based on model's context length
                optimal_max_tokens = await self._get_optimal_max_tokens()
                
                # Try with structured outputs first (if model supports it)
                used_structured_outputs = False
                supports_structured = await self._supports_structured_outputs()
                
                if supports_structured:
                    try:
                        response = await self.client.chat.completions.create(
                            model=self.model,
                            messages=[
                                {"role": "system", "content": system_message},
                                {"role": "user", "content": user_message}
                            ],
                            response_format={
                                "type": "json_schema",
                                "json_schema": {
                                    "name": "trading_decision",
                                    "strict": True,
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "action": {
                                                "type": "string",
                                                "description": "Trading action to take",
                                                "enum": ["LONG", "SHORT", "CLOSE", "HOLD"],
                                            },
                                            "reasoning": {
                                                "type": "string",
                                                "description": "Explanation for the decision based on indicators and market context",
                                            },
                                            "entry_price": {
                                                "type": "number",
                                                "description": "Desired entry price. If omitted, enter at current close.",
                                            },
                                            "stop_loss_price": {
                                                "type": "number",
                                                "description": "Absolute stop loss price level. Optional; can be omitted.",
                                            },
                                            "take_profit_price": {
                                                "type": "number",
                                                "description": "Absolute take profit price level. Optional; can be omitted.",
                                            },
                                            "size_percentage": {
                                                "type": "number",
                                                "description": "Fraction of capital to use between 0.0 and 1.0",
                                                "minimum": 0.0,
                                                "maximum": 1.0,
                                            },
                                            "leverage": {
                                                "type": "integer",
                                                "description": "Leverage multiplier between 1 and 5",
                                                "minimum": 1,
                                                "maximum": 5,
                                            },
                                        },
                                        "required": ["action", "reasoning", "size_percentage", "leverage"],
                                        "additionalProperties": False,
                                    },
                                },
                            },
                            temperature=0,
                            max_tokens=optimal_max_tokens,
                        )
                        used_structured_outputs = True
                    except Exception as structured_error:
                        # If structured outputs fail, log and try fallback
                        logger.warning(
                            f"Structured outputs failed for model {self.model}, trying fallback: {str(structured_error)}"
                        )
                        # Fallback: request JSON mode without strict schema
                        response = await self.client.chat.completions.create(
                            model=self.model,
                            messages=[
                                {"role": "system", "content": system_message},
                                {"role": "user", "content": user_message}
                            ],
                            response_format={"type": "json_object"},  # JSON mode (less strict)
                            temperature=0,
                            max_tokens=optimal_max_tokens,
                        )
                else:
                    # Model doesn't support structured outputs, use JSON mode directly
                    logger.debug(f"Model {self.model} doesn't support structured outputs, using JSON mode")
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": user_message}
                        ],
                        response_format={"type": "json_object"},  # JSON mode (less strict)
                        temperature=0,
                        max_tokens=optimal_max_tokens,
                    )

                # OpenAI / OpenRouter client returns the content on the first choice
                if not response.choices or len(response.choices) == 0:
                    raise OpenRouterAPIError("No choices in API response")
                
                choice = response.choices[0]
                if not hasattr(choice, 'message') or choice.message is None:
                    raise OpenRouterAPIError("No message in API response choice")
                
                content = choice.message.content
                
                # Log the raw response for debugging
                logger.debug(
                    f"OpenRouter API response: model={response.model}, "
                    f"choices_count={len(response.choices)}, "
                    f"content_type={type(content)}, "
                    f"content_length={len(str(content)) if content else 0}, "
                    f"finish_reason={getattr(choice, 'finish_reason', 'unknown')}"
                )
                
                if content is None or (isinstance(content, str) and not content.strip()):
                    # Check finish_reason to understand why content is empty
                    finish_reason = getattr(choice, 'finish_reason', None)
                    
                    # If we used structured outputs and got empty response, try fallback
                    # Some models don't support json_schema structured outputs properly
                    if used_structured_outputs:
                        logger.warning(
                            f"Empty response with structured outputs for model {self.model}, "
                            f"trying fallback with json_object mode"
                        )
                        # Retry with json_object mode (less strict)
                        # Use optimal max_tokens (already computed)
                        response = await self.client.chat.completions.create(
                            model=self.model,
                            messages=[
                                {"role": "system", "content": system_message},
                                {"role": "user", "content": user_message}
                            ],
                            response_format={"type": "json_object"},
                            temperature=0,
                            max_tokens=optimal_max_tokens,
                        )
                        
                        # Check the fallback response
                        if not response.choices or len(response.choices) == 0:
                            raise OpenRouterAPIError("No choices in fallback API response")
                        
                        choice = response.choices[0]
                        content = choice.message.content if choice.message else None
                        
                        if content is None or (isinstance(content, str) and not content.strip()):
                            finish_reason = getattr(choice, 'finish_reason', None)
                            error_msg = f"Empty response from API even with fallback (finish_reason: {finish_reason})"
                            if finish_reason == "length":
                                error_msg += " - Response was truncated (increase max_tokens)"
                            elif finish_reason == "content_filter":
                                error_msg += " - Content was filtered by safety system"
                            raise OpenRouterAPIError(error_msg)
                    else:
                        # Already tried fallback or didn't use structured outputs
                        error_msg = f"Empty response from API (finish_reason: {finish_reason})"
                        if finish_reason == "length":
                            error_msg += " - Response was truncated (increase max_tokens)"
                        elif finish_reason == "content_filter":
                            error_msg += " - Content was filtered by safety system"
                        elif finish_reason == "stop":
                            error_msg += " - Model stopped early (may indicate an issue)"
                        raise OpenRouterAPIError(error_msg)

                # In most cases this will already be a JSON string; if not, we
                # serialize whatever object we got so that _parse_response can
                # still call json.loads on it.
                if isinstance(content, str):
                    full_response = content.strip()
                else:
                    full_response = json.dumps(content)

                if not full_response:
                    raise OpenRouterAPIError("Empty response from API (content was empty string)")

                return full_response
                
            except Exception as e:
                # Check if this is a rate limit error (429)
                error_str = str(e).lower()
                if "429" in error_str or "rate limit" in error_str or "too many requests" in error_str:
                    # Try to extract rate limit info from the error
                    reset_at = None
                    try:
                        # The error might contain headers with rate limit info
                        # Look for various formats:
                        # - X-RateLimit-Reset: timestamp in seconds or milliseconds
                        # - Retry-After: seconds to wait
                        import re
                        
                        # Try to find X-RateLimit-Reset header (milliseconds or seconds)
                        reset_match = re.search(r"[Xx]-[Rr]ate[Ll]imit-[Rr]eset['\"]?\s*:\s*['\"]?(\d+)", str(e))
                        if reset_match:
                            reset_value = int(reset_match.group(1))
                            # If value is in seconds (< year 2100 in Unix seconds)
                            if reset_value < 5_000_000_000:
                                reset_at = reset_value * 1000  # Convert to milliseconds
                            else:
                                reset_at = reset_value  # Already in milliseconds
                        
                        # Try to find Retry-After header (seconds to wait)
                        retry_after_match = re.search(r"[Rr]etry-[Aa]fter['\"]?\s*:\s*['\"]?(\d+)", str(e))
                        if retry_after_match and not reset_at:
                            retry_after = int(retry_after_match.group(1))
                            # Calculate reset time (current time + retry_after)
                            reset_at = int((time.time() + retry_after) * 1000)
                        
                        if reset_at:
                            logger.debug(f"Extracted rate limit reset time: {reset_at}ms")
                    except Exception as parse_error:
                        logger.debug(f"Could not parse rate limit headers: {parse_error}")
                    
                    raise RateLimitError(
                        resource="openrouter",
                        reset_at=reset_at
                    )
                
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
            # Normalize and extract JSON payload
            if not response_text:
                raise OpenRouterAPIError("Empty response from API")

            stripped = response_text.strip()
            if not stripped:
                raise OpenRouterAPIError("Empty response from API")

            # Some models may wrap JSON in extra text or markdown fences.
            # Try to isolate the first {...} block before parsing.
            start = stripped.find("{")
            end = stripped.rfind("}")
            if start != -1 and end != -1 and end > start:
                json_str = stripped[start : end + 1]
            else:
                # Fall back to full string; this will raise a clear JSON error.
                json_str = stripped

            # Parse JSON
            data = json.loads(json_str)
            
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
            entry_price = data.get("entry_price")
            stop_loss_price = data.get("stop_loss_price")
            take_profit_price = data.get("take_profit_price")
            size_percentage = data.get("size_percentage", 0.0)
            leverage = data.get("leverage", 1)

            # Be tolerant of null coming back from the model by treating it as 0
            if size_percentage is None:
                size_percentage = 0.0
            
            # Validate size_percentage
            if not isinstance(size_percentage, (int, float)):
                raise OpenRouterAPIError(f"Invalid size_percentage type: {type(size_percentage)}")
            if size_percentage < 0.0 or size_percentage > 1.0:
                raise OpenRouterAPIError(f"size_percentage must be between 0.0 and 1.0, got {size_percentage}")
            
            # Validate leverage
            if leverage is None:
                leverage = 1
            if not isinstance(leverage, int):
                try:
                    leverage = int(leverage)
                except (TypeError, ValueError):
                    raise OpenRouterAPIError(f"Invalid leverage value: {leverage!r}")
            if leverage < 1 or leverage > 5:
                raise OpenRouterAPIError(f"leverage must be between 1 and 5, got {leverage}")
            
            # Validate entry_price, stop_loss_price and take_profit_price if provided
            if entry_price is not None and not isinstance(entry_price, (int, float)):
                raise OpenRouterAPIError(f"Invalid entry_price type: {type(entry_price)}")
            if stop_loss_price is not None and not isinstance(stop_loss_price, (int, float)):
                raise OpenRouterAPIError(f"Invalid stop_loss_price type: {type(stop_loss_price)}")
            if take_profit_price is not None and not isinstance(take_profit_price, (int, float)):
                raise OpenRouterAPIError(f"Invalid take_profit_price type: {type(take_profit_price)}")
            
            candle_index = data.get("candle_index")
            decision_context = data.get("decision_context")
            
            # Create AIDecision
            return AIDecision(
                action=action,
                reasoning=data["reasoning"],
                entry_price=float(entry_price) if entry_price is not None else None,
                stop_loss_price=float(stop_loss_price) if stop_loss_price is not None else None,
                take_profit_price=float(take_profit_price) if take_profit_price is not None else None,
                size_percentage=float(size_percentage),
                leverage=leverage,
                candle_index=int(candle_index) if candle_index is not None else None,
                decision_context=decision_context,
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
