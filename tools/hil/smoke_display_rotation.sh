#!/bin/bash
# Smoke test script for weather display feature on Raspberry Pi
# Tests basic functionality without full hardware (can run in mock mode)
# Usage: ./spec-hil/smoke_display_rotation.sh [--hardware]

set -e

#Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$SCRIPT_DIR"

# Default to mock mode (no real hardware required)
HARDWARE_MODE=false
if [[ "$1" == "--hardware" ]]; then
    HARDWARE_MODE=true
fi

echo "=========================================="
echo "Weather Display Smoke Test"
echo "=========================================="
echo "Mode: $([ "$HARDWARE_MODE" = true ] && echo "HARDWARE" || echo "MOCK")"
echo "Repo: $SCRIPT_DIR"
echo ""

# Check dependencies
echo -n "Checking dependencies..."
if ! python3 -c "import weatherbox" 2>/dev/null; then
    echo -e " ${RED}FAIL${NC}"
    echo "  weatherbox package not installed"
    echo "  Run: pip install -e .[dev]"
    exit 1
fi
echo -e " ${GREEN}OK${NC}"

# Test 1: Import core modules
echo -n "Test 1: Import core modules..."
python3 << 'PYTEST1'
try:
    from weatherbox.display_service import WeatherDisplayService
    from weatherbox.weather.retry_scheduler import RetryScheduler, UpdateWindowScheduler
    from weatherbox.weather.forecast_parser import ForecastParser
    from weatherbox.brightness.controller import BrightnessController
    from weatherbox.icons.loader import IconLoader
    from weatherbox.display.adapter import DisplayAdapter, MockDisplayAdapter
    from weatherbox.display.frame_capture import FrameCaptureAdapter
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")
    exit(1)
PYTEST1

# Test 2: Create display service with mocks
echo -n "Test 2: Create display service with mocks..."
python3 << 'PYTEST2'
try:
    from weatherbox.display_service import WeatherDisplayService
    from weatherbox.display.adapter import MockDisplayAdapter
    from weatherbox.brightness.controller import BrightnessController
    from weatherbox.icons.loader import IconLoader
    
    class StubAPI:
        def fetch_forecast(self):
            from datetime import datetime
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
            return [
                DailySummary(datetime.now(), 'Clear', 'Clear', 'Clear', 15, 5, ),
            ]
    
    display = MockDisplayAdapter()
    api = StubAPI()
    icons = IconLoader()
    icons.mappings = {'Clear': 1}
    brightness = BrightnessController()
    
    service = WeatherDisplayService(display, api, icons, brightness)
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")
    exit(1)
PYTEST2

# Test 3: Initialize display service
echo -n "Test 3: Initialize display service..."
python3 << 'PYTEST3'
try:
    from weatherbox.display_service import WeatherDisplayService
    from weatherbox.display.adapter import MockDisplayAdapter
    from weatherbox.brightness.controller import BrightnessController
    from weatherbox.icons.loader import IconLoader
    from datetime import datetime
    from dataclasses import dataclass
    
    class StubAPI:
        def fetch_forecast(self):
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
            return [
                DailySummary(datetime.now(), 'Clear', 'Clear', 'Clear', 15, 5),
            ]
    
    display = MockDisplayAdapter()
    api = StubAPI()
    icons = IconLoader()
    icons.mappings = {'Clear': 1}
    brightness = BrightnessController()
    service = WeatherDisplayService(display, api, icons, brightness)
    
    if not service.initialize():
        print("FAIL: initialization returned False")
        exit(1)
    
    if not display.is_initialized():
        print("FAIL: display not initialized")
        exit(1)
    
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")
    exit(1)
PYTEST3

# Test 4: Fetch forecast
echo -n "Test 4: Fetch forecast..."
python3 << 'PYTEST4'
try:
    from weatherbox.display_service import WeatherDisplayService
    from weatherbox.display.adapter import MockDisplayAdapter
    from weatherbox.brightness.controller import BrightnessController
    from weatherbox.icons.loader import IconLoader
    from datetime import datetime
    from dataclasses import dataclass
    
    class StubAPI:
        def fetch_forecast(self):
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
            return [
                DailySummary(datetime.now(), 'Clear', 'Clear', 'Clear', 15, 5),
            ]
    
    display = MockDisplayAdapter()
    api = StubAPI()
    icons = IconLoader()
    icons.mappings = {'Clear': 1}
    brightness = BrightnessController()
    service = WeatherDisplayService(display, api, icons, brightness)
    service.initialize()
    
    forecast = service.fetch_forecast()
    if not forecast or len(forecast) == 0:
        print("FAIL: no forecast data")
        exit(1)
    
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")
    exit(1)
PYTEST4

# Test 5: Render forecast
echo -n "Test 5: Render forecast..."
python3 << 'PYTEST5'
try:
    from weatherbox.display_service import WeatherDisplayService
    from weatherbox.display.adapter import MockDisplayAdapter
    from weatherbox.brightness.controller import BrightnessController
    from weatherbox.icons.loader import IconLoader
    from datetime import datetime
    from dataclasses import dataclass
    
    class StubAPI:
        def fetch_forecast(self):
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
            return [
                DailySummary(datetime.now(), 'Clear', 'Clear', 'Clear', 15, 5),
            ]
    
    display = MockDisplayAdapter()
    api = StubAPI()
    icons = IconLoader()
    icons.mappings = {'Clear': 1}
    brightness = BrightnessController()
    service = WeatherDisplayService(display, api, icons, brightness)
    service.initialize()
    
    forecast = service.fetch_forecast()
    if not service.render_forecast(forecast):
        print("FAIL: render returned False")
        exit(1)
    
    # Check that matrices have been rendered (contain bitmaps)
    if sum(1 for m in display.matrices if m) == 0:
        print("FAIL: no matrices rendered")
        exit(1)
    
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")
    exit(1)
PYTEST5

# Test 6: Update scheduling
echo -n "Test 6: Update scheduling..."
python3 << 'PYTEST6'
try:
    from weatherbox.weather.retry_scheduler import UpdateWindowScheduler
    from datetime import datetime, timedelta
    
    scheduler = UpdateWindowScheduler()
    
    # Test daytime
    is_day = scheduler.is_daytime(datetime(2024, 1, 15, 12, 0))
    if not is_day:
        print("FAIL: noon not detected as daytime")
        exit(1)
    
    # Test night
    is_night = not scheduler.is_daytime(datetime(2024, 1, 15, 23, 0))
    if not is_night:
        print("FAIL: 23:00 not detected as night")
        exit(1)
    
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")
    exit(1)
PYTEST6

# Test 7: Brightness control
echo -n "Test 7: Brightness control..."
python3 << 'PYTEST7'
try:
    from weatherbox.brightness.controller import BrightnessController
    from datetime import datetime
    
    brightness = BrightnessController(max_brightness=200, day_brightness=150, night_mode_brightness=50)
    
    # Test daytime brightness
    day_brightness = brightness.calculate_brightness(datetime(2024, 1, 15, 12, 0))
    if day_brightness != 150:
        print(f"FAIL: day brightness should be 150, got {day_brightness}")
        exit(1)
    
    # Test night brightness
    night_brightness = brightness.calculate_brightness(datetime(2024, 1, 15, 23, 0))
    if night_brightness != 50:
        print(f"FAIL: night brightness should be 50, got {night_brightness}")
        exit(1)
    
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")
    exit(1)
PYTEST7

# Test 8: Retry scheduler
echo -n "Test 8: Retry scheduler..."
python3 << 'PYTEST8'
try:
    from weatherbox.weather.retry_scheduler import RetryScheduler, RetryState
    from datetime import timedelta
    
    scheduler = RetryScheduler()
    
    # First failure should trigger 1-min backoff
    interval = scheduler.record_failure()
    if interval != timedelta(minutes=1):
        print(f"FAIL: first failure should be 1min, got {interval}")
        exit(1)
    
    if scheduler.state != RetryState.BACKOFF_1_MIN:
        print(f"FAIL: should be in BACKOFF_1_MIN state, got {scheduler.state}")
        exit(1)
    
    # Success should reset
    scheduler.record_success()
    if scheduler.state != RetryState.IDLE:
        print(f"FAIL: should be in IDLE after success, got {scheduler.state}")
        exit(1)
    
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")
    exit(1)
PYTEST8

# Test 9: Icon loader
echo -n "Test 9: Icon loader..."
python3 << 'PYTEST9'
try:
    from weatherbox.icons.loader import IconLoader
    
    loader = IconLoader()
    loader.mappings = {'Clear': 1, 'Rainy': 2, 'Cloudy': 3}
    
    # Test mapped type
    icon_id = loader.get_icon_id('Clear')
    if icon_id != 1:
        print(f"FAIL: Clear should map to 1, got {icon_id}")
        exit(1)
    
    # Test unmapped type (should use fallback)
    icon_id = loader.get_icon_id('Unknown')
    if icon_id != loader.fallback_icon_id:
        print(f"FAIL: Unknown should use fallback")
        exit(1)
    
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")
    exit(1)
PYTEST9

# Test 10: Forecast parser
echo -n "Test 10: Forecast parser..."
python3 << 'PYTEST10'
try:
    from weatherbox.weather.forecast_parser import ForecastParser
    from datetime import datetime
    
    parser = ForecastParser()
    
    periods = [
        {'timestamp': datetime(2024, 1, 15, 12, 0), 'weather_type': 'Clear', 'temperature': 15},
        {'timestamp': datetime(2024, 1, 15, 15, 0), 'weather_type': 'Clear', 'temperature': 14},
        {'timestamp': datetime(2024, 1, 15, 23, 0), 'weather_type': 'Cloudy', 'temperature': 8},
    ]
    
    summary = parser.aggregate_daily_summary(periods, datetime(2024, 1, 15))
    
    if summary['max_temperature'] != 15:
        print(f"FAIL: max temp should be 15, got {summary['max_temperature']}")
        exit(1)
    
    if summary['min_temperature'] != 8:
        print(f"FAIL: min temp should be 8, got {summary['min_temperature']}")
        exit(1)
    
    print("OK")
except Exception as e:
    print(f"FAIL: {e}")
    exit(1)
PYTEST10

echo ""
echo "=========================================="
echo -e "${GREEN}All smoke tests PASSED${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  - Run full test suite: pytest tests/"
echo "  - Set up systemd service on Pi"
echo "  - Configure Met Office API key"
echo "  - Run hardware tests (with --hardware flag)"
echo ""
