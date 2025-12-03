"""
Live test of AI Trader service with real OpenRouter API.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from dotenv import load_dotenv

# Load environment variables from backend/.env
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path)

from services.ai_trader import AITrader, Candle


async def test_ai_trader():
    """Test AI Trader with real OpenRouter API"""

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not found in .env file")
        return

    print("=" * 70)
    print("AI TRADER SERVICE - LIVE TEST")
    print("=" * 70)
    print(f"\n✓ API Key found: {api_key[:20]}...")

    # Initialize AI Trader
    print("\n📊 Initializing AI Trader...")
    trader = AITrader(
        api_key=api_key,
        model="deepseek/deepseek-chat",  # Free model
        strategy_prompt="""
You are a momentum trader focusing on RSI and MACD signals.

Strategy Rules:
- Buy (LONG) when RSI < 30 (oversold) and MACD shows bullish crossover
- Sell (SHORT) when RSI > 70 (overbought) and MACD shows bearish crossover
- Use 2% stop loss and 4% take profit
- Position size: 50% of capital
- No leverage (leverage = 1)
        """,
        mode="monk",
    )
    print("✓ AI Trader initialized")

    # Create sample market data (Bitcoin at $65,000)
    print("\n📈 Creating sample market data...")
    candle = Candle(
        timestamp=datetime.utcnow(),
        open=65000.0,
        high=65500.0,
        low=64800.0,
        close=65200.0,
        volume=1000000.0,
    )

    # Sample indicators showing oversold conditions
    indicators = {
        "rsi_14": 28.5,  # Oversold
        "macd": 150.0,
        "macd_signal": 100.0,  # Bullish crossover (MACD > signal)
        "macd_histogram": 50.0,
        "ema_20": 64500.0,
        "sma_50": 64000.0,
    }

    print(f"  Current Price: ${candle.close:,.2f}")
    print(f"  RSI: {indicators['rsi_14']}")
    print(f"  MACD: {indicators['macd']}")
    print(f"  MACD Signal: {indicators['macd_signal']}")

    # No open position
    position_state = None
    equity = 10000.0

    print(f"\n💰 Current Equity: ${equity:,.2f}")
    print("📍 Position: None (no open position)")

    # Get AI decision
    print("\n🤖 Requesting AI trading decision...")
    print("⏳ This may take a few seconds...")

    decision = await trader.get_decision(
        candle=candle,
        indicators=indicators,
        position_state=position_state,
        equity=equity,
    )

    # Display decision
    print("\n" + "=" * 70)
    print("AI TRADING DECISION")
    print("=" * 70)
    print(f"\n🎯 Action: {decision.action}")
    print(f"\n💭 Reasoning:")
    print(f"   {decision.reasoning}")
    print(f"\n📊 Order Parameters:")
    print(f"   Size: {decision.size_percentage * 100}% of capital")
    print(f"   Leverage: {decision.leverage}x")

    if decision.stop_loss_price:
        print(f"   Stop Loss: ${decision.stop_loss_price:,.2f}")
        sl_pct = ((decision.stop_loss_price - candle.close) / candle.close) * 100
        print(f"              ({sl_pct:+.2f}% from current price)")
    else:
        print(f"   Stop Loss: Not set")

    if decision.take_profit_price:
        print(f"   Take Profit: ${decision.take_profit_price:,.2f}")
        tp_pct = ((decision.take_profit_price - candle.close) / candle.close) * 100
        print(f"                ({tp_pct:+.2f}% from current price)")
    else:
        print(f"   Take Profit: Not set")

    # Calculate position details if action is LONG or SHORT
    if decision.action in ["LONG", "SHORT"]:
        capital_to_use = equity * decision.size_percentage
        position_size = (capital_to_use * decision.leverage) / candle.close

        print(f"\n💵 Position Details:")
        print(f"   Capital to use: ${capital_to_use:,.2f}")
        print(f"   Position size: {position_size:.6f} BTC")
        print(f"   Position value: ${position_size * candle.close:,.2f}")

    print("\n" + "=" * 70)
    print("✅ Test completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_ai_trader())
