# WebSocket Manager

Real-time WebSocket communication system for AlphaLab trading sessions.

## Overview

The WebSocket Manager provides real-time bidirectional communication between the backend trading engine and frontend clients during backtests and forward tests. It supports multiple connections per session (multi-tab), automatic heartbeats, and event broadcasting.

## Architecture

```
Frontend (Next.js) ←→ WebSocket ←→ Backend (FastAPI)
                                      ↓
                              Trading Engine
                              (broadcasts events)
```

## Components

### 1. WebSocketManager (`manager.py`)

Manages WebSocket connections and event broadcasting.

**Key Features:**
- Connection lifecycle management (connect/disconnect)
- Multi-connection support (multiple tabs per session)
- Event broadcasting (to session or individual connections)
- Automatic heartbeat every 30 seconds
- Stale connection cleanup

**Usage:**
```python
from websocket.manager import websocket_manager

# Connect a client
connection_id = await websocket_manager.connect(websocket, session_id)

# Broadcast event to all clients in session
await websocket_manager.broadcast_to_session(session_id, event)

# Send to specific connection
await websocket_manager.send_to_connection(connection_id, event)

# Disconnect
await websocket_manager.disconnect(connection_id)
```

### 2. Event System (`events.py`)

Defines event types and data structures for WebSocket communication.

**Event Types:**
- `session_initialized` - Test session is ready
- `candle` - New candle processed with indicators
- `ai_thinking` - Streaming AI reasoning text
- `ai_decision` - Final AI decision made
- `position_opened` - Trade opened
- `position_closed` - Trade closed
- `position_updated` - Position PnL updated
- `stats_update` - Updated metrics (PnL, win rate, etc.)
- `session_completed` - Test finished
- `countdown_update` - Forward test countdown (30s intervals)
- `heartbeat` - Connection health check
- `error` - Error occurred

**Usage:**
```python
from websocket.events import (
    create_candle_event,
    create_ai_decision_event,
    create_position_opened_event,
)

# Create events
candle_event = create_candle_event(candle_data, indicators)
decision_event = create_ai_decision_event(decision_data)
position_event = create_position_opened_event(position_data)

# Broadcast to session
await websocket_manager.broadcast_to_session(session_id, candle_event)
```

### 3. Route Handlers (`handlers.py`)

FastAPI WebSocket endpoint handlers.

**Endpoints:**
- `/ws/backtest/{session_id}` - Backtest session WebSocket
- `/ws/forward/{session_id}` - Forward test session WebSocket

**Usage:**
```python
from fastapi import FastAPI, WebSocket
from websocket.handlers import handle_backtest_websocket

app = FastAPI()

@app.websocket("/ws/backtest/{session_id}")
async def backtest_websocket(websocket: WebSocket, session_id: str):
    await handle_backtest_websocket(websocket, session_id)
```

## Event Flow Example

### Backtest Session

```python
# 1. Session initialized
init_event = create_session_initialized_event(session_id, config)
await websocket_manager.broadcast_to_session(session_id, init_event)

# 2. Process each candle
for candle in candles:
    # Calculate indicators
    indicators = indicator_calculator.calculate_all(index)
    
    # Broadcast candle event
    candle_event = create_candle_event(candle, indicators)
    await websocket_manager.broadcast_to_session(session_id, candle_event)
    
    # Get AI decision (with streaming)
    async for chunk in ai_trader.get_decision_stream(...):
        thinking_event = create_ai_thinking_event(chunk)
        await websocket_manager.broadcast_to_session(session_id, thinking_event)
    
    # Broadcast final decision
    decision_event = create_ai_decision_event(decision)
    await websocket_manager.broadcast_to_session(session_id, decision_event)
    
    # If position opened
    if decision.action in ["LONG", "SHORT"]:
        position = position_manager.open_position(...)
        position_event = create_position_opened_event(position)
        await websocket_manager.broadcast_to_session(session_id, position_event)
    
    # Update stats
    stats = position_manager.get_stats()
    stats_event = create_stats_update_event(stats)
    await websocket_manager.broadcast_to_session(session_id, stats_event)

# 3. Session completed
result_id = result_service.create_result(...)
completed_event = create_session_completed_event(result_id, final_stats)
await websocket_manager.broadcast_to_session(session_id, completed_event)
```

### Forward Test Session

```python
# Similar to backtest, but with countdown updates
while running:
    # Wait for next candle
    seconds_remaining = calculate_time_to_next_candle()
    
    # Send countdown every 30 seconds
    if seconds_remaining % 30 == 0:
        countdown_event = create_countdown_update_event(
            seconds_remaining,
            next_candle_time
        )
        await websocket_manager.broadcast_to_session(session_id, countdown_event)
    
    await asyncio.sleep(1)
```

## Multi-Connection Support

The WebSocket Manager supports multiple connections per session, allowing users to:
- Open multiple browser tabs
- View the same session on different devices
- Reconnect without losing test state

**Implementation:**
```python
# Multiple connections to same session
connection_id_1 = await websocket_manager.connect(websocket_1, session_id)
connection_id_2 = await websocket_manager.connect(websocket_2, session_id)

# Broadcast reaches all connections
await websocket_manager.broadcast_to_session(session_id, event)
# Both connection_id_1 and connection_id_2 receive the event
```

## Heartbeat System

Automatic heartbeat messages are sent every 30 seconds to:
- Keep connections alive
- Detect stale connections
- Enable reconnection logic

**Heartbeat Flow:**
1. Connection established → heartbeat task started
2. Every 30 seconds → heartbeat event sent
3. If send fails → connection marked as stale
4. Stale connections cleaned up periodically

**Manual Cleanup:**
```python
# Clean up connections older than 5 minutes
cleaned = await websocket_manager.cleanup_stale_connections(max_age_seconds=300)
print(f"Cleaned up {cleaned} stale connections")
```

## Connection Metadata

Each connection stores metadata:
```python
{
    "session_id": "session-123",
    "connected_at": datetime(2024, 3, 15, 10, 30, 0),
    "last_heartbeat": datetime(2024, 3, 15, 10, 35, 0)
}
```

**Access metadata:**
```python
metadata = websocket_manager.get_connection_metadata(connection_id)
print(f"Connected at: {metadata['connected_at']}")
print(f"Last heartbeat: {metadata['last_heartbeat']}")
```

## Error Handling

**Connection Errors:**
```python
try:
    await websocket_manager.send_to_connection(connection_id, event)
except WebSocketDisconnect:
    # Connection dropped, cleanup handled automatically
    pass
```

**Broadcasting Errors:**
```python
# Broadcast continues even if some connections fail
sent_count = await websocket_manager.broadcast_to_session(session_id, event)
print(f"Event sent to {sent_count} connections")
```

**Error Events:**
```python
# Send error to client
error_event = create_error_event(
    error_code="INVALID_SESSION",
    message="Session not found",
    details={"session_id": session_id}
)
await websocket_manager.send_to_connection(connection_id, error_event)
```

## Testing

Run the example script to see the WebSocket Manager in action:

```bash
python examples/websocket_example.py
```

This demonstrates:
- Event creation and broadcasting
- Multi-connection support
- Complete backtest session flow

## Integration with Trading Engine

The WebSocket Manager is designed to be used by:
- **Backtest Engine** - Broadcasts candle, decision, and position events
- **Forward Engine** - Broadcasts countdown and live trading events
- **Result Service** - Broadcasts completion events
- **API Routes** - Handles WebSocket endpoint connections

## Performance Considerations

- **Concurrent Broadcasting**: Events are sent to all connections concurrently using `asyncio.gather`
- **Connection Limits**: Configurable max connections (default: 100)
- **Memory Management**: Stale connections cleaned up automatically
- **Heartbeat Overhead**: Minimal (one small message per connection every 30s)

## Future Enhancements

- [ ] Message compression for large payloads
- [ ] Client-to-server commands (pause/resume/stop)
- [ ] Connection authentication and authorization
- [ ] Rate limiting per connection
- [ ] Message queuing for offline clients
- [ ] WebSocket metrics and monitoring

## Related Documentation

- [Design Document](../.kiro/specs/backend-implementation/design.md)
- [Requirements](../.kiro/specs/backend-implementation/requirements.md)
- [Backtest Engine](../services/trading/README.md)
- [API Routes](../routes/README.md)
