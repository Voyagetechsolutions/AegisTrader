"""
Tests for Multi-Market Coordinator.

Verifies parallel processing of multiple instruments.
"""

import pytest
import asyncio
from datetime import datetime, timedelta

from backend.strategy.multi_market_coordinator import (
    MultiMarketCoordinator,
    MultiMarketConfig
)
from backend.strategy.dual_engine_models import Instrument, OHLCVBar
from backend.strategy.session_manager import SessionManager


class MockNewsFilter:
    """Mock news filter for testing."""
    async def check_news_blackout(self):
        return {"blocked": False}


@pytest.fixture
def session_manager():
    """Create session manager."""
    return SessionManager()


@pytest.fixture
def news_filter():
    """Create mock news filter."""
    return MockNewsFilter()


@pytest.fixture
def multi_market_config():
    """Create multi-market configuration."""
    return MultiMarketConfig(
        instruments=[Instrument.US30, Instrument.NAS100, Instrument.XAUUSD],
        spread_limits_global={
            Instrument.US30: 5.0,
            Instrument.NAS100: 4.0,
            Instrument.XAUUSD: 3.0,
        },
        spread_limits_scalp={
            Instrument.US30: 3.0,
            Instrument.NAS100: 2.0,
            Instrument.XAUUSD: 2.0,
        },
        core_risk_per_trade=0.01,
        scalp_risk_per_trade=0.005,
        rolling_window_size=20,
        min_bars_for_regime=250
    )


@pytest.fixture
def coordinator(multi_market_config, session_manager, news_filter):
    """Create multi-market coordinator."""
    return MultiMarketCoordinator(
        config=multi_market_config,
        session_manager=session_manager,
        news_filter=news_filter
    )


def generate_bars(count: int, base_price: float) -> list[OHLCVBar]:
    """Generate test OHLCV bars."""
    bars = []
    now = datetime.now()
    
    for i in range(count):
        timestamp = now - timedelta(minutes=count - i)
        bars.append(OHLCVBar(
            timestamp=timestamp,
            open=base_price + (i % 10),
            high=base_price + (i % 10) + 2,
            low=base_price + (i % 10) - 2,
            close=base_price + (i % 10) + 1,
            volume=1000 + (i * 10)
        ))
    
    return bars


class TestMultiMarketCoordinator:
    """Test suite for MultiMarketCoordinator."""
    
    def test_initialization(self, coordinator):
        """Test coordinator initializes with all instruments."""
        assert len(coordinator.coordinators) == 3
        assert Instrument.US30 in coordinator.coordinators
        assert Instrument.NAS100 in coordinator.coordinators
        assert Instrument.XAUUSD in coordinator.coordinators
    
    def test_get_coordinator(self, coordinator):
        """Test getting coordinator for specific instrument."""
        us30_coordinator = coordinator.get_coordinator(Instrument.US30)
        assert us30_coordinator is not None
        
        # Invalid instrument - use None instead of non-existent enum
        invalid = coordinator.get_coordinator(None)
        assert invalid is None
    
    def test_process_market_sync(self, coordinator):
        """Test synchronous market processing."""
        bars = generate_bars(300, 40000.0)
        spread = 2.5
        
        signal = coordinator.process_market_sync(
            instrument=Instrument.US30,
            bars=bars,
            current_spread=spread
        )
        
        # No signal expected (no strategy engines configured)
        assert signal is None
    
    @pytest.mark.asyncio
    async def test_process_all_markets(self, coordinator):
        """Test parallel processing of all markets."""
        market_data = {
            Instrument.US30: (generate_bars(300, 40000.0), 2.5),
            Instrument.NAS100: (generate_bars(300, 18000.0), 2.0),
            Instrument.XAUUSD: (generate_bars(300, 2000.0), 1.5),
        }
        
        signals = await coordinator.process_all_markets(market_data)
        
        assert len(signals) == 3
        assert Instrument.US30 in signals
        assert Instrument.NAS100 in signals
        assert Instrument.XAUUSD in signals
        
        # All None (no strategy engines)
        assert all(sig is None for sig in signals.values())
    
    def test_get_all_regimes(self, coordinator):
        """Test getting regimes for all instruments."""
        # Process some data first
        for instrument in [Instrument.US30, Instrument.NAS100, Instrument.XAUUSD]:
            bars = generate_bars(300, 40000.0 if instrument == Instrument.US30 else 2000.0)
            coordinator.process_market_sync(instrument, bars, 2.0)
        
        regimes = coordinator.get_all_regimes()
        
        assert len(regimes) == 3
        assert Instrument.US30 in regimes
        assert Instrument.NAS100 in regimes
        assert Instrument.XAUUSD in regimes
        
        # Check regime structure
        for regime in regimes.values():
            assert "volatility" in regime
            assert "trend" in regime
            assert "atr_current" in regime
            assert "atr_average" in regime
            assert "atr_ratio" in regime
            assert "timestamp" in regime
    
    def test_get_all_active_signals(self, coordinator):
        """Test getting active signals for all instruments."""
        signals = coordinator.get_all_active_signals()
        
        assert len(signals) == 3
        assert Instrument.US30 in signals
        assert Instrument.NAS100 in signals
        assert Instrument.XAUUSD in signals
        
        # All empty (no trades executed)
        assert all(len(sigs) == 0 for sigs in signals.values())
    
    def test_record_trade_outcome(self, coordinator):
        """Test recording trade outcome for specific instrument."""
        # This should not raise an error even with no active signal
        coordinator.record_trade_outcome(
            instrument=Instrument.US30,
            signal_id="test_signal_123",
            win=True,
            r_multiple=2.0,
            profit_loss=100.0
        )
        
        # Verify no crash
        assert True
    
    def test_clear_all_state(self, coordinator):
        """Test clearing state for all coordinators."""
        # Process some data
        bars = generate_bars(300, 40000.0)
        coordinator.process_market_sync(Instrument.US30, bars, 2.0)
        
        # Clear state
        coordinator.clear_all_state()
        
        # Verify regimes cleared
        regimes = coordinator.get_all_regimes()
        assert len(regimes) == 0
    
    def test_default_config(self):
        """Test default configuration values."""
        config = MultiMarketConfig()
        
        assert len(config.instruments) == 3
        assert Instrument.US30 in config.instruments
        assert Instrument.NAS100 in config.instruments
        assert Instrument.XAUUSD in config.instruments
        
        assert config.spread_limits_global[Instrument.US30] == 5.0
        assert config.spread_limits_global[Instrument.NAS100] == 4.0
        assert config.spread_limits_global[Instrument.XAUUSD] == 3.0
        
        assert config.spread_limits_scalp[Instrument.US30] == 3.0
        assert config.spread_limits_scalp[Instrument.NAS100] == 2.0
        assert config.spread_limits_scalp[Instrument.XAUUSD] == 2.0
        
        assert config.core_risk_per_trade == 0.01
        assert config.scalp_risk_per_trade == 0.005
        assert config.rolling_window_size == 20
        assert config.min_bars_for_regime == 250
    
    @pytest.mark.asyncio
    async def test_parallel_processing_performance(self, coordinator):
        """Test that parallel processing works correctly."""
        market_data = {
            Instrument.US30: (generate_bars(300, 40000.0), 2.5),
            Instrument.NAS100: (generate_bars(300, 18000.0), 2.0),
            Instrument.XAUUSD: (generate_bars(300, 2000.0), 1.5),
        }
        
        # Test parallel processing completes successfully
        signals = await coordinator.process_all_markets(market_data)
        
        # Verify all markets were processed
        assert len(signals) == 3
        assert all(instrument in signals for instrument in market_data.keys())
        
        # Note: Actual performance comparison is unreliable in tests
        # due to overhead and no real strategy engines
        print(f"Parallel processing completed for {len(signals)} markets")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
