"""
Integration tests for Backtest Engine.

Tests:
- Complete backtest flow with mock data
- Pause/resume functionality
- Stop functionality
- Result generation
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from services.trading.backtest_engine import BacktestEngine, SessionState
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
def mock_candles():
    """Create mock historical candles."""
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    candles = []
    
    # Create 100 candles with realistic price movement
    base_price = 50000.0
    for i in range(100):
        # Simple price movement simulation
        price_change = (i % 10 - 5) * 100  # Oscillate between -500 and +500
        close_price = base_price + price_change
        
        candle = Candle(
            timestamp=base_time + timedelta(hours=i),
            open=close_price - 50,
            high=close_price + 100,
            low=close_price - 100,
            close=close_price,
            volume=1000000.0
        )
        candles.append(candle)
    
    return candles


@pytest.mark.asyncio
async def test_backtest_engine_initialization(db_session, websocket_manager):
    """Test backtest engine initialization."""
    engine = BacktestEngine(db_session, websocket_manager)
    
    assert engine.db == db_session
    assert engine.websocket_manager == websocket_manager
    assert isinstance(engine.active_sessions, dict)
    assert len(engine.active_sessions) == 0


@pytest.mark.asyncio
async def test_validate_parameters(db_session, websocket_manager):
    """Test parameter validation."""
    engine = BacktestEngine(db_session, websocket_manager)
    
    # Valid parameters should not raise
    engine._validate_parameters(
        asset="BTC/USDT",
        timeframe="1h",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 31),
        starting_capital=10000.0
    )
    
    # Invalid asset
    with pytest.raises(ValidationError, match="Unsupported asset"):
        engine._validate_parameters(
            asset="INVALID/USDT",
            timeframe="1h",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            starting_capital=10000.0
        )
    
    # Invalid timeframe
    with pytest.raises(ValidationError, match="Unsupported timeframe"):
        engine._validate_parameters(
            asset="BTC/USDT",
            timeframe="5m",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            starting_capital=10000.0
        )
    
    # Invalid date range
    with pytest.raises(ValidationError, match="must be before"):
        engine._validate_parameters(
            asset="BTC/USDT",
            timeframe="1h",
            start_date=datetime(2024, 1, 31),
            end_date=datetime(2024, 1, 1),
            starting_capital=10000.0
        )
    
    # Invalid starting capital
    with pytest.raises(ValidationError, match="must be positive"):
        engine._validate_parameters(
            asset="BTC/USDT",
            timeframe="1h",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            starting_capital=-1000.0
        )


@pytest.mark.asyncio
async def test_start_backtest_with_mock_data(
    db_session,
    websocket_manager,
    mock_agent,
    mock_candles
):
    """Test starting a backtest with mock data."""
    engine = BacktestEngine(db_session, websocket_manager)
    
    # Mock database operations
    with patch.object(engine, '_update_session_status', new=AsyncMock()):
        with patch.object(engine, '_update_session_total_candles', new=AsyncMock()):
            with patch.object(engine, '_update_session_started_at', new=AsyncMock()):
                with patch.object(engine, '_broadcast_session_initialized', new=AsyncMock()):
                    with patch.object(engine.market_data_service, 'get_historical_data', new=AsyncMock(return_value=mock_candles)):
                        with patch('core.encryption.decrypt_api_key', return_value="test_api_key"):
                            with patch('services.trading.backtest_engine.asyncio.create_task'):
                                # Start backtest
                                await engine.start_backtest(
                                    session_id="session-123",
                                    agent=mock_agent,
                                    asset="BTC/USDT",
                                    timeframe="1h",
                                    start_date=datetime(2024, 1, 1),
                                    end_date=datetime(2024, 1, 31),
                                    starting_capital=10000.0,
                                    safety_mode=True
                                )
                                
                                # Verify session state was created
                                assert "session-123" in engine.active_sessions
                                session_state = engine.active_sessions["session-123"]
                                
                                assert session_state.session_id == "session-123"
                                assert session_state.agent == mock_agent
                                assert len(session_state.candles) == 100
                                assert session_state.current_index == 0
                                assert session_state.position_manager is not None
                                assert session_state.indicator_calculator is not None
                                assert session_state.ai_trader is not None


@pytest.mark.asyncio
async def test_pause_resume_backtest(db_session, websocket_manager, mock_agent, mock_candles):
    """Test pause and resume functionality."""
    engine = BacktestEngine(db_session, websocket_manager)
    
    # Create a session state
    session_state = SessionState(
        session_id="session-123",
        agent=mock_agent,
        candles=mock_candles,
        current_index=0,
        position_manager=Mock(),
        indicator_calculator=Mock(),
        ai_trader=Mock()
    )
    engine.active_sessions["session-123"] = session_state
    
    # Mock database operations and prevent _process_backtest from being called
    with patch.object(engine, '_update_session_status', new=AsyncMock()):
        with patch.object(engine, '_update_session_paused_at', new=AsyncMock()):
            with patch.object(engine, '_process_backtest', new=AsyncMock()):
                # Test pause
                await engine.pause_backtest("session-123")
                
                assert session_state.is_paused is True
                assert not session_state.pause_event.is_set()
                
                # Verify WebSocket event was broadcast
                websocket_manager.broadcast_to_session.assert_called()
                
                # Test resume
                await engine.resume_backtest("session-123")
                
                assert session_state.is_paused is False
                assert session_state.pause_event.is_set()


@pytest.mark.asyncio
async def test_stop_backtest(db_session, websocket_manager, mock_agent, mock_candles):
    """Test stop functionality."""
    engine = BacktestEngine(db_session, websocket_manager)
    
    # Create a session state with an open position
    position_manager = Mock()
    position_manager.has_open_position.return_value = True
    position_manager.close_position = AsyncMock(return_value=Mock(
        action="long",
        entry_price=50000.0,
        exit_price=51000.0,
        pnl=1000.0,
        pnl_pct=2.0,
        reason="manual"
    ))
    position_manager.get_stats.return_value = {
        "current_equity": 11000.0,
        "equity_change_pct": 10.0,
        "total_trades": 5,
        "win_rate": 60.0,
        "total_pnl": 1000.0,
        "total_pnl_pct": 10.0
    }
    
    session_state = SessionState(
        session_id="session-123",
        agent=mock_agent,
        candles=mock_candles,
        current_index=50,
        position_manager=position_manager,
        indicator_calculator=Mock(),
        ai_trader=Mock()
    )
    engine.active_sessions["session-123"] = session_state
    
    # Mock database operations and methods
    with patch.object(engine, '_update_session_status', new=AsyncMock()):
        with patch.object(engine, '_update_session_completed_at', new=AsyncMock()):
            with patch.object(engine, '_update_session_final_stats', new=AsyncMock()):
                with patch.object(engine, '_save_ai_thoughts', new=AsyncMock()):
                    with patch.object(engine, '_handle_position_closed', new=AsyncMock()):
                        # Stop backtest
                        result_id = await engine.stop_backtest("session-123", close_position=True)
                        
                        # Verify stop flag was set
                        assert session_state.is_stopped is True
                        
                        # Verify position was closed
                        position_manager.close_position.assert_called_once()
                        
                        # Verify result was generated
                        assert result_id is not None


@pytest.mark.asyncio
async def test_process_candle_with_position_opening(
    db_session,
    websocket_manager,
    mock_agent,
    mock_candles
):
    """Test candle processing with position opening."""
    engine = BacktestEngine(db_session, websocket_manager)
    
    # Create mocks
    position_manager = Mock()
    position_manager.has_open_position.return_value = False
    position_manager.open_position = AsyncMock(return_value=True)
    position_manager.get_position.return_value = Mock(
        action="long",
        entry_price=50000.0,
        size=0.2,
        leverage=1,
        stop_loss=49000.0,
        take_profit=52000.0
    )
    position_manager.get_total_equity.return_value = 10000.0
    position_manager.get_stats.return_value = {
        "current_equity": 10000.0,
        "total_trades": 0,
        "win_rate": 0.0
    }
    
    indicator_calculator = Mock()
    indicator_calculator.calculate_all.return_value = {
        "rsi": 30.0,
        "macd": 0.5
    }
    
    ai_trader = Mock()
    ai_trader.get_decision = AsyncMock(return_value=Mock(
        action="LONG",
        reasoning="RSI oversold",
        stop_loss_price=49000.0,
        take_profit_price=52000.0,
        size_percentage=0.5,
        leverage=1
    ))
    
    session_state = SessionState(
        session_id="session-123",
        agent=mock_agent,
        candles=mock_candles,
        current_index=0,
        position_manager=position_manager,
        indicator_calculator=indicator_calculator,
        ai_trader=ai_trader
    )
    
    # Mock database and broadcast methods
    with patch.object(engine, '_broadcast_candle', new=AsyncMock()):
        with patch.object(engine, '_broadcast_ai_thinking', new=AsyncMock()):
            with patch.object(engine, '_broadcast_ai_decision', new=AsyncMock()):
                with patch.object(engine, '_broadcast_stats_update', new=AsyncMock()):
                    with patch.object(engine, '_handle_position_opened', new=AsyncMock()):
                        # Process candle
                        await engine._process_candle("session-123", session_state, mock_candles[0])
                        
                        # Verify indicator calculation was called
                        indicator_calculator.calculate_all.assert_called_once_with(0)
                        
                        # Verify AI decision was requested
                        ai_trader.get_decision.assert_called_once()
                        
                        # Verify position was opened
                        position_manager.open_position.assert_called_once()
                        
                        # Verify events were broadcast
                        engine._broadcast_candle.assert_called_once()
                        engine._broadcast_ai_thinking.assert_called_once()
                        engine._broadcast_ai_decision.assert_called_once()
                        engine._broadcast_stats_update.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
