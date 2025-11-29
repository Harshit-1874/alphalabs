"""
Test AI Trader with an open position scenario.
"""
import asyncio
import sys
import os
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from dotenv import load_dotenv

# Load environment variables from backend/.env
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

from services.ai_trader import AITrader, Candle
from services.trading.position_manager import Position


async def test_with_position():
    """Test AI Trader with an open position"""
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    print("="*70)
    print("AI TRADER - TEST WITH OPEN POSITION")
    print("="*70)
    
    # Initialize AI Trader
    trader = AITrader(
        api_key=api_key,
        model="deepseek/deepseek-chat",
        strategy_prompt="""
You are a momentum trader. When you have an open position:
- CLOSE if indicators turn against you
- HOLD if conditions are still favorable
- Never open a new position while one is already open
        """,
        mode="monk"
    )
    
    # Current market data (price moved up from entry)
    candle = Candle(
        timestamp=datetime.utcnow(),
        open=66000.0,
        high=66500.0,
        low=65800.0,
        close=66200.0,  # Price went up
        volume=1200000.0
    )
    
    # Indicators now showing overbought
    indicators = {
        "rsi_14": 72.0,  # Overbought
        "macd": 100.0,
        "macd_signal": 150.0,  # Bearish crossover (MACD < signal)
        "macd_histogram": -50.0
    }
    
    # Open long position from $65,000
    position = Position(
        action="long",
        entry_price=65000.0,
        size=0.076923,  # ~$5000 worth
        stop_loss=63700.0,
        take_profit=67600.0,
        entry_time=datetime.utcnow(),
        leverage=1,
        unrealized_pnl=92.31  # Profit from price increase
    )
    
    equity = 10092.31  # Original 10k + unrealized profit
    
    print(f"\n📈 Current Market:")
    print(f"   Price: ${candle.close:,.2f}")
    print(f"   RSI: {indicators['rsi_14']} (Overbought)")
    print(f"   MACD: {indicators['macd']} < Signal: {indicators['macd_signal']} (Bearish)")
    
    print(f"\n📍 Open Position:")
    print(f"   Type: {position.action.upper()}")
    print(f"   Entry: ${position.entry_price:,.2f}")
    print(f"   Current: ${candle.close:,.2f}")
    print(f"   Size: {position.size:.6f} BTC")
    print(f"   Unrealized P&L: ${position.unrealized_pnl:,.2f}")
    print(f"   Stop Loss: ${position.stop_loss:,.2f}")
    print(f"   Take Profit: ${position.take_profit:,.2f}")
    
    print(f"\n💰 Current Equity: ${equity:,.2f}")
    
    print("\n🤖 Requesting AI decision...")
    
    decision = await trader.get_decision(
        candle=candle,
        indicators=indicators,
        position_state=position,
        equity=equity
    )
    
    print("\n" + "="*70)
    print("AI DECISION")
    print("="*70)
    print(f"\n🎯 Action: {decision.action}")
    print(f"\n💭 Reasoning:")
    print(f"   {decision.reasoning}")
    
    if decision.action == "CLOSE":
        print(f"\n💵 If closed at current price:")
        realized_pnl = (candle.close - position.entry_price) * position.size
        print(f"   Realized P&L: ${realized_pnl:,.2f}")
        print(f"   Final Equity: ${equity - position.unrealized_pnl + realized_pnl:,.2f}")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    asyncio.run(test_with_position())
