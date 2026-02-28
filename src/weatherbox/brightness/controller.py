"""
Brightness controller for LED matrix displays.
Handles hardware brightness limits, night mode, and optional sensor integration.
"""

import logging
from datetime import datetime, time
from typing import Optional

logger = logging.getLogger(__name__)


class BrightnessController:
    """
    Manages display brightness with caps and time-based modes.

    Features:
    - Hardware brightness cap to prevent damage
    - Night mode (after 22:00) with reduced brightness
    - Optional ambient brightness sensor integration
    """

    # Night mode threshold (hour when brightness reduces)
    NIGHT_MODE_START_HOUR = 22  # 22:00
    NIGHT_MODE_END_HOUR = 6     # 06:00 (morning)

    def __init__(
        self,
        max_brightness: int = 200,          # Hardware cap (0-255)
        night_mode_brightness: int = 50,    # Reduced brightness after 22:00
        # Optional explicit day brightness
        day_brightness: Optional[int] = None
    ):
        """
        Initialize brightness controller.

        Args:
            max_brightness: Hard cap for brightness (0-255, prevents overheating)
            night_mode_brightness: Brightness when night mode active (0-255)
            day_brightness: Explicit daytime brightness (None = use max_brightness)
        """
        self.max_brightness = max(0, min(255, max_brightness))
        self.night_mode_brightness = max(0, min(255, night_mode_brightness))
        self.day_brightness = (
            max(0, min(255, day_brightness))
            if day_brightness is not None
            else self.max_brightness
        )

        self.current_brightness = self.day_brightness
        self.sensor_adapter = None
        self.last_sensor_value = None

        logger.info(
            f"Brightness controller initialized: "
            f"day={self.day_brightness}, night={self.night_mode_brightness}, "
            f"max={self.max_brightness}"
        )

    def is_night_mode(self, dt: datetime = None) -> bool:
        """Check if current time is within night mode window."""
        dt = dt or datetime.now()
        current_time = dt.time()

        # Handle overnight window (e.g., 22:00-06:00)
        if self.NIGHT_MODE_START_HOUR > self.NIGHT_MODE_END_HOUR:
            # Window crosses midnight
            return current_time >= time(self.NIGHT_MODE_START_HOUR) or \
                current_time < time(self.NIGHT_MODE_END_HOUR)
        else:
            # Window within same day
            return time(self.NIGHT_MODE_START_HOUR) <= current_time < \
                time(self.NIGHT_MODE_END_HOUR)

    def calculate_brightness(self, dt: datetime = None) -> int:
        """
        Calculate appropriate brightness for current time.

        Algorithm:
        1. Start with day or night base brightness
        2. If sensor available, apply ambient adjustment
        3. Cap at max_brightness
        4. Log transitions

        Args:
            dt: Current time (for testing)

        Returns:
            Brightness value (0-255)
        """
        dt = dt or datetime.now()

        # Base brightness from time of day
        if self.is_night_mode(dt):
            base_brightness = self.night_mode_brightness
            mode = "night"
        else:
            base_brightness = self.day_brightness
            mode = "day"

        # Apply sensor adjustment if available
        brightness = base_brightness
        if self.sensor_adapter:
            try:
                sensor_value = self.sensor_adapter.read_ambient_brightness()
                if sensor_value is not None:
                    # Sensor value (0-255) can reduce brightness further
                    # Use minimum of base and sensor value
                    brightness = min(base_brightness, sensor_value)
                    self.last_sensor_value = sensor_value
                    logger.debug(
                        f"Sensor adjusted brightness: {sensor_value} → {brightness}")
            except Exception as e:
                logger.warning(f"Sensor read error: {e}")

        # Apply hardware cap
        final_brightness = min(brightness, self.max_brightness)

        if final_brightness != self.current_brightness:
            logger.info(
                f"Brightness transition: {self.current_brightness} → {final_brightness} "
                f"(mode={mode}, base={base_brightness}, max={self.max_brightness})"
            )
            self.current_brightness = final_brightness

        return final_brightness

    def get_brightness(self, dt: datetime = None) -> int:
        """Get current appropriate brightness."""
        return self.calculate_brightness(dt)

    def set_sensor_adapter(self, adapter) -> None:
        """
        Set optional ambient brightness sensor adapter.

        Args:
            adapter: Adapter with read_ambient_brightness() method
        """
        self.sensor_adapter = adapter
        logger.info("Brightness sensor adapter installed")

    def has_sensor(self) -> bool:
        """Check if sensor adapter is installed."""
        return self.sensor_adapter is not None

    def set_max_brightness(self, max_brightness: int) -> None:
        """
        Update hardware brightness cap.

        Args:
            max_brightness: New max brightness (0-255)
        """
        self.max_brightness = max(0, min(255, max_brightness))
        logger.info(f"Max brightness updated to {self.max_brightness}")

    def set_night_mode_brightness(self, brightness: int) -> None:
        """
        Update night mode brightness.

        Args:
            brightness: New night brightness (0-255)
        """
        self.night_mode_brightness = max(0, min(255, brightness))
        logger.info(
            f"Night mode brightness updated to {
                self.night_mode_brightness}")

    def set_day_brightness(self, brightness: int) -> None:
        """
        Update daytime brightness.

        Args:
            brightness: New day brightness (0-255)
        """
        self.day_brightness = max(0, min(255, brightness))
        logger.info(f"Day brightness updated to {self.day_brightness}")

    def get_status(self) -> dict:
        """Get current brightness controller status."""
        return {
            'current_brightness': self.current_brightness,
            'day_brightness': self.day_brightness,
            'night_mode_brightness': self.night_mode_brightness,
            'max_brightness': self.max_brightness,
            'is_night_mode': self.is_night_mode(),
            'has_sensor': self.has_sensor(),
            'last_sensor_value': self.last_sensor_value,
        }
