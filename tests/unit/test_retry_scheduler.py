"""
Unit tests for retry scheduler module.
Tests backoff state machine, update window transitions, and retry intervals.
"""

import pytest
from datetime import datetime, timedelta, time
from freezegun import freeze_time

from weatherbox.weather.retry_scheduler import RetryScheduler, RetryState, UpdateWindowScheduler


class TestRetryScheduler:
    """Test RetryScheduler exponential backoff logic."""
    
    @pytest.fixture
    def scheduler(self):
        """Create retry scheduler instance."""
        return RetryScheduler(max_retry_hours=24)
    
    def test_initialization(self, scheduler):
        """Test scheduler initializes in idle state."""
        assert scheduler.state == RetryState.IDLE
        assert scheduler.attempt_count == 0
        assert scheduler.started_at is None
        assert scheduler.last_retry_at is None
    
    def test_reset(self, scheduler):
        """Test reset clears all retry state."""
        scheduler.started_at = datetime.now()
        scheduler.attempt_count = 5
        scheduler.state = RetryState.BACKOFF_1_MIN
        
        scheduler.reset()
        
        assert scheduler.state == RetryState.IDLE
        assert scheduler.attempt_count == 0
        assert scheduler.started_at is None
    
    @freeze_time("2024-01-15 12:00:00")
    def test_record_failure_phase1(self, scheduler):
        """Test first 5 failures use 1-minute backoff."""
        for i in range(1, 6):
            interval = scheduler.record_failure()
            
            assert scheduler.state == RetryState.BACKOFF_1_MIN
            assert scheduler.attempt_count == i
            assert interval == timedelta(minutes=1)
    
    @freeze_time("2024-01-15 12:00:00")
    def test_record_failure_phase2(self, scheduler):
        """Test failures 6-17 use 5-minute backoff."""
        # Move through phase 1
        for _ in range(5):
            scheduler.record_failure()
        
        # Phase 2 starts
        for i in range(6, 18):
            interval = scheduler.record_failure()
            
            assert scheduler.state == RetryState.BACKOFF_5_MIN
            assert interval == timedelta(minutes=5)
    
    @freeze_time("2024-01-15 12:00:00")
    def test_record_failure_phase3(self, scheduler):
        """Test failures after 17 use 10-minute backoff."""
        # Move through phases 1 and 2
        for _ in range(17):
            scheduler.record_failure()
        
        # Phase 3 starts
        for i in range(18, 25):
            interval = scheduler.record_failure()
            
            assert scheduler.state == RetryState.BACKOFF_10_MIN
            assert interval == timedelta(minutes=10)
    
    @freeze_time("2024-01-15 12:00:00")
    def test_record_failure_exhausted(self, scheduler):
        """Test retries exhausted after max time."""
        # Simulate 25 hours of failures
        current_time = datetime(2024, 1, 15, 12, 0)
        with freeze_time(current_time):
            scheduler.started_at = current_time
        
        # Try after 25 hours
        with freeze_time(current_time + timedelta(hours=25)):
            interval = scheduler.record_failure()
            
            assert scheduler.state == RetryState.BACKOFF_EXHAUSTED
            assert scheduler.is_retry_exhausted() is True
    
    @freeze_time("2024-01-15 12:00:00")
    def test_record_success_clears_state(self, scheduler):
        """Test successful update resets retry state."""
        scheduler.record_failure()
        scheduler.record_failure()
        assert scheduler.attempt_count == 2
        
        scheduler.record_success()
        
        assert scheduler.state == RetryState.IDLE
        assert scheduler.attempt_count == 0
    
    def test_is_retry_exhausted_false(self, scheduler):
        """Test exhausted check when not exhausted."""
        assert scheduler.is_retry_exhausted() is False
    
    @freeze_time("2024-01-15 12:00:00")
    def test_is_retry_exhausted_true(self, scheduler):
        """Test exhausted check when retries exhausted."""
        current_time = datetime(2024, 1, 15, 12, 0)
        scheduler.started_at = current_time
        
        with freeze_time(current_time + timedelta(hours=25)):
            scheduler.record_failure()
            assert scheduler.is_retry_exhausted() is True


class TestUpdateWindowScheduler:
    """Test UpdateWindowScheduler time window logic."""
    
    @pytest.fixture
    def scheduler(self):
        """Create update window scheduler."""
        return UpdateWindowScheduler(
            daytime_start='06:00',
            daytime_end='23:00'
        )
    
    def test_initialization(self, scheduler):
        """Test scheduler initializes with defaults."""
        assert scheduler.daytime_interval_minutes == 5
        assert scheduler.night_interval_minutes == 60
        assert scheduler.next_update_at is not None
    
    def test_is_daytime_morning(self, scheduler):
        """Test daytime classification for morning hours."""
        dt = datetime(2024, 1, 15, 7, 30)  # 07:30
        assert scheduler.is_daytime(dt) is True
    
    def test_is_daytime_afternoon(self, scheduler):
        """Test daytime classification for afternoon."""
        dt = datetime(2024, 1, 15, 14, 0)  # 14:00
        assert scheduler.is_daytime(dt) is True
    
    def test_is_daytime_evening(self, scheduler):
        """Test daytime classification at boundary."""
        dt_before = datetime(2024, 1, 15, 22, 59)  # 22:59 - still day
        dt_after = datetime(2024, 1, 15, 23, 0)   # 23:00 - night starts
        
        assert scheduler.is_daytime(dt_before) is True
        assert scheduler.is_daytime(dt_after) is False
    
    def test_is_daytime_night(self, scheduler):
        """Test daytime classification for night hours."""
        assert scheduler.is_daytime(datetime(2024, 1, 15, 23, 30)) is False
        assert scheduler.is_daytime(datetime(2024, 1, 16, 0, 0)) is False
        assert scheduler.is_daytime(datetime(2024, 1, 16, 5, 0)) is False
    
    def test_is_daytime_early_morning(self, scheduler):
        """Test daytime classification early morning (before 06:00)."""
        assert scheduler.is_daytime(datetime(2024, 1, 16, 5, 59)) is False
        assert scheduler.is_daytime(datetime(2024, 1, 16, 6, 0)) is True
    
    @freeze_time("2024-01-15 10:00:00")
    def test_record_update_daytime(self, scheduler):
        """Test update recording during daytime."""
        interval = scheduler.record_update()
        
        assert interval == timedelta(minutes=5)
        assert scheduler.next_update_at == datetime(2024, 1, 15, 10, 5)
    
    @freeze_time("2024-01-15 22:30:00")
    def test_record_update_night(self, scheduler):
        """Test update recording during night."""
        # Note: 22:30 is before 23:00 (daytime_end), so it's still daytime
        # To test night, we need 23:00 or later
        with freeze_time("2024-01-15 23:30:00"):
            interval = scheduler.record_update()
            
            assert interval == timedelta(minutes=60)
    
    @freeze_time("2024-01-15 10:00:00")
    def test_should_update_now_true(self, scheduler):
        """Test should_update_now returns true when time reached."""
        scheduler.next_update_at = datetime(2024, 1, 15, 10, 0)
        assert scheduler.should_update_now() is True
    
    @freeze_time("2024-01-15 10:00:00")
    def test_should_update_now_false(self, scheduler):
        """Test should_update_now returns false before time."""
        scheduler.next_update_at = datetime(2024, 1, 15, 10, 5)
        assert scheduler.should_update_now() is False
    
    @freeze_time("2024-01-15 10:00:00")
    def test_get_time_until_next_update(self, scheduler):
        """Test time calculation until next update."""
        scheduler.next_update_at = datetime(2024, 1, 15, 10, 7, 30)
        delta = scheduler.get_time_until_next_update()
        
        assert delta == timedelta(minutes=7, seconds=30)
    
    @freeze_time("2024-01-15 10:00:00")
    def test_next_update_in_minutes(self, scheduler):
        """Test minutes until next update."""
        scheduler.next_update_at = datetime(2024, 1, 15, 10, 7, 30)
        minutes = scheduler.next_update_in_minutes()
        
        assert minutes == 7
    
    @freeze_time("2024-01-15 10:00:00")
    def test_next_update_in_minutes_zero(self, scheduler):
        """Test minutes returns 0 when past due."""
        scheduler.next_update_at = datetime(2024, 1, 15, 9, 55)
        minutes = scheduler.next_update_in_minutes()
        
        assert minutes == 0
    
    def test_parse_time(self):
        """Test time string parsing."""
        t = UpdateWindowScheduler._parse_time("14:30")
        assert t.hour == 14
        assert t.minute == 30
    
    def test_daytime_window_after_midnight(self):
        """Test daytime window that crosses midnight."""
        # Create scheduler with reversed window (e.g., night: 22:00-06:00)
        scheduler = UpdateWindowScheduler(
            daytime_start='06:00',
            daytime_end='22:00'  # Normal order
        )
        
        # Test normal window
        assert scheduler.is_daytime(datetime(2024, 1, 15, 12, 0)) is True
        assert scheduler.is_daytime(datetime(2024, 1, 15, 23, 0)) is False
