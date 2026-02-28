# Quick Start: Weather Display (002-weather-display)

This guide walks through deploying the weather display feature on Raspberry Pi with attached 8×8 LED matrices.

## Prerequisites

- **Hardware**: Raspberry Pi 3B+ or later with 4× chained 8×8 RGB LED matrices
- **OS**: Raspberry Pi OS (Debian-based)
- **Connectivity**: Wi-Fi connected (use 001-connect provisioning)
- **API Key**: Met Office DataPoint API key (optional; local fallback available)

## Installation

### 1. Install Dependencies

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python and build tools
sudo apt install -y python3.11 python3-pip python3-dev git

# Install RGB LED matrix library dependencies (if using real hardware)
sudo apt install -y build-essential libpython3-dev

# Clone or navigate to weatherbox repository
cd ~/src/weatherbox
```

### 2. Install Weatherbox Package

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install weatherbox with display dependencies
pip install -e ".[display]"

# Or install all dependencies
pip install -e ".[display, sensors, dev]"
```

### 3. Configure Display Service

#### Create configuration directory

```bash
sudo mkdir -p /etc/weatherbox
sudo chown $(whoami) /etc/weatherbox
```

#### Copy example configs

```bash
# Weather display configuration
cp config/weather-display.yaml.example /etc/weatherbox/weather-display.yaml
cp config/icons.yaml.example /etc/weatherbox/icons.yaml

# Edit configuration (set your location, API key, brightness)
nano /etc/weatherbox/weather-display.yaml
```

#### Configure Met Office API

Two options:

**Option A: DataPoint API (recommended for UK)**
- Get free API key from [Met Office DataPoint](https://www.metoffice.gov.uk/services/data/datapoint)
- Edit `/etc/weatherbox/weather-display.yaml`:
  ```yaml
  met_office:
    api_key: YOUR_KEY_HERE
    location_code: "352409"  # e.g., London
    cache_minutes: 60
  ```

**Option B: Local fallback (no API key needed)**
- Edit `/etc/weatherbox/weather-display.yaml`:
  ```yaml
  met_office:
    api_key: null  # Use local fallback
    use_fallback: true
  ```

#### Customize icon mapping

Edit `/etc/weatherbox/icons.yaml` to map weather types to LED icons:

```yaml
fallback: 0  # Icon ID for unknown types

mappings:
  "Clear": 1
  "Partly cloudy": 2
  "Overcast": 3
  "Light rain": 5
  "Heavy rain": 6
  "Snow": 7
```

### 4. Install Systemd Service

```bash
# Copy systemd unit
sudo cp packaging/systemd/weatherbox-display.service \
  /etc/systemd/system/

# Edit service if needed (GPIO pins, user, etc.)
sudo nano /etc/systemd/system/weatherbox-display.service

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable weatherbox-display
sudo systemctl start weatherbox-display

# Check status
sudo systemctl status weatherbox-display

# View logs
sudo journalctl -u weatherbox-display -f
```

## Verification

### 1. Check Display Output

Watch the LED matrices after starting the service:

```bash
# Display should show weather forecast within 10-15 seconds
# Matrix 0: Today's weather
# Matrices 1-3: Next 3 days

# Watch logs for activity
journalctl -u weatherbox-display -f | grep -i "render\|fetch\|update"
```

### 2. Verify Update Schedule

```bash
# Daytime (06:00-23:00): Updates every 5 minutes
# Nighttime (23:00-06:00): Updates every 60 minutes

# Check next scheduled update (in minutes)
systemctl status weatherbox-display | grep "Active:"

# Watch for update events in logs
journalctl -u weatherbox-display | grep "updated\|next update"
```

### 3. Test API Failure Handling

```bash
# Temporarily disconnect Internet (or stop Wi-Fi)
# Display should show error symbol (X pattern)
# Check retry schedule in logs

# Reconnect Internet
# Display should recover within next retry interval
# Watch logs for recovery: grep "success\|recovered"
```

### 4. Brightness Control

```bash
# Observe brightness changes:
# - Daytime (06:00-23:00): Full brightness
# - Night (23:00-06:00): Reduced brightness
# - After 22:00: Extra low brightness (night mode)

# Adjust brightness in config if needed:
nano /etc/weatherbox/weather-display.yaml
# Change: day_brightness, night_brightness, max_brightness
```

## Troubleshooting

### Display not showing data

```bash
# Check service status
sudo systemctl status weatherbox-display

# View error logs
sudo journalctl -u weatherbox-display -n 30

# Test API connectivity
curl -s "https://api.metoffice.gov.uk/..." | head

# Verify config files
ls -la /etc/weatherbox/

# Test display manually (requires systemd service stopped)
sudo systemctl stop weatherbox-display
sudo python3 -c "from weatherbox.display.rpi_adapter import RpiAdapter; a = RpiAdapter(); a.initialize(); print('Display OK')"
```

### Service crashes on startup

```bash
# Check GPIO permissions
ls -la /dev/mem /dev/gpiomem

# Add user to correct group
sudo usermod -a -G gpio $(whoami)

# Or run service as root (less secure)
sudo nano /etc/systemd/system/weatherbox-display.service
# Change: User=root
sudo systemctl daemon-reload
sudo systemctl restart weatherbox-display
```

### API errors / no weather data

```bash
# Check API key config
cat /etc/weatherbox/weather-display.yaml | grep api_key

# Test API manually
curl "https://api.metoffice.gov.uk/v0/forecasts/point/daily?key=YOUR_KEY&latitude=51.5&longitude=-0.1"

# Check Met Office API status
# Visit: https://www.metoffice.gov.uk/services/data/datapoint

# Switch to fallback if API unavailable
sed -i 's/use_fallback: false/use_fallback: true/' /etc/weatherbox/weather-display.yaml
sudo systemctl restart weatherbox-display
```

### Brightness not adjusting

```bash
# Check brightness controller logs
journalctl -u weatherbox-display | grep -i "brightness"

# Verify brightness sensor (if installed)
ls -la /sys/bus/i2c/devices/

# Manually set brightness to test
sudo python3 << 'EOF'
from weatherbox.brightness.controller import BrightnessController
b = BrightnessController(day_brightness=200, max_brightness=255)
print(f"Test brightness: {b.get_brightness()}")
EOF
```

## Advanced Configuration

### Optional: Install Brightness Sensor

For automatic brightness adjustment based on ambient light:

```bash
# Install sensor adapter
pip install adafruit-circuitpython-tsl2561

# Configure sensor in weather-display.yaml
nano /etc/weatherbox/weather-display.yaml

brightness:
  sensor:
    enable: true
    type: "tsl2561"  # or "adc"
    i2c_address: 0x39
```

### Performance Tuning

```yaml
# Increase forecast cache time to reduce API calls
met_office:
  cache_minutes: 120  # Cache for 2 hours instead of 1

# Reduce brightness updates
brightness:
  update_interval_seconds: 300  # Update every 5 min instead of per-render

# Optimize rendering
display:
  frame_timeout_ms: 100
  render_threads: 1
```

### Diagnostic Mode

Enable verbose logging and frame capture:

```bash
# Edit systemd service
sudo nano /etc/systemd/system/weatherbox-display.service

# Add environment variable
Environment="WEATHERBOX_LOG_LEVEL=DEBUG"
Environment="WEATHERBOX_DIAGNOSTICS=/var/log/weatherbox/diagnostics"

sudo systemctl daemon-reload && sudo systemctl restart weatherbox-display

# Check diagnostics
ls -la /var/log/weatherbox/diagnostics/
```

## Maintenance

### Update Weather Display

```bash
# Pull latest code
cd ~/src/weatherbox
git pull origin main

# Reinstall package
source venv/bin/activate
pip install -e ".[display]"

# Restart service
sudo systemctl restart weatherbox-display
```

### Monitor logs regularly

```bash
# Watch for errors
journalctl -u weatherbox-display -f | grep -E "ERROR|FAIL|Traceback"

# Rotate logs if needed
sudo journalctl --vacuum=time=30d
```

### Check disk usage

```bash
# Diagnostics directory
du -sh /var/log/weatherbox/

# Clean old diagnostics
find /var/log/weatherbox -name "*.json" -mtime +7 -delete
```

## Support

For issues or questions:

1. Check logs: `journalctl -u weatherbox-display -n 50`
2. Verify config: `cat /etc/weatherbox/weather-display.yaml`
3. Run smoke tests: `./tools/hil/smoke_display_rotation.sh`
4. See full HIL checklist: `cat specs/002-weather-display/checklists/hil.md`

---

**Feature**: Weather Display (002-weather-display)
**Status**: Production Ready
**Last Updated**: 2024
