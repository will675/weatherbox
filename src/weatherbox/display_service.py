"""
Main display service for weather forecast rendering.
Coordinates weather API fetching, retry scheduling, and LED matrix rendering.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import json

from .weather.retry_scheduler import RetryScheduler, UpdateWindowScheduler
from .weather.metoffice_adapter import MetOfficeAdapter, DailySummary
from .weather.forecast_parser import ForecastParser
from .icons.loader import IconLoader
from .display.adapter import DisplayAdapter, Bitmap
from .brightness.controller import BrightnessController

logger = logging.getLogger(__name__)


class WeatherDisplayService:
    """
    Main weather display service.

    Lifecycle:
    1. Initialize: Connect to display hardware, load configs, verify API
    2. Run loop: Fetch forecasts, apply retry/update schedules, render, sleep
    3. Error handling: Display error symbol if API fails
    4. Cleanup: Shutdown display and save diagnostics
    """

    # Default update window (daytime 06:00-23:00, nighttime 1h)
    DEFAULT_UPDATE_WINDOW = {
        'daytime_start': '06:00',
        'daytime_end': '23:00',
        'daytime_interval_minutes': 5,
        'night_interval_minutes': 60,
    }

    # Default brightness caps
    DEFAULT_BRIGHTNESS = {
        'max_brightness': 200,
        'day_brightness': 150,
        'night_brightness': 50,
    }

    def __init__(
        self,
        display_adapter: DisplayAdapter,
        metoffice_adapter: MetOfficeAdapter,
        icon_loader: IconLoader,
        brightness_controller: Optional[BrightnessController] = None,
        diagnostics_dir: Optional[str] = None,
    ):
        """
        Initialize display service.

        Args:
            display_adapter: LED matrix display adapter
            metoffice_adapter: Met Office API client
            icon_loader: Weather type → icon ID mapper
            brightness_controller: Brightness management (optional)
            diagnostics_dir: Directory for error diagnostics (optional)
        """
        self.display = display_adapter
        self.metoffice = metoffice_adapter
        self.icons = icon_loader
        self.brightness = brightness_controller or BrightnessController()
        self.diagnostics_dir = diagnostics_dir

        self.forecast_parser = ForecastParser()
        self.retry_scheduler = RetryScheduler()
        self.update_scheduler = UpdateWindowScheduler()

        self._running = False
        self._last_forecast = None

        logger.info("WeatherDisplayService initialized")

    def initialize(self) -> bool:
        """
        Initialize display service hardware and check API.

        Returns:
            True if successful
        """
        try:
            # Initialize display hardware
            if not self.display.initialize():
                logger.error("Display adapter initialization failed")
                return False

            logger.info("Display adapter initialized successfully")

            # Verify API connectivity
            forecast = self.metoffice.fetch_forecast()
            if forecast:
                logger.info(
                    f"API connectivity verified: got {
                        len(forecast)} days")
                self.retry_scheduler.record_success()
                self._last_forecast = forecast
            else:
                logger.warning(
                    "Initial API fetch failed; will retry on schedule")

            # Set initial brightness
            brightness = self.brightness.get_brightness()
            self.display.set_brightness(brightness)
            logger.info(f"Display brightness set to {brightness}")

            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False

    def fetch_forecast(self) -> Optional[List[DailySummary]]:
        """
        Fetch forecast from API with retry scheduling.

        Uses exponential backoff on failure.

        Returns:
            List of DailySummary objects, or None if fetch fails
        """
        forecast = self.metoffice.fetch_forecast()

        if forecast:
            logger.info(f"Forecast fetched: {len(forecast)} days")
            self.retry_scheduler.record_success()
            self._last_forecast = forecast
            return forecast
        else:
            # Record failure and get retry interval
            interval = self.retry_scheduler.record_failure()
            logger.warning(
                f"Forecast fetch failed; retry in {interval} "
                f"(attempt {self.retry_scheduler.attempt_count})"
            )
            return None

    def render_forecast(self, forecast: List[DailySummary]) -> bool:
        """
        Render forecast to LED matrices.

        Layout:
        - Matrix 0: Current day summary
        - Matrices 1-3: Next 3 days forecasts

        Args:
            forecast: List of daily summaries

        Returns:
            True if rendering successful
        """
        try:
            if not forecast:
                logger.warning("Cannot render empty forecast")
                return False

            # Prepare bitmaps for each matrix
            bitmaps = []

            # Matrix 0: Current day
            if len(forecast) > 0:
                summary = forecast[0]
                bitmap = self._render_day_summary(
                    summary,
                    is_current=True
                )
                bitmaps.append(bitmap)

            # Matrices 1-3: Next 3 days
            for i in range(1, 4):
                if len(forecast) > i:
                    summary = forecast[i]
                    bitmap = self._render_day_summary(summary)
                    bitmaps.append(bitmap)
                else:
                    # No forecast data; fill with blank
                    bitmaps.append(Bitmap())

            # Render to display
            success = self.display.render_all(bitmaps)

            if success:
                logger.info(f"Rendered {len(bitmaps)} matrices")
            else:
                logger.error("Display render failed")

            return success

        except Exception as e:
            logger.error(f"Rendering error: {e}")
            return False

    def _render_day_summary(
        self,
        summary: DailySummary,
        is_current: bool = False
    ) -> Bitmap:
        """
        Render single day summary to 8×8 bitmap.

        Format: Weather icon + temperature (simplified)
        Current day: Show current conditions or min/max based on time
        Future days: Max temp + day weather icon

        Args:
            summary: Daily weather summary
            is_current: Whether this is current day

        Returns:
            8×8 Bitmap
        """
        bitmap = Bitmap()

        try:
            if is_current:
                # Current day: show max/min temps based on time of day
                now = datetime.now()
                if now.hour < 18:
                    # Show max temp this afternoon
                    temp = summary.max_temperature or 0
                    weather_type = summary.day_weather_type
                else:
                    # Show min temp tonight
                    temp = summary.min_temperature or 0
                    weather_type = summary.night_weather_type
            else:
                # Future day: show max temp + day weather
                temp = summary.max_temperature or 0
                weather_type = summary.day_weather_type

            # Get icon ID for weather type
            icon_id = self.icons.get_icon_id(weather_type)

            # Load icon bitmap (for now, using placeholder)
            # TODO: Load from led8x8icons.py
            self._render_icon_and_temp(bitmap, icon_id, temp)

            logger.debug(
                f"Rendered day {summary.date.date()}: "
                f"weather={weather_type}, temp={temp}, icon={icon_id}"
            )

            return bitmap

        except Exception as e:
            logger.error(f"Error rendering day summary: {e}")
            return Bitmap()  # Return blank bitmap on error

    def _render_icon_and_temp(
        self,
        bitmap: Bitmap,
        icon_id: int,
        temp: Optional[int]
    ) -> None:
        """
        Render weather icon and temperature to bitmap.

        Simple placeholder: Draw icon pattern based on icon_id.
        TODO: Integrate with actual led8x8icons loading.

        Args:
            bitmap: 8×8 bitmap to render to
            icon_id: Weather icon ID
            temp: Temperature to display
        """
        # Simple placeholder: Fill bitmap with pattern based on icon_id
        pattern_val = min(255, icon_id * 25)
        for y in range(8):
            for x in range(8):
                if (x + y) % 2 == 0:
                    bitmap.set_pixel(x, y, pattern_val)

    def display_error(self, error_msg: str = "API error") -> bool:
        """
        Display error symbol on all matrices.

        Args:
            error_msg: Error message for logging

        Returns:
            True if error display successful
        """
        try:
            logger.error(f"Displaying error: {error_msg}")

            # Create error bitmap (simple X pattern)
            error_bitmap = Bitmap()
            for i in range(8):
                error_bitmap.set_pixel(i, i, 255)        # Diagonal \
                error_bitmap.set_pixel(7 - i, i, 255)      # Diagonal /

            # Render error bitmap to all matrices
            bitmaps = [error_bitmap] * 4
            success = self.display.render_all(bitmaps)

            if success:
                # Save diagnostics
                self._save_error_diagnostics(error_msg)

            return success

        except Exception as e:
            logger.error(f"Error displaying error state: {e}")
            return False

    def _save_error_diagnostics(self, error_msg: str) -> None:
        """
        Save diagnostic information on error.

        Includes: error message, last forecast, API response, stack traces

        Args:
            error_msg: Error message
        """
        if not self.diagnostics_dir:
            return

        try:
            diag_dir = Path(self.diagnostics_dir)
            diag_dir.mkdir(parents=True, exist_ok=True)

            # Timestamp for filename
            timestamp = datetime.now().isoformat().replace(':', '-')

            # Save error report
            report = {
                'timestamp': timestamp,
                'error': error_msg,
                'retry_state': self.retry_scheduler.state.value,
                'attempt_count': self.retry_scheduler.attempt_count,
                'last_forecast': None,
            }

            if self._last_forecast:
                report['last_forecast'] = [
                    s.to_dict() for s in self._last_forecast
                ]

            report_path = diag_dir / f"error_{timestamp}.json"
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)

            logger.info(f"Error diagnostics saved to {report_path}")

        except Exception as e:
            logger.warning(f"Failed to save diagnostics: {e}")

    def update_brightness(self) -> None:
        """Update display brightness based on time of day."""
        try:
            brightness = self.brightness.get_brightness()
            self.display.set_brightness(brightness)
            logger.debug(f"Brightness updated to {brightness}")
        except Exception as e:
            logger.warning(f"Brightness update error: {e}")

    def run_cycle(self) -> bool:
        """
        Execute single update cycle: fetch, parse, render, sleep.

        Returns:
            True if cycle completed successfully
        """
        try:
            # Check if we should update (based on window scheduler)
            if not self.update_scheduler.should_update_now():
                wait_minutes = self.update_scheduler.next_update_in_minutes()
                logger.debug(
                    f"Update window not ready; next in {wait_minutes}m")
                return True

            # Update brightness
            self.update_brightness()

            # Fetch forecast
            forecast = self.fetch_forecast()

            if forecast:
                # Render to display
                if self.render_forecast(forecast):
                    # Record successful update
                    self.update_scheduler.record_update()
                    return True
                else:
                    logger.error("Rendering failed")
                    return False
            else:
                # API failed; check if retries exhausted
                if self.retry_scheduler.is_retry_exhausted():
                    logger.error("Retries exhausted")
                    self.display_error("Retries exceeded")
                    return False

                # Display stays as-is, will retry on schedule
                return True

        except Exception as e:
            logger.error(f"Cycle error: {e}")
            self._save_error_diagnostics(str(e))
            return False

    def shutdown(self) -> None:
        """Clean up and shutdown service."""
        try:
            self._running = False

            # Clear display
            self.display.clear_all()

            # Shutdown hardware
            self.display.shutdown()

            logger.info("WeatherDisplayService shut down")

        except Exception as e:
            logger.error(f"Shutdown error: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get service status for diagnostics."""
        return {
            'running': self._running,
            'display_initialized': self.display.is_initialized(),
            'display_brightness': self.display.get_brightness(),
            'brightness_controller': self.brightness.get_status(),
            'retry_state': self.retry_scheduler.state.value,
            'retry_attempt': self.retry_scheduler.attempt_count,
            'last_forecast_count': len(
                self._last_forecast) if self._last_forecast else 0,
            'next_update_minutes': self.update_scheduler.next_update_in_minutes(),
        }
