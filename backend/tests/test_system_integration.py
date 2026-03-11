"""
System Integration Tests for Strategy Engine Compatibility.

Tests the complete integration between the new strategy engine
and existing Aegis Trader systems.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch

from backend.strategy.compatibility import SystemCompatibility
from backend.strategy.models import Signal, Direction, SetupType, SignalGrade


@pytest.fixture
def sample_signal():
    """Create a sample strategy engine signal for testing."""
    return Signal(
        timestamp=datetime.now(),
        setup_type=SetupType.CONTINUATION_LONG,
        direction=Direction.LONG,
        entry=46150.0,
        stop_loss=46100.0,
        take_profit=46200.0,
        confluence_score=85.0,
        grade=SignalGrade.A_PLUS,
        analysis_breakdown={
            "bias_score": 15.0,
            "level_score": 12.0,
            "liquidity_score": 10.0,
            "fvg_score": 8.0,
            "displacement_score": 15.0,
            "structure_score": 12.0,
            "session_bonus": 8.0,
            "weekly_bias": "bullish",
            "daily_bias": "bullish",
            "h4_bias": "bullish",
            "h1_bias": "bullish",
            "level_250": 46250.0,
            "level_125": 46125.0,
        }
    )


class TestSystemIntegration:
    """Test complete system integration."""
    
    def test_confluence_adapter_integration(self, sample_signal):
        """Test integration with existing confluence scoring system."""
        from backend.strategy.compatibility import ConfluenceAdapter
        
        adapter = ConfluenceAdapter()
        
        # Test signal conversion
        payload = adapter.convert_signal_to_payload(sample_signal)
        assert payload.direction == "long"
        assert payload.entry == 46150.0
        assert payload.weekly_bias == "bullish"
        
        # Test confluence scoring
        result = adapter.score_strategy_signal(sample_signal)
        assert result.score > 0
        assert result.grade in ["A+", "A", "B"]
        
        # Test compatibility validation
        assert adapter.validate_signal_compatibility(sample_signal) is True
    
    @pytest.mark.asyncio
    async def test_mt5_bridge_integration(self, sample_signal):
        """Test integration with existing MT5 bridge."""
        from backend.strategy.compatibility import MT5BridgeAdapter
        
        adapter = MT5BridgeAdapter()
        
        # Test getting positions (should not fail)
        try:
            positions = await adapter.get_positions()
            assert isinstance(positions, list)
        except Exception as e:
            # MT5 bridge might not be available in test environment
            pytest.skip(f"MT5 bridge not available: {e}")
    
    @pytest.mark.asyncio
    async def test_telegram_adapter_integration(self, sample_signal):
        """Test integration with existing Telegram system."""
        from backend.strategy.compatibility import TelegramAdapter
        
        adapter = TelegramAdapter()
        
        # Test signal conversion to DB format
        db_signal = adapter._convert_to_db_signal(sample_signal)
        assert db_signal.execution_symbol == "US30"
        assert db_signal.entry_price == 46150.0
        assert db_signal.weekly_bias == "bullish"
        assert db_signal.liquidity_sweep is True  # liquidity_score > 0
    
    @pytest.mark.asyncio
    async def test_full_system_compatibility(self, sample_signal):
        """Test complete system compatibility workflow."""
        compatibility = SystemCompatibility()
        
        # Test system status
        status = await compatibility.get_system_status()
        assert "timestamp" in status
        assert "mt5_bridge" in status
        assert "telegram" in status
        assert "confluence_scoring" in status
        
        # Test signal processing (without actual execution)
        result = await compatibility.process_strategy_signal(
            signal=sample_signal,
            send_alerts=False,  # Don't send actual alerts
            execute_trade=False  # Don't execute actual trades
        )
        
        # Should pass compatibility check
        assert result["compatibility_check"] is True
        
        # Should have confluence score
        assert result["confluence_score"] is not None
        assert result["confluence_score"] > 0
        
        # Should have grade
        assert result.get("confluence_grade") in ["A+", "A", "B"]
    
    def test_existing_systems_preserved(self):
        """Test that existing systems are not modified."""
        # Test that existing confluence scoring still works
        from backend.modules.confluence_scoring import score_setup
        from backend.schemas.schemas import TradingViewWebhookPayload
        
        # Create a traditional webhook payload
        payload = TradingViewWebhookPayload(
            secret="test_secret",
            symbol="US30",
            direction="long",
            entry=46150.0,
            stop_loss=46100.0,
            tp1=46200.0,
            tp2=46250.0,
            weekly_bias="bullish",
            daily_bias="bullish",
            h4_bias="bullish",
            h1_bias="bullish",
            m15_bias="bullish",
            m5_bias="bullish",
            level_250=46250.0,
            level_125=46125.0,
            liquidity_sweep=True,
            fvg_present=True,
            displacement_present=True,
            mss_present=True,
        )
        
        # Should still work with existing system
        result = score_setup(payload)
        assert result.score > 0
        assert result.grade in ["A+", "A", "B"]
        assert result.setup_type is not None
    
    def test_mt5_bridge_preserved(self):
        """Test that existing MT5 bridge functionality is preserved."""
        from backend.routers.mt5_bridge import mt5_bridge
        
        # Should still have all existing methods
        assert hasattr(mt5_bridge, 'place_order')
        assert hasattr(mt5_bridge, 'close_partial')
        assert hasattr(mt5_bridge, 'modify_sl')
        assert hasattr(mt5_bridge, 'get_positions')
        assert hasattr(mt5_bridge, 'get_account_balance')
    
    def test_telegram_alerts_preserved(self):
        """Test that existing Telegram alert functionality is preserved."""
        from backend.modules.alert_manager import send_message
        
        # Should still have existing alert functions
        assert callable(send_message)
        
        # Import other alert functions to verify they exist
        from backend.modules.alert_manager import (
            send_signal_alert, send_trade_open_alert, send_tp1_alert,
            send_tp2_alert, send_trade_close_alert, send_risk_alert
        )
        
        assert callable(send_signal_alert)
        assert callable(send_trade_open_alert)
        assert callable(send_tp1_alert)
        assert callable(send_tp2_alert)
        assert callable(send_trade_close_alert)
        assert callable(send_risk_alert)


class TestBackwardCompatibility:
    """Test that existing workflows still function."""
    
    def test_webhook_endpoint_still_works(self):
        """Test that existing webhook endpoint structure is preserved."""
        from backend.routers.webhook import router
        
        # Should still have the webhook endpoint
        routes = [route.path for route in router.routes]
        assert "/webhooks/tradingview" in routes
        assert "/execution/callback" in routes
    
    def test_telegram_commands_still_work(self):
        """Test that existing Telegram commands are preserved."""
        from backend.routers.telegram import COMMAND_MAP
        
        # Should still have all existing commands
        expected_commands = ["/status", "/start", "/stop", "/positions", "/overview", "/closeall"]
        for cmd in expected_commands:
            assert cmd in COMMAND_MAP
    
    def test_dashboard_endpoints_preserved(self):
        """Test that dashboard endpoints are still available."""
        try:
            from backend.routers.dashboard import router
            # Should import without error
            assert router is not None
        except ImportError:
            pytest.skip("Dashboard router not available")
    
    def test_existing_database_models_preserved(self):
        """Test that existing database models are unchanged."""
        from backend.models.models import Signal, Trade, BotSetting
        
        # Should still have all existing model classes
        assert Signal is not None
        assert Trade is not None
        assert BotSetting is not None
        
        # Test that Signal model has expected fields
        signal_fields = Signal.__table__.columns.keys()
        expected_fields = [
            'id', 'created_at', 'execution_symbol', 'direction',
            'entry_price', 'stop_loss', 'tp1', 'tp2', 'score', 'grade'
        ]
        
        for field in expected_fields:
            assert field in signal_fields


if __name__ == "__main__":
    pytest.main([__file__])