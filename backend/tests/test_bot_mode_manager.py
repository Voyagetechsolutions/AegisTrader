"""
Tests for Bot Mode Manager.

Verifies that bot mode management maintains identical behavior
to the existing webhook-based system.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from backend.strategy.bot_mode_manager import BotModeManager
from backend.strategy.models import Signal, Direction, SetupType, SignalGrade
from backend.models.models import BotMode, BotSetting


class TestBotModeManager:
    """Test bot mode manager functionality."""
    
    @pytest.fixture
    def bot_mode_manager(self):
        """Create bot mode manager instance."""
        return BotModeManager()
    
    @pytest.fixture
    def mock_bot_settings(self):
        """Create mock bot settings."""
        settings = MagicMock(spec=BotSetting)
        settings.mode = BotMode.ANALYZE
        settings.auto_trade_enabled = False
        settings.execution_symbol = "US30"
        settings.analysis_symbol = "TVC:DJI"
        settings.sessions = {
            "london": {"start": "10:00", "end": "13:00"},
            "new_york": {"start": "15:30", "end": "17:30"},
            "power_hour": {"start": "20:00", "end": "22:00"}
        }
        settings.max_trades_per_day = 2
        settings.max_losses_per_day = 2
        settings.max_daily_drawdown_pct = 2.0
        settings.max_slippage_points = 10.0
        return settings
    
    @pytest.fixture
    def sample_signal(self):
        """Create sample signal for testing."""
        return Signal(
            timestamp=datetime.now(),
            setup_type=SetupType.CONTINUATION_LONG,
            direction=Direction.LONG,
            entry=46150.0,
            stop_loss=46100.0,
            take_profit=46200.0,
            confluence_score=85.0,
            grade=SignalGrade.A_PLUS,
            analysis_breakdown={}
        )
    
    @pytest.mark.asyncio
    async def test_analyze_mode_behavior(self, bot_mode_manager, mock_bot_settings, sample_signal):
        """Test that analyze mode always alerts only."""
        mock_bot_settings.mode = BotMode.ANALYZE
        
        with patch.object(bot_mode_manager, 'get_bot_settings', return_value=mock_bot_settings):
            decision = await bot_mode_manager.should_execute_signal(
                signal=sample_signal,
                session_active=True,
                risk_allowed=True
            )
        
        assert decision["execute"] is False
        assert decision["action"] == "alerted"
        assert decision["reason"] == "Analyze mode - alert only"
        assert decision["mode"] == "analyze"
    
    @pytest.mark.asyncio
    async def test_trade_mode_a_plus_execution(self, bot_mode_manager, mock_bot_settings, sample_signal):
        """Test that trade mode executes A+ signals when conditions met."""
        mock_bot_settings.mode = BotMode.TRADE
        mock_bot_settings.auto_trade_enabled = True
        sample_signal.grade = SignalGrade.A_PLUS
        
        with patch.object(bot_mode_manager, 'get_bot_settings', return_value=mock_bot_settings):
            decision = await bot_mode_manager.should_execute_signal(
                signal=sample_signal,
                session_active=True,
                risk_allowed=True
            )
        
        assert decision["execute"] is True
        assert decision["action"] == "executed"
        assert decision["reason"] == "A+ grade in Trade mode - executing"
        assert decision["mode"] == "trade"
    
    @pytest.mark.asyncio
    async def test_trade_mode_grade_a_alert_only(self, bot_mode_manager, mock_bot_settings, sample_signal):
        """Test that trade mode alerts only for A grade signals."""
        mock_bot_settings.mode = BotMode.TRADE
        mock_bot_settings.auto_trade_enabled = True
        sample_signal.grade = SignalGrade.A
        
        with patch.object(bot_mode_manager, 'get_bot_settings', return_value=mock_bot_settings):
            decision = await bot_mode_manager.should_execute_signal(
                signal=sample_signal,
                session_active=True,
                risk_allowed=True
            )
        
        assert decision["execute"] is False
        assert decision["action"] == "alerted"
        assert decision["reason"] == "Grade A - alert only"
        assert decision["mode"] == "trade"
    
    @pytest.mark.asyncio
    async def test_trade_mode_auto_trade_disabled(self, bot_mode_manager, mock_bot_settings, sample_signal):
        """Test that trade mode alerts only when auto trade disabled."""
        mock_bot_settings.mode = BotMode.TRADE
        mock_bot_settings.auto_trade_enabled = False
        sample_signal.grade = SignalGrade.A_PLUS
        
        with patch.object(bot_mode_manager, 'get_bot_settings', return_value=mock_bot_settings):
            decision = await bot_mode_manager.should_execute_signal(
                signal=sample_signal,
                session_active=True,
                risk_allowed=True
            )
        
        assert decision["execute"] is False
        assert decision["action"] == "alerted"
        assert decision["reason"] == "Auto trading disabled - alert only"
        assert decision["mode"] == "trade"
    
    @pytest.mark.asyncio
    async def test_trade_mode_outside_session(self, bot_mode_manager, mock_bot_settings, sample_signal):
        """Test that trade mode alerts only outside trading session."""
        mock_bot_settings.mode = BotMode.TRADE
        mock_bot_settings.auto_trade_enabled = True
        sample_signal.grade = SignalGrade.A_PLUS
        
        with patch.object(bot_mode_manager, 'get_bot_settings', return_value=mock_bot_settings):
            decision = await bot_mode_manager.should_execute_signal(
                signal=sample_signal,
                session_active=False,  # Outside session
                risk_allowed=True
            )
        
        assert decision["execute"] is False
        assert decision["action"] == "alerted"
        assert decision["reason"] == "Outside trading session - alert only"
        assert decision["mode"] == "trade"
    
    @pytest.mark.asyncio
    async def test_trade_mode_risk_limits_exceeded(self, bot_mode_manager, mock_bot_settings, sample_signal):
        """Test that trade mode alerts only when risk limits exceeded."""
        mock_bot_settings.mode = BotMode.TRADE
        mock_bot_settings.auto_trade_enabled = True
        sample_signal.grade = SignalGrade.A_PLUS
        
        with patch.object(bot_mode_manager, 'get_bot_settings', return_value=mock_bot_settings):
            decision = await bot_mode_manager.should_execute_signal(
                signal=sample_signal,
                session_active=True,
                risk_allowed=False  # Risk limits exceeded
            )
        
        assert decision["execute"] is False
        assert decision["action"] == "alerted"
        assert decision["reason"] == "Risk limits exceeded - alert only"
        assert decision["mode"] == "trade"
    
    @pytest.mark.asyncio
    async def test_swing_mode_behavior(self, bot_mode_manager, mock_bot_settings, sample_signal):
        """Test that swing mode always alerts only."""
        mock_bot_settings.mode = BotMode.SWING
        sample_signal.grade = SignalGrade.A_PLUS
        
        with patch.object(bot_mode_manager, 'get_bot_settings', return_value=mock_bot_settings):
            decision = await bot_mode_manager.should_execute_signal(
                signal=sample_signal,
                session_active=True,
                risk_allowed=True
            )
        
        assert decision["execute"] is False
        assert decision["action"] == "alerted"
        assert decision["reason"] == "Swing mode - alert only"
        assert decision["mode"] == "swing"
    
    @pytest.mark.asyncio
    async def test_swing_setup_in_trade_mode(self, bot_mode_manager, mock_bot_settings, sample_signal):
        """Test that swing setups alert only even in trade mode."""
        mock_bot_settings.mode = BotMode.TRADE
        mock_bot_settings.auto_trade_enabled = True
        sample_signal.setup_type = SetupType.SWING_LONG  # Swing setup
        sample_signal.grade = SignalGrade.A_PLUS
        
        with patch.object(bot_mode_manager, 'get_bot_settings', return_value=mock_bot_settings):
            decision = await bot_mode_manager.should_execute_signal(
                signal=sample_signal,
                session_active=True,
                risk_allowed=True
            )
        
        assert decision["execute"] is False
        assert decision["action"] == "alerted"
        assert decision["reason"] == "Swing setup - user approval required"
        assert decision["mode"] == "trade"
    
    @pytest.mark.asyncio
    async def test_get_current_mode(self, bot_mode_manager, mock_bot_settings):
        """Test getting current bot mode."""
        mock_bot_settings.mode = BotMode.TRADE
        
        with patch.object(bot_mode_manager, 'get_bot_settings', return_value=mock_bot_settings):
            mode = await bot_mode_manager.get_current_mode()
        
        assert mode == BotMode.TRADE
    
    @pytest.mark.asyncio
    async def test_get_current_mode_no_settings(self, bot_mode_manager):
        """Test getting current mode when no settings found."""
        with patch.object(bot_mode_manager, 'get_bot_settings', return_value=None):
            mode = await bot_mode_manager.get_current_mode()
        
        assert mode == BotMode.ANALYZE  # Default
    
    @pytest.mark.asyncio
    async def test_is_auto_trade_enabled(self, bot_mode_manager, mock_bot_settings):
        """Test checking auto trade status."""
        mock_bot_settings.auto_trade_enabled = True
        
        with patch.object(bot_mode_manager, 'get_bot_settings', return_value=mock_bot_settings):
            enabled = await bot_mode_manager.is_auto_trade_enabled()
        
        assert enabled is True
    
    @pytest.mark.asyncio
    async def test_get_execution_symbol(self, bot_mode_manager, mock_bot_settings):
        """Test getting execution symbol."""
        mock_bot_settings.execution_symbol = "US30"
        
        with patch.object(bot_mode_manager, 'get_bot_settings', return_value=mock_bot_settings):
            symbol = await bot_mode_manager.get_execution_symbol()
        
        assert symbol == "US30"
    
    @pytest.mark.asyncio
    async def test_get_session_config(self, bot_mode_manager, mock_bot_settings):
        """Test getting session configuration."""
        expected_sessions = {
            "london": {"start": "10:00", "end": "13:00"},
            "new_york": {"start": "15:30", "end": "17:30"},
            "power_hour": {"start": "20:00", "end": "22:00"}
        }
        mock_bot_settings.sessions = expected_sessions
        
        with patch.object(bot_mode_manager, 'get_bot_settings', return_value=mock_bot_settings):
            sessions = await bot_mode_manager.get_session_config()
        
        assert sessions == expected_sessions
    
    @pytest.mark.asyncio
    async def test_get_risk_config(self, bot_mode_manager, mock_bot_settings):
        """Test getting risk configuration."""
        with patch.object(bot_mode_manager, 'get_bot_settings', return_value=mock_bot_settings):
            risk_config = await bot_mode_manager.get_risk_config()
        
        expected = {
            "max_trades_per_day": 2,
            "max_losses_per_day": 2,
            "max_daily_drawdown_pct": 2.0,
            "max_slippage_points": 10.0
        }
        assert risk_config == expected
    
    @pytest.mark.asyncio
    async def test_cache_functionality(self, bot_mode_manager, mock_bot_settings):
        """Test that settings are cached properly."""
        user_id = uuid4()
        
        # Mock the database access directly instead of the method being tested
        with patch('backend.strategy.bot_mode_manager.get_db') as mock_get_db:
            # Create mock database session
            mock_db = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_bot_settings
            mock_db.execute.return_value = mock_result
            mock_db.close = AsyncMock()
            
            # Mock the async generator
            async def mock_db_generator():
                yield mock_db
            
            mock_get_db.return_value = mock_db_generator()
            
            # First call should fetch from database
            settings1 = await bot_mode_manager.get_bot_settings(user_id)
            
            # Second call should use cache (within cache duration)
            settings2 = await bot_mode_manager.get_bot_settings(user_id)
            
            # Should only call database once due to caching
            assert mock_db.execute.call_count == 1
            assert settings1 == settings2
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, bot_mode_manager):
        """Test cache invalidation."""
        user_id = uuid4()
        
        # Add something to cache
        bot_mode_manager._cached_settings[str(user_id)] = "test"
        bot_mode_manager._cache_expiry[str(user_id)] = datetime.now()
        
        # Invalidate cache
        await bot_mode_manager.invalidate_cache(user_id)
        
        # Cache should be empty
        assert str(user_id) not in bot_mode_manager._cached_settings
        assert str(user_id) not in bot_mode_manager._cache_expiry


class TestBotModeCompatibility:
    """Test bot mode compatibility with existing systems."""
    
    @pytest.mark.asyncio
    async def test_mode_behavior_identical_to_webhook_system(self):
        """
        Test that bot mode behavior is identical to existing webhook system.
        
        This test verifies the core requirement that the strategy engine
        maintains identical behavior to the webhook-based system.
        """
        bot_mode_manager = BotModeManager()
        
        # Test cases that should match existing webhook behavior
        test_cases = [
            {
                "mode": BotMode.ANALYZE,
                "auto_trade": True,
                "grade": SignalGrade.A_PLUS,
                "session_active": True,
                "risk_allowed": True,
                "expected_execute": False,
                "expected_reason": "Analyze mode - alert only"
            },
            {
                "mode": BotMode.TRADE,
                "auto_trade": True,
                "grade": SignalGrade.A_PLUS,
                "session_active": True,
                "risk_allowed": True,
                "expected_execute": True,
                "expected_reason": "A+ grade in Trade mode - executing"
            },
            {
                "mode": BotMode.TRADE,
                "auto_trade": True,
                "grade": SignalGrade.A,
                "session_active": True,
                "risk_allowed": True,
                "expected_execute": False,
                "expected_reason": "Grade A - alert only"
            },
            {
                "mode": BotMode.SWING,
                "auto_trade": True,
                "grade": SignalGrade.A_PLUS,
                "session_active": True,
                "risk_allowed": True,
                "expected_execute": False,
                "expected_reason": "Swing mode - alert only"
            }
        ]
        
        for case in test_cases:
            # Create mock settings
            mock_settings = MagicMock(spec=BotSetting)
            mock_settings.mode = case["mode"]
            mock_settings.auto_trade_enabled = case["auto_trade"]
            
            # Create test signal
            signal = Signal(
                timestamp=datetime.now(),
                setup_type=SetupType.CONTINUATION_LONG,
                direction=Direction.LONG,
                entry=46150.0,
                stop_loss=46100.0,
                take_profit=46200.0,
                confluence_score=85.0 if case["grade"] == SignalGrade.A_PLUS else 80.0,
                grade=case["grade"],
                analysis_breakdown={}
            )
            
            with patch.object(bot_mode_manager, 'get_bot_settings', return_value=mock_settings):
                decision = await bot_mode_manager.should_execute_signal(
                    signal=signal,
                    session_active=case["session_active"],
                    risk_allowed=case["risk_allowed"]
                )
            
            assert decision["execute"] == case["expected_execute"], f"Failed for case: {case}"
            assert case["expected_reason"] in decision["reason"], f"Failed for case: {case}"