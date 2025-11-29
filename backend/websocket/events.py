"""
WebSocket Event Definitions.

Purpose:
    Define event types and data structures for WebSocket communication
    between backend and frontend during trading sessions.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, Optional
import json


@dataclass
class Event:
    """
    WebSocket event sent from backend to frontend.
    
    Attributes:
        type: Event type identifier
        data: Event payload data
        timestamp: When the event was created
    """
    type: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_json(self) -> str:
        """
        Convert event to JSON string for transmission.
        
        Returns:
            JSON string representation
        """
        event_dict = {
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }
        return json.dumps(event_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert event to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }


# Event Type Constants
class EventType:
    """Constants for event types sent to frontend."""
    
    # Session lifecycle
    SESSION_INITIALIZED = "session_initialized"
    SESSION_COMPLETED = "session_completed"
    SESSION_PAUSED = "session_paused"
    SESSION_RESUMED = "session_resumed"
    
    # Market data
    CANDLE = "candle"
    
    # AI decision making
    AI_THINKING = "ai_thinking"
    AI_DECISION = "ai_decision"
    
    # Position management
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    POSITION_UPDATED = "position_updated"
    
    # Statistics
    STATS_UPDATE = "stats_update"
    
    # Forward test specific
    COUNTDOWN_UPDATE = "countdown_update"
    
    # Connection health
    HEARTBEAT = "heartbeat"
    
    # Errors
    ERROR = "error"


def create_session_initialized_event(session_id: str, config: Dict[str, Any]) -> Event:
    """Create a session initialized event."""
    return Event(
        type=EventType.SESSION_INITIALIZED,
        data={
            "session_id": session_id,
            "config": config
        }
    )


def create_candle_event(candle: Dict[str, Any], indicators: Dict[str, Any]) -> Event:
    """Create a candle processed event."""
    return Event(
        type=EventType.CANDLE,
        data={
            "candle": candle,
            "indicators": indicators
        }
    )


def create_ai_thinking_event(text: str, is_complete: bool = False) -> Event:
    """Create an AI thinking (streaming) event."""
    return Event(
        type=EventType.AI_THINKING,
        data={
            "text": text,
            "is_complete": is_complete
        }
    )


def create_ai_decision_event(decision: Dict[str, Any]) -> Event:
    """Create an AI decision event."""
    return Event(
        type=EventType.AI_DECISION,
        data=decision
    )


def create_position_opened_event(position: Dict[str, Any]) -> Event:
    """Create a position opened event."""
    return Event(
        type=EventType.POSITION_OPENED,
        data=position
    )


def create_position_closed_event(trade: Dict[str, Any]) -> Event:
    """Create a position closed event."""
    return Event(
        type=EventType.POSITION_CLOSED,
        data=trade
    )


def create_stats_update_event(stats: Dict[str, Any]) -> Event:
    """Create a stats update event."""
    return Event(
        type=EventType.STATS_UPDATE,
        data=stats
    )


def create_session_completed_event(result_id: str, final_stats: Dict[str, Any]) -> Event:
    """Create a session completed event."""
    return Event(
        type=EventType.SESSION_COMPLETED,
        data={
            "result_id": result_id,
            "final_stats": final_stats
        }
    )


def create_countdown_update_event(seconds_remaining: int, next_candle_time: str) -> Event:
    """Create a countdown update event (forward test)."""
    return Event(
        type=EventType.COUNTDOWN_UPDATE,
        data={
            "seconds_remaining": seconds_remaining,
            "next_candle_time": next_candle_time
        }
    )


def create_heartbeat_event() -> Event:
    """Create a heartbeat event."""
    return Event(
        type=EventType.HEARTBEAT,
        data={}
    )


def create_error_event(error_code: str, message: str, details: Optional[Dict] = None) -> Event:
    """Create an error event."""
    return Event(
        type=EventType.ERROR,
        data={
            "error_code": error_code,
            "message": message,
            "details": details or {}
        }
    )
