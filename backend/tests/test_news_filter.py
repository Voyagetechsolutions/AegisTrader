"""
Test suite for News Filter component (Task 3.1)
Tests Requirements 17.1-17.7 from dual-engine-strategy-system spec
"""

import pytest
from datetime import datetime, timedelta
import pytz
from unittest.mock import AsyncMock, MagicMock

from backend.modules.news_filter import (
    check_news_blackout,
    NewsCheckResult,
    NEWS_BUFFER_BEFORE,
    NEWS_BUFFER_AFTER,
    _is_high_impact,
)
from backend.models.models import NewsEvent


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock()
    return db


@pytest.fixture
def sample_news_event():
    """Create a sample high-impact news event."""
    return NewsEvent(
        title="US CPI Release",
        country="US",
        currency="USD",
        impact="high",
        starts_at=datetime(2024, 1, 15, 14, 30, tzinfo=pytz.UTC),
        is_major=True,
        source="manual",
    )


class TestNewsFilterBasics:
    """Test basic news filter functionality."""
    
    def test_high_impact_event_detection(self):
        """Test that high-impact events are correctly identified."""
        # CPI, NFP, FOMC, Fed speeches should be detected
        assert _is_high_impact("US CPI Release")
        assert _is_high_impact("Non-Farm Payrolls")
        assert _is_high_impact("FOMC Meeting")
        assert _is_high_impact("Fed Chair Powell Speech")
        assert _is_high_impact("Federal Reserve Rate Decision")
        
        # Non-high-impact events should not be detected
        assert not _is_high_impact("Random Economic Data")
        assert not _is_high_impact("Stock Market Update")
    
    @pytest.mark.asyncio
    async def test_bypass_mode(self, mock_db):
        """Test that bypass mode disables the filter."""
        from backend.config import settings
        original_bypass = settings.news_filter_bypass
        
        try:
            settings.news_filter_bypass = True
            result = await check_news_blackout(mock_db)
            assert result.blocked is False
            assert "bypassed" in result.reason.lower()
        finally:
            settings.news_filter_bypass = original_bypass


class TestNewsBufferTiming:
    """Test the 30-minute before / 60-minute after buffer requirements."""
    
    @pytest.mark.asyncio
    async def test_blocks_30_minutes_before_event(self, mock_db, sample_news_event):
        """Test Requirement 17.2: Block trading 30 minutes before news events."""
        # Set current time to 29 minutes before event (should block)
        current_time = sample_news_event.starts_at - timedelta(minutes=29)
        
        # Mock database query to return the event
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_news_event]
        mock_db.execute.return_value = mock_result
        
        result = await check_news_blackout(mock_db, now=current_time)
        
        assert result.blocked is True
        assert "News blackout" in result.reason
        assert result.blocking_event == sample_news_event.title
    
    @pytest.mark.asyncio
    async def test_blocks_60_minutes_after_event(self, mock_db, sample_news_event):
        """Test Requirement 17.3: Block trading 60 minutes after news events."""
        # Set current time to 59 minutes after event (should block)
        current_time = sample_news_event.starts_at + timedelta(minutes=59)
        
        # Mock database query to return the event
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_news_event]
        mock_db.execute.return_value = mock_result
        
        result = await check_news_blackout(mock_db, now=current_time)
        
        assert result.blocked is True
        assert "News blackout" in result.reason
        assert result.blocking_event == sample_news_event.title
    
    @pytest.mark.asyncio
    async def test_allows_trading_31_minutes_before_event(self, mock_db, sample_news_event):
        """Test that trading is allowed 31 minutes before event (outside buffer)."""
        # Set current time to 31 minutes before event (should allow)
        current_time = sample_news_event.starts_at - timedelta(minutes=31)
        
        # Mock database query to return the event
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_news_event]
        mock_db.execute.return_value = mock_result
        
        result = await check_news_blackout(mock_db, now=current_time)
        
        assert result.blocked is False
    
    @pytest.mark.asyncio
    async def test_allows_trading_61_minutes_after_event(self, mock_db, sample_news_event):
        """Test that trading is allowed 61 minutes after event (outside buffer)."""
        # Set current time to 61 minutes after event (should allow)
        current_time = sample_news_event.starts_at + timedelta(minutes=61)
        
        # Mock database query to return the event
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_news_event]
        mock_db.execute.return_value = mock_result
        
        result = await check_news_blackout(mock_db, now=current_time)
        
        assert result.blocked is False
    
    @pytest.mark.asyncio
    async def test_blocks_exactly_at_event_time(self, mock_db, sample_news_event):
        """Test that trading is blocked exactly at event time."""
        current_time = sample_news_event.starts_at
        
        # Mock database query to return the event
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_news_event]
        mock_db.execute.return_value = mock_result
        
        result = await check_news_blackout(mock_db, now=current_time)
        
        assert result.blocked is True


class TestConservativeMode:
    """Test conservative mode when calendar is unavailable."""
    
    @pytest.mark.asyncio
    async def test_conservative_mode_blocks_typical_news_times(self, mock_db):
        """Test that conservative mode blocks trading during typical news times."""
        # Simulate database error
        mock_db.execute.side_effect = Exception("Database unavailable")
        
        # Test time at 08:30 SAST (typical CPI release time)
        sast = pytz.timezone("Africa/Johannesburg")
        test_time = sast.localize(datetime(2024, 1, 15, 8, 30))
        
        result = await check_news_blackout(mock_db, now=test_time, enable_conservative_mode=True)
        
        assert result.blocked is True
        assert result.conservative_mode is True
        assert "Conservative mode" in result.reason
    
    @pytest.mark.asyncio
    async def test_conservative_mode_allows_outside_typical_times(self, mock_db):
        """Test that conservative mode allows trading outside typical news times."""
        # Simulate database error
        mock_db.execute.side_effect = Exception("Database unavailable")
        
        # Test time at 12:00 SAST (outside typical news windows)
        sast = pytz.timezone("Africa/Johannesburg")
        test_time = sast.localize(datetime(2024, 1, 15, 12, 0))
        
        result = await check_news_blackout(mock_db, now=test_time, enable_conservative_mode=True)
        
        assert result.blocked is False
    
    @pytest.mark.asyncio
    async def test_conservative_mode_can_be_disabled(self, mock_db):
        """Test that conservative mode can be disabled."""
        # Simulate database error
        mock_db.execute.side_effect = Exception("Database unavailable")
        
        # Test time at 08:30 SAST (typical news time)
        sast = pytz.timezone("Africa/Johannesburg")
        test_time = sast.localize(datetime(2024, 1, 15, 8, 30))
        
        result = await check_news_blackout(mock_db, now=test_time, enable_conservative_mode=False)
        
        # Should allow trading when conservative mode is disabled
        assert result.blocked is False


class TestProcessingBuffer:
    """Test the processing buffer functionality."""
    
    @pytest.mark.asyncio
    async def test_processing_buffer_prevents_late_execution(self, mock_db, sample_news_event):
        """Test that processing buffer prevents signals from executing during news."""
        # Set current time to 28 minutes before event
        # With 5-second buffer, effective time is 27:55 before event (should block)
        current_time = sample_news_event.starts_at - timedelta(minutes=28)
        
        # Mock database query to return the event
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_news_event]
        mock_db.execute.return_value = mock_result
        
        result = await check_news_blackout(mock_db, now=current_time, processing_buffer_seconds=5)
        
        assert result.blocked is True


class TestMultipleEvents:
    """Test handling of multiple news events."""
    
    @pytest.mark.asyncio
    async def test_blocks_for_nearest_event(self, mock_db):
        """Test that the filter blocks for the nearest event."""
        event1 = NewsEvent(
            title="CPI Release",
            country="US",
            currency="USD",
            impact="high",
            starts_at=datetime(2024, 1, 15, 14, 30, tzinfo=pytz.UTC),
            is_major=True,
            source="manual",
        )
        event2 = NewsEvent(
            title="NFP Release",
            country="US",
            currency="USD",
            impact="high",
            starts_at=datetime(2024, 1, 15, 16, 0, tzinfo=pytz.UTC),
            is_major=True,
            source="manual",
        )
        
        # Current time is 20 minutes before first event
        current_time = event1.starts_at - timedelta(minutes=20)
        
        # Mock database query to return both events
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [event1, event2]
        mock_db.execute.return_value = mock_result
        
        result = await check_news_blackout(mock_db, now=current_time)
        
        assert result.blocked is True
        assert result.blocking_event == event1.title


class TestTimezoneHandling:
    """Test timezone handling."""
    
    @pytest.mark.asyncio
    async def test_handles_naive_datetime(self, mock_db, sample_news_event):
        """Test that naive datetimes are handled correctly."""
        # Create naive datetime (no timezone)
        naive_time = datetime(2024, 1, 15, 14, 0)
        
        # Mock database query to return the event
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_news_event]
        mock_db.execute.return_value = mock_result
        
        # Should not raise an error
        result = await check_news_blackout(mock_db, now=naive_time)
        
        assert isinstance(result, NewsCheckResult)
    
    @pytest.mark.asyncio
    async def test_handles_different_timezones(self, mock_db, sample_news_event):
        """Test that different timezones are converted correctly."""
        # Create time in SAST timezone
        sast = pytz.timezone("Africa/Johannesburg")
        sast_time = sast.localize(datetime(2024, 1, 15, 16, 0))  # 14:00 UTC
        
        # Mock database query to return the event
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_news_event]
        mock_db.execute.return_value = mock_result
        
        result = await check_news_blackout(mock_db, now=sast_time)
        
        assert isinstance(result, NewsCheckResult)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
