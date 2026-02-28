"""
Ambient brightness sensor adapter interface and implementations.
Allows optional light sensor integration for brightness auto-adjustment.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class SensorAdapter(ABC):
    """
    Abstract interface for ambient brightness sensors.

    Implementations should provide light level readings (0-255 or normalized).
    """

    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize sensor hardware/connection.

        Returns:
            True if successful, False if sensor unavailable
        """

    @abstractmethod
    def read_ambient_brightness(self) -> Optional[int]:
        """
        Read current ambient brightness level.

        Returns:
            Brightness reading (0-255) or None if error
        """

    @abstractmethod
    def shutdown(self) -> None:
        """Release sensor resources."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if sensor is available and initialized."""


class MockSensorAdapter(SensorAdapter):
    """
    Mock sensor adapter for testing brightness controller.

    Always returns a configurable brightness value.
    """

    def __init__(self, brightness_value: int = 128):
        """
        Initialize mock sensor.

        Args:
            brightness_value: Fixed brightness to return (0-255)
        """
        self.brightness_value = max(0, min(255, brightness_value))
        self._available = False

    def initialize(self) -> bool:
        """Initialize mock sensor (always succeeds)."""
        self._available = True
        logger.info(
            f"Mock sensor initialized (brightness={
                self.brightness_value})")
        return True

    def read_ambient_brightness(self) -> Optional[int]:
        """Return configured brightness value."""
        if not self._available:
            return None
        return self.brightness_value

    def shutdown(self) -> None:
        """Shutdown mock sensor."""
        self._available = False
        logger.info("Mock sensor shut down")

    def is_available(self) -> bool:
        """Check if mock sensor is available."""
        return self._available

    def set_brightness(self, brightness: int) -> None:
        """Update mock sensor brightness for testing."""
        self.brightness_value = max(0, min(255, brightness))


class ADCLuminositySensor(SensorAdapter):
    """
    ADC-based luminosity sensor adapter (e.g., via I2C ADC).

    Wraps I2C analog-to-digital converter reading for light level.
    Common sensors: Adafruit ADS1115, MCP3008, etc.
    """

    def __init__(
        self,
        i2c_address: int = 0x48,
        channel: int = 0,
        min_adc: int = 0,
        max_adc: int = 65535,
        invert: bool = False
    ):
        """
        Initialize ADC luminosity sensor.

        Args:
            i2c_address: I2C address of ADC
            channel: ADC channel to read
            min_adc: ADC value corresponding to darkness (0-255)
            max_adc: ADC value corresponding to bright (0-255)
            invert: Invert reading (True = darker = higher value)
        """
        self.i2c_address = i2c_address
        self.channel = channel
        self.min_adc = min_adc
        self.max_adc = max_adc
        self.invert = invert

        self.adc = None
        self._available = False

    def initialize(self) -> bool:
        """Initialize I2C ADC connection."""
        try:
            # Lazy import to avoid dependency on I2C libraries
            try:
                from Adafruit_ADS1x15 import ADS1115
                self.adc = ADS1115(address=self.i2c_address)
                logger.info(
                    f"ADC sensor initialized at 0x{
                        self.i2c_address:02x}")
                self._available = True
                return True
            except ImportError:
                logger.warning("Adafruit I2C libraries not available")
                return False

        except Exception as e:
            logger.error(f"Failed to initialize ADC sensor: {e}")
            return False

    def read_ambient_brightness(self) -> Optional[int]:
        """Read luminosity from ADC channel."""
        if not self._available or not self.adc:
            return None

        try:
            # Read analog value (0-32767 for typical 16-bit ADC)
            raw_value = self.adc.read_adc(self.channel, gain=1)

            # Normalize to 0-255 range
            if raw_value < self.min_adc:
                normalized = 0
            elif raw_value > self.max_adc:
                normalized = 255
            else:
                # Linear interpolation
                normalized = int(
                    255 * (raw_value - self.min_adc) / (self.max_adc - self.min_adc)
                )

            # Apply inversion if needed
            if self.invert:
                normalized = 255 - normalized

            return normalized

        except Exception as e:
            logger.warning(f"ADC read error: {e}")
            return None

    def shutdown(self) -> None:
        """Shutdown ADC connection."""
        self.adc = None
        self._available = False
        logger.info("ADC sensor shut down")

    def is_available(self) -> bool:
        """Check if ADC sensor is available."""
        return self._available


class TSL2561LuminositySensor(SensorAdapter):
    """
    TSL2561 light sensor adapter via I2C.

    More sophisticated light sensor with better accuracy across
    different light spectra. Common Adafruit breakout board.
    """

    def __init__(self, i2c_address: int = 0x39):
        """
        Initialize TSL2561 sensor.

        Args:
            i2c_address: I2C address (0x29, 0x39, or 0x49 depending on pins)
        """
        self.i2c_address = i2c_address
        self.sensor = None
        self._available = False

    def initialize(self) -> bool:
        """Initialize I2C connection to TSL2561."""
        try:
            try:
                from Adafruit_TSL2561 import Adafruit_TSL2561
                self.sensor = Adafruit_TSL2561(address=self.i2c_address)
                self.sensor.enable()
                logger.info(
                    f"TSL2561 sensor initialized at 0x{
                        self.i2c_address:02x}")
                self._available = True
                return True
            except ImportError:
                logger.warning("Adafruit TSL2561 library not available")
                return False

        except Exception as e:
            logger.error(f"Failed to initialize TSL2561 sensor: {e}")
            return False

    def read_ambient_brightness(self) -> Optional[int]:
        """Read lux value and normalize to 0-255."""
        if not self._available or not self.sensor:
            return None

        try:
            # Read broadband and infrared
            broadband = self.sensor.readBroadband()
            ir = self.sensor.readIR()

            # Calculate lux value
            lux = self.sensor.calculateLux(broadband, ir)

            # Normalize to 0-255 (typical room: 0-10000 lux)
            # Indoor: 50 lux = dark, 500 lux = normal, 10000 lux = very bright
            if lux < 100:
                normalized = 0
            elif lux > 5000:
                normalized = 255
            else:
                normalized = int(255 * (lux - 100) / (5000 - 100))

            return max(0, min(255, normalized))

        except Exception as e:
            logger.warning(f"TSL2561 read error: {e}")
            return None

    def shutdown(self) -> None:
        """Shutdown TSL2561 connection."""
        if self.sensor:
            try:
                self.sensor.disable()
            except Exception as e:
                logger.warning(f"Error disabling TSL2561: {e}")

        self.sensor = None
        self._available = False
        logger.info("TSL2561 sensor shut down")

    def is_available(self) -> bool:
        """Check if TSL2561 sensor is available."""
        return self._available
