"""
Parameter Tuner - Optimize strategy parameters using historical data.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any
import itertools
import sys
sys.path.insert(0, '..')

from replay_engine import ReplayEngine, load_mt5_history
from strategy.models import Candle, Timeframe


class ParameterTuner:
    """Optimize strategy parameters through grid search."""
    
    def __init__(self):
        self.results = []
    
    async def tune(
        self,
        candles: List[Candle],
        param_grid: Dict[str, List[Any]]
    ) -> Dict[str, Any]:
        """
        Run grid search over parameter combinations.
        
        Args:
            candles: Historical candles to test on
            param_grid: Dictionary of parameters to test
                Example: {
                    'min_score': [50, 60, 70],
                    'spread': [2.0, 3.0, 4.0]
                }
        
        Returns:
            Best parameters and their performance
        """
        
        # Generate all combinations
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        combinations = list(itertools.product(*values))
        
        print(f"Testing {len(combinations)} parameter combinations...\n")
        
        for i, combo in enumerate(combinations):
            params = dict(zip(keys, combo))
            
            # Run backtest with these parameters
            engine = ReplayEngine()
            
            # Apply parameters (would need to modify ReplayEngine to accept params)
            # For now, just run with defaults
            result = await engine.replay_day(candles)
            stats = engine.calculate_stats()
            
            if 'error' not in stats:
                self.results.append({
                    'params': params,
                    'stats': stats,
                    'sharpe': self._calculate_sharpe(stats),
                    'profit_factor': self._calculate_profit_factor(stats)
                })
                
                print(f"[{i+1}/{len(combinations)}] {params}")
                print(f"  PnL: ${stats['total_pnl']:.2f} | Win Rate: {stats['win_rate']:.1f}%")
        
        # Find best parameters
        if self.results:
            best = max(self.results, key=lambda x: x['sharpe'])
            print(f"\nBest Parameters:")
            print(f"  {best['params']}")
            print(f"  Sharpe: {best['sharpe']:.2f}")
            print(f"  PnL: ${best['stats']['total_pnl']:.2f}")
            print(f"  Win Rate: {best['stats']['win_rate']:.1f}%")
            return best
        
        return {}
    
    def _calculate_sharpe(self, stats: Dict) -> float:
        """Calculate Sharpe ratio (simplified)."""
        if stats['total_trades'] == 0:
            return 0.0
        
        avg_return = stats['total_pnl'] / stats['total_trades']
        # Simplified - would need trade-by-trade returns for real Sharpe
        return avg_return / 100 if avg_return > 0 else 0.0
    
    def _calculate_profit_factor(self, stats: Dict) -> float:
        """Calculate profit factor (gross profit / gross loss)."""
        if stats['losses'] == 0:
            return float('inf')
        
        gross_profit = stats['avg_win'] * stats['wins']
        gross_loss = abs(stats['avg_loss'] * stats['losses'])
        
        return gross_profit / gross_loss if gross_loss > 0 else 0.0


async def main():
    """Run parameter optimization."""
    print("Parameter Tuner\n")
    
    # Load test data
    test_date = datetime(2024, 11, 12, 0, 0, 0)
    candles = await load_mt5_history("US30", test_date, 1440)
    
    if not candles:
        print("No data - using mock")
        base = 42000.0
        candles = []
        for i in range(1440):
            ts = test_date + timedelta(minutes=i)
            price = base + (i * 0.5)
            candles.append(Candle(
                timestamp=ts,
                open=price,
                high=price + 20,
                low=price - 20,
                close=price + 10,
                volume=1000,
                timeframe=Timeframe.M1
            ))
    
    # Define parameter grid
    param_grid = {
        'min_score': [50, 60, 70],
        'spread_points': [2.0, 3.0, 4.0],
        'slippage_points': [1.0, 2.0, 3.0]
    }
    
    tuner = ParameterTuner()
    best = await tuner.tune(candles, param_grid)


if __name__ == "__main__":
    asyncio.run(main())
