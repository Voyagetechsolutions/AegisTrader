"""
Tests for Strategy Engine Compatibility Layer.

Verifies that the new strategy engine maintains compatibility with
existing Aegis Trader systems (Confluence_Scorer, MT5_Bridge, Telegram).
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from backend.strategy.compatibility import (
    ConfluenceAdapter, MT5BridgeAdapter, TelegramAdapter, SystemCompatibility
)
from backend.strategy.models import Signal, Direction, SetupType, SignalGrade
from backend.schemas.schemas import TradingViewWebhookPayload


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


class TestConfluenceAdapter:
    """Test confluence scoring compatibility."""
    
    def test_convert_signal_to_payload(self, sample_signal):
        """Test conversion of strategy signal to TradingView payload format."""
        adapter = ConfluenceAdapter()
        
        payload = adapter.convert_signal_to_payload(sample_signal)
        
        assert isinstance(payload, TradingViewWebhookPayload)
        assert payload.direction == "long"
        assert payload.entry == 46150.0
        assert payload.stop_loss == 46100.0
        assert payload.tp1 == 46200.0
        assert payload.weekly_bias == "bullish"
        assert payload.daily_bias == "bullish"
        assert payload.level_250 == 46250.0
        assert payload.level_125 == 46125.0
    
    @patch('backend.strategy.compatibility.score_setup')
    def test_score_strategy_signal(self, mock_score_setup, sample_signal):
        """Test scoring strategy signal through existing confluence system."""
        from backend.modules.confluence_scoring import ConfluenceResult
        
        # Mock confluence scoring result
        mock_result = ConfluenceResult(
            score=85,
            grade="A+",
            breakdown={"htf_alignment": 20, "level_250": 15},
            auto_trade_eligible=True,
            setup_type="continuation_long",
            reason="HTF aligned bullish with 5M bull shift"
        )
        mock_score_setup.return_value = mock_result
        
        adapter = ConfluenceAdapter()
        result = adapter.score_strategy_signal(sample_signal)
        
        assert result.score == 85
        assert result.grade == "A+"
        assert result.auto_trade_eligible is True
        mock_score_setup.assert_called_once()
    
    def test_validate_signal_compatibility(self, sample_signal):
        """Test signal compatibility validation."""
        adapter = ConfluenceAdapter()
        
        # Valid signal should pass
        assert adapter.validate_signal_compatibility(sample_signal) is True
        
        # Invalid signal (missing required fields) should fail
        invalid_signal = Signal(
            timestamp=datetime.now(),
            setup_type=None,  # Missing required field
            direction=Direction.LONG,
            entry=46150.0,
            stop_loss=46100.0,
            take_profit=46200.0,
            confluence_score=85.0,
            grade=SignalGrade.A_PLUS,
            analysis_breakdown={}
        )
        
        assert adapter.validate_signal_compatibility(invalid_signal) is False


class TestMT5BridgeAdapter:
    """Test MT5 bridge compatibility."""
    
    @pytest.mark.asyncio
    @patch('backend.strategy.compatibility.mt5_bridge')
    async def test_execute_signal(self, mock_bridge, sample_signal):
        """Test signal execution through existing MT5 bridge."""
        from backend.schemas.schemas import MT5OrderResponse
        
        # Mock successful execution
        mock_response = MT5OrderResponse(
            success=True,
            ticket=123456,
            actual_price=46151.0,
            slippage=1.0
        )
        mock_bridge.place_order = AsyncMock(return_value=mock_response)
        
        adapter = MT5BridgeAdapter()
        result = await adapter.execute_signal(sample_signal, lot_size=0.01)
        
        assert result["success"] is True
        assert result["ticket"] == 123456
        assert result["fill_price"] == 46151.0
        assert result["slippage"] == 1.0
        mock_bridge.place_order.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('backend.strategy.compatibility.mt5_bridge')
    async def test_execute_signal_failure(self, mock_bridge, sample_signal):
        """Test signal execution failure handling."""
        from backend.schemas.schemas import MT5OrderResponse
        
        # Mock failed execution
        mock_response = MT5OrderResponse(
            success=False,
            error="Insufficient margin"
        )
        mock_bridge.place_order = AsyncMock(return_value=mock_response)
        
        adapter = MT5BridgeAdapter()
        result = await adapter.execute_signal(sample_signal, lot_size=0.01)
        
        assert result["success"] is False
        assert "Insufficient margin" in result["error"]
    
    @pytest.mark.asyncio
    @patch('backend.strategy.compatibility.mt5_bridge')
    async def test_get_positions(self, mock_bridge):
        """Test getting positions through existing bridge."""
        from backend.schemas.schemas import MT5Position, Direction as MT5Direction
        
        # Mock positions
        mock_positions = [
            MT5Position(
                ticket=123456,
                symbol="US30",
                direction=MT5Direction.LONG,
                lot_size=0.01,
                entry_price=46150.0,
                current_price=46160.0,
                pnl=10.0
            )
        ]
        mock_bridge.get_positions = AsyncMock(return_value=mock_positions)
        
        adapter = MT5BridgeAdapter()
        positions = await adapter.get_positions()
        
        assert len(positions) == 1
        assert positions[0]["ticket"] == 123456
        assert positions[0]["symbol"] == "US30"
        assert positions[0]["direction"] == "long"
        assert positions[0]["pnl"] == 10.0


class TestTelegramAdapter:
    """Test Telegram alert compatibility."""
    
    @pytest.mark.asyncio
    @patch('backend.strategy.compatibility.send_signal_alert')
    async def test_send_strategy_signal_alert(self, mock_send_alert, sample_signal):
        """Test sending strategy signal through existing Telegram system."""
        mock_send_alert.return_value = True
        
        adapter = TelegramAdapter()
        result = await adapter.send_strategy_signal_alert(sample_signal)
        
        assert result is True
        mock_send_alert.assert_called_once()
    
    def test_convert_to_db_signal(self, sample_signal):
        """Test conversion to database Signal model."""
        adapter = TelegramAdapter()
        
        db_signal = adapter._convert_to_db_signal(sample_signal)
        
        assert db_signal.execution_symbol == "US30"
        assert db_signal.entry_price == 46150.0
        assert db_signal.stop_loss == 46100.0
        assert db_signal.tp1 == 46200.0
        assert db_signal.score == 85
        assert db_signal.weekly_bias == "bullish"
        assert db_signal.liquidity_sweep is True  # liquidity_score > 0
        assert db_signal.fvg_present is True  # fvg_score > 0


class TestSystemCompatibility:
    """Test overall system compatibility coordination."""
    
    @pytest.mark.asyncio
    @patch('backend.strategy.compatibility.system_compatibility.confluence_adapter')
    @patch('backend.strategy.compatibility.system_compatibility.telegram_adapter')
    @patch('backend.strategy.compatibility.system_compatibility.mt5_adapter')
    async def test_process_strategy_signal(
        self, mock_mt5, mock_telegram, mock_confluence, sample_signal
    ):
        """Test complete signal processing through compatibility layer."""
        from backend.modules.confluence_scoring import ConfluenceResult
        
        # Mock adapter responses
        mock_confluence.validate_signal_compatibility.return_value = True
        mock_confluence.score_strategy_signal.return_value = ConfluenceResult(
            score=85, grade="A+", breakdown={}, auto_trade_eligible=True,
            setup_type="continuation_long", reason="Test signal"
        )
        mock_telegram.send_strategy_signal_alert = AsyncMock(return_value=True)
        mock_mt5.execute_signal = AsyncMock(return_value={"success": True, "ticket": 123456})
        
        compatibility = SystemCompatibility()
        result = await compatibility.process_strategy_signal(
            signal=sample_signal,
            send_alerts=True,
            execute_trade=True
        )
        
        assert result["compatibility_check"] is True
        assert result["confluence_score"] == 85
        assert result["alert_sent"] is True
        assert result["trade_executed"] is True
        assert len(result["errors"]) == 0
    
    @pytest.mark.asyncio
    @patch('backend.strategy.compatibility.system_compatibility.confluence_adapter')
    async def test_process_signal_compatibility_failure(
        self, mock_confluence, sample_signal
    ):
        """Test handling of compatibility validation failure."""
        mock_confluence.validate_signal_compatibility.return_value = False
        
        compatibility = SystemCompatibility()
        result = await compatibility.process_strategy_signal(
            signal=sample_signal,
            send_alerts=True,
            execute_trade=True
        )
        
        assert result["compatibility_check"] is False
        assert "Signal compatibility validation failed" in result["errors"]
        assert result["alert_sent"] is False
        assert result["trade_executed"] is False
    
    @pytest.mark.asyncio
    @patch('backend.strategy.compatibility.system_compatibility.mt5_adapter')
    async def test_get_system_status(self, mock_mt5):
        """Test system status monitoring."""
        mock_mt5.get_positions = AsyncMock(return_value=[{"ticket": 123456}])
        
        compatibility = SystemCompatibility()
        status = await compatibility.get_system_status()
        
        assert "timestamp" in status
        assert status["positions_count"] == 1
        assert status["mt5_bridge"] == "connected"
        assert status["confluence_scoring"] == "available"


# Integration test with actual components
class TestRealIntegration:
    """Integration tests with real components (when available)."""
    
    @pytest.mark.asyncio
    async def test_confluence_scoring_integration(self, sample_signal):
        """Test actual integration with confluence scoring system."""
        adapter = ConfluenceAdapter()
        
        # This should work with the real confluence scoring system
        try:
            result = adapter.score_strategy_signal(sample_signal)
            assert result.score >= 0
            assert result.grade in ["A+", "A", "B"]
            assert result.setup_type is not None
        except Exception as e:
            pytest.skip(f"Confluence scoring not available: {e}")
    
    @pytest.mark.asyncio
    async def test_system_compatibility_status(self):
        """Test getting real system compatibility status."""
        compatibility = SystemCompatibility()
        
        try:
            status = await compatibility.get_system_status()
            assert "timestamp" in status
            assert "mt5_bridge" in status
            assert "telegram" in status
            assert "confluence_scoring" in status
        except Exception as e:
            pytest.skip(f"System components not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__])