"""
Unit tests for brightness controller module.
Tests hardware caps, night mode transitions, and sensor integration.
"""

import pytest
from datetime import datetime, time
from freezegun import freeze_time

from weatherbox.brightness.controller import BrightnessController
from weatherbox.brightness.sensor_adapter import MockSensorAdapter


class TestBrightnessController:
    """Test BrightnessController brightness adjustment logic."""
    
    @pytest.fixture
    def controller(self):
        """Create brightness controller with defaults."""
        return BrightnessController(
            max_brightness=200,
            day_brightness=150,
            night_mode_brightness=50
        )
    
    def test_initialization(self, controller):
        """Test controller initializes correctly."""
        assert controller.max_brightness == 200
        assert controller.day_brightness == 150
        assert controller.night_mode_brightness == 50
        assert controller.current_brightness == 150
    
    def test_brightness_clamping_min(self):
        """Test that negative brightness is clamped to 0."""
        controller = BrightnessController(
            max_brightness=-10,
            day_brightness=-50
        )
        assert controller.max_brightness == 0
        assert controller.day_brightness == 0
    
    def test_brightness_clamping_max(self):
        """Test that brightness > 255 is clamped to 255."""
        controller = BrightnessController(
            max_brightness=300,
            day_brightness=400
        )
        assert controller.max_brightness == 255
        assert controller.day_brightness == 255
    
    @freeze_time("2024-01-15 12:00:00")
    def test_is_night_mode_false_daytime(self, controller):
        """Test night mode detection for daytime."""
        assert controller.is_night_mode() is False
    
    @freeze_time("2024-01-15 22:30:00")
    def test_is_night_mode_true_night(self, controller):
        """Test night mode detection for night."""
        assert controller.is_night_mode() is True
    
    @freeze_time("2024-01-15 23:59:59")
    def test_is_night_mode_late_night(self, controller):
        """Test night mode detection late night."""
        assert controller.is_night_mode() is True
    
    @freeze_time("2024-01-16 00:30:00")
    def test_is_night_mode_after_midnight(self, controller):
        """Test night mode detection after midnight."""
        assert controller.is_night_mode() is True
    
    @freeze_time("2024-01-16 05:59:59")
    def test_is_night_mode_just_before_dawn(self, controller):
        """Test night mode detection just before dawn."""
        assert controller.is_night_mode() is True
    
    @freeze_time("2024-01-16 06:00:00")
    def test_is_night_mode_dawn(self, controller):
        """Test night mode detection at dawn."""
        assert controller.is_night_mode() is False
    
    @freeze_time("2024-01-15 12:00:00")
    def test_calculate_brightness_daytime(self, controller):
        """Test brightness calculation during daytime."""
        brightness = controller.calculate_brightness()
        
        assert brightness == 150
        assert controller.current_brightness == 150
    
    @freeze_time("2024-01-15 22:30:00")
    def test_calculate_brightness_nighttime(self, controller):
        """Test brightness calculation during nighttime."""
        controller.current_brightness = 150  # Start at day value
        brightness = controller.calculate_brightness()
        
        assert brightness == 50
        assert controller.current_brightness == 50
    
    @freeze_time("2024-01-15 12:00:00")
    def test_brightness_capped_by_max(self, controller):
        """Test brightness is capped by max_brightness."""
        controller.day_brightness = 200
        controller.max_brightness = 100
        
        brightness = controller.calculate_brightness()
        
        assert brightness == 100  # Capped to max
    
    @freeze_time("2024-01-15 12:00:00")
    def test_get_brightness(self, controller):
        """Test get_brightness returns current value."""
        brightness = controller.get_brightness()
        assert brightness == 150
    
    def test_set_max_brightness(self, controller):
        """Test updating max brightness."""
        controller.set_max_brightness(150)
        assert controller.max_brightness == 150
    
    def test_set_night_mode_brightness(self, controller):
        """Test updating night mode brightness."""
        controller.set_night_mode_brightness(40)
        assert controller.night_mode_brightness == 40
    
    def test_set_day_brightness(self, controller):
        """Test updating day brightness."""
        controller.set_day_brightness(180)
        assert controller.day_brightness == 180
    
    @freeze_time("2024-01-15 12:00:00")
    def test_brightness_sensor_integration(self, controller):
        """Test brightness adjustment with sensor."""
        sensor = MockSensorAdapter(brightness_value=80)
        sensor.initialize()
        controller.set_sensor_adapter(sensor)
        
        # Sensor reading (80) is lower than day brightness (150)
        brightness = controller.calculate_brightness()
        
        assert brightness == 80  # Uses sensor value
        assert controller.last_sensor_value == 80
    
    def test_has_sensor_false(self, controller):
        """Test sensor detection when not installed."""
        assert controller.has_sensor() is False
    
    def test_has_sensor_true(self, controller):
        """Test sensor detection when installed."""
        sensor = MockSensorAdapter()
        controller.set_sensor_adapter(sensor)
        assert controller.has_sensor() is True
    
    @freeze_time("2024-01-15 12:00:00")
    def test_brightness_sensor_higher_than_base(self, controller):
        """Test sensor reading higher than base doesn't exceed it."""
        sensor = MockSensorAdapter(brightness_value=200)
        sensor.initialize()
        controller.set_sensor_adapter(sensor)
        controller.day_brightness = 150
        
        brightness = controller.calculate_brightness()
        
        # Sensor (200) is higher, so use day brightness (150)
        assert brightness == 150
    
    @freeze_time("2024-01-15 12:00:00")
    def test_brightness_transition_logging(self, controller, caplog):
        """Test brightness transition is logged."""
        import logging
        caplog.set_level(logging.INFO)
        
        controller.day_brightness = 180
        brightness = controller.calculate_brightness()
        
        assert "Brightness transition" in caplog.text
        assert "180" in caplog.text
    
    def test_get_status(self, controller):
        """Test status reporting."""
        status = controller.get_status()
        
        assert status['current_brightness'] == 150
        assert status['day_brightness'] == 150
        assert status['night_mode_brightness'] == 50
        assert status['max_brightness'] == 200
        assert status['has_sensor'] is False
    
    @freeze_time("2024-01-15 12:00:00")
    def test_get_status_with_sensor(self, controller):
        """Test status reporting with sensor."""
        sensor = MockSensorAdapter(brightness_value=100)
        sensor.initialize()
        controller.set_sensor_adapter(sensor)
        controller.calculate_brightness()
        
        status = controller.get_status()
        
        assert status['has_sensor'] is True
        assert status['last_sensor_value'] == 100
    
    @freeze_time("2024-01-15 12:00:00")
    def test_get_status_night_mode(self, controller):
        """Test status correctly reports night mode."""
        with freeze_time("2024-01-15 23:00:00"):
            status = controller.get_status()
            assert status['is_night_mode'] is True
    
    def test_default_day_brightness_uses_max(self):
        """Test that day_brightness defaults to max_brightness when None."""
        controller = BrightnessController(
            max_brightness=200,
            day_brightness=None,
            night_mode_brightness=50
        )
        assert controller.day_brightness == 200
    
    @freeze_time("2024-01-15 12:00:00")
    def test_brightness_no_sensor_error(self, controller):
        """Test brightness calculation is resilient to sensor errors."""
        # Create a mock sensor that raises an error
        class BadSensor:
            def read_ambient_brightness(self):
                raise Exception("Sensor error")
        
        controller.set_sensor_adapter(BadSensor())
        
        # Should still return day brightness despite sensor error
        brightness = controller.calculate_brightness()
        assert brightness == 150
