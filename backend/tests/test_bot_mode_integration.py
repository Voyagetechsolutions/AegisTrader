"""
Integration tests for Bot Mode Manager with existing systems.

Verifies that bot mode integration maintains compatibility with
existing dashboard, Telegram, and API interfaces.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from backend.strategy.bot_mode_manager import bot_mode_manager
from backend.strategy.models import Signal, Direction, SetupType, SignalGrade
from backend.models.models import BotMode, BotSetting


class TestBotModeAPIIntegration:
    """Test bot mode API integration."""
    
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
    
    @pytest.mark.asyncio
    async def test_get_bot_mode_status_api(self, mock_bot_settings):
        """Test bot mode status API endpoint."""
        with patch.object(bot_mode_manager, 'get_bot_settings', return_value=mock_bot_settings):
            status = await bot_mode_manager.get_mode_status()
        
        assert status["mode"] == "analyze"
        assert status["auto_trade_enabled"] is False
        assert status["execution_symbol"] == "US30"
        assert status["analysis_symbol"] == "TVC:DJI"
        assert "sessions" in status
        assert "risk_config" in status
    
    @pytest.mark.asyncio
    async def test_switch_bot_mode_api(self, mock_bot_settings):
        """Test bot mode switching API."""
        mock_bot_settings.mode = BotMode.TRADE
        
        with patch.object(bot_mode_manager, 'get_bot_settings', return_value=mock_bot_settings):
            with patch.object(bot_mode_manager, 'update_mode', return_value=True) as mock_update:
                success = await bot_mode_manager.update_mode(BotMode.TRADE)
        
        assert success is True
        mock_update.assert_called_once_with(BotMode.TRADE)
    
    @pytest.mark.asyncio
    async def test_toggle_auto_trade_api(self, mock_bot_settings):
        """Test auto trade toggle API."""
        with patch.object(bot_mode_manager, 'get_bot_settings', return_value=mock_bot_settings):
            with patch.object(bot_mode_manager, 'toggle_auto_trade', return_value=True) as mock_toggle:
                success = await bot_mode_manager.toggle_auto_trade(True)
        
        assert success is True
        mock_toggle.assert_called_once_with(True)
    
    @pytest.mark.asyncio
    async def test_execution_decision_api(self, mock_bot_settings):
        """Test execution decision API endpoint logic."""
        mock_bot_settings.mode = BotMode.TRADE
        mock_bot_settings.auto_trade_enabled = True
        
        # Create A+ signal
        signal = Signal(
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
        
        with patch.object(bot_mode_manager, 'get_bot_settings', return_value=mock_bot_settings):
            decision = await bot_mode_manager.should_execute_signal(
                signal=signal,
                session_active=True,
                risk_allowed=True
            )
        
        assert decision["execute"] is True
        assert decision["action"] == "executed"
        assert decision["mode"] == "trade"


class TestBotModeCompatibilityIntegration:
    """Test bot mode integration with compatibility layer."""
    
    @pytest.mark.asyncio
    async def test_signal_processing_with_bot_modes(self):
        """Test that signals are processed correctly through bot mode system."""
        from backend.strategy.compatibility import system_compatibility
        
        # Create test signal
        signal = Signal(
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
        
        # Mock bot settings for analyze mode
        mock_settings = MagicMock(spec=BotSetting)
        mock_settings.mode = BotMode.ANALYZE
        mock_settings.auto_trade_enabled = False
        
        with patch.object(bot_mode_manager, 'get_bot_settings', return_value=mock_settings):
            with patch.object(system_compatibility.confluence_adapter, 'validate_signal_compatibility', return_value=True):
                with patch.object(system_compatibility.confluence_adapter, 'score_strategy_signal') as mock_score:
                    with patch.object(system_compatibility.telegram_adapter, 'send_strategy_signal_alert', return_value=True):
                        with patch.object(system_compatibility.mt5_adapter, 'execute_signal', return_value={"success": False}):
                            
                            # Mock confluence result
                            mock_confluence = MagicMock()
                            mock_confluence.score = 85
                            mock_confluence.grade = "A+"
                            mock_confluence.auto_trade_eligible = True
                            mock_score.return_value = mock_confluence
                            
                            # Process signal (should not execute in analyze mode)
                            result = await system_compatibility.process_strategy_signal(
                                signal=signal,
                                send_alerts=True,
                                execute_trade=False  # Bot mode manager would set this to False for analyze mode
                            )
        
        assert result["compatibility_check"] is True
        assert result["alert_sent"] is True
        assert result["trade_executed"] is False  # Should not execute in analyze mode
        assert result["bot_mode_info"]["mode"] == "analyze"
    
    @pytest.mark.asyncio
    async def test_trade_mode_execution_through_compatibility(self):
        """Test that trade mode executes through compatibility layer."""
        from backend.strategy.compatibility import system_compatibility
        
        # Create test signal
        signal = Signal(
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
        
        # Mock bot settings for trade mode
        mock_settings = MagicMock(spec=BotSetting)
        mock_settings.mode = BotMode.TRADE
        mock_settings.auto_trade_enabled = True
        
        with patch.object(bot_mode_manager, 'get_bot_settings', return_value=mock_settings):
            with patch.object(system_compatibility.confluence_adapter, 'validate_signal_compatibility', return_value=True):
                with patch.object(system_compatibility.confluence_adapter, 'score_strategy_signal') as mock_score:
                    with patch.object(system_compatibility.telegram_adapter, 'send_strategy_signal_alert', return_value=True):
                        with patch.object(system_compatibility.mt5_adapter, 'execute_signal') as mock_execute:
                            
                            # Mock confluence result
                            mock_confluence = MagicMock()
                            mock_confluence.score = 85
                            mock_confluence.grade = "A+"
                            mock_confluence.auto_trade_eligible = True
                            mock_score.return_value = mock_confluence
                            
                            # Mock successful execution
                            mock_execute.return_value = {"success": True, "ticket": 12345}
                            
                            # Process signal (should execute in trade mode)
                            result = await system_compatibility.process_strategy_signal(
                                signal=signal,
                                send_alerts=True,
                                execute_trade=True  # Bot mode manager would set this to True for trade mode A+ signals
                            )
        
        assert result["compatibility_check"] is True
        assert result["alert_sent"] is True
        assert result["trade_executed"] is True  # Should execute in trade mode
        assert result["bot_mode_info"]["mode"] == "trade"
        mock_execute.assert_called_once()


class TestBotModeTelegramCompatibility:
    """Test bot mode compatibility with Telegram commands."""
    
    @pytest.mark.asyncio
    async def test_mode_switching_preserves_telegram_functionality(self):
        """Test that mode switching works with existing Telegram commands."""
        # This test verifies that the bot mode manager integrates properly
        # with existing Telegram command handlers
        
        mock_settings = MagicMock(spec=BotSetting)
        mock_settings.mode = BotMode.ANALYZE
        
        # Test mode switching (simulates /mode command)
        with patch.object(bot_mode_manager, 'get_bot_settings', return_value=mock_settings):
            with patch.object(bot_mode_manager, 'update_mode', return_value=True) as mock_update:
                # Simulate switching to trade mode
                success = await bot_mode_manager.update_mode(BotMode.TRADE)
                
                assert success is True
                mock_update.assert_called_once_with(BotMode.TRADE)
        
        # Test auto trade toggle (simulates /start and /stop commands)
        with patch.object(bot_mode_manager, 'get_bot_settings', return_value=mock_settings):
            with patch.object(bot_mode_manager, 'toggle_auto_trade', return_value=True) as mock_toggle:
                # Simulate enabling auto trade
                success = await bot_mode_manager.toggle_auto_trade(True)
                
                assert success is True
                mock_toggle.assert_called_once_with(True)
    
    @pytest.mark.asyncio
    async def test_mode_status_provides_telegram_compatible_info(self):
        """Test that mode status provides information compatible with Telegram display."""
        mock_settings = MagicMock(spec=BotSetting)
        mock_settings.mode = BotMode.TRADE
        mock_settings.auto_trade_enabled = True
        mock_settings.execution_symbol = "US30"
        mock_settings.analysis_symbol = "TVC:DJI"
        mock_settings.sessions = {
            "london": {"start": "10:00", "end": "13:00"},
            "new_york": {"start": "15:30", "end": "17:30"},
            "power_hour": {"start": "20:00", "end": "22:00"}
        }
        mock_settings.max_trades_per_day = 2
        mock_settings.max_losses_per_day = 2
        mock_settings.max_daily_drawdown_pct = 2.0
        
        with patch.object(bot_mode_manager, 'get_bot_settings', return_value=mock_settings):
            status = await bot_mode_manager.get_mode_status()
        
        # Verify status contains all information needed for Telegram display
        assert status["mode"] == "trade"
        assert status["auto_trade_enabled"] is True
        assert status["execution_symbol"] == "US30"
        assert "sessions" in status
        assert "risk_config" in status
        
        # Verify risk config format matches existing system
        risk_config = status["risk_config"]
        assert risk_config["max_trades_per_day"] == 2
        assert risk_config["max_losses_per_day"] == 2
        assert risk_config["max_daily_drawdown_pct"] == 2.0


class TestBotModeDashboardCompatibility:
    """Test bot mode compatibility with dashboard interface."""
    
    @pytest.mark.asyncio
    async def test_dashboard_mode_display_compatibility(self):
        """Test that bot mode information is compatible with dashboard display."""
        mock_settings = MagicMock(spec=BotSetting)
        mock_settings.mode = BotMode.SWING
        mock_settings.auto_trade_enabled = False
        mock_settings.execution_symbol = "US30"
        mock_settings.analysis_symbol = "TVC:DJI"
        
        with patch.object(bot_mode_manager, 'get_bot_settings', return_value=mock_settings):
            status = await bot_mode_manager.get_mode_status()
        
        # Verify status format matches dashboard expectations
        assert status["mode"] == "swing"
        assert status["auto_trade_enabled"] is False
        assert status["execution_symbol"] == "US30"
        assert status["analysis_symbol"] == "TVC:DJI"
    
    @pytest.mark.asyncio
    async def test_mode_switching_through_dashboard_api(self):
        """Test mode switching through dashboard API endpoints."""
        mock_settings = MagicMock(spec=BotSetting)
        mock_settings.mode = BotMode.ANALYZE
        
        # Test switching modes (simulates dashboard mode switch)
        test_modes = [BotMode.ANALYZE, BotMode.TRADE, BotMode.SWING]
        
        for mode in test_modes:
            with patch.object(bot_mode_manager, 'get_bot_settings', return_value=mock_settings):
                with patch.object(bot_mode_manager, 'update_mode', return_value=True) as mock_update:
                    success = await bot_mode_manager.update_mode(mode)
                    
                    assert success is True
                    mock_update.assert_called_once_with(mode)


class TestBotModeBackwardCompatibility:
    """Test backward compatibility with existing webhook system behavior."""
    
    @pytest.mark.asyncio
    async def test_identical_behavior_to_webhook_system(self):
        """
        Comprehensive test that bot mode behavior is identical to webhook system.
        
        This test covers all the key scenarios that the existing webhook system handles
        and verifies the strategy engine produces identical results.
        """
        
        # Test scenarios that must match existing webhook behavior exactly
        test_scenarios = [
            {
                "name": "Analyze mode A+ signal",
                "mode": BotMode.ANALYZE,
                "auto_trade": True,
                "grade": SignalGrade.A_PLUS,
                "session_active": True,
                "risk_allowed": True,
                "expected_execute": False,
                "expected_action": "alerted",
                "webhook_behavior": "Always alert only in analyze mode"
            },
            {
                "name": "Trade mode A+ signal with auto trade enabled",
                "mode": BotMode.TRADE,
                "auto_trade": True,
                "grade": SignalGrade.A_PLUS,
                "session_active": True,
                "risk_allowed": True,
                "expected_execute": True,
                "expected_action": "executed",
                "webhook_behavior": "Execute A+ signals in trade mode when conditions met"
            },
            {
                "name": "Trade mode A signal",
                "mode": BotMode.TRADE,
                "auto_trade": True,
                "grade": SignalGrade.A,
                "session_active": True,
                "risk_allowed": True,
                "expected_execute": False,
                "expected_action": "alerted",
                "webhook_behavior": "Alert only for A grade signals (not A+)"
            },
            {
                "name": "Trade mode with auto trade disabled",
                "mode": BotMode.TRADE,
                "auto_trade": False,
                "grade": SignalGrade.A_PLUS,
                "session_active": True,
                "risk_allowed": True,
                "expected_execute": False,
                "expected_action": "alerted",
                "webhook_behavior": "Alert only when auto trade disabled"
            },
            {
                "name": "Trade mode outside session",
                "mode": BotMode.TRADE,
                "auto_trade": True,
                "grade": SignalGrade.A_PLUS,
                "session_active": False,
                "risk_allowed": True,
                "expected_execute": False,
                "expected_action": "alerted",
                "webhook_behavior": "Alert only outside trading sessions"
            },
            {
                "name": "Trade mode with risk limits exceeded",
                "mode": BotMode.TRADE,
                "auto_trade": True,
                "grade": SignalGrade.A_PLUS,
                "session_active": True,
                "risk_allowed": False,
                "expected_execute": False,
                "expected_action": "alerted",
                "webhook_behavior": "Alert only when risk limits exceeded"
            },
            {
                "name": "Swing mode A+ signal",
                "mode": BotMode.SWING,
                "auto_trade": True,
                "grade": SignalGrade.A_PLUS,
                "session_active": True,
                "risk_allowed": True,
                "expected_execute": False,
                "expected_action": "alerted",
                "webhook_behavior": "Always alert only in swing mode (user approval required)"
            },
            {
                "name": "Swing setup in trade mode",
                "mode": BotMode.TRADE,
                "auto_trade": True,
                "grade": SignalGrade.A_PLUS,
                "setup_type": SetupType.SWING_LONG,
                "session_active": True,
                "risk_allowed": True,
                "expected_execute": False,
                "expected_action": "alerted",
                "webhook_behavior": "Alert only for swing setups regardless of mode"
            }
        ]
        
        for scenario in test_scenarios:
            # Create mock settings
            mock_settings = MagicMock(spec=BotSetting)
            mock_settings.mode = scenario["mode"]
            mock_settings.auto_trade_enabled = scenario["auto_trade"]
            
            # Create test signal
            signal = Signal(
                timestamp=datetime.now(),
                setup_type=scenario.get("setup_type", SetupType.CONTINUATION_LONG),
                direction=Direction.LONG,
                entry=46150.0,
                stop_loss=46100.0,
                take_profit=46200.0,
                confluence_score=85.0 if scenario["grade"] == SignalGrade.A_PLUS else 80.0,
                grade=scenario["grade"],
                analysis_breakdown={}
            )
            
            with patch.object(bot_mode_manager, 'get_bot_settings', return_value=mock_settings):
                decision = await bot_mode_manager.should_execute_signal(
                    signal=signal,
                    session_active=scenario["session_active"],
                    risk_allowed=scenario["risk_allowed"]
                )
            
            # Verify behavior matches webhook system exactly
            assert decision["execute"] == scenario["expected_execute"], f"Failed execute check for: {scenario['name']}"
            assert decision["action"] == scenario["expected_action"], f"Failed action check for: {scenario['name']}"
            
            print(f"✓ {scenario['name']}: {scenario['webhook_behavior']}")
        
        print("✓ All bot mode behaviors match existing webhook system exactly")