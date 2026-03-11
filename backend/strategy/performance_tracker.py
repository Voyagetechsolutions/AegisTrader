"""
Performance Tracking Module for Dual-Engine Strategy System.

Tracks performance metrics separately for Core Strategy and Quick Scalp engines,
per instrument, with both rolling (last 20 trades) and lifetime statistics.

This feeds the Auto-Trade Decision Engine's tiebreaker logic.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import deque
from backend.strategy.dual_engine_models import (
    Instrument,
    EngineType,
    TradeOutcome,
    PerformanceMetrics
)


@dataclass
class TradeRecord:
    """Single trade record for performance tracking."""
    trade_id: str
    engine: EngineType
    instrument: Instrument
    win: bool
    r_multiple: float
    profit_loss: float
    timestamp: datetime


@dataclass
class EngineInstrumentKey:
    """Key for tracking performance by engine and instrument."""
    engine: EngineType
    instrument: Instrument
    
    def __hash__(self):
        return hash((self.engine, self.instrument))
    
    def __eq__(self, other):
        if not isinstance(other, EngineInstrumentKey):
            return False
        return self.engine == other.engine and self.instrument == other.instrument


class PerformanceTracker:
    """
    Tracks trading performance for decision engine tiebreaker logic.
    
    Maintains separate statistics for:
    - Each engine (Core Strategy, Quick Scalp)
    - Each instrument (US30, XAUUSD, NAS100)
    - Rolling window (last 20 trades)
    - Lifetime (all trades)
    
    This is what lets the decision engine learn from experience.
    """
    
    def __init__(self, rolling_window_size: int = 20):
        """
        Initialize performance tracker.
        
        Args:
            rolling_window_size: Number of recent trades to track (default 20)
        """
        self.rolling_window_size = rolling_window_size
        
        # Trade history per engine+instrument
        self._trade_history: Dict[EngineInstrumentKey, deque] = {}
        
        # Lifetime trade history per engine (all instruments combined)
        self._lifetime_history: Dict[EngineType, List[TradeRecord]] = {
            EngineType.CORE_STRATEGY: [],
            EngineType.QUICK_SCALP: []
        }
        
        # Consecutive win/loss tracking
        self._consecutive_wins: Dict[EngineInstrumentKey, int] = {}
        self._consecutive_losses: Dict[EngineInstrumentKey, int] = {}
        
        # Max drawdown tracking
        self._peak_balance: Dict[EngineInstrumentKey, float] = {}
        self._current_balance: Dict[EngineInstrumentKey, float] = {}
        self._max_drawdown: Dict[EngineInstrumentKey, float] = {}
    
    def record_trade(
        self,
        trade_id: str,
        engine: EngineType,
        instrument: Instrument,
        win: bool,
        r_multiple: float,
        profit_loss: float,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Record a completed trade.
        
        Args:
            trade_id: Unique trade identifier
            engine: Which engine executed the trade
            instrument: Which instrument was traded
            win: True if trade was profitable
            r_multiple: Risk multiple achieved (e.g., 2.0 for 2R)
            profit_loss: Actual P&L in account currency
            timestamp: Trade completion time (defaults to now)
        """
        timestamp = timestamp or datetime.now()
        
        record = TradeRecord(
            trade_id=trade_id,
            engine=engine,
            instrument=instrument,
            win=win,
            r_multiple=r_multiple,
            profit_loss=profit_loss,
            timestamp=timestamp
        )
        
        key = EngineInstrumentKey(engine, instrument)
        
        # Initialize if first trade for this key
        if key not in self._trade_history:
            self._trade_history[key] = deque(maxlen=self.rolling_window_size)
            self._consecutive_wins[key] = 0
            self._consecutive_losses[key] = 0
            self._peak_balance[key] = 0.0
            self._current_balance[key] = 0.0
            self._max_drawdown[key] = 0.0
        
        # Add to rolling window
        self._trade_history[key].append(record)
        
        # Add to lifetime history
        self._lifetime_history[engine].append(record)
        
        # Update consecutive wins/losses
        if win:
            self._consecutive_wins[key] += 1
            self._consecutive_losses[key] = 0
        else:
            self._consecutive_losses[key] += 1
            self._consecutive_wins[key] = 0
        
        # Update drawdown tracking
        self._current_balance[key] += profit_loss
        if self._current_balance[key] > self._peak_balance[key]:
            self._peak_balance[key] = self._current_balance[key]
        
        drawdown = self._peak_balance[key] - self._current_balance[key]
        if drawdown > self._max_drawdown[key]:
            self._max_drawdown[key] = drawdown
    
    def get_rolling_metrics(
        self,
        engine: EngineType,
        instrument: Optional[Instrument] = None
    ) -> PerformanceMetrics:
        """
        Get rolling window performance metrics (last N trades).
        
        Args:
            engine: Which engine to get metrics for
            instrument: Specific instrument (None = all instruments combined)
        
        Returns:
            PerformanceMetrics for rolling window
        """
        if instrument:
            # Single instrument
            key = EngineInstrumentKey(engine, instrument)
            if key not in self._trade_history or len(self._trade_history[key]) == 0:
                return self._empty_metrics()
            
            trades = list(self._trade_history[key])
        else:
            # All instruments combined
            trades = []
            for inst in Instrument:
                key = EngineInstrumentKey(engine, inst)
                if key in self._trade_history:
                    trades.extend(list(self._trade_history[key]))
            
            if not trades:
                return self._empty_metrics()
            
            # Sort by timestamp and take last N
            trades.sort(key=lambda t: t.timestamp)
            trades = trades[-self.rolling_window_size:]
        
        return self._calculate_metrics(trades)
    
    def get_lifetime_metrics(
        self,
        engine: EngineType,
        instrument: Optional[Instrument] = None
    ) -> PerformanceMetrics:
        """
        Get lifetime performance metrics (all trades).
        
        Args:
            engine: Which engine to get metrics for
            instrument: Specific instrument (None = all instruments combined)
        
        Returns:
            PerformanceMetrics for lifetime
        """
        if instrument:
            # Filter lifetime history by instrument
            trades = [
                t for t in self._lifetime_history[engine]
                if t.instrument == instrument
            ]
        else:
            # All instruments
            trades = self._lifetime_history[engine]
        
        if not trades:
            return self._empty_metrics()
        
        return self._calculate_metrics(trades)
    
    def get_consecutive_wins(
        self,
        engine: EngineType,
        instrument: Instrument
    ) -> int:
        """Get current consecutive wins for engine+instrument."""
        key = EngineInstrumentKey(engine, instrument)
        return self._consecutive_wins.get(key, 0)
    
    def get_consecutive_losses(
        self,
        engine: EngineType,
        instrument: Instrument
    ) -> int:
        """Get current consecutive losses for engine+instrument."""
        key = EngineInstrumentKey(engine, instrument)
        return self._consecutive_losses.get(key, 0)
    
    def get_max_drawdown(
        self,
        engine: EngineType,
        instrument: Instrument
    ) -> float:
        """Get maximum drawdown for engine+instrument."""
        key = EngineInstrumentKey(engine, instrument)
        return self._max_drawdown.get(key, 0.0)
    
    def get_trade_count(
        self,
        engine: EngineType,
        instrument: Optional[Instrument] = None,
        rolling: bool = False
    ) -> int:
        """
        Get trade count.
        
        Args:
            engine: Which engine
            instrument: Specific instrument (None = all)
            rolling: True for rolling window, False for lifetime
        
        Returns:
            Number of trades
        """
        if rolling:
            if instrument:
                key = EngineInstrumentKey(engine, instrument)
                return len(self._trade_history.get(key, []))
            else:
                count = 0
                for inst in Instrument:
                    key = EngineInstrumentKey(engine, inst)
                    count += len(self._trade_history.get(key, []))
                return min(count, self.rolling_window_size)
        else:
            # Lifetime
            if instrument:
                return len([
                    t for t in self._lifetime_history[engine]
                    if t.instrument == instrument
                ])
            else:
                return len(self._lifetime_history[engine])
    
    def _calculate_metrics(self, trades: List[TradeRecord]) -> PerformanceMetrics:
        """
        Calculate performance metrics from trade list.
        
        Args:
            trades: List of trade records
        
        Returns:
            PerformanceMetrics object
        """
        if not trades:
            return self._empty_metrics()
        
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.win)
        losing_trades = total_trades - winning_trades
        
        # Win rate
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        # Average R
        r_multiples = [t.r_multiple for t in trades]
        average_rr = sum(r_multiples) / len(r_multiples) if r_multiples else 0.0
        
        # Profit factor
        gross_profit = sum(t.profit_loss for t in trades if t.win)
        gross_loss = abs(sum(t.profit_loss for t in trades if not t.win))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (
            float('inf') if gross_profit > 0 else 0.0
        )
        
        return PerformanceMetrics(
            win_rate=win_rate,
            profit_factor=profit_factor,
            average_rr=average_rr,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades
        )
    
    def _empty_metrics(self) -> PerformanceMetrics:
        """Return empty metrics for no trade history."""
        return PerformanceMetrics(
            win_rate=0.0,
            profit_factor=0.0,
            average_rr=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0
        )
    
    def clear_history(
        self,
        engine: Optional[EngineType] = None,
        instrument: Optional[Instrument] = None
    ) -> None:
        """
        Clear trade history.
        
        Args:
            engine: Clear specific engine (None = all)
            instrument: Clear specific instrument (None = all)
        """
        if engine and instrument:
            # Clear specific engine+instrument
            key = EngineInstrumentKey(engine, instrument)
            if key in self._trade_history:
                self._trade_history[key].clear()
                self._consecutive_wins[key] = 0
                self._consecutive_losses[key] = 0
                self._peak_balance[key] = 0.0
                self._current_balance[key] = 0.0
                self._max_drawdown[key] = 0.0
            
            # Also clear from lifetime history
            self._lifetime_history[engine] = [
                t for t in self._lifetime_history[engine]
                if t.instrument != instrument
            ]
        elif engine:
            # Clear all instruments for engine
            for inst in Instrument:
                key = EngineInstrumentKey(engine, inst)
                if key in self._trade_history:
                    self._trade_history[key].clear()
                    self._consecutive_wins[key] = 0
                    self._consecutive_losses[key] = 0
                    self._peak_balance[key] = 0.0
                    self._current_balance[key] = 0.0
                    self._max_drawdown[key] = 0.0
            
            # Clear lifetime history
            self._lifetime_history[engine].clear()
        else:
            # Clear everything
            self._trade_history.clear()
            self._consecutive_wins.clear()
            self._consecutive_losses.clear()
            self._peak_balance.clear()
            self._current_balance.clear()
            self._max_drawdown.clear()
            for engine_type in EngineType:
                self._lifetime_history[engine_type].clear()
    
    def get_summary(self, engine: EngineType) -> Dict:
        """
        Get comprehensive summary for an engine.
        
        Returns dict with rolling and lifetime metrics for all instruments.
        """
        summary = {
            "engine": engine.value,
            "rolling": {},
            "lifetime": {},
            "by_instrument": {}
        }
        
        # Overall rolling and lifetime
        summary["rolling"] = self._metrics_to_dict(
            self.get_rolling_metrics(engine)
        )
        summary["lifetime"] = self._metrics_to_dict(
            self.get_lifetime_metrics(engine)
        )
        
        # Per instrument
        for instrument in Instrument:
            inst_data = {
                "rolling": self._metrics_to_dict(
                    self.get_rolling_metrics(engine, instrument)
                ),
                "lifetime": self._metrics_to_dict(
                    self.get_lifetime_metrics(engine, instrument)
                ),
                "consecutive_wins": self.get_consecutive_wins(engine, instrument),
                "consecutive_losses": self.get_consecutive_losses(engine, instrument),
                "max_drawdown": self.get_max_drawdown(engine, instrument)
            }
            summary["by_instrument"][instrument.value] = inst_data
        
        return summary
    
    def _metrics_to_dict(self, metrics: PerformanceMetrics) -> Dict:
        """Convert PerformanceMetrics to dict."""
        return {
            "win_rate": metrics.win_rate,
            "profit_factor": metrics.profit_factor,
            "average_rr": metrics.average_rr,
            "total_trades": metrics.total_trades,
            "winning_trades": metrics.winning_trades,
            "losing_trades": metrics.losing_trades
        }
