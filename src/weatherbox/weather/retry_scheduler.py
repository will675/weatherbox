"""
Retry scheduler for managing API and update retry logic.
Implements exponential backoff and update window management for weather forecast fetching.
"""

import logging
from datetime import datetime, time, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class RetryState(Enum):
    """Retry state machine states."""
    IDLE = "idle"                         # No retry active
    BACKOFF_1_MIN = "backoff_1m"          # First retry (1 min)
    BACKOFF_5_MIN = "backoff_5m"          # After 5 x 1min, use 5min
    BACKOFF_10_MIN = "backoff_10m"        # After 12 x 5min, use 10min
    BACKOFF_EXHAUSTED = "backoff_exhausted"  # Retries exceeded


class RetryScheduler:
    """
    Manages retry schedule with exponential backoff.
    
    Schedule:
    - Phase 1: 1 minute × 5 attempts (5 minutes total)
    - Phase 2: 5 minutes × 12 attempts (60 minutes total)
    - Phase 3: 10 minutes until 24 hours exceeded
    - Give up after 24 hours
    """
    
    def __init__(self, max_retry_hours: int = 24):
        """
        Initialize retry scheduler.
        
        Args:
            max_retry_hours: Maximum hours to retry before giving up (default: 24)
        """
        self.max_retry_hours = max_retry_hours
        self.state = RetryState.IDLE
        self.attempt_count = 0
        self.phase_1_attempts = 5
        self.phase_2_attempts = 12
        self.started_at = None
        self.last_retry_at = None
    
    def reset(self) -> None:
        """Reset retry state."""
        self.state = RetryState.IDLE
        self.attempt_count = 0
        self.started_at = None
        self.last_retry_at = None
        logger.info("Retry scheduler reset")
    
    def record_failure(self) -> timedelta:
        """
        Record a failure and return time until next retry.
        
        Returns:
            timedelta until next retry
        """
        if self.started_at is None:
            self.started_at = datetime.now()
        
        self.attempt_count += 1
        self.last_retry_at = datetime.now()
        
        # Check if exceeded max time
        elapsed = datetime.now() - self.started_at
        if elapsed.total_seconds() > self.max_retry_hours * 3600:
            self.state = RetryState.BACKOFF_EXHAUSTED
            logger.warning(f"Retry exhausted after {elapsed} and {self.attempt_count} attempts")
            return timedelta(hours=self.max_retry_hours)  # Large value to signal stop
        
        # Determine next backoff interval
        if self.attempt_count <= self.phase_1_attempts:
            self.state = RetryState.BACKOFF_1_MIN
            interval = timedelta(minutes=1)
        elif self.attempt_count <= self.phase_1_attempts + self.phase_2_attempts:
            self.state = RetryState.BACKOFF_5_MIN
            interval = timedelta(minutes=5)
        else:
            self.state = RetryState.BACKOFF_10_MIN
            interval = timedelta(minutes=10)
        
        logger.info(
            f"Retry scheduled: attempt {self.attempt_count}, "
            f"state={self.state.value}, next_interval={interval}"
        )
        return interval
    
    def record_success(self) -> None:
        """Record successful update; reset retry state."""
        logger.info(f"Update successful after {self.attempt_count} retries")
        self.reset()
    
    def is_retry_exhausted(self) -> bool:
        """Check if retries are exhausted."""
        return self.state == RetryState.BACKOFF_EXHAUSTED


class UpdateWindowScheduler:
    """
    Manages update window schedule (daytime vs nighttime).
    
    Daytime (e.g., 06:00–23:00): Update every 5 minutes
    Night (e.g., 23:01–05:59): Update hourly
    """
    
    def __init__(
        self,
        daytime_start: str = "06:00",      # HH:MM format
        daytime_end: str = "23:00",        # HH:MM format (when night starts)
        night_interval_minutes: int = 60,
        daytime_interval_minutes: int = 5,
        next_update_at: datetime = None
    ):
        """
        Initialize update window scheduler.
        
        Args:
            daytime_start: Start time for daytime window (HH:MM)
            daytime_end: End time for daytime window (start of night)
            night_interval_minutes: Update interval during night
            daytime_interval_minutes: Update interval during day
            next_update_at: Override next update time (for testing)
        """
        self.daytime_start = self._parse_time(daytime_start)
        self.daytime_end = self._parse_time(daytime_end)
        self.night_interval_minutes = night_interval_minutes
        self.daytime_interval_minutes = daytime_interval_minutes
        self.next_update_at = next_update_at or datetime.now()
    
    @staticmethod
    def _parse_time(time_str: str) -> time:
        """Parse HH:MM format time string."""
        parts = time_str.split(':')
        return time(int(parts[0]), int(parts[1]))
    
    def is_daytime(self, dt: datetime = None) -> bool:
        """Check if given time is within daytime window."""
        dt = dt or datetime.now()
        current_time = dt.time()
        
        # Handle case where daytime_end < daytime_start (e.g., crosses midnight)
        if self.daytime_start <= self.daytime_end:
            return self.daytime_start <= current_time < self.daytime_end
        else:
            return current_time >= self.daytime_start or current_time < self.daytime_end
    
    def should_update_now(self, dt: datetime = None) -> bool:
        """Check if update should happen now."""
        dt = dt or datetime.now()
        return dt >= self.next_update_at
    
    def record_update(self, dt: datetime = None) -> timedelta:
        """
        Record an update; return time until next update.
        
        Args:
            dt: Current time (for testing)
        
        Returns:
            timedelta until next update
        """
        dt = dt or datetime.now()
        
        if self.is_daytime(dt):
            interval = timedelta(minutes=self.daytime_interval_minutes)
            window = "daytime"
        else:
            interval = timedelta(minutes=self.night_interval_minutes)
            window = "night"
        
        self.next_update_at = dt + interval
        logger.info(
            f"Update recorded: next at {self.next_update_at} "
            f"({window} interval: {interval})"
        )
        return interval
    
    def get_time_until_next_update(self, dt: datetime = None) -> timedelta:
        """Calculate time remaining until next update."""
        dt = dt or datetime.now()
        if dt < self.next_update_at:
            return self.next_update_at - dt
        return timedelta(0)
    
    def next_update_in_minutes(self, dt: datetime = None) -> int:
        """Get minutes until next update (rounded)."""
        delta = self.get_time_until_next_update(dt)
        return max(0, int(delta.total_seconds() / 60))
