"""
WebSocket Package.

Purpose:
    WebSocket connection management and real-time event broadcasting
    for backtest and forward test sessions.
"""

from .manager import WebSocketManager, websocket_manager
from .events import (
    Event,
    EventType,
    create_session_initialized_event,
    create_candle_event,
    create_ai_thinking_event,
    create_ai_decision_event,
    create_position_opened_event,
    create_position_closed_event,
    create_stats_update_event,
    create_session_completed_event,
    create_countdown_update_event,
    create_heartbeat_event,
    create_error_event,
)
from .handlers import (
    handle_backtest_websocket,
    handle_forward_websocket,
)

__all__ = [
    # Manager
    "WebSocketManager",
    "websocket_manager",
    
    # Events
    "Event",
    "EventType",
    "create_session_initialized_event",
    "create_candle_event",
    "create_ai_thinking_event",
    "create_ai_decision_event",
    "create_position_opened_event",
    "create_position_closed_event",
    "create_stats_update_event",
    "create_session_completed_event",
    "create_countdown_update_event",
    "create_heartbeat_event",
    "create_error_event",
    
    # Handlers
    "handle_backtest_websocket",
    "handle_forward_websocket",
]
