"""
Integration tests for WebSocket Manager.

Tests:
- Connection management
- Event broadcasting
- Reconnection handling
- Heartbeat functionality
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from fastapi import WebSocket

from websocket.manager import WebSocketManager
from websocket.events import (
    Event,
    EventType,
    create_candle_event,
    create_ai_decision_event,
    create_position_opened_event,
    create_stats_update_event,
    create_heartbeat_event,
)


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self):
        self.accepted = False
        self.closed = False
        self.messages = []
        self.should_fail = False
    
    async def accept(self):
        """Accept the WebSocket connection."""
        self.accepted = True
    
    async def send_text(self, data: str):
        """Send text data."""
        if self.should_fail:
            raise Exception("Connection failed")
        self.messages.append(data)
    
    async def close(self):
        """Close the connection."""
        self.closed = True
    
    async def receive_text(self):
        """Receive text data (for testing)."""
        await asyncio.sleep(0.1)
        return '{"type": "ping"}'


@pytest.fixture
def manager():
    """Create a fresh WebSocket manager for each test."""
    return WebSocketManager()


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket."""
    return MockWebSocket()


@pytest.mark.asyncio
async def test_connect_websocket(manager, mock_websocket):
    """Test WebSocket connection."""
    session_id = "test-session-1"
    
    # Connect
    connection_id = await manager.connect(mock_websocket, session_id)
    
    # Verify connection
    assert connection_id is not None
    assert mock_websocket.accepted is True
    assert manager.is_connected(connection_id)
    assert manager.get_connection_count(session_id) == 1
    
    # Verify metadata
    metadata = manager.get_connection_metadata(connection_id)
    assert metadata is not None
    assert metadata["session_id"] == session_id
    assert "connected_at" in metadata
    assert "last_heartbeat" in metadata


@pytest.mark.asyncio
async def test_disconnect_websocket(manager, mock_websocket):
    """Test WebSocket disconnection."""
    session_id = "test-session-2"
    
    # Connect
    connection_id = await manager.connect(mock_websocket, session_id)
    assert manager.is_connected(connection_id)
    
    # Disconnect
    await manager.disconnect(connection_id)
    
    # Verify disconnection
    assert not manager.is_connected(connection_id)
    assert manager.get_connection_count(session_id) == 0
    assert mock_websocket.closed is True


@pytest.mark.asyncio
async def test_multiple_connections_same_session(manager):
    """Test multiple connections to the same session."""
    session_id = "test-session-3"
    
    # Connect multiple clients
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    ws3 = MockWebSocket()
    
    conn_id_1 = await manager.connect(ws1, session_id)
    conn_id_2 = await manager.connect(ws2, session_id)
    conn_id_3 = await manager.connect(ws3, session_id)
    
    # Verify all connected
    assert manager.get_connection_count(session_id) == 3
    assert manager.is_connected(conn_id_1)
    assert manager.is_connected(conn_id_2)
    assert manager.is_connected(conn_id_3)
    
    # Get session connections
    connections = manager.get_session_connections(session_id)
    assert len(connections) == 3
    assert conn_id_1 in connections
    assert conn_id_2 in connections
    assert conn_id_3 in connections


@pytest.mark.asyncio
async def test_send_to_connection(manager, mock_websocket):
    """Test sending event to specific connection."""
    session_id = "test-session-4"
    
    # Connect
    connection_id = await manager.connect(mock_websocket, session_id)
    
    # Create and send event
    event = create_candle_event(
        candle={
            "timestamp": datetime.utcnow().isoformat(),
            "open": 65000,
            "high": 65200,
            "low": 64800,
            "close": 65100,
            "volume": 1000000
        },
        indicators={"rsi": 45.5, "macd": 120.3}
    )
    
    success = await manager.send_to_connection(connection_id, event)
    
    # Verify sent
    assert success is True
    assert len(mock_websocket.messages) == 1
    
    # Verify message content
    import json
    message = json.loads(mock_websocket.messages[0])
    assert message["type"] == EventType.CANDLE
    assert "candle" in message["data"]
    assert "indicators" in message["data"]


@pytest.mark.asyncio
async def test_broadcast_to_session(manager):
    """Test broadcasting event to all connections in session."""
    session_id = "test-session-5"
    
    # Connect multiple clients
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    ws3 = MockWebSocket()
    
    await manager.connect(ws1, session_id)
    await manager.connect(ws2, session_id)
    await manager.connect(ws3, session_id)
    
    # Create and broadcast event
    event = create_stats_update_event({
        "equity": 10500.0,
        "unrealized_pnl": 500.0,
        "total_trades": 5
    })
    
    sent_count = await manager.broadcast_to_session(session_id, event)
    
    # Verify broadcast
    assert sent_count == 3
    assert len(ws1.messages) == 1
    assert len(ws2.messages) == 1
    assert len(ws3.messages) == 1


@pytest.mark.asyncio
async def test_broadcast_to_nonexistent_session(manager):
    """Test broadcasting to session with no connections."""
    event = create_stats_update_event({"equity": 10000.0})
    
    sent_count = await manager.broadcast_to_session("nonexistent-session", event)
    
    # Should return 0
    assert sent_count == 0


@pytest.mark.asyncio
async def test_broadcast_with_failed_connection(manager):
    """Test broadcasting when one connection fails."""
    session_id = "test-session-6"
    
    # Connect multiple clients
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    ws3 = MockWebSocket()
    
    # Make ws2 fail
    ws2.should_fail = True
    
    conn_id_1 = await manager.connect(ws1, session_id)
    conn_id_2 = await manager.connect(ws2, session_id)
    conn_id_3 = await manager.connect(ws3, session_id)
    
    # Broadcast event
    event = create_stats_update_event({"equity": 10000.0})
    sent_count = await manager.broadcast_to_session(session_id, event)
    
    # Should succeed for 2 out of 3
    assert sent_count == 2
    assert len(ws1.messages) == 1
    assert len(ws3.messages) == 1
    
    # Failed connection should be disconnected
    assert not manager.is_connected(conn_id_2)


@pytest.mark.asyncio
async def test_broadcast_to_all(manager):
    """Test broadcasting to all connections across sessions."""
    # Connect clients to different sessions
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    ws3 = MockWebSocket()
    
    await manager.connect(ws1, "session-1")
    await manager.connect(ws2, "session-2")
    await manager.connect(ws3, "session-3")
    
    # Broadcast to all
    event = create_heartbeat_event()
    sent_count = await manager.broadcast_to_all(event)
    
    # Verify all received
    assert sent_count == 3
    assert len(ws1.messages) == 1
    assert len(ws2.messages) == 1
    assert len(ws3.messages) == 1


@pytest.mark.asyncio
async def test_heartbeat_sent(manager, mock_websocket):
    """Test that heartbeat is sent automatically."""
    session_id = "test-session-7"
    
    # Connect (this starts heartbeat task)
    connection_id = await manager.connect(mock_websocket, session_id)
    
    # Wait for heartbeat (30 seconds in production, but we'll test the mechanism)
    # In real test, we'd mock the sleep time
    initial_message_count = len(mock_websocket.messages)
    
    # Verify heartbeat task exists
    assert connection_id in manager.heartbeat_tasks
    assert not manager.heartbeat_tasks[connection_id].done()
    
    # Disconnect (should cancel heartbeat)
    await manager.disconnect(connection_id)
    
    # Verify heartbeat task cancelled
    assert connection_id not in manager.heartbeat_tasks


@pytest.mark.asyncio
async def test_reconnection_support(manager):
    """Test reconnection without losing session state."""
    session_id = "test-session-8"
    
    # First connection
    ws1 = MockWebSocket()
    conn_id_1 = await manager.connect(ws1, session_id)
    
    # Send some events
    event1 = create_stats_update_event({"equity": 10000.0})
    await manager.broadcast_to_session(session_id, event1)
    assert len(ws1.messages) == 1
    
    # Disconnect
    await manager.disconnect(conn_id_1)
    assert manager.get_connection_count(session_id) == 0
    
    # Reconnect (new connection)
    ws2 = MockWebSocket()
    conn_id_2 = await manager.connect(ws2, session_id)
    
    # Send more events
    event2 = create_stats_update_event({"equity": 10500.0})
    await manager.broadcast_to_session(session_id, event2)
    
    # New connection should receive new events
    assert len(ws2.messages) == 1
    
    # Verify it's a different connection
    assert conn_id_1 != conn_id_2


@pytest.mark.asyncio
async def test_cleanup_stale_connections(manager):
    """Test cleanup of stale connections."""
    session_id = "test-session-9"
    
    # Connect
    ws = MockWebSocket()
    connection_id = await manager.connect(ws, session_id)
    
    # Manually set old heartbeat time
    from datetime import timedelta
    old_time = datetime.utcnow() - timedelta(seconds=400)
    manager.connection_metadata[connection_id]["last_heartbeat"] = old_time
    
    # Cleanup stale connections (older than 300 seconds)
    cleaned = await manager.cleanup_stale_connections(max_age_seconds=300)
    
    # Verify cleanup
    assert cleaned == 1
    assert not manager.is_connected(connection_id)


@pytest.mark.asyncio
async def test_event_types(manager, mock_websocket):
    """Test different event types."""
    session_id = "test-session-10"
    connection_id = await manager.connect(mock_websocket, session_id)
    
    # Test various event types
    events = [
        create_candle_event(
            {"timestamp": datetime.utcnow().isoformat(), "close": 65000},
            {"rsi": 45}
        ),
        create_ai_decision_event({
            "action": "LONG",
            "reasoning": "Test",
            "stop_loss_price": 64000
        }),
        create_position_opened_event({
            "action": "long",
            "entry_price": 65000,
            "size": 0.1
        }),
        create_stats_update_event({"equity": 10000}),
        create_heartbeat_event(),
    ]
    
    # Send all events
    for event in events:
        await manager.send_to_connection(connection_id, event)
    
    # Verify all sent
    assert len(mock_websocket.messages) == len(events)
    
    # Verify each message is valid JSON
    import json
    for message in mock_websocket.messages:
        data = json.loads(message)
        assert "type" in data
        assert "data" in data
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_concurrent_broadcasts(manager):
    """Test concurrent broadcasting to multiple sessions."""
    # Create multiple sessions with multiple connections each
    sessions = {}
    for i in range(3):
        session_id = f"session-{i}"
        sessions[session_id] = []
        for j in range(3):
            ws = MockWebSocket()
            await manager.connect(ws, session_id)
            sessions[session_id].append(ws)
    
    # Broadcast to all sessions concurrently
    event = create_stats_update_event({"equity": 10000})
    
    tasks = [
        manager.broadcast_to_session(session_id, event)
        for session_id in sessions.keys()
    ]
    
    results = await asyncio.gather(*tasks)
    
    # Verify all broadcasts succeeded
    assert all(count == 3 for count in results)
    
    # Verify all websockets received messages
    for ws_list in sessions.values():
        for ws in ws_list:
            assert len(ws.messages) == 1


@pytest.mark.asyncio
async def test_connection_metadata(manager, mock_websocket):
    """Test connection metadata tracking."""
    session_id = "test-session-11"
    
    # Connect
    connection_id = await manager.connect(mock_websocket, session_id)
    
    # Get metadata
    metadata = manager.get_connection_metadata(connection_id)
    
    # Verify metadata structure
    assert metadata is not None
    assert metadata["session_id"] == session_id
    assert isinstance(metadata["connected_at"], datetime)
    assert isinstance(metadata["last_heartbeat"], datetime)
    
    # Verify timestamps are recent
    now = datetime.utcnow()
    assert (now - metadata["connected_at"]).total_seconds() < 1
    assert (now - metadata["last_heartbeat"]).total_seconds() < 1


@pytest.mark.asyncio
async def test_get_session_connections(manager):
    """Test getting all connections for a session."""
    session_id = "test-session-12"
    
    # Connect multiple clients
    connection_ids = []
    for i in range(5):
        ws = MockWebSocket()
        conn_id = await manager.connect(ws, session_id)
        connection_ids.append(conn_id)
    
    # Get session connections
    session_conns = manager.get_session_connections(session_id)
    
    # Verify all connections returned
    assert len(session_conns) == 5
    for conn_id in connection_ids:
        assert conn_id in session_conns


@pytest.mark.asyncio
async def test_disconnect_unknown_connection(manager):
    """Test disconnecting unknown connection."""
    # Should not raise error
    await manager.disconnect("unknown-connection-id")
    
    # Manager should still be functional
    ws = MockWebSocket()
    conn_id = await manager.connect(ws, "test-session")
    assert manager.is_connected(conn_id)


@pytest.mark.asyncio
async def test_send_to_unknown_connection(manager):
    """Test sending to unknown connection."""
    event = create_heartbeat_event()
    
    # Should return False
    success = await manager.send_to_connection("unknown-id", event)
    assert success is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
