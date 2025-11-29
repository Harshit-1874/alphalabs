import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app import app
from services.market_data_service import MarketDataService, Candle

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_market_data_service():
    with patch("api.data.MarketDataService") as mock:
        yield mock

@pytest.fixture
def mock_indicator_calculator():
    with patch("api.data.IndicatorCalculator") as mock:
        yield mock

@pytest.mark.asyncio
async def test_get_assets(client, mock_auth_dependency):
    response = client.get("/api/data/assets")
    assert response.status_code == 200
    data = response.json()
    assert "assets" in data
    assert isinstance(data["assets"], list)
    assert "BTC/USDT" in data["assets"]

@pytest.mark.asyncio
async def test_get_timeframes(client, mock_auth_dependency):
    response = client.get("/api/data/timeframes")
    assert response.status_code == 200
    data = response.json()
    assert "timeframes" in data
    assert isinstance(data["timeframes"], list)
    assert "1h" in data["timeframes"]

@pytest.mark.asyncio
async def test_get_candles(client, mock_auth_dependency, mock_market_data_service):
    # Setup mock
    service_instance = mock_market_data_service.return_value
    mock_candles = [
        Candle(
            timestamp=datetime.now(),
            open=100.0,
            high=110.0,
            low=90.0,
            close=105.0,
            volume=1000.0
        )
    ]
    service_instance.get_historical_data = AsyncMock(return_value=mock_candles)
    
    response = client.get("/api/data/candles?asset=BTC/USDT&timeframe=1h&limit=10")
    
    assert response.status_code == 200
    data = response.json()
    assert "candles" in data
    assert len(data["candles"]) == 1
    assert data["candles"][0]["open"] == 100.0

@pytest.mark.asyncio
async def test_calculate_indicators(client, mock_auth_dependency, mock_market_data_service, mock_indicator_calculator):
    # Setup mocks
    service_instance = mock_market_data_service.return_value
    mock_candles = [
        Candle(
            timestamp=datetime.now(),
            open=100.0,
            high=110.0,
            low=90.0,
            close=105.0,
            volume=1000.0
        )
    ] * 20 # Need enough candles
    service_instance.get_historical_data = AsyncMock(return_value=mock_candles)
    
    calc_instance = mock_indicator_calculator.return_value
    calc_instance.calculate_all.return_value = {"RSI": 50.0, "SMA_20": 100.0}
    
    response = client.get("/api/data/indicators?asset=BTC/USDT&timeframe=1h&indicators=RSI&indicators=SMA_20&limit=10")
    
    assert response.status_code == 200
    data = response.json()
    assert "indicators" in data
    assert "RSI" in data["indicators"]
    assert "SMA_20" in data["indicators"]
    assert "timestamps" in data
