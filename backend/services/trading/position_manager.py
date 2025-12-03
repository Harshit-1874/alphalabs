"""
Position Manager for AlphaLab Trading Engine

Manages trading positions, calculates PnL, enforces risk limits,
and handles stop-loss/take-profit logic.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal


@dataclass
class Position:
    """Represents an open trading position"""
    action: str  # "long" or "short"
    entry_price: float
    size: float  # Position size in base currency
    stop_loss: Optional[float]
    take_profit: Optional[float]
    entry_time: datetime
    leverage: int = 1
    unrealized_pnl: float = 0.0


@dataclass
class Trade:
    """Represents a closed trade with complete information"""
    action: str  # "long" or "short"
    entry_price: float
    exit_price: float
    size: float
    pnl: float  # Absolute PnL
    pnl_pct: float  # Percentage PnL
    entry_time: datetime
    exit_time: datetime
    reason: str  # "stop_loss", "take_profit", "ai_decision", "manual"
    leverage: int = 1


class PositionManager:
    """
    Manages trading positions for backtests and forward tests.
    
    Handles:
    - Position opening with risk validation
    - Position updates and PnL tracking
    - Stop-loss and take-profit execution
    - Equity tracking and statistics
    """
    
    def __init__(self, starting_capital: float, safety_mode: bool = False):
        """
        Initialize Position Manager
        
        Args:
            starting_capital: Initial capital amount
            safety_mode: If True, enforces -2% stop loss to prevent liquidation
        """
        self.starting_capital = starting_capital
        self.equity = starting_capital
        self.safety_mode = safety_mode
        self.position: Optional[Position] = None
        self.closed_trades: List[Trade] = []
        
    def has_open_position(self) -> bool:
        """Check if there is an open position"""
        return self.position is not None
    
    def get_position(self) -> Optional[Position]:
        """Get the current open position"""
        return self.position
    
    def get_equity(self) -> float:
        """Get current equity including unrealized PnL"""
        return self.equity
    
    def get_closed_trades(self) -> List[Trade]:
        """Get list of all closed trades"""
        return self.closed_trades

    async def open_position(
        self,
        action: str,
        entry_price: float,
        size_percentage: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        leverage: int = 1
    ) -> bool:
        """
        Open a new trading position with risk validation
        
        Args:
            action: "long" or "short"
            entry_price: Entry price for the position
            size_percentage: Percentage of capital to use (0.0 to 1.0)
            stop_loss: Stop loss price (absolute price level)
            take_profit: Take profit price (absolute price level)
            leverage: Leverage multiplier (1 to 5)
            
        Returns:
            True if position opened successfully, False otherwise
        """
        # Validate no existing position
        if self.position is not None:
            return False
        
        # Validate action
        if action not in ["long", "short"]:
            return False
        
        # Validate size_percentage
        if size_percentage <= 0 or size_percentage > 1.0:
            return False
        
        # Validate leverage
        if leverage < 1 or leverage > 5:
            return False
        
        # Calculate position size based on size_percentage and leverage
        capital_to_use = self.equity * size_percentage
        position_size = (capital_to_use * leverage) / entry_price
        
        # Apply safety mode: enforce -2% stop loss to prevent liquidation
        if self.safety_mode:
            if action == "long":
                safety_stop = entry_price * 0.98  # -2% from entry
                if stop_loss is None or stop_loss < safety_stop:
                    stop_loss = safety_stop
            else:  # short
                safety_stop = entry_price * 1.02  # +2% from entry
                if stop_loss is None or stop_loss > safety_stop:
                    stop_loss = safety_stop
        
        # Create position
        self.position = Position(
            action=action,
            entry_price=entry_price,
            size=position_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            entry_time=datetime.utcnow(),
            leverage=leverage,
            unrealized_pnl=0.0
        )
        
        return True
    
    def calculate_position_size(self, entry_price: float, size_percentage: float, leverage: int = 1) -> float:
        """
        Calculate position size based on capital, size percentage, and leverage
        
        Args:
            entry_price: Entry price for the position
            size_percentage: Percentage of capital to use (0.0 to 1.0)
            leverage: Leverage multiplier (1 to 5)
            
        Returns:
            Position size in base currency
        """
        capital_to_use = self.equity * size_percentage
        return (capital_to_use * leverage) / entry_price

    async def update_position(self, candle_high: float, candle_low: float, current_price: float) -> Optional[str]:
        """
        Update position and check for stop-loss/take-profit triggers
        
        Args:
            candle_high: High price of current candle
            candle_low: Low price of current candle
            current_price: Current/close price of candle
            
        Returns:
            Reason for closure if position was closed ("stop_loss" or "take_profit"), None otherwise
        """
        if self.position is None:
            return None
        
        # Update unrealized PnL
        self._update_unrealized_pnl(current_price)
        
        # Check stop-loss and take-profit triggers
        if self.position.action == "long":
            # For long positions: check if low hit stop loss
            if self.position.stop_loss is not None and candle_low <= self.position.stop_loss:
                await self.close_position(self.position.stop_loss, "stop_loss")
                return "stop_loss"
            
            # For long positions: check if high hit take profit
            if self.position.take_profit is not None and candle_high >= self.position.take_profit:
                await self.close_position(self.position.take_profit, "take_profit")
                return "take_profit"
        
        else:  # short position
            # For short positions: check if high hit stop loss
            if self.position.stop_loss is not None and candle_high >= self.position.stop_loss:
                await self.close_position(self.position.stop_loss, "stop_loss")
                return "stop_loss"
            
            # For short positions: check if low hit take profit
            if self.position.take_profit is not None and candle_low <= self.position.take_profit:
                await self.close_position(self.position.take_profit, "take_profit")
                return "take_profit"
        
        return None
    
    def _update_unrealized_pnl(self, current_price: float) -> None:
        """
        Update unrealized PnL for open position
        
        Args:
            current_price: Current market price
        """
        if self.position is None:
            return
        
        if self.position.action == "long":
            # Long: profit when price goes up
            price_change = current_price - self.position.entry_price
            self.position.unrealized_pnl = price_change * self.position.size
        else:  # short
            # Short: profit when price goes down
            price_change = self.position.entry_price - current_price
            self.position.unrealized_pnl = price_change * self.position.size
    
    async def close_position(self, exit_price: float, reason: str) -> Optional[Trade]:
        """
        Close the current position and calculate realized PnL
        
        Args:
            exit_price: Exit price for the position
            reason: Reason for closing ("stop_loss", "take_profit", "ai_decision", "manual")
            
        Returns:
            Trade object with complete trade information, or None if no position open
        """
        if self.position is None:
            return None
        
        # Calculate realized PnL with leverage
        if self.position.action == "long":
            price_change = exit_price - self.position.entry_price
            realized_pnl = price_change * self.position.size
        else:  # short
            price_change = self.position.entry_price - exit_price
            realized_pnl = price_change * self.position.size
        
        # Calculate PnL percentage (based on capital used, not position size)
        capital_used = (self.position.entry_price * self.position.size) / self.position.leverage
        pnl_pct = (realized_pnl / capital_used) * 100 if capital_used > 0 else 0.0
        
        # Update equity
        self.equity += realized_pnl
        
        # Create trade record
        trade = Trade(
            action=self.position.action,
            entry_price=self.position.entry_price,
            exit_price=exit_price,
            size=self.position.size,
            pnl=realized_pnl,
            pnl_pct=pnl_pct,
            entry_time=self.position.entry_time,
            exit_time=datetime.utcnow(),
            reason=reason,
            leverage=self.position.leverage
        )
        
        # Store trade and clear position
        self.closed_trades.append(trade)
        self.position = None
        
        return trade

    def get_total_equity(self) -> float:
        """
        Get total equity including unrealized PnL from open positions
        
        Returns:
            Total equity (realized + unrealized)
        """
        total = self.equity
        if self.position is not None:
            total += self.position.unrealized_pnl
        return total
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Calculate comprehensive trading statistics
        
        Returns:
            Dictionary containing:
            - total_trades: Total number of closed trades
            - winning_trades: Number of profitable trades
            - losing_trades: Number of losing trades
            - win_rate: Percentage of winning trades
            - total_pnl: Total realized PnL
            - total_pnl_pct: Total PnL as percentage of starting capital
            - average_win: Average profit from winning trades
            - average_loss: Average loss from losing trades
            - largest_win: Largest single winning trade
            - largest_loss: Largest single losing trade
            - profit_factor: Ratio of gross profit to gross loss
            - current_equity: Current equity including unrealized PnL
            - equity_change_pct: Percentage change from starting capital
        """
        total_trades = len(self.closed_trades)
        
        if total_trades == 0:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "total_pnl_pct": 0.0,
                "average_win": 0.0,
                "average_loss": 0.0,
                "largest_win": 0.0,
                "largest_loss": 0.0,
                "profit_factor": 0.0,
                "current_equity": self.get_total_equity(),
                "equity_change_pct": 0.0
            }
        
        # Separate winning and losing trades
        winning_trades = [t for t in self.closed_trades if t.pnl > 0]
        losing_trades = [t for t in self.closed_trades if t.pnl <= 0]
        
        # Calculate totals
        total_pnl = sum(t.pnl for t in self.closed_trades)
        gross_profit = sum(t.pnl for t in winning_trades) if winning_trades else 0.0
        gross_loss = abs(sum(t.pnl for t in losing_trades)) if losing_trades else 0.0
        
        # Calculate averages
        average_win = gross_profit / len(winning_trades) if winning_trades else 0.0
        average_loss = gross_loss / len(losing_trades) if losing_trades else 0.0
        
        # Find largest win/loss
        largest_win = max((t.pnl for t in winning_trades), default=0.0)
        largest_loss = min((t.pnl for t in losing_trades), default=0.0)
        
        # Calculate profit factor
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
        
        # Calculate percentages
        win_rate = (len(winning_trades) / total_trades) * 100
        total_pnl_pct = (total_pnl / self.starting_capital) * 100
        current_equity = self.get_total_equity()
        equity_change_pct = ((current_equity - self.starting_capital) / self.starting_capital) * 100
        
        return {
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": round(win_rate, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "average_win": round(average_win, 2),
            "average_loss": round(average_loss, 2),
            "largest_win": round(largest_win, 2),
            "largest_loss": round(largest_loss, 2),
            "profit_factor": round(profit_factor, 2),
            "current_equity": round(current_equity, 2),
            "equity_change_pct": round(equity_change_pct, 2)
        }
    
    def reset(self) -> None:
        """Reset the position manager to initial state"""
        self.equity = self.starting_capital
        self.position = None
        self.closed_trades = []
