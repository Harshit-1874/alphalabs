"""
Example usage of AI Trader service.

This example demonstrates how to use the AITrader class to get
trading decisions from OpenRouter API.
"""
import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from services.ai_trader import AITrader, AIDecision, Candle
from services.trading.position_manager import Position

# Load environment variables
load_dotenv()


async def main():
    """Example usage of AI Trader"""
    
    # Get API key from environment
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("[ERROR] OPENROUTER_API_KEY not found in environment")
        print("[INFO] Please set OPENROUTER_API_KEY environment variable or add it to .env file")
        sys.exit(1)
    
    # Initialize AI Trader
    trader = AITrader(
        api_key=api_key,
        model="anthropic/claude-3.5-sonnet",
        strategy_prompt="""
        You are a momentum trader focusing on RSI and MACD signals.
        
        Strategy:
        - Buy (LONG) when RSI < 30 and MACD shows bullish crossover
        - Sell (SHORT) when RSI > 70 and MACD shows bearish crossover
        - Use 2% stop loss and 4% take profit
        - Position size: 50% of capital
        - No leverage
        """,
        mode="monk"
    )
    
    # Create sample candle data
    candle = Candle(
        timestamp=datetime.utcnow(),
        open=65000.0,
        high=65500.0,
        low=64800.0,
        close=65200.0,
        volume=1000000.0
    )
    
    # Sample indicators (from Indicator Calculator)
    indicators = {
        "rsi_14": 28.5,  # Oversold
        "macd": 150.0,
        "macd_signal": 100.0,  # Bullish crossover
        "macd_histogram": 50.0
    }
    
    # No open position
    position_state = None
    
    # Current equity
    equity = 10000.0
    
    # Get AI decision
    print("Requesting AI trading decision...")
    decision = await trader.get_decision(
        candle=candle,
        indicators=indicators,
        position_state=position_state,
        equity=equity
    )
    
    # Display decision
    print(f"\nAI Decision:")
    print(f"  Action: {decision.action}")
    print(f"  Reasoning: {decision.reasoning}")
    print(f"  Size Percentage: {decision.size_percentage * 100}%")
    print(f"  Leverage: {decision.leverage}x")
    if decision.stop_loss_price:
        print(f"  Stop Loss: ${decision.stop_loss_price:,.2f}")
    if decision.take_profit_price:
        print(f"  Take Profit: ${decision.take_profit_price:,.2f}")
    
    # Example with open position
    print("\n" + "="*60)
    print("Example with open position:")
    print("="*60)
    
    position_state = Position(
        action="long",
        entry_price=65000.0,
        size=0.1,
        stop_loss=63700.0,
        take_profit=67600.0,
        entry_time=datetime.utcnow(),
        leverage=1,
        unrealized_pnl=20.0
    )
    
    decision2 = await trader.get_decision(
        candle=candle,
        indicators=indicators,
        position_state=position_state,
        equity=equity
    )
    
    print(f"\nAI Decision (with position):")
    print(f"  Action: {decision2.action}")
    print(f"  Reasoning: {decision2.reasoning}")


if __name__ == "__main__":
    asyncio.run(main())
