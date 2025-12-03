import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime
from fastapi.testclient import TestClient
from app import app
from models.arena import TestSession, Trade, AiThought
from models.agent import Agent

@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.asyncio
async def test_list_results(client, mock_auth_dependency, mock_db_session):
    # Mock count query
    mock_db_session.scalar.return_value = 1
    
    # Mock sessions query
    mock_session = MagicMock(spec=TestSession)
    mock_session.id = uuid4()
    mock_session.type = "backtest"
    mock_session.agent_id = uuid4()
    mock_session.asset = "BTC/USDT"
    mock_session.created_at = datetime.now()
    mock_session.current_pnl_pct = 10.5
    
    mock_db_session.execute.return_value.scalars.return_value.all.return_value = [mock_session]
    
    # Mock agent query inside loop
    mock_agent = MagicMock(spec=Agent)
    mock_agent.name = "Test Agent"
    # We need to handle multiple execute calls. 
    # The first one is for sessions, subsequent ones for agents.
    # This is tricky with a single mock.
    # Simplified: We can mock side_effect.
    
    async def mock_execute(query):
        mock_result = MagicMock()
        if "FROM test_sessions" in str(query):
            mock_result.scalars.return_value.all.return_value = [mock_session]
        elif "FROM agents" in str(query):
            mock_result.scalar_one_or_none.return_value = mock_agent
        return mock_result
        
    mock_db_session.execute.side_effect = mock_execute
    
    response = client.get("/api/results/")
    
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["agent_name"] == "Test Agent"

@pytest.mark.asyncio
async def test_get_result_stats(client, mock_auth_dependency, mock_db_session):
    # Mock sessions
    s1 = MagicMock(spec=TestSession, type="backtest", current_pnl_pct=10.0)
    s2 = MagicMock(spec=TestSession, type="forward", current_pnl_pct=-5.0)
    
    # Setup mock result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [s1, s2]
    
    # Configure execute to return the mock result when awaited
    mock_db_session.execute.return_value = mock_result
    
    response = client.get("/api/results/stats")
    
    assert response.status_code == 200
    data = response.json()
    assert data["stats"]["total_tests"] == 2
    assert data["stats"]["profitable"] == 1
    assert data["stats"]["by_type"]["backtest"]["count"] == 1

@pytest.mark.asyncio
async def test_get_result_detail(client, mock_auth_dependency, mock_db_session):
    session_id = uuid4()
    
    # Mock session
    mock_session = MagicMock(spec=TestSession)
    mock_session.id = session_id
    mock_session.agent_id = uuid4()
    mock_session.asset = "BTC/USDT"
    mock_session.starting_capital = 10000
    mock_session.current_equity = 11000
    mock_session.current_pnl_pct = 10.0
    mock_session.type = "backtest"
    mock_session.start_date = datetime.now()
    mock_session.end_date = datetime.now()
    
    # Mock agent
    mock_agent = MagicMock(spec=Agent, name="Test Agent", model="gpt-4")
    mock_agent.name = "Test Agent"
    
    # Mock trades
    mock_trade = MagicMock(spec=Trade)
    mock_trade.trade_number = 1
    mock_trade.type = "LONG"
    mock_trade.entry_price = 100.0
    mock_trade.pnl_amount = 100.0
    mock_trade.entry_reasoning = "Test reasoning"
    mock_trade.exit_type = "take_profit"
    
    async def mock_execute(query):
        mock_result = MagicMock()
        q_str = str(query)
        if "FROM test_sessions" in q_str:
            mock_result.scalar_one_or_none.return_value = mock_session
        elif "FROM agents" in q_str:
            mock_result.scalar_one_or_none.return_value = mock_agent
        elif "FROM trades" in q_str:
            mock_result.scalars.return_value.all.return_value = [mock_trade]
        return mock_result
    
    mock_db_session.execute.side_effect = mock_execute
    
    response = client.get(f"/api/results/{session_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["result"]["id"] == str(session_id)
    assert len(data["result"]["trades"]) == 1
