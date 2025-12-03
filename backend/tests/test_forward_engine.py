"""
Integration tests for Forward Test Engine.

Tests:
- Forward test initialization
- Candle waiting and polling
- Countdown updates
- Auto-stop conditions
- Result generation
- Email notifications (mocked)
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from services.trading.forward_engine import ForwardEngine, SessionState
from services.market_data_service import Candle
from models.agent import Agent
from models.arena import TestSession
from websocket.manager import WebSocketManager
from exceptions import ValidationError


@pytest.fixture
async def db_session():
    """Create a test database session."""
    # Use in-memory SQLite for testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    # Create tables (simplified for testing)
    async with engine.begin() as conn:
        # In a real test, we'd create all tables
        # For now, we'll mock the database operations
        pass
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def websocket_manager():
    """Create a mock WebSocket manager."""
    manager = Mock(spec=WebSocketManager)
    manager.broadcast_to_session = AsyncMock()
    return manager


@pytest.fixture
def mock_agent():
    """Create a mock agent."""
    agent = Mock(spec=Agent)
    agent.id = "agent-123"
    agent.name = "Test Agent"
    agent.mode = "monk"
    agent.model = "deepseek-r1"
    agent.indicators = ["rsi", "macd"]
    agent.custom_indicators = []
    agent.strategy_prompt = "Trade based on RSI and MACD"
    
    # Mock API key
    api_key = Mock()
    api_key.encrypted_key = "encrypted_key_data"
    agent.api_key = api_key
    
    return agent


@pytest.fixture
def mock_candle():
    """Create a mock candle."""
    return Candle(
        timestamp=datetime.utcnow(),
        open=50000.0,
        high=50500.0,
        low=49500.0,
        close=50200.0,
        volume=1000000.0
    )


@pytest.mark.asyncio
async def test_forward_engine_initialization(db_session, websocket_manager):
    """Test forward engine initialization."""
    # Create a mock session factory
    async def mock_session_factory():
        yield db_session
    
    engine = ForwardEngine(mock_session_factory, websocket_manager)
    
    assert engine.session_factory == mock_session_factory
    assert engine.websocket_manager == websocket_manager
    assert isinstance(engine.active_sessions, dict)
    assert len(engine.active_sessions) == 0


@pytest.mark.asyncio
async def test_validate_parameters(db_session, websocket_manager):
    """Test parameter validation."""
    async def mock_session_factory():
        yield db_session
    
    engine = ForwardEngine(mock_session_factory, websocket_manager)
    
    # Valid parameters should not raise
    engine._validate_parameters(
        asset="BTC/USDT",
        timeframe="1h",
        starting_capital=10000.0
    )
    
    # Invalid asset
    with pytest.raises(ValidationError, match="Unsupported asset"):
        engine._validate_parameters(
            asset="INVALID/USDT",
            timeframe="1h",
            starting_capital=10000.0
        )
    
    # Invalid timeframe
    with pytest.raises(ValidationError, match="Unsupported timeframe"):
        engine._validate_parameters(
            asset="BTC/USDT",
            timeframe="5m",
            starting_capital=10000.0
        )
    
    # Invalid starting capital
    with pytest.raises(ValidationError, match="must be positive"):
        engine._validate_parameters(
            asset="BTC/USDT",
            timeframe="1h",
            starting_capital=-1000.0
        )


@pytest.mark.asyncio
async def test_calculate_next_candle_close_time(db_session, websocket_manager):
    """Test next candle close time calculation."""
    async def mock_session_factory():
        yield db_session
    
    engine = ForwardEngine(mock_session_factory, websocket_manager)
    
    # Test 1h timeframe
    current_time = datetime(2024, 1, 1, 10, 23, 45)
    next_close = engine._calculate_next_candle_close_time(current_time, "1h")
    
    # Should round to next hour
    assert next_close == datetime(2024, 1, 1, 11, 0, 0)
    
    # Test 15m timeframe
    current_time = datetime(2024, 1, 1, 10, 23, 45)
    next_close = engine._calculate_next_candle_close_time(current_time, "15m")
    
    # Should round to next 15-minute boundary
    assert next_close == datetime(2024, 1, 1, 10, 30, 0)
    
    # Test 4h timeframe
    current_time = datetime(2024, 1, 1, 10, 23, 45)
    next_close = engine._calculate_next_candle_close_time(current_time, "4h")
    
    # Should round to next 4-hour boundary (12:00)
    assert next_close == datetime(2024, 1, 1, 12, 0, 0)


@pytest.mark.asyncio
async def test_start_forward_test(db_session, websocket_manager, mock_agent):
    """Test starting a forward test."""
    async def mock_session_factory():
        yield db_session
    
    engine = ForwardEngine(mock_session_factory, websocket_manager)
    
    # Mock database operations
    with patch.object(engine, '_update_session_status', new=AsyncMock()):
        with patch.object(engine, '_update_session_started_at', new=AsyncMock()):
            with patch.object(engine, '_broadcast_session_initialized', new=AsyncMock()):
                with patch('core.encryption.decrypt_api_key', return_value="test_api_key"):
                    with patch('asyncio.create_task'):
                        # Start forward test
                        await engine.start_forward_test(
                            session_id="session-123",
                            agent=mock_agent,
                            asset="BTC/USDT",
                            timeframe="1h",
                            starting_capital=10000.0,
                            safety_mode=True,
                            auto_stop_config={"enabled": True, "loss_pct": 5.0},
                            email_notifications=True
                        )
                        
                        # Verify session state was created
                        assert "session-123" in engine.active_sessions
                        session_state = engine.active_sessions["session-123"]
                        
                        assert session_state.session_id == "session-123"
                        assert session_state.agent == mock_agent
                        assert session_state.asset == "BTC/USDT"
                        assert session_state.timeframe == "1h"
                        assert session_state.position_manager is not None
                        assert session_state.ai_trader is not None
                        assert session_state.auto_stop_config == {"enabled": True, "loss_pct": 5.0}


@pytest.mark.asyncio
async def test_wait_for_candle_close(db_session, websocket_manager, mock_agent, mock_candle):
    """Test waiting for candle close with countdown updates."""
    async def mock_session_factory():
        yield db_session
    
    engine = ForwardEngine(mock_session_factory, websocket_manager)
    
    # Create session state
    session_state = SessionState(
        session_id="session-123",
        agent=mock_agent,
        asset="BTC/USDT",
        timeframe="1h",
        position_manager=Mock(),
        ai_trader=Mock()
    )
    
    # Mock market data service
    market_data_service = Mock()
    market_data_service.get_latest_candle = AsyncMock(return_value=mock_candle)
    
    # Mock broadcast method
    with patch.object(engine, '_broadcast_countdown_update', new=AsyncMock()):
        # Mock asyncio.sleep to avoid actual waiting
        with patch('asyncio.sleep', new=AsyncMock()):
            # Set next candle time to past to trigger immediate return
            session_state.next_candle_time = datetime.utcnow() - timedelta(seconds=10)
            
            # Wait for candle
            candle = await engine._wait_for_candle_close(
                "session-123",
                session_state,
                market_data_service
            )
            
            # Verify candle was returned
            assert candle == mock_candle
            
            # Verify market data service was called
            market_data_service.get_latest_candle.assert_called()


@pytest.mark.asyncio
async def test_check_auto_stop_conditions(db_session, websocket_manager, mock_agent):
    """Test auto-stop condition monitoring."""
    async def mock_session_factory():
        yield db_session
    
    engine = ForwardEngine(mock_session_factory, websocket_manager)
    
    # Create session state with auto-stop enabled
    position_manager = Mock()
    position_manager.get_stats.return_value = {
        "total_pnl_pct": -6.0  # Loss exceeds threshold
    }
    
    session_state = SessionState(
        session_id="session-123",
        agent=mock_agent,
        asset="BTC/USDT",
        timeframe="1h",
        position_manager=position_manager,
        ai_trader=Mock(),
        auto_stop_config={"enabled": True, "loss_pct": 5.0}
    )
    
    # Check auto-stop conditions
    should_stop = await engine._check_auto_stop_conditions(
        "session-123",
        session_state
    )
    
    # Should trigger auto-stop
    assert should_stop is True
    
    # Test with loss below threshold
    position_manager.get_stats.return_value = {
        "total_pnl_pct": -3.0  # Loss below threshold
    }
    
    should_stop = await engine._check_auto_stop_conditions(
        "session-123",
        session_state
    )
    
    # Should not trigger auto-stop
    assert should_stop is False
    
    # Test with auto-stop disabled
    session_state.auto_stop_config = {"enabled": False}
    position_manager.get_stats.return_value = {
        "total_pnl_pct": -10.0  # Large loss
    }
    
    should_stop = await engine._check_auto_stop_conditions(
        "session-123",
        session_state
    )
    
    # Should not trigger auto-stop when disabled
    assert should_stop is False


@pytest.mark.asyncio
async def test_stop_forward_test(db_session, websocket_manager, mock_agent, mock_candle):
    """Test stopping a forward test."""
    async def mock_session_factory():
        yield db_session
    
    engine = ForwardEngine(mock_session_factory, websocket_manager)
    
    # Create session state with open position
    position_manager = Mock()
    position_manager.has_open_position.return_value = True
    position_manager.close_position = AsyncMock(return_value=Mock(
        action="long",
        entry_price=50000.0,
        exit_price=50200.0,
        pnl=200.0,
        pnl_pct=0.4,
        reason="manual"
    ))
    position_manager.get_stats.return_value = {
        "current_equity": 10200.0,
        "equity_change_pct": 2.0,
        "total_trades": 3,
        "win_rate": 66.7,
        "total_pnl": 200.0,
        "total_pnl_pct": 2.0
    }
    
    session_state = SessionState(
        session_id="session-123",
        agent=mock_agent,
        asset="BTC/USDT",
        timeframe="1h",
        position_manager=position_manager,
        ai_trader=Mock()
    )
    session_state.candles_processed = [mock_candle]
    
    engine.active_sessions["session-123"] = session_state
    
    # Mock market data service
    market_data_service = Mock()
    market_data_service.get_latest_candle = AsyncMock(return_value=mock_candle)
    
    # Mock database operations
    with patch.object(engine, '_update_session_status', new=AsyncMock()):
        with patch.object(engine, '_update_session_completed_at', new=AsyncMock()):
            with patch.object(engine, '_update_session_final_stats', new=AsyncMock()):
                with patch.object(engine, '_save_ai_thoughts', new=AsyncMock()):
                    with patch.object(engine, '_handle_position_closed', new=AsyncMock()):
                        with patch('services.trading.forward_engine.MarketDataService', return_value=market_data_service):
                            # Stop forward test
                            result_id = await engine.stop_forward_test("session-123")
                            
                            # Verify stop flag was set
                            assert session_state.is_stopped is True
                            
                            # Verify position was closed
                            position_manager.close_position.assert_called_once()
                            
                            # Verify result was generated
                            assert result_id is not None


@pytest.mark.asyncio
async def test_process_candle_with_ai_decision(
    db_session,
    websocket_manager,
    mock_agent,
    mock_candle
):
    """Test candle processing with AI decision."""
    async def mock_session_factory():
        yield db_session
    
    engine = ForwardEngine(mock_session_factory, websocket_manager)
    
    # Create mocks
    position_manager = Mock()
    position_manager.has_open_position.return_value = False
    position_manager.open_position = AsyncMock(return_value=True)
    position_manager.get_position.return_value = Mock(
        action="long",
        entry_price=50200.0,
        size=0.5,
        leverage=1,
        stop_loss=49500.0,
        take_profit=51500.0
    )
    position_manager.get_total_equity.return_value = 10000.0
    position_manager.get_stats.return_value = {
        "current_equity": 10000.0,
        "total_trades": 0,
        "win_rate": 0.0
    }
    
    ai_trader = Mock()
    ai_trader.get_decision = AsyncMock(return_value=Mock(
        action="LONG",
        reasoning="RSI oversold, MACD bullish crossover",
        stop_loss_price=49500.0,
        take_profit_price=51500.0,
        size_percentage=0.5,
        leverage=1
    ))
    
    session_state = SessionState(
        session_id="session-123",
        agent=mock_agent,
        asset="BTC/USDT",
        timeframe="1h",
        position_manager=position_manager,
        ai_trader=ai_trader
    )
    session_state.candles_processed = [mock_candle]
    
    # Mock database and broadcast methods
    with patch.object(engine, '_broadcast_candle', new=AsyncMock()):
        with patch.object(engine, '_broadcast_ai_thinking', new=AsyncMock()):
            with patch.object(engine, '_broadcast_ai_decision', new=AsyncMock()):
                with patch.object(engine, '_broadcast_stats_update', new=AsyncMock()):
                    with patch.object(engine, '_handle_position_opened', new=AsyncMock()):
                        with patch('services.trading.forward_engine.IndicatorCalculator') as MockIndicatorCalc:
                            # Mock indicator calculator
                            mock_calc = Mock()
                            mock_calc.calculate_all.return_value = {"rsi": 28.5, "macd": 0.3}
                            MockIndicatorCalc.return_value = mock_calc
                            
                            # Process candle
                            await engine._process_candle(
                                db_session,
                                "session-123",
                                session_state,
                                mock_candle,
                                email_notifications=False
                            )
                            
                            # Verify AI decision was requested
                            ai_trader.get_decision.assert_called_once()
                            
                            # Verify position was opened
                            position_manager.open_position.assert_called_once()
                            
                            # Verify events were broadcast
                            engine._broadcast_candle.assert_called_once()
                            engine._broadcast_ai_thinking.assert_called_once()
                            engine._broadcast_ai_decision.assert_called_once()
                            engine._broadcast_stats_update.assert_called_once()
                            
                            # Verify AI thought was stored
                            assert len(session_state.ai_thoughts) == 1
                            assert session_state.ai_thoughts[0]["decision"] == "LONG"


@pytest.mark.asyncio
async def test_email_notifications(db_session, websocket_manager, mock_agent):
    """Test email notification methods (mocked)."""
    async def mock_session_factory():
        yield db_session
    
    engine = ForwardEngine(mock_session_factory, websocket_manager)
    
    # Create session state
    session_state = SessionState(
        session_id="session-123",
        agent=mock_agent,
        asset="BTC/USDT",
        timeframe="1h",
        position_manager=Mock(),
        ai_trader=Mock()
    )
    
    # Test position opened notification
    position = Mock(
        action="long",
        entry_price=50000.0
    )
    
    # Should not raise exception
    await engine._send_position_opened_notification(session_state, position)
    
    # Test position closed notification
    trade = Mock(
        pnl=500.0,
        reason="take_profit"
    )
    
    # Should not raise exception
    await engine._send_position_closed_notification(session_state, trade)
    
    # Test auto-stop notification
    session_state.position_manager.get_stats.return_value = {
        "total_pnl_pct": -5.5
    }
    
    # Should not raise exception
    await engine._send_auto_stop_notification(session_state)


@pytest.mark.asyncio
async def test_result_generation(db_session, websocket_manager, mock_agent):
    """Test result generation on completion."""
    async def mock_session_factory():
        yield db_session
    
    engine = ForwardEngine(mock_session_factory, websocket_manager)
    
    # Create session state
    position_manager = Mock()
    position_manager.get_stats.return_value = {
        "current_equity": 11500.0,
        "equity_change_pct": 15.0,
        "total_trades": 10,
        "win_rate": 70.0,
        "total_pnl": 1500.0,
        "total_pnl_pct": 15.0
    }
    
    session_state = SessionState(
        session_id="session-123",
        agent=mock_agent,
        asset="BTC/USDT",
        timeframe="1h",
        position_manager=position_manager,
        ai_trader=Mock()
    )
    session_state.ai_thoughts = [
        {
            "candle_number": 0,
            "timestamp": datetime.utcnow(),
            "candle_data": {},
            "indicator_values": {},
            "reasoning": "Test reasoning",
            "decision": "LONG"
        }
    ]
    
    # Mock database operations
    with patch.object(engine, '_update_session_status', new=AsyncMock()):
        with patch.object(engine, '_update_session_completed_at', new=AsyncMock()):
            with patch.object(engine, '_update_session_final_stats', new=AsyncMock()):
                with patch.object(engine, '_save_ai_thoughts', new=AsyncMock()):
                    # Complete forward test
                    result_id = await engine._complete_forward_test(
                        db_session,
                        "session-123",
                        session_state,
                        force_stop=False,
                        auto_stop=False
                    )
                    
                    # Verify result was generated
                    assert result_id is not None
                    
                    # Verify database updates were called
                    engine._update_session_status.assert_called_with(db_session, "session-123", "completed")
                    engine._update_session_final_stats.assert_called_once()
                    engine._save_ai_thoughts.assert_called_once()
                    
                    # Verify WebSocket event was broadcast
                    websocket_manager.broadcast_to_session.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
