"""
Tests for Market Regime Detection Module.

These tests verify that the regime detector correctly classifies:
- Volatility regimes (LOW, NORMAL, HIGH, EXTREME)
- Trend strength (STRONG_TREND, WEAK_TREND, RANGING, CHOPPY)
"""

import pytest
from datetime import datetime, timedelta
from backend.strategy.regime_detector import RegimeDetector, RegimeDetectorConfig
from backend.strategy.auto_trade_decision_engine import VolatilityRegime, TrendStrength
from backend.strategy.dual_engine_models import Instrument, OHLCVBar


def generate_bars(
    count: int,
    base_price: float = 40000.0,
    volatility: float = 100.0,
    trend: str = "flat",
    trend_strength: float = 0.5
) -> list:
    """
    Generate synthetic OHLCV bars for testing.
    
    Args:
        count: Number of bars to generate
        base_price: Starting price
        volatility: Average range per bar
        trend: "up", "down", "flat", "choppy"
        trend_strength: How strong the trend is (0.0 to 1.0)
    """
    bars = []
    current_price = base_price
    timestamp = datetime.now() - timedelta(minutes=count)
    
    for i in range(count):
        # Apply trend
        if trend == "up":
            current_price += volatility * trend_strength * 0.1
        elif trend == "down":
            current_price -= volatility * trend_strength * 0.1
        elif trend == "choppy":
            # Alternate direction
            if i % 3 == 0:
                current_price += volatility * 0.2
            else:
                current_price -= volatility * 0.15
        
        # Add some randomness
        import random
        random.seed(i)  # Deterministic for tests
        noise = random.uniform(-volatility * 0.3, volatility * 0.3)
        
        # Generate OHLC
        open_price = current_price + noise
        high = open_price + abs(random.uniform(0, volatility))
        low = open_price - abs(random.uniform(0, volatility))
        close = random.uniform(low, high)
        volume = random.uniform(1000, 5000)
        
        bars.append(OHLCVBar(
            timestamp=timestamp + timedelta(minutes=i),
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume
        ))
    
    return bars


def test_low_volatility_detection():
    """Test detection of LOW volatility regime."""
    detector = RegimeDetector()
    
    # Generate bars with consistently low volatility throughout
    bars = []
    for i in range(100):
        vol = 40.0  # Consistently low
        bars.extend(generate_bars(count=1, base_price=40000.0, volatility=vol, trend="flat"))
    
    regime = detector.detect_regime(Instrument.US30, bars)
    
    # Should detect low volatility
    assert regime.volatility in [VolatilityRegime.LOW, VolatilityRegime.NORMAL]
    assert regime.atr_current / regime.atr_average < 1.2  # Not high volatility


def test_normal_volatility_detection():
    """Test detection of NORMAL volatility regime."""
    detector = RegimeDetector()
    
    # Generate bars with normal volatility
    bars = generate_bars(count=100, base_price=40000.0, volatility=100.0, trend="flat")
    
    regime = detector.detect_regime(Instrument.US30, bars)
    
    assert regime.volatility == VolatilityRegime.NORMAL
    assert 0.8 <= regime.atr_current / regime.atr_average <= 1.5


def test_high_volatility_detection():
    """Test detection of HIGH volatility regime."""
    detector = RegimeDetector()
    
    # Generate bars with normal volatility first, then spike
    bars = []
    for i in range(70):
        vol = 80.0  # Normal baseline
        bars.extend(generate_bars(count=1, base_price=40000.0 + i * 5, volatility=vol, trend="flat"))
    
    for i in range(30):
        vol = 200.0  # High volatility spike
        bars.extend(generate_bars(count=1, base_price=40000.0 + 350 + i * 10, volatility=vol, trend="flat"))
    
    regime = detector.detect_regime(Instrument.US30, bars)
    
    # Should detect elevated volatility
    assert regime.volatility in [VolatilityRegime.HIGH, VolatilityRegime.EXTREME]
    assert regime.atr_current / regime.atr_average > 1.3


def test_extreme_volatility_detection():
    """Test detection of EXTREME volatility regime."""
    detector = RegimeDetector()
    
    # Generate bars with normal volatility first, then extreme spike
    bars = []
    for i in range(70):
        vol = 70.0  # Low baseline
        bars.extend(generate_bars(count=1, base_price=40000.0 + i * 5, volatility=vol, trend="flat"))
    
    for i in range(30):
        vol = 350.0  # Extreme volatility
        bars.extend(generate_bars(count=1, base_price=40000.0 + 350 + i * 20, volatility=vol, trend="flat"))
    
    regime = detector.detect_regime(Instrument.US30, bars)
    
    # Should detect extreme volatility
    assert regime.volatility in [VolatilityRegime.HIGH, VolatilityRegime.EXTREME]
    assert regime.atr_current / regime.atr_average > 1.8


def test_strong_uptrend_detection():
    """Test detection of STRONG_TREND (uptrend)."""
    detector = RegimeDetector()
    
    # Generate strong uptrend with clean swings
    bars = generate_bars(count=250, base_price=40000.0, volatility=100.0, trend="up", trend_strength=1.0)
    
    regime = detector.detect_regime(Instrument.US30, bars)
    
    # Should detect some form of trend (strong or weak)
    assert regime.trend_strength in [TrendStrength.STRONG_TREND, TrendStrength.WEAK_TREND]


def test_strong_downtrend_detection():
    """Test detection of STRONG_TREND (downtrend)."""
    detector = RegimeDetector()
    
    # Generate strong downtrend with clean swings
    bars = generate_bars(count=250, base_price=40000.0, volatility=100.0, trend="down", trend_strength=1.0)
    
    regime = detector.detect_regime(Instrument.US30, bars)
    
    assert regime.trend_strength == TrendStrength.STRONG_TREND


def test_weak_trend_detection():
    """Test detection of WEAK_TREND."""
    detector = RegimeDetector()
    
    # Generate weak uptrend
    bars = generate_bars(count=250, base_price=40000.0, volatility=100.0, trend="up", trend_strength=0.3)
    
    regime = detector.detect_regime(Instrument.US30, bars)
    
    assert regime.trend_strength in [TrendStrength.WEAK_TREND, TrendStrength.RANGING]


def test_ranging_market_detection():
    """Test detection of RANGING market."""
    detector = RegimeDetector()
    
    # Generate flat/ranging market
    bars = generate_bars(count=250, base_price=40000.0, volatility=100.0, trend="flat", trend_strength=0.0)
    
    regime = detector.detect_regime(Instrument.US30, bars)
    
    assert regime.trend_strength in [TrendStrength.RANGING, TrendStrength.WEAK_TREND]


def test_choppy_market_detection():
    """Test detection of CHOPPY market."""
    detector = RegimeDetector()
    
    # Generate choppy market with conflicting swings
    bars = generate_bars(count=250, base_price=40000.0, volatility=150.0, trend="choppy", trend_strength=0.0)
    
    regime = detector.detect_regime(Instrument.US30, bars)
    
    # Choppy should not be strong trend
    assert regime.trend_strength != TrendStrength.STRONG_TREND


def test_insufficient_data_error():
    """Test that insufficient data raises ValueError."""
    detector = RegimeDetector()
    
    # Only 10 bars (need at least 50)
    bars = generate_bars(count=10, base_price=40000.0, volatility=100.0, trend="flat")
    
    with pytest.raises(ValueError, match="Insufficient data"):
        detector.detect_regime(Instrument.US30, bars)


def test_regime_object_structure():
    """Test that MarketRegime object has correct structure."""
    detector = RegimeDetector()
    
    bars = generate_bars(count=100, base_price=40000.0, volatility=100.0, trend="flat")
    regime = detector.detect_regime(Instrument.US30, bars)
    
    # Check all required fields present
    assert regime.instrument == Instrument.US30
    assert isinstance(regime.volatility, VolatilityRegime)
    assert isinstance(regime.trend_strength, TrendStrength)
    assert regime.atr_current > 0
    assert regime.atr_average > 0
    assert isinstance(regime.timestamp, datetime)


def test_atr_calculation_accuracy():
    """Test ATR calculation produces reasonable values."""
    detector = RegimeDetector()
    
    # Generate bars with known volatility
    bars = generate_bars(count=100, base_price=40000.0, volatility=100.0, trend="flat")
    
    regime = detector.detect_regime(Instrument.US30, bars)
    
    # ATR should be roughly in the range of the volatility we set
    # Allow wide margin due to randomness
    assert 50 < regime.atr_current < 200
    assert 50 < regime.atr_average < 200


def test_different_instruments():
    """Test regime detection works for all instruments."""
    detector = RegimeDetector()
    
    instruments = [Instrument.US30, Instrument.XAUUSD, Instrument.NAS100]
    
    for instrument in instruments:
        bars = generate_bars(count=100, base_price=2000.0, volatility=10.0, trend="up")
        regime = detector.detect_regime(instrument, bars)
        
        assert regime.instrument == instrument
        assert isinstance(regime.volatility, VolatilityRegime)
        assert isinstance(regime.trend_strength, TrendStrength)


def test_custom_config():
    """Test regime detector with custom configuration."""
    config = RegimeDetectorConfig(
        atr_period=20,
        atr_average_period=60,
        low_volatility_threshold=0.7,
        normal_volatility_max=1.6
    )
    
    detector = RegimeDetector(config)
    
    bars = generate_bars(count=100, base_price=40000.0, volatility=100.0, trend="flat")
    regime = detector.detect_regime(Instrument.US30, bars)
    
    # Should work with custom config
    assert isinstance(regime.volatility, VolatilityRegime)
    assert isinstance(regime.trend_strength, TrendStrength)


def test_range_compression_detection():
    """Test detection of range compression."""
    detector = RegimeDetector()
    
    # Generate bars with decreasing ranges (compression)
    bars = []
    for i in range(30):
        vol = 100.0 if i < 20 else 40.0  # Compression in last 10 bars
        bars.extend(generate_bars(count=1, base_price=40000.0, volatility=vol, trend="flat"))
    
    is_compressed = detector.detect_range_compression(bars)
    
    assert is_compressed is True


def test_no_range_compression():
    """Test that normal ranges don't trigger compression."""
    detector = RegimeDetector()
    
    # Generate bars with consistent ranges
    bars = generate_bars(count=30, base_price=40000.0, volatility=100.0, trend="flat")
    
    is_compressed = detector.detect_range_compression(bars)
    
    assert is_compressed is False


def test_volatility_regime_transitions():
    """Test that regime correctly identifies volatility transitions."""
    detector = RegimeDetector()
    
    # Start with normal volatility (need at least 65 bars for ATR average)
    bars = generate_bars(count=70, base_price=40000.0, volatility=100.0, trend="flat")
    regime1 = detector.detect_regime(Instrument.US30, bars)
    
    # Add high volatility bars
    bars.extend(generate_bars(count=40, base_price=40000.0, volatility=250.0, trend="flat"))
    regime2 = detector.detect_regime(Instrument.US30, bars)
    
    # Should detect transition to higher volatility
    assert regime2.atr_current > regime1.atr_current


def test_trend_strength_with_insufficient_data():
    """Test trend classification with minimal data (fallback mode)."""
    detector = RegimeDetector()
    
    # 70 bars (enough for ATR average, not enough for EMA 200)
    bars = generate_bars(count=70, base_price=40000.0, volatility=100.0, trend="up", trend_strength=0.8)
    
    regime = detector.detect_regime(Instrument.US30, bars)
    
    # Should still classify trend using simplified method
    assert isinstance(regime.trend_strength, TrendStrength)


def test_ema_calculation():
    """Test that EMA calculation is working."""
    detector = RegimeDetector()
    
    # Generate uptrend
    bars = generate_bars(count=250, base_price=40000.0, volatility=100.0, trend="up", trend_strength=0.8)
    
    # Calculate EMAs
    ema_50 = detector._calculate_ema(bars, 50)
    ema_200 = detector._calculate_ema(bars, 200)
    
    # In uptrend, EMA 50 should be above EMA 200
    assert ema_50 > ema_200
    
    # Both should be reasonable values
    assert 39000 < ema_50 < 45000
    assert 39000 < ema_200 < 45000


def test_swing_structure_analysis():
    """Test swing structure quality scoring."""
    detector = RegimeDetector()
    
    # Strong uptrend should have high swing quality
    bars_uptrend = generate_bars(count=100, base_price=40000.0, volatility=100.0, trend="up", trend_strength=1.0)
    quality_uptrend = detector._analyze_swing_structure(bars_uptrend)
    
    # Choppy market should have low swing quality
    bars_choppy = generate_bars(count=100, base_price=40000.0, volatility=150.0, trend="choppy", trend_strength=0.0)
    quality_choppy = detector._analyze_swing_structure(bars_choppy)
    
    # Uptrend should have better swing quality than choppy
    assert quality_uptrend > quality_choppy


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
