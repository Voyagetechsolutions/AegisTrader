"""
Execution Simulator - Realistic trade execution for backtesting.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from enum import Enum


class TradeStatus(Enum):
    OPEN = "open"
    TP1_HIT = "tp1_hit"
    TP2_HIT = "tp2_hit"
    SL_HIT = "sl_hit"
    CLOSED = "closed"


@dataclass
class Position:
    entry_time: datetime
    entry_price: float
    direction: str  # "long" or "short"
    size: float
    sl: float
    tp1: float
    tp2: float
    status: TradeStatus = TradeStatus.OPEN
    
    # Partial close tracking
    remaining_size: float = None
    tp1_exit_price: float = None
    tp2_exit_price: float = None
    final_exit_price: float = None
    
    # Costs
    entry_spread: float = 0.0
    exit_spread: float = 0.0
    slippage: float = 0.0
    
    def __post_init__(self):
        if self.remaining_size is None:
            self.remaining_size = self.size


class ExecutionSimulator:
    """Simulates realistic trade execution with spreads, slippage, and partial closes."""
    
    def __init__(self, spread_points: float = 3.0, slippage_points: float = 2.0):
        self.spread = spread_points
        self.slippage = slippage_points
        self.positions: List[Position] = []
        
    def open_position(
        self,
        timestamp: datetime,
        direction: str,
        entry: float,
        sl: float,
        tp1: float,
        tp2: float,
        size: float = 1.0
    ) -> Position:
        """Open a new position with realistic entry costs."""
        
        # Apply spread and slippage to entry
        if direction == "long":
            actual_entry = entry + self.spread + self.slippage
        else:
            actual_entry = entry - self.spread - self.slippage
        
        position = Position(
            entry_time=timestamp,
            entry_price=actual_entry,
            direction=direction,
            size=size,
            sl=sl,
            tp1=tp1,
            tp2=tp2,
            entry_spread=self.spread,
            slippage=self.slippage
        )
        
        self.positions.append(position)
        return position
    
    def update_position(self, position: Position, current_price: float, timestamp: datetime) -> Optional[dict]:
        """Update position and check for TP/SL hits. Returns event if triggered."""
        
        if position.status == TradeStatus.CLOSED:
            return None
        
        if position.direction == "long":
            return self._update_long(position, current_price, timestamp)
        else:
            return self._update_short(position, current_price, timestamp)
    
    def _update_long(self, pos: Position, price: float, timestamp: datetime) -> Optional[dict]:
        """Update long position."""
        
        # Check SL first
        if price <= pos.sl:
            pos.status = TradeStatus.SL_HIT
            pos.final_exit_price = pos.sl - self.spread - self.slippage
            pos.remaining_size = 0
            return {
                "event": "sl_hit",
                "time": timestamp,
                "price": pos.final_exit_price,
                "pnl": self._calculate_pnl(pos)
            }
        
        # Check TP1 (50% close)
        if pos.status == TradeStatus.OPEN and price >= pos.tp1:
            pos.status = TradeStatus.TP1_HIT
            pos.tp1_exit_price = pos.tp1 - self.spread - self.slippage
            pos.remaining_size = pos.size * 0.5
            # Move SL to breakeven
            pos.sl = pos.entry_price
            return {
                "event": "tp1_hit",
                "time": timestamp,
                "price": pos.tp1_exit_price,
                "closed_size": pos.size * 0.5,
                "pnl": (pos.tp1_exit_price - pos.entry_price) * (pos.size * 0.5)
            }
        
        # Check TP2 (40% close)
        if pos.status == TradeStatus.TP1_HIT and price >= pos.tp2:
            pos.status = TradeStatus.TP2_HIT
            pos.tp2_exit_price = pos.tp2 - self.spread - self.slippage
            closed_size = pos.size * 0.4
            pos.remaining_size = pos.size * 0.1
            return {
                "event": "tp2_hit",
                "time": timestamp,
                "price": pos.tp2_exit_price,
                "closed_size": closed_size,
                "pnl": (pos.tp2_exit_price - pos.entry_price) * closed_size
            }
        
        return None
    
    def _update_short(self, pos: Position, price: float, timestamp: datetime) -> Optional[dict]:
        """Update short position."""
        
        # Check SL first
        if price >= pos.sl:
            pos.status = TradeStatus.SL_HIT
            pos.final_exit_price = pos.sl + self.spread + self.slippage
            pos.remaining_size = 0
            return {
                "event": "sl_hit",
                "time": timestamp,
                "price": pos.final_exit_price,
                "pnl": self._calculate_pnl(pos)
            }
        
        # Check TP1 (50% close)
        if pos.status == TradeStatus.OPEN and price <= pos.tp1:
            pos.status = TradeStatus.TP1_HIT
            pos.tp1_exit_price = pos.tp1 + self.spread + self.slippage
            pos.remaining_size = pos.size * 0.5
            pos.sl = pos.entry_price
            return {
                "event": "tp1_hit",
                "time": timestamp,
                "price": pos.tp1_exit_price,
                "closed_size": pos.size * 0.5,
                "pnl": (pos.entry_price - pos.tp1_exit_price) * (pos.size * 0.5)
            }
        
        # Check TP2 (40% close)
        if pos.status == TradeStatus.TP1_HIT and price <= pos.tp2:
            pos.status = TradeStatus.TP2_HIT
            pos.tp2_exit_price = pos.tp2 + self.spread + self.slippage
            closed_size = pos.size * 0.4
            pos.remaining_size = pos.size * 0.1
            return {
                "event": "tp2_hit",
                "time": timestamp,
                "price": pos.tp2_exit_price,
                "closed_size": closed_size,
                "pnl": (pos.entry_price - pos.tp2_exit_price) * closed_size
            }
        
        return None
    
    def close_position(self, position: Position, price: float, timestamp: datetime) -> dict:
        """Force close remaining position (e.g., end of day)."""
        
        if position.remaining_size == 0:
            return {"event": "already_closed", "pnl": 0}
        
        if position.direction == "long":
            exit_price = price - self.spread - self.slippage
            pnl = (exit_price - position.entry_price) * position.remaining_size
        else:
            exit_price = price + self.spread + self.slippage
            pnl = (position.entry_price - exit_price) * position.remaining_size
        
        position.final_exit_price = exit_price
        position.status = TradeStatus.CLOSED
        position.remaining_size = 0
        
        return {
            "event": "force_close",
            "time": timestamp,
            "price": exit_price,
            "pnl": pnl
        }
    
    def _calculate_pnl(self, position: Position) -> float:
        """Calculate total PnL for a position."""
        total_pnl = 0.0
        
        # TP1 (50%)
        if position.tp1_exit_price:
            if position.direction == "long":
                total_pnl += (position.tp1_exit_price - position.entry_price) * (position.size * 0.5)
            else:
                total_pnl += (position.entry_price - position.tp1_exit_price) * (position.size * 0.5)
        
        # TP2 (40%)
        if position.tp2_exit_price:
            if position.direction == "long":
                total_pnl += (position.tp2_exit_price - position.entry_price) * (position.size * 0.4)
            else:
                total_pnl += (position.entry_price - position.tp2_exit_price) * (position.size * 0.4)
        
        # Final exit (remaining or SL)
        if position.final_exit_price:
            remaining = position.size - (position.size * 0.5 if position.tp1_exit_price else 0) - (position.size * 0.4 if position.tp2_exit_price else 0)
            if position.direction == "long":
                total_pnl += (position.final_exit_price - position.entry_price) * remaining
            else:
                total_pnl += (position.entry_price - position.final_exit_price) * remaining
        
        return total_pnl
    
    def get_open_positions(self) -> List[Position]:
        """Get all open positions."""
        return [p for p in self.positions if p.status != TradeStatus.CLOSED and p.status != TradeStatus.SL_HIT]
    
    def get_closed_positions(self) -> List[Position]:
        """Get all closed positions."""
        return [p for p in self.positions if p.status == TradeStatus.CLOSED or p.status == TradeStatus.SL_HIT]
