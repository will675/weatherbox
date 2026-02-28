"""
Integration tests for weather forecast fetch and display rendering.
Tests full cycle: API fetch → parse → render with stubbed API and mock display.
"""

import pytest
from datetime import datetime

from weatherbox.display_service import WeatherDisplayService
from weatherbox.weather.retry_scheduler import RetryState
from weatherbox.display.adapter import DisplayAdapter
from weatherbox.icons.loader import IconLoader


class StubMetOfficeAdapter:
    """Stub Met Office API that returns predictable test data."""

    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.fetch_count = 0

    def fetch_forecast(self):
        """Return test forecast data or None if simulating failure."""
        self.fetch_count += 1

        if self.should_fail:
            return None

        # Return test forecast data
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
                return {
                    'date': self.date.isoformat(),
                    'weather_type': self.weather_type,
                    'day_weather_type': self.day_weather_type,
                    'night_weather_type': self.night_weather_type,
                    'max_temperature': self.max_temperature,
                    'min_temperature': self.min_temperature,
                }

        return [
            DailySummary(
                date=datetime(2024, 1, 15, 12, 0),
                weather_type='Clear',
                day_weather_type='Clear',
                night_weather_type='Overcast',
                max_temperature=12,
                min_temperature=3,
            ),
            DailySummary(
                date=datetime(2024, 1, 16, 12, 0),
                weather_type='Partly cloudy',
                day_weather_type='Partly cloudy',
                night_weather_type='Clear',
                max_temperature=14,
                min_temperature=5,
            ),
            DailySummary(
                date=datetime(2024, 1, 17, 12, 0),
                weather_type='Rainy',
                day_weather_type='Light rain',
                night_weather_type='Rainy',
                max_temperature=8,
                min_temperature=4,
            ),
            DailySummary(
                date=datetime(2024, 1, 18, 12, 0),
                weather_type='Clear',
                day_weather_type='Clear',
                night_weather_type='Clear',
                max_temperature=10,
                min_temperature=2,
            ),
        ]


class MockDisplayAdapter(DisplayAdapter):
    """Mock display adapter that records renders."""

    def __init__(self):
        self._initialized = False
        self.brightness = 100
        self.rendered_frames = []
        self.cleared = False

    def initialize(self) -> bool:
        self._initialized = True
        return True

    def render_frame(self, matrix_index, bitmap) -> bool:
        self.rendered_frames.append((matrix_index, bitmap))
        return True

    def render_all(self, bitmaps) -> bool:
        for i, bitmap in enumerate(bitmaps):
            self.rendered_frames.append((i, bitmap))
        return len(self.rendered_frames) > 0

    def clear_all(self) -> bool:
        self.cleared = True
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


class TestForecastFetchAndRender:
    """Test forecast fetch and render integration."""

    @pytest.fixture
    def mock_display(self):
        """Create mock display adapter."""
        return MockDisplayAdapter()

    @pytest.fixture
    def stub_api(self):
        """Create stub Met Office adapter."""
        return StubMetOfficeAdapter()

    @pytest.fixture
    def icon_loader(self):
        """Create icon loader with test mappings."""
        loader = IconLoader()
        # Override with test mappings
        loader.mappings = {
            'Clear': 1,
            'Partly cloudy': 2,
            'Overcast': 3,
            'Light rain': 5,
            'Rainy': 6,
        }
        return loader

    @pytest.fixture
    def service(self, mock_display, stub_api, icon_loader):
        """Create display service with mocks."""
        from weatherbox.brightness.controller import BrightnessController

        brightness = BrightnessController()
        service = WeatherDisplayService(
            display_adapter=mock_display,
            metoffice_adapter=stub_api,
            icon_loader=icon_loader,
            brightness_controller=brightness,
            diagnostics_dir=None,
        )
        return service

    def test_service_initialization(self, service, mock_display):
        """Test service initializes display and API."""
        assert service.initialize() is True
        assert mock_display.is_initialized()
        assert service._last_forecast is not None

    def test_fetch_forecast_success(self, service):
        """Test successful forecast fetch."""
        forecast = service.fetch_forecast()

        assert forecast is not None
        assert len(forecast) == 4  # 4-day forecast
        assert forecast[0].max_temperature == 12

    def test_fetch_forecast_failure_triggers_retry(self, service, stub_api):
        """Test failed fetch triggers retry scheduler."""
        stub_api.should_fail = True

        forecast = service.fetch_forecast()

        assert forecast is None
        assert service.retry_scheduler.attempt_count == 1
        assert service.retry_scheduler.state == service.retry_scheduler.state.BACKOFF_1_MIN

    def test_fetch_success_resets_retry(self, service, stub_api):
        """Test successful fetch resets retry scheduler."""
        stub_api.should_fail = True
        service.fetch_forecast()  # First attempt fails
        assert service.retry_scheduler.attempt_count == 1

        stub_api.should_fail = False
        service.fetch_forecast()  # Second succeeds
        assert service.retry_scheduler.attempt_count == 0

    def test_render_forecast_to_display(self, service, mock_display):
        """Test rendering forecast to display matrices."""
        forecast = service.fetch_forecast()
        assert forecast is not None

        result = service.render_forecast(forecast)

        assert result is True
        # At least 4 matrices rendered
        assert len(mock_display.rendered_frames) >= 4

    def test_render_empty_forecast(self, service):
        """Test rendering empty forecast."""
        result = service.render_forecast([])
        assert result is False

    def test_full_cycle_success(self, service, mock_display, stub_api):
        """Test complete cycle: init → fetch → render."""
        # Initialize
        assert service.initialize() is True
        assert mock_display.is_initialized()

        # Fetch
        forecast = service.fetch_forecast()
        assert forecast is not None
        assert len(forecast) == 4

        # Render
        assert service.render_forecast(forecast) is True
        assert len(mock_display.rendered_frames) > 0

    def test_full_cycle_with_retry(self, service, mock_display, stub_api):
        """Test cycle with API failure and recovery."""
        service.initialize()

        # First attempt fails
        stub_api.should_fail = True
        forecast = service.fetch_forecast()
        assert forecast is None
        assert service.retry_scheduler.attempt_count == 1

        # Second attempt succeeds
        stub_api.should_fail = False
        forecast = service.fetch_forecast()
        assert forecast is not None
        assert service.retry_scheduler.attempt_count == 0

        # Render successful forecast
        assert service.render_forecast(forecast) is True

    def test_run_cycle_with_update_window(self, service, mock_display):
        """Test run_cycle respects update window."""
        from freezegun import freeze_time

        service.initialize()

        with freeze_time("2024-01-15 10:00:00"):
            # First update
            service.update_scheduler.next_update_at = datetime(
                2024, 1, 15, 10, 0)
            result = service.run_cycle()

            assert result is True
            # Next update should be in 5 minutes (daytime)
            assert service.update_scheduler.next_update_in_minutes() == 5

    def test_error_display_on_failure(self, service, mock_display):
        """Test error display on API failure."""
        service.initialize()

        # Force API failure
        stub_api = StubMetOfficeAdapter(should_fail=True)
        service.metoffice = stub_api

        # Exhaust retries (phase 1: 5×1min, phase 2: 12×5min, phase 3: need to cross 24h)
        # Simulate getting to phase 3 (18+ attempts)
        for _ in range(20):
            forecast = service.fetch_forecast()
            assert forecast is None

        # After 20 attempts, should be in phase 3
        assert service.retry_scheduler.state in [
            service.retry_scheduler.state.BACKOFF_10_MIN,
            service.retry_scheduler.state.BACKOFF_5_MIN
        ]
        # Don't test full exhaustion without time simulation

        # Display error
        assert service.display_error() is True
        assert mock_display.cleared is False  # Error display rendered, not cleared

    def test_display_shutdown_clears_display(self, service, mock_display):
        """Test shutdown clears display."""
        service.initialize()

        service.shutdown()

        assert mock_display.cleared is True

    def test_get_service_status(self, service):
        """Test status reporting."""
        service.initialize()
        forecast = service.fetch_forecast()
        service.render_forecast(forecast)

        status = service.get_status()

        assert status['display_initialized'] is True
        assert status['last_forecast_count'] == 4
        assert status['retry_state'] == 'idle'


class TestApiFailureAndRecovery:
    """Test API failure scenarios and recovery."""

    @pytest.fixture
    def service_setup(self):
        """Setup service with stub API."""
        display = MockDisplayAdapter()
        api = StubMetOfficeAdapter()
        icons = IconLoader()
        icons.mappings = {'Clear': 1, 'Partly cloudy': 2}

        from weatherbox.brightness.controller import BrightnessController
        brightness = BrightnessController()

        service = WeatherDisplayService(
            display_adapter=display,
            metoffice_adapter=api,
            icon_loader=icons,
            brightness_controller=brightness,
        )
        return service, display, api

    def test_persistent_api_failure(self, service_setup):
        """Test behavior with persistent API failures."""
        service, display, api = service_setup
        service.initialize()

        api.should_fail = True

        # Attempt multiple fetches
        for _ in range(18):
            forecast = service.fetch_forecast()
            assert forecast is None

        # Should be in phase 3 of retries after 18 attempts
        assert service.retry_scheduler.state in [
            service.retry_scheduler.state.BACKOFF_10_MIN,
            service.retry_scheduler.state.BACKOFF_5_MIN
        ]
        # Note: Full exhaustion would require simulating 24+ hours of elapsed
        # time

    def test_transient_failure_recovery(self, service_setup):
        """Test recovery from transient failure."""
        service, display, api = service_setup
        service.initialize()

        # Fail once
        api.should_fail = True
        forecast = service.fetch_forecast()
        assert forecast is None
        attempt_1 = service.retry_scheduler.attempt_count

        # Recover
        api.should_fail = False
        forecast = service.fetch_forecast()
        assert forecast is not None

        # Retry counter reset
        assert service.retry_scheduler.attempt_count == 0
        assert service.retry_scheduler.state == RetryState.IDLE

    def test_multiple_failure_cycles(self, service_setup):
        """Test multiple failure/recovery cycles."""
        service, display, api = service_setup
        service.initialize()

        for cycle in range(3):
            # Fail
            api.should_fail = True
            for _ in range(5):
                service.fetch_forecast()
            assert service.retry_scheduler.attempt_count > 0

            # Recover
            api.should_fail = False
            forecast = service.fetch_forecast()
            assert forecast is not None
            assert service.retry_scheduler.attempt_count == 0
