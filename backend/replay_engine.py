"""
Historical Replay Engine - Tests strategy against real data.
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dataclasses import dataclass
import json
import sys
sys.path.insert(0, '..')

from strategy.models import Candle, Timeframe, Signal
from strategy.engine import strategy_engine
from execution_simulator import ExecutionSimulator, Position
from news_filter import news_filter
from trade_journal import TradeJournal, TradeRecord


@dataclass
class Trade:
    pass  # Kept for compatibility
    

class ReplayEngine:
    def __init__(self):
        self.executor = ExecutionSimulator(spread_points=3.0, slippage_points=2.0)
        self.journal = TradeJournal()
        self.balance = 10000.0
        self.starting_balance = 10000.0
        self.daily_trades = 0
        self.daily_losses = 0
        self.max_trades_per_day = 2
        self.max_losses_per_day = 2
        self.max_drawdown_pct = 2.0
        self.trade_log = []
        
    async def replay_day(self, candles_1m: List[Candle]) -> Dict[str, Any]:
        """Replay one day with execution simulation."""
        signals_generated = []
        trades_executed = []
        
        for i, candle in enumerate(candles_1m):
            # Update open positions
            for position in self.executor.get_open_positions():
                event = self.executor.update_position(position, candle.close, candle.timestamp)
                if event:
                    self._log_event(event, position)
                    if event['event'] == 'sl_hit':
                        self.daily_losses += 1
            
            await strategy_engine.market_data.store_candle(candle)
            await strategy_engine.aggregator.process_new_candle(candle)
            
            # Run analysis every 5 minutes
            if i % 5 == 0 and i >= 100:
                # Check news filter
                allowed, reason = news_filter.is_trading_allowed(candle.timestamp)
                if not allowed:
                    continue
                
                if not self._check_risk_limits():
                    continue
                
                candles_5m = await strategy_engine.aggregator.get_timeframe_candles(Timeframe.M5, 100)
                
                if len(candles_5m) >= 50:
                    signal = await self._generate_signal(candles_5m, candle)
                    
                    if signal and signal.grade.value in ['A+', 'A']:
                        signals_generated.append(self._format_signal(signal, candle.timestamp))
                        
                        if signal.grade.value == 'A+':
                            position = self.executor.open_position(
                                timestamp=candle.timestamp,
                                direction=signal.direction.value,
                                entry=signal.entry,
                                sl=signal.stop_loss,
                                tp1=signal.take_profit,
                                tp2=signal.take_profit + (signal.take_profit - signal.entry),
                                size=1.0
                            )
                            self.daily_trades += 1
                            
                            # Log to journal
                            trade_id = f"{candle.timestamp.strftime('%Y%m%d_%H%M')}_{signal.direction.value}"
                            self.journal.log_trade(TradeRecord(
                                trade_id=trade_id,
                                timestamp=candle.timestamp,
                                direction=signal.direction.value,
                                setup_type=signal.setup_type.value,
                                grade=signal.grade.value,
                                confluence_score=signal.confluence_score,
                                entry_price=position.entry_price,
                                entry_time=candle.timestamp,
                                sl=position.sl,
                                tp1=position.tp1,
                                tp2=position.tp2,
                                spread_at_entry=position.entry_spread,
                                slippage=position.slippage
                            ))
                            
                            trades_executed.append({
                                "time": candle.timestamp.isoformat(),
                                "direction": signal.direction.value,
                                "entry": position.entry_price
                            })
        
        # Close remaining positions
        for position in self.executor.get_open_positions():
            event = self.executor.close_position(position, candles_1m[-1].close, candles_1m[-1].timestamp)
            self._log_event(event, position)
        
        return {
            "date": candles_1m[0].timestamp.date().isoformat(),
            "candles_processed": len(candles_1m),
            "signals_generated": len(signals_generated),
            "trades_executed": len(trades_executed),
            "signals": signals_generated,
            "trades": trades_executed,
            "pnl": self.balance - self.starting_balance,
            "balance": self.balance
        }
    
    def _check_risk_limits(self) -> bool:
        if self.daily_trades >= self.max_trades_per_day:
            return False
        if self.daily_losses >= self.max_losses_per_day:
            return False
        drawdown_pct = ((self.starting_balance - self.balance) / self.starting_balance) * 100
        if drawdown_pct >= self.max_drawdown_pct:
            return False
        return True
    
    async def _generate_signal(self, candles_5m, candle):
        from strategy.models import AnalysisResult
        
        bias = await strategy_engine.bias_engine.analyze(candles_5m, Timeframe.M5)
        levels = await strategy_engine.level_engine.analyze(candles_5m)
        liquidity = await strategy_engine.liquidity_engine.analyze(candles_5m, Timeframe.M5)
        fvg = await strategy_engine.fvg_engine.analyze(candles_5m, Timeframe.M5)
        displacement = await strategy_engine.displacement_engine.analyze(candles_5m, Timeframe.M5)
        structure = await strategy_engine.structure_engine.analyze(candles_5m, Timeframe.M5)
        
        analysis = AnalysisResult(
            timestamp=candle.timestamp,
            timeframe=Timeframe.M5,
            bias=bias,
            levels=levels,
            liquidity=liquidity,
            fvg=fvg,
            displacement=displacement,
            structure=structure
        )
        
        return await strategy_engine.signal_generator.evaluate_setup(
            analysis=analysis,
            current_price=candle.close
        )
    
    def _format_signal(self, signal, timestamp):
        return {
            "time": timestamp.isoformat(),
            "grade": signal.grade.value,
            "score": signal.confluence_score,
            "direction": signal.direction.value,
            "entry": signal.entry,
            "sl": signal.stop_loss,
            "tp": signal.take_profit
        }
    
    def _log_event(self, event, position):
        pnl = event.get('pnl', 0)
        self.balance += pnl
        self.trade_log.append({
            "event": event['event'],
            "time": event['time'].isoformat(),
            "price": event['price'],
            "pnl": pnl,
            "balance": self.balance
        })
    
    def calculate_stats(self) -> Dict[str, Any]:
        closed = self.executor.get_closed_positions()
        
        if not closed:
            return {"error": "No closed trades"}
        
        wins = [p for p in closed if self.executor._calculate_pnl(p) > 0]
        losses = [p for p in closed if self.executor._calculate_pnl(p) <= 0]
        
        total_pnl = sum(self.executor._calculate_pnl(p) for p in closed)
        
        return {
            "total_trades": len(closed),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": len(wins) / len(closed) * 100 if closed else 0,
            "total_pnl": total_pnl,
            "avg_win": sum(self.executor._calculate_pnl(p) for p in wins) / len(wins) if wins else 0,
            "avg_loss": sum(self.executor._calculate_pnl(p) for p in losses) / len(losses) if losses else 0,
            "final_balance": self.balance,
            "return_pct": (self.balance - self.starting_balance) / self.starting_balance * 100
        }


async def load_mt5_history(symbol: str, date: datetime, count: int = 1440) -> List[Candle]:
    """Load historical 1M candles from MT5."""
    try:
        import MetaTrader5 as mt5  # type: ignore
        
        if not mt5.initialize():
            raise Exception("MT5 init failed")
        
        rates = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M1, date, count)
        
        if rates is None:
            raise ValueError("No data available from MT5")
        
        candles = []
        for rate in rates:
            candles.append(Candle(
                timestamp=datetime.fromtimestamp(rate['time'], tz=None),
                open=float(rate['open']),
                high=float(rate['high']),
                low=float(rate['low']),
                close=float(rate['close']),
                volume=int(rate['tick_volume']),
                timeframe=Timeframe.M1
            ))
        
        mt5.shutdown()
        return candles
        
    except Exception as e:
        print(f"MT5 load failed: {e}")
        return []


async def main():
    """Run replay test."""
    print("Historical Replay Engine\n")
    
    # Initialize
    await strategy_engine.initialize()
    
    # Test date
    test_date = datetime(2024, 11, 12, 0, 0, 0)
    
    print(f"Loading data for {test_date.date()}...")
    candles = await load_mt5_history("US30", test_date, 1440)
    
    if not candles:
        print("No data loaded. Using mock data for demo.")
        # Generate mock trending data
        base = 42000.0
        candles = [
            Candle(
                timestamp=test_date + timedelta(minutes=i),
                open=base + (i * 0.5),
                high=base + (i * 0.5) + 20,
                low=base + (i * 0.5) - 20,
                close=base + (i * 0.5) + 10,
                volume=1000,
                timeframe=Timeframe.M1
            )
            for i in range(1440)
        ]
    
    print(f"Loaded {len(candles)} candles")
    print(f"Range: {candles[0].timestamp} to {candles[-1].timestamp}\n")
    
    # Replay
    engine = ReplayEngine()
    result = await engine.replay_day(candles)
    
    print(f"Results for {result['date']}:")
    print(f"  Candles processed: {result['candles_processed']}")
    print(f"  Signals generated: {result['signals_generated']}")
    print(f"  Trades executed: {result['trades_executed']}")
    print(f"  PnL: ${result['pnl']:.2f}")
    print(f"  Balance: ${result['balance']:.2f}\n")
    
    if result['trades']:
        print("Trades:")
        for trade in result['trades']:
            print(f"  {trade['time']} | {trade['direction']} @ {trade['entry']}")
        print()
    
    # Show stats
    stats = engine.calculate_stats()
    if 'error' not in stats:
        print("Performance:")
        print(f"  Win Rate: {stats['win_rate']:.1f}%")
        print(f"  Total PnL: ${stats['total_pnl']:.2f}")
        print(f"  Return: {stats['return_pct']:.2f}%")
    
    await strategy_engine.stop()


if __name__ == "__main__":
    asyncio.run(main())
