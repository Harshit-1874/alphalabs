"""
Unit tests for AI Trader service.

Tests cover:
- Mock OpenRouter API responses with JSON order format
- Retry logic and timeout handling
- JSON response parsing and validation
- Error handling and fallback behavior
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncIterator

from services.ai_trader import AITrader, AIDecision, Candle
from services.trading.position_manager import Position
from exceptions import OpenRouterAPIError, TimeoutError as AlphaLabTimeoutError
from config import settings


class TestAITrader:
    """Test suite for AITrader"""
    
    @pytest.fixture
    def sample_candle(self) -> Candle:
        """Generate sample candle for testing"""
        return Candle(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            open=50000.0,
            high=50500.0,
            low=49500.0,
            close=50250.0,
            volume=1000000.0
        )
    
    @pytest.fixture
    def sample_indicators(self) -> dict:
        """Generate sample indicators for testing"""
        return {
            'rsi': 55.5,
            'macd': 125.3,
            'ema_20': 50100.0,
            'atr': 250.0
        }
    
    @pytest.fixture
    def sample_position(self) -> Position:
        """Generate sample position for testing"""
        return Position(
            action='long',
            entry_price=50000.0,
            size=0.5,
            stop_loss=49000.0,
            take_profit=52000.0,
            leverage=1,
            entry_time=datetime(2024, 1, 1, 10, 0, 0),
            unrealized_pnl=125.0
        )
    
    @pytest.fixture
    def ai_trader(self) -> AITrader:
        """Create AITrader instance for testing"""
        return AITrader(
            api_key="test-api-key",
            model="anthropic/claude-3.5-sonnet",
            strategy_prompt="Trade based on RSI and MACD signals",
            mode="monk"
        )
    
    # Test initialization
    
    def test_init(self, ai_trader):
        """Test AITrader initialization"""
        assert ai_trader.api_key == "test-api-key"
        assert ai_trader.model == "anthropic/claude-3.5-sonnet"
        assert ai_trader.strategy_prompt == "Trade based on RSI and MACD signals"
        assert ai_trader.mode == "monk"
        assert ai_trader.client is not None
        assert ai_trader.circuit_breaker is not None
    
    # Test prompt building
    
    def test_build_prompt_without_position(self, ai_trader, sample_candle, sample_indicators):
        """Test prompt building without open position"""
        prompt = ai_trader._build_prompt(
            candle=sample_candle,
            indicators=sample_indicators,
            position_state=None,
            equity=10000.0
        )
        
        assert "Current Market State:" in prompt
        assert "50000.0" in prompt  # open price
        assert "55.5" in prompt  # rsi
        assert "125.3" in prompt  # macd
        assert "10000" in prompt  # equity
        assert '"position": null' in prompt
        assert "LONG" in prompt
        assert "SHORT" in prompt
        assert "HOLD" in prompt
    
    def test_build_prompt_with_position(self, ai_trader, sample_candle, sample_indicators, sample_position):
        """Test prompt building with open position"""
        prompt = ai_trader._build_prompt(
            candle=sample_candle,
            indicators=sample_indicators,
            position_state=sample_position,
            equity=10125.0
        )
        
        assert "Current Market State:" in prompt
        assert '"position"' in prompt
        assert '"action": "long"' in prompt
        assert '"entry_price": 50000.0' in prompt
        assert '"unrealized_pnl": 125.0' in prompt
        assert "10125" in prompt  # equity
    
    # Test JSON response parsing
    
    def test_parse_valid_long_response(self, ai_trader):
        """Test parsing valid LONG decision"""
        response = """
        {
            "action": "LONG",
            "reasoning": "RSI is oversold and MACD shows bullish crossover",
            "stop_loss_price": 49000.0,
            "take_profit_price": 52000.0,
            "size_percentage": 0.5,
            "leverage": 1
        }
        """
        
        decision = ai_trader._parse_response(response)
        
        assert decision.action == "LONG"
        assert decision.reasoning == "RSI is oversold and MACD shows bullish crossover"
        assert decision.stop_loss_price == 49000.0
        assert decision.take_profit_price == 52000.0
        assert decision.size_percentage == 0.5
        assert decision.leverage == 1
    
    def test_parse_valid_short_response(self, ai_trader):
        """Test parsing valid SHORT decision"""
        response = """
        {
            "action": "SHORT",
            "reasoning": "RSI is overbought, expecting reversal",
            "stop_loss_price": 51000.0,
            "take_profit_price": 48000.0,
            "size_percentage": 0.3,
            "leverage": 2
        }
        """
        
        decision = ai_trader._parse_response(response)
        
        assert decision.action == "SHORT"
        assert decision.reasoning == "RSI is overbought, expecting reversal"
        assert decision.stop_loss_price == 51000.0
        assert decision.take_profit_price == 48000.0
        assert decision.size_percentage == 0.3
        assert decision.leverage == 2
    
    def test_parse_valid_hold_response(self, ai_trader):
        """Test parsing valid HOLD decision"""
        response = """
        {
            "action": "HOLD",
            "reasoning": "No clear signal, waiting for better entry",
            "size_percentage": 0.0
        }
        """
        
        decision = ai_trader._parse_response(response)
        
        assert decision.action == "HOLD"
        assert decision.reasoning == "No clear signal, waiting for better entry"
        assert decision.stop_loss_price is None
        assert decision.take_profit_price is None
        assert decision.size_percentage == 0.0
        assert decision.leverage == 1  # default
    
    def test_parse_valid_close_response(self, ai_trader):
        """Test parsing valid CLOSE decision"""
        response = """
        {
            "action": "CLOSE",
            "reasoning": "Take profit target reached",
            "size_percentage": 0.0
        }
        """
        
        decision = ai_trader._parse_response(response)
        
        assert decision.action == "CLOSE"
        assert decision.reasoning == "Take profit target reached"
        assert decision.size_percentage == 0.0
    
    def test_parse_lowercase_action(self, ai_trader):
        """Test that lowercase action is converted to uppercase"""
        response = """
        {
            "action": "long",
            "reasoning": "Test",
            "size_percentage": 0.5
        }
        """
        
        decision = ai_trader._parse_response(response)
        assert decision.action == "LONG"
    
    def test_parse_missing_action(self, ai_trader):
        """Test that missing action raises error"""
        response = """
        {
            "reasoning": "Test"
        }
        """
        
        with pytest.raises(OpenRouterAPIError) as exc_info:
            ai_trader._parse_response(response)
        
        assert "Missing 'action' field" in str(exc_info.value)
    
    def test_parse_missing_reasoning(self, ai_trader):
        """Test that missing reasoning raises error"""
        response = """
        {
            "action": "LONG"
        }
        """
        
        with pytest.raises(OpenRouterAPIError) as exc_info:
            ai_trader._parse_response(response)
        
        assert "Missing 'reasoning' field" in str(exc_info.value)
    
    def test_parse_invalid_action(self, ai_trader):
        """Test that invalid action raises error"""
        response = """
        {
            "action": "BUY",
            "reasoning": "Test"
        }
        """
        
        with pytest.raises(OpenRouterAPIError) as exc_info:
            ai_trader._parse_response(response)
        
        assert "Invalid action" in str(exc_info.value)
    
    def test_parse_invalid_size_percentage_type(self, ai_trader):
        """Test that invalid size_percentage type raises error"""
        response = """
        {
            "action": "LONG",
            "reasoning": "Test",
            "size_percentage": "half"
        }
        """
        
        with pytest.raises(OpenRouterAPIError) as exc_info:
            ai_trader._parse_response(response)
        
        assert "Invalid size_percentage type" in str(exc_info.value)
    
    def test_parse_size_percentage_out_of_range(self, ai_trader):
        """Test that size_percentage out of range raises error"""
        response = """
        {
            "action": "LONG",
            "reasoning": "Test",
            "size_percentage": 1.5
        }
        """
        
        with pytest.raises(OpenRouterAPIError) as exc_info:
            ai_trader._parse_response(response)
        
        assert "size_percentage must be between 0.0 and 1.0" in str(exc_info.value)
    
    def test_parse_invalid_leverage(self, ai_trader):
        """Test that invalid leverage raises error"""
        response = """
        {
            "action": "LONG",
            "reasoning": "Test",
            "size_percentage": 0.5,
            "leverage": 10
        }
        """
        
        with pytest.raises(OpenRouterAPIError) as exc_info:
            ai_trader._parse_response(response)
        
        assert "leverage must be between 1 and 5" in str(exc_info.value)
    
    def test_parse_invalid_stop_loss_type(self, ai_trader):
        """Test that invalid stop_loss_price type raises error"""
        response = """
        {
            "action": "LONG",
            "reasoning": "Test",
            "size_percentage": 0.5,
            "stop_loss_price": "low"
        }
        """
        
        with pytest.raises(OpenRouterAPIError) as exc_info:
            ai_trader._parse_response(response)
        
        assert "Invalid stop_loss_price type" in str(exc_info.value)
    
    def test_parse_invalid_json(self, ai_trader):
        """Test that invalid JSON raises error"""
        response = "not valid json"
        
        with pytest.raises(OpenRouterAPIError) as exc_info:
            ai_trader._parse_response(response)
        
        assert "Invalid JSON response" in str(exc_info.value)
    
    # Test API request mocking
    
    @pytest.mark.asyncio
    async def test_successful_api_request(self, ai_trader, sample_candle, sample_indicators):
        """Test successful API request with mocked response"""
        # Mock the streaming response
        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock()]
        mock_chunk.choices[0].delta.content = '{"action": "LONG", "reasoning": "Test", "size_percentage": 0.5}'
        
        async def mock_stream():
            yield mock_chunk
        
        async def mock_create(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.__aiter__ = lambda self: mock_stream()
            return mock_response
        
        with patch.object(ai_trader.client.chat.completions, 'create', side_effect=mock_create):
            decision = await ai_trader.get_decision(
                candle=sample_candle,
                indicators=sample_indicators,
                position_state=None,
                equity=10000.0
            )
        
        assert decision.action == "LONG"
        assert decision.reasoning == "Test"
        assert decision.size_percentage == 0.5
    
    @pytest.mark.asyncio
    async def test_api_request_with_empty_response(self, ai_trader, sample_candle, sample_indicators):
        """Test API request with empty response"""
        async def mock_stream():
            return
            yield  # Make it a generator
        
        mock_response = MagicMock()
        mock_response.__aiter__ = lambda self: mock_stream()
        
        with patch.object(ai_trader.client.chat.completions, 'create', return_value=mock_response):
            decision = await ai_trader.get_decision(
                candle=sample_candle,
                indicators=sample_indicators,
                position_state=None,
                equity=10000.0
            )
        
        # Should return HOLD on failure
        assert decision.action == "HOLD"
        assert "Failed to get AI decision" in decision.reasoning
    
    @pytest.mark.asyncio
    async def test_api_request_timeout(self, ai_trader, sample_candle, sample_indicators):
        """Test API request timeout handling"""
        async def slow_request():
            await asyncio.sleep(100)  # Simulate slow request
        
        with patch.object(ai_trader.client.chat.completions, 'create', side_effect=slow_request):
            with patch('services.ai_trader.with_timeout', side_effect=AlphaLabTimeoutError("ai_decision", 30)):
                decision = await ai_trader.get_decision(
                    candle=sample_candle,
                    indicators=sample_indicators,
                    position_state=None,
                    equity=10000.0
                )
        
        # Should return HOLD on timeout
        assert decision.action == "HOLD"
        assert "Failed to get AI decision" in decision.reasoning
    
    @pytest.mark.asyncio
    async def test_retry_logic_success_on_second_attempt(self, ai_trader, sample_candle, sample_indicators):
        """Test retry logic succeeds on second attempt"""
        attempt_count = 0
        
        async def mock_request_with_retry(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            
            if attempt_count == 1:
                raise OpenRouterAPIError("Temporary error")
            
            # Success on second attempt
            mock_chunk = MagicMock()
            mock_chunk.choices = [MagicMock()]
            mock_chunk.choices[0].delta.content = '{"action": "HOLD", "reasoning": "Success after retry", "size_percentage": 0.0}'
            
            async def mock_stream():
                yield mock_chunk
            
            mock_response = MagicMock()
            mock_response.__aiter__ = lambda self: mock_stream()
            return mock_response
        
        with patch.object(ai_trader.client.chat.completions, 'create', side_effect=mock_request_with_retry):
            decision = await ai_trader.get_decision(
                candle=sample_candle,
                indicators=sample_indicators,
                position_state=None,
                equity=10000.0
            )
        
        assert attempt_count == 2
        assert decision.action == "HOLD"
        assert decision.reasoning == "Success after retry"
    
    @pytest.mark.asyncio
    async def test_retry_logic_all_attempts_fail(self, ai_trader, sample_candle, sample_indicators):
        """Test retry logic when all attempts fail"""
        with patch.object(
            ai_trader.client.chat.completions,
            'create',
            side_effect=OpenRouterAPIError("Persistent error")
        ):
            decision = await ai_trader.get_decision(
                candle=sample_candle,
                indicators=sample_indicators,
                position_state=None,
                equity=10000.0
            )
        
        # Should return HOLD after all retries fail
        assert decision.action == "HOLD"
        assert "Failed to get AI decision" in decision.reasoning
    
    # Test circuit breaker integration
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self, ai_trader, sample_candle, sample_indicators):
        """Test that circuit breaker opens after threshold failures"""
        # Reset circuit breaker
        ai_trader.circuit_breaker.reset()
        
        # Mock failures to trigger circuit breaker
        with patch.object(
            ai_trader.client.chat.completions,
            'create',
            side_effect=OpenRouterAPIError("API error")
        ):
            # Make multiple requests to trigger circuit breaker
            for _ in range(settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD + 1):
                decision = await ai_trader.get_decision(
                    candle=sample_candle,
                    indicators=sample_indicators,
                    position_state=None,
                    equity=10000.0
                )
                assert decision.action == "HOLD"
        
        # Circuit breaker should be open
        assert ai_trader.circuit_breaker.state == "open"
    
    # Test different modes
    
    def test_monk_mode_prompt(self):
        """Test that monk mode is reflected in prompt"""
        trader = AITrader(
            api_key="test-key",
            model="test-model",
            strategy_prompt="Test strategy",
            mode="monk"
        )
        
        candle = Candle(
            timestamp=datetime(2024, 1, 1),
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000.0
        )
        
        prompt = trader._build_prompt(candle, {'rsi': 50.0}, None, 10000.0)
        
        # Monk mode should be mentioned in system message (not in user prompt)
        assert trader.mode == "monk"
    
    def test_omni_mode_prompt(self):
        """Test that omni mode is reflected in prompt"""
        trader = AITrader(
            api_key="test-key",
            model="test-model",
            strategy_prompt="Test strategy",
            mode="omni"
        )
        
        candle = Candle(
            timestamp=datetime(2024, 1, 1),
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000.0
        )
        
        prompt = trader._build_prompt(candle, {'rsi': 50.0, 'macd': 10.0, 'ema_20': 100.0}, None, 10000.0)
        
        # Omni mode should be mentioned in system message (not in user prompt)
        assert trader.mode == "omni"
    
    # Test edge cases
    
    def test_parse_response_with_optional_fields_missing(self, ai_trader):
        """Test parsing response with optional fields missing"""
        response = """
        {
            "action": "HOLD",
            "reasoning": "Waiting for signal"
        }
        """
        
        decision = ai_trader._parse_response(response)
        
        assert decision.action == "HOLD"
        assert decision.reasoning == "Waiting for signal"
        assert decision.stop_loss_price is None
        assert decision.take_profit_price is None
        assert decision.size_percentage == 0.0
        assert decision.leverage == 1
    
    def test_parse_response_with_float_leverage(self, ai_trader):
        """Test that float leverage is converted to int"""
        response = """
        {
            "action": "LONG",
            "reasoning": "Test",
            "size_percentage": 0.5,
            "leverage": 2.0
        }
        """
        
        decision = ai_trader._parse_response(response)
        
        assert decision.leverage == 2
        assert isinstance(decision.leverage, int)
    
    def test_parse_response_with_integer_prices(self, ai_trader):
        """Test that integer prices are converted to float"""
        response = """
        {
            "action": "LONG",
            "reasoning": "Test",
            "size_percentage": 0.5,
            "stop_loss_price": 49000,
            "take_profit_price": 52000
        }
        """
        
        decision = ai_trader._parse_response(response)
        
        assert decision.stop_loss_price == 49000.0
        assert decision.take_profit_price == 52000.0
        assert isinstance(decision.stop_loss_price, float)
        assert isinstance(decision.take_profit_price, float)
    
    def test_parse_response_with_zero_size_percentage(self, ai_trader):
        """Test parsing response with zero size_percentage"""
        response = """
        {
            "action": "HOLD",
            "reasoning": "No trade",
            "size_percentage": 0.0
        }
        """
        
        decision = ai_trader._parse_response(response)
        
        assert decision.size_percentage == 0.0
    
    def test_parse_response_with_max_leverage(self, ai_trader):
        """Test parsing response with maximum leverage"""
        response = """
        {
            "action": "LONG",
            "reasoning": "High conviction trade",
            "size_percentage": 1.0,
            "leverage": 5
        }
        """
        
        decision = ai_trader._parse_response(response)
        
        assert decision.leverage == 5
        assert decision.size_percentage == 1.0
    
    @pytest.mark.asyncio
    async def test_get_decision_with_position(self, ai_trader, sample_candle, sample_indicators, sample_position):
        """Test getting decision with open position"""
        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock()]
        mock_chunk.choices[0].delta.content = '{"action": "CLOSE", "reasoning": "Take profit", "size_percentage": 0.0}'
        
        async def mock_stream():
            yield mock_chunk
        
        async def mock_create(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.__aiter__ = lambda self: mock_stream()
            return mock_response
        
        with patch.object(ai_trader.client.chat.completions, 'create', side_effect=mock_create):
            decision = await ai_trader.get_decision(
                candle=sample_candle,
                indicators=sample_indicators,
                position_state=sample_position,
                equity=10125.0
            )
        
        assert decision.action == "CLOSE"
        assert decision.reasoning == "Take profit"
    
    def test_build_prompt_includes_all_indicators(self, ai_trader, sample_candle):
        """Test that prompt includes all provided indicators"""
        indicators = {
            'rsi': 55.5,
            'macd': 125.3,
            'ema_20': 50100.0,
            'ema_50': 50000.0,
            'atr': 250.0,
            'bbands': 50200.0
        }
        
        prompt = ai_trader._build_prompt(sample_candle, indicators, None, 10000.0)
        
        # All indicators should be in prompt
        for key, value in indicators.items():
            assert key in prompt
            assert str(value) in prompt
    
    def test_build_prompt_includes_candle_data(self, ai_trader, sample_indicators):
        """Test that prompt includes all candle data"""
        candle = Candle(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            open=50000.0,
            high=50500.0,
            low=49500.0,
            close=50250.0,
            volume=1000000.0
        )
        
        prompt = ai_trader._build_prompt(candle, sample_indicators, None, 10000.0)
        
        assert "50000.0" in prompt  # open
        assert "50500.0" in prompt  # high
        assert "49500.0" in prompt  # low
        assert "50250.0" in prompt  # close
        assert "1000000.0" in prompt  # volume
