"""
Integration test for update schedule cadence.
Tests daytime/night update intervals and update window transitions with mocked time.
"""

import pytest
from datetime import datetime, timedelta
from freezegun import freeze_time

from weatherbox.display_service import WeatherDisplayService
from weatherbox.display.adapter import DisplayAdapter
from weatherbox.icons.loader import IconLoader


class StubMetOfficeAdapter:
    """Stub API returning consistent data."""

    def __init__(self):
        self.fetch_count = 0

    def fetch_forecast(self):
        from dataclasses import dataclass

        @dataclass
        class DailySummary:
            date: datetime
            weather_type: str
            day_weather_type: str
            night_weather_type: str
            max_temperature: int
            min_temperature: int

            def to_dict(self):
                return {}

        self.fetch_count += 1
        return [
            DailySummary(
                date=datetime.now().replace(hour=12),
                weather_type='Clear',
                day_weather_type='Clear',
                night_weather_type='Clear',
                max_temperature=15,
                min_temperature=5,
            )
        ]


class MockDisplayAdapter(DisplayAdapter):
    """Mock display tracking renders."""

    def __init__(self):
        self._initialized = False
        self.brightness = 100
        self.renders = []

    def initialize(self) -> bool:
        self._initialized = True
        return True

    def render_frame(self, matrix_index, bitmap) -> bool:
        self.renders.append(('render_frame', matrix_index))
        return True

    def render_all(self, bitmaps) -> bool:
        self.renders.append(('render_all', len(bitmaps)))
        return True

    def clear_all(self) -> bool:
        self.renders.append(('clear_all',))
        return True

    def shutdown(self) -> None:
        pass

    def set_brightness(self, brightness) -> bool:
        self.brightness = brightness
        return True

    def get_brightness(self) -> int:
        return self.brightness

    def is_initialized(self) -> bool:
        return self._initialized


class TestUpdateSchedule:
    """Test update cadence and scheduling."""

    @pytest.fixture
    def service(self):
        """Create service with mocks."""
        from weatherbox.brightness.controller import BrightnessController

        display = MockDisplayAdapter()
        api = StubMetOfficeAdapter()
        icons = IconLoader()
        icons.mappings = {'Clear': 1}
        brightness = BrightnessController()

        service = WeatherDisplayService(
            display_adapter=display,
            metoffice_adapter=api,
            icon_loader=icons,
            brightness_controller=brightness,
        )
        return service

    @freeze_time("2024-01-15 10:00:00")
    def test_daytime_update_interval_5min(self, service):
        """Test daytime has 5-minute update interval."""
        # 10:00 is daytime
        scheduler = service.update_scheduler

        interval = scheduler.record_update()

        assert interval == timedelta(minutes=5)
        assert scheduler.next_update_at == datetime(2024, 1, 15, 10, 5)

    @freeze_time("2024-01-15 23:30:00")
    def test_night_update_interval_60min(self, service):
        """Test nighttime has 60-minute update interval."""
        # 23:30 is night
        scheduler = service.update_scheduler

        interval = scheduler.record_update()

        assert interval == timedelta(minutes=60)
        assert scheduler.next_update_at == datetime(2024, 1, 16, 0, 30)

    @freeze_time("2024-01-15 06:00:00")
    def test_dawn_transition_day_to_day(self, service):
        """Test transition at dawn stays daytime."""
        scheduler = service.update_scheduler

        # Just at start of day
        assert scheduler.is_daytime() is True
        interval = scheduler.record_update()
        assert interval == timedelta(minutes=5)

    @freeze_time("2024-01-15 22:59:59")
    def test_dusk_transition_just_before_night(self, service):
        """Test transition just before night."""
        scheduler = service.update_scheduler

        # Just before night starts (22:59:59 is still day)
        assert scheduler.is_daytime() is True

    @freeze_time("2024-01-15 23:00:00")
    def test_dusk_transition_night_starts(self, service):
        """Test transition at night start."""
        scheduler = service.update_scheduler

        # Exactly at 23:00 (night starts)
        assert scheduler.is_daytime() is False
        interval = scheduler.record_update()
        assert interval == timedelta(minutes=60)

    @freeze_time("2024-01-15 05:59:59")
    def test_pre_dawn_still_night(self, service):
        """Test pre-dawn is still night."""
        scheduler = service.update_scheduler

        assert scheduler.is_daytime() is False

    @freeze_time("2024-01-15 06:00:00")
    def test_dawn_starts_day(self, service):
        """Test dawn starts daytime."""
        scheduler = service.update_scheduler

        assert scheduler.is_daytime() is True

    @freeze_time("2024-01-15 10:00:00")
    def test_should_update_now_true(self, service):
        """Test should_update_now when time reached."""
        scheduler = service.update_scheduler
        scheduler.next_update_at = datetime(2024, 1, 15, 10, 0)

        assert scheduler.should_update_now() is True

    @freeze_time("2024-01-15 10:00:00")
    def test_should_update_now_false(self, service):
        """Test should_update_now when time not reached."""
        scheduler = service.update_scheduler
        scheduler.next_update_at = datetime(2024, 1, 15, 10, 5)

        assert scheduler.should_update_now() is False

    @freeze_time("2024-01-15 10:00:00")
    def test_next_update_in_minutes(self, service):
        """Test minutes until next update."""
        scheduler = service.update_scheduler
        scheduler.next_update_at = datetime(2024, 1, 15, 10, 7, 30)

        minutes = scheduler.next_update_in_minutes()
        assert minutes == 7

    @freeze_time("2024-01-15 10:00:00")
    def test_daytime_sequence(self, service):
        """Test sequence of daytime updates."""
        scheduler = service.update_scheduler

        # Record multiple daytime updates
        times = [
            datetime(2024, 1, 15, 10, 0),
            datetime(2024, 1, 15, 10, 5),
            datetime(2024, 1, 15, 10, 10),
            datetime(2024, 1, 15, 10, 15),
        ]

        for t in times:
            with freeze_time(t):
                interval = scheduler.record_update()
                assert interval == timedelta(minutes=5)

    @freeze_time("2024-01-15 23:00:00")
    def test_night_sequence(self, service):
        """Test sequence of night updates."""
        scheduler = service.update_scheduler

        # Record multiple night updates
        times = [
            datetime(2024, 1, 15, 23, 0),
            # After midnight, still same "night" schedule
            datetime(2024, 1, 16, 0, 0),
            datetime(2024, 1, 16, 1, 0),
        ]

        for t in times:
            with freeze_time(t):
                interval = scheduler.record_update()
                assert interval == timedelta(minutes=60)

    @freeze_time("2024-01-15 22:55:00")
    def test_transition_daytime_to_night(self, service):
        """Test transition from daytime to night update schedule."""
        scheduler = service.update_scheduler

        # Update just before transition
        with freeze_time("2024-01-15 22:55:00"):
            interval = scheduler.record_update()
            assert interval == timedelta(minutes=5)
            next_update_time = datetime(2024, 1, 15, 23, 0)

        # At transition point
        with freeze_time("2024-01-15 23:00:00"):
            # Simulate manually setting update time to now
            scheduler.next_update_at = datetime(2024, 1, 15, 23, 0)
            assert scheduler.should_update_now() is True

            interval = scheduler.record_update()
            assert interval == timedelta(minutes=60)
            # Next update should be 60 min later
            assert scheduler.next_update_at == datetime(2024, 1, 16, 0, 0)

    @freeze_time("2024-01-15 05:55:00")
    def test_transition_night_to_daytime(self, service):
        """Test transition from night to daytime schedule."""
        scheduler = service.update_scheduler

        # Update in night
        with freeze_time("2024-01-15 05:55:00"):
            interval = scheduler.record_update()
            assert interval == timedelta(minutes=60)

        # At dawn transition
        with freeze_time("2024-01-15 06:00:00"):
            scheduler.next_update_at = datetime(2024, 1, 15, 6, 0)
            assert scheduler.should_update_now() is True

            interval = scheduler.record_update()
            assert interval == timedelta(minutes=5)
            # Next update should be 5 min later
            assert scheduler.next_update_at == datetime(2024, 1, 15, 6, 5)


class TestDisplayRotation:
    """Test display rotation patterns."""

    @freeze_time("2024-01-15 12:00:00")
    def test_service_cycles_match_schedule(self):
        """Test service cycles respect update schedule."""
        from weatherbox.brightness.controller import BrightnessController

        display = MockDisplayAdapter()
        api = StubMetOfficeAdapter()
        icons = IconLoader()
        icons.mappings = {'Clear': 1}
        brightness = BrightnessController()

        service = WeatherDisplayService(
            display_adapter=display,
            metoffice_adapter=api,
            icon_loader=icons,
            brightness_controller=brightness,
        )

        service.initialize()

        # Record initial state
        scheduler = service.update_scheduler
        initial_next_update = scheduler.next_update_at

        # Run one cycle
        with freeze_time("2024-01-15 12:00:00"):
            # Set next update to now so cycle runs
            scheduler.next_update_at = datetime(2024, 1, 15, 12, 0)
            result = service.run_cycle()

        # Verify cycle ran and scheduled next update
        assert result is True
        # Next scheduled update should be in 5 minutes (daytime)
        with freeze_time("2024-01-15 12:00:00"):
            minutes_until = scheduler.next_update_in_minutes()
            assert minutes_until == 5

    @freeze_time("2024-01-15 23:00:00")
    def test_night_cycle_scheduling(self):
        """Test night cycles have longer intervals."""
        from weatherbox.brightness.controller import BrightnessController

        display = MockDisplayAdapter()
        api = StubMetOfficeAdapter()
        icons = IconLoader()
        icons.mappings = {'Clear': 1}
        brightness = BrightnessController()

        service = WeatherDisplayService(
            display_adapter=display,
            metoffice_adapter=api,
            icon_loader=icons,
            brightness_controller=brightness,
        )

        service.initialize()
        scheduler = service.update_scheduler

        # Record night update
        with freeze_time("2024-01-15 23:00:00"):
            scheduler.next_update_at = datetime(2024, 1, 15, 23, 0)
            result = service.run_cycle()
            assert result is True

            # Should be ~60 minutes until next update
            minutes_until = scheduler.next_update_in_minutes()
            assert 59 <= minutes_until <= 61
