"""
WebSocket Manager Example.

Purpose:
    Demonstrates how to use the WebSocket manager for broadcasting
    events during trading sessions.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from websocket.manager import websocket_manager
from websocket.events import (
    create_session_initialized_event,
    create_candle_event,
    create_ai_thinking_event,
    create_ai_decision_event,
    create_position_opened_event,
    create_stats_update_event,
    create_session_completed_event,
)


async def simulate_backtest_session():
    """
    Simulate a backtest session with WebSocket events.
    
    This example shows how the backtest engine would use the
    WebSocket manager to broadcast events to connected clients.
    """
    session_id = "test-session-123"
    
    print(f"\n{'='*60}")
    print("WebSocket Manager Example - Simulated Backtest")
    print(f"{'='*60}\n")
    
    # Note: In real usage, clients would connect via WebSocket endpoints
    # For this example, we'll just show how to broadcast events
    
    print(f"Session ID: {session_id}")
    print(f"Connected clients: {websocket_manager.get_connection_count(session_id)}")
    print()
    
    # 1. Session initialized
    print("1. Broadcasting session initialized event...")
    init_event = create_session_initialized_event(
        session_id=session_id,
        config={
            "agent_id": "agent-456",
            "asset": "BTC/USDT",
            "timeframe": "1h",
            "starting_capital": 10000.0
        }
    )
    await websocket_manager.broadcast_to_session(session_id, init_event)
    print(f"   Event: {init_event.type}")
    print()
    
    # 2. Process candles
    print("2. Processing candles...")
    for i in range(3):
        candle_event = create_candle_event(
            candle={
                "timestamp": datetime.utcnow().isoformat(),
                "open": 65000 + i * 100,
                "high": 65200 + i * 100,
                "low": 64800 + i * 100,
                "close": 65100 + i * 100,
                "volume": 1000000
            },
            indicators={
                "rsi": 45.5 + i,
                "macd": 120.3,
                "ema_20": 64900
            }
        )
        await websocket_manager.broadcast_to_session(session_id, candle_event)
        print(f"   Candle {i+1}: close=${65100 + i * 100}")
        await asyncio.sleep(0.5)
    print()
    
    # 3. AI thinking (streaming)
    print("3. AI making decision (streaming)...")
    thinking_chunks = [
        "Analyzing market conditions...",
        "RSI is showing oversold conditions.",
        "MACD indicates potential bullish crossover.",
        "Decision: LONG position recommended."
    ]
    for chunk in thinking_chunks:
        thinking_event = create_ai_thinking_event(
            text=chunk,
            is_complete=(chunk == thinking_chunks[-1])
        )
        await websocket_manager.broadcast_to_session(session_id, thinking_event)
        print(f"   {chunk}")
        await asyncio.sleep(0.3)
    print()
    
    # 4. AI decision
    print("4. Broadcasting AI decision...")
    decision_event = create_ai_decision_event({
        "action": "LONG",
        "reasoning": "RSI oversold + MACD bullish crossover",
        "stop_loss_price": 64000,
        "take_profit_price": 68000,
        "size_percentage": 0.5,
        "leverage": 1
    })
    await websocket_manager.broadcast_to_session(session_id, decision_event)
    print(f"   Action: LONG")
    print(f"   Entry: $65100")
    print(f"   Stop Loss: $64000")
    print(f"   Take Profit: $68000")
    print()
    
    # 5. Position opened
    print("5. Broadcasting position opened...")
    position_event = create_position_opened_event({
        "action": "long",
        "entry_price": 65100,
        "size": 0.076,
        "stop_loss": 64000,
        "take_profit": 68000,
        "entry_time": datetime.utcnow().isoformat()
    })
    await websocket_manager.broadcast_to_session(session_id, position_event)
    print(f"   Position opened: 0.076 BTC @ $65100")
    print()
    
    # 6. Stats update
    print("6. Broadcasting stats update...")
    stats_event = create_stats_update_event({
        "equity": 10500.0,
        "unrealized_pnl": 500.0,
        "unrealized_pnl_pct": 5.0,
        "total_trades": 1,
        "win_rate": 100.0
    })
    await websocket_manager.broadcast_to_session(session_id, stats_event)
    print(f"   Equity: $10,500")
    print(f"   Unrealized PnL: +$500 (+5.0%)")
    print()
    
    # 7. Session completed
    print("7. Broadcasting session completed...")
    completed_event = create_session_completed_event(
        result_id="result-789",
        final_stats={
            "total_pnl": 1250.0,
            "total_pnl_pct": 12.5,
            "win_rate": 75.0,
            "total_trades": 8,
            "sharpe_ratio": 1.8
        }
    )
    await websocket_manager.broadcast_to_session(session_id, completed_event)
    print(f"   Result ID: result-789")
    print(f"   Total PnL: +$1,250 (+12.5%)")
    print(f"   Win Rate: 75.0%")
    print(f"   Sharpe Ratio: 1.8")
    print()
    
    print(f"{'='*60}")
    print("Backtest simulation completed!")
    print(f"{'='*60}\n")


async def demonstrate_multi_connection():
    """
    Demonstrate multi-connection support (multi-tab).
    """
    print(f"\n{'='*60}")
    print("Multi-Connection Support Demo")
    print(f"{'='*60}\n")
    
    session_id = "multi-session-456"
    
    print("Simulating multiple frontend connections to same session...")
    print(f"(In real usage, these would be actual WebSocket connections)")
    print()
    
    # Show connection count
    count = websocket_manager.get_connection_count(session_id)
    print(f"Current connections for session '{session_id}': {count}")
    print()
    
    # Broadcast to session (would reach all connected tabs)
    print("Broadcasting event to all connections in session...")
    stats_event = create_stats_update_event({
        "equity": 11000.0,
        "total_trades": 5
    })
    sent_count = await websocket_manager.broadcast_to_session(session_id, stats_event)
    print(f"Event sent to {sent_count} connection(s)")
    print()
    
    print(f"{'='*60}\n")


async def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("ALPHALAB WEBSOCKET MANAGER EXAMPLES")
    print("="*60)
    
    # Run examples
    await simulate_backtest_session()
    await demonstrate_multi_connection()
    
    print("\nNote: This example demonstrates the WebSocket manager API.")
    print("In production, clients connect via WebSocket endpoints:")
    print("  - wss://api.alphalab.io/ws/backtest/{session_id}")
    print("  - wss://api.alphalab.io/ws/forward/{session_id}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
