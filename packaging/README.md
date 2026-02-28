# Packaging & Installation Guide

This guide explains how to build and deploy Weatherbox services on a Raspberry Pi.

## Overview

Weatherbox consists of two main services:
1. **Wi-Fi Provisioning** (`weatherbox-provisioning`): Allows network setup via captive portal on first boot
2. **Weather Display** (`weatherbox-display`): Fetches forecasts and renders on LED matrices

Both services run as systemd units and start automatically on boot.

## Prerequisites

- Raspberry Pi 3/4/5 with Raspbian (Buster, Bullseye, or Bookworm)
- SSH access or keyboard+monitor
- Internet connection (for initial setup; device can work offline once provisioned)
- (Optional) 4× 8×8 RGB LED matrices with GPIO/SPI connections

## Build & Deployment

### 1. Prepare the OS Image

#### Option A: Flash a Pre-built Image (Recommended)

```bash
# Download latest Weatherbox Raspbian image
wget https://releases.example.com/weatherbox-latest.img.gz
gunzip weatherbox-latest.img.gz

# Flash to SD card (on macOS/Linux)
sudo dd if=weatherbox-latest.img of=/dev/diskX bs=4m conv=fsync
# Or use Raspberry Pi Imager GUI
```

#### Option B: Manual Installation

If building from scratch:

```bash
# Install base Raspbian OS (using Raspberry Pi Imager or following official docs)
# Then SSH into Pi:
ssh pi@raspberrypi.local

# Update packages
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y \
  python3 python3-pip python3-venv \
  git curl wget \
  network-manager dnsmasq hostapd \
  build-essential libatlas-base-dev

# (Optional) Install GPIO/SPI libraries for LED matrices
sudo apt install -y libgpiod2 python3-libgpiod
```

### 2. Clone & Install Weatherbox

```bash
# Clone repository (or scp from your dev machine):
git clone https://github.com/yourusername/weatherbox.git /opt/weatherbox
cd /opt/weatherbox

# Install Python dependencies
sudo pip3 install -r requirements.txt

# Create configuration directory
sudo mkdir -p /etc/weatherbox /var/log/weatherbox
sudo chown root:root /etc/weatherbox /var/log/weatherbox
sudo chmod 755 /etc/weatherbox /var/log/weatherbox

# Copy configuration templates
sudo cp config.yaml.example /etc/weatherbox/config.yaml
sudo cp config/weather-display.yaml.example /etc/weatherbox/weather-display.yaml
sudo cp config/icons.yaml.example /etc/weatherbox/icons.yaml
```

### 3. Install Systemd Services

#### Wi-Fi Provisioning Service

```bash
# Copy systemd unit
sudo cp packaging/systemd/weatherbox-provisioning.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable weatherbox-provisioning
sudo systemctl start weatherbox-provisioning

# Verify running
sudo systemctl status weatherbox-provisioning
```

#### Weather Display Service (Optional)

```bash
# Copy systemd unit
sudo cp packaging/systemd/weatherbox-display.service /etc/systemd/system/

# Configure location and API key (if using Met Office API)
sudo nano /etc/weatherbox/weather-display.yaml
# Or set via environment:
# export MET_OFFICE_LOCATION="350023"
# export MET_OFFICE_API_KEY="your-api-key-here"

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable weatherbox-display
sudo systemctl start weatherbox-display

# Verify running
sudo systemctl status weatherbox-display
```

### 4. Verify Installation

```bash
# Check both services
sudo systemctl status weatherbox-provisioning weatherbox-display

# View logs
journalctl -u weatherbox-provisioning -n 20
journalctl -u weatherbox-display -n 20

# Follow logs in real-time
journalctl -u weatherbox-provisioning -f
```

## Configuration

### Wi-Fi Provisioning (`/etc/weatherbox/config.yaml`)

Key settings:
- `ap_ssid`: Name of the provisioning hotspot (default: `weatherbox-setup`)
- `ap_mode`: Security mode `open` or `wpa2` (default: `open` for UX)
- `credential_file_path`: Where credentials are stored (default: `/etc/weatherbox/credentials.yaml`)
- `captive_ui_port`: Captive portal web port (default: `8080`)
- `connection_attempts`: Retry attempts before starting AP (default: 3)

### Weather Display (`/etc/weatherbox/weather-display.yaml`)

Key settings:
- `met_office.location_code`: Met Office location ID (e.g., `350023` for Bristol)
- `met_office.api_key`: Optional API key for higher rate limits
- `brightness.cap`: Max LED brightness 0–255 (default: 200)
- `brightness.night_mode_start`: Time to dim (default: `22:00`)
- `display.matrix_count`: Number of 8×8 matrices (default: 4)

### Icon Mapping (`/etc/weatherbox/icons.yaml`)

Maps Met Office weather type codes to LED icon bitmaps (see file comments for reference).

#### Weather Display Icon Configuration

The `icons.yaml` file maps Met Office weather type strings to LED bitmap IDs:

```yaml
icons:
  "Sunny": 0                    # Sun icon (bitmap ID)
  "Partly cloudy": 1            # Partly cloudy
  "Overcast": 2                 # Overcast
  "Mist": 3                     # Mist/fog
  "Patchy rain nearby": 4       # Light rain
  "Patchy rain possible": 4     # Light rain
  "Patchy light rain": 4        # Light rain
  "Light rain": 5               # Rain icon
  "Heavy rain": 6               # Heavy rain icon
  "Patchy snow possible": 7     # Light snow
  "Light snow": 8               # Snow icon
  "Heavy snow": 9               # Heavy snow
  "Thundery outbreaks possible": 10  # Thunder
  "Blizzard": 11                # Blizzard (snow + wind)

# Fallback icon for unmapped weather types
fallback_icon: 0  # Use sunny icon as fallback
```

See `config/icons.yaml.example` for complete mapping reference.

## Weather Display Service Deployment

### Met Office API Integration

The weather display service fetches 3-hourly forecasts from the Met Office DataPoint API:

1. **Get an API Key** (optional but recommended)
   - Visit https://register.ftp.metoffice.gov.uk/WaveRegistrationClient/registration/testapi
   - Free tier supports hourly access with rate limits
   - Register and note your API key

2. **Configure Location**
   ```bash
   sudo nano /etc/weatherbox/weather-display.yaml
   ```
   
   Set your location code (Met Office DataPoint location ID):
   ```yaml
   met_office:
     api_key: "your-api-key-here"      # Leave blank to use free tier
     location_code: "350023"             # Example: Bristol, UK
     # Other location codes: 350009 (London), 350011 (Edinburgh), 350005 (Belfast)
     timeout_seconds: 15
   ```

3. **Verify Configuration**
   ```bash
   # Test API connectivity
   sudo systemctl restart weatherbox-display
   sudo journalctl -u weatherbox-display -f
   # Watch for "Forecast fetched successfully" message
   ```

### Brightness Control

The weather display automatically adjusts LED brightness:

```yaml
brightness:
  cap: 200                          # Max brightness (0-255, prevents overheating)
  night_mode_start: "22:00"         # When to dim (24-hour format)
  night_mode_brightness: 100        # Brightness during night mode (0-255)
  
  # Optional: ambient brightness sensor
  sensor:
    type: "none"                    # Options: none, mock, adc, tsl2561
    # adc: Uses ADS1115 I2C ADC (Ch0 pin)
    # tsl2561: Uses TSL2561 I2C light sensor
```

### Update Windows

The service respects different update intervals for day and night:

```yaml
update_windows:
  daytime_interval_minutes: 5       # Fetch every 5 min during day (06:00-23:00)
  night_interval_minutes: 60        # Fetch every 60 min at night (23:00-06:00)
  daytime_start: "06:00"            # When daytime starts
  daytime_end: "23:00"              # When daytime ends
```

### Retry Schedule

If the API is unavailable, the service automatically retries with exponential backoff:

- **Phase 1**: 1 minute interval (5 attempts, 0-5 min)
- **Phase 2**: 5 minute interval (12 attempts, 5-65 min)
- **Phase 3**: 10 minute interval (up to 24 hours max)

The service will display an error symbol if all retries are exhausted.

### GPIO/SPI Hardware Setup

For real LED matrices:

1. **Enable SPI**
   ```bash
   sudo raspi-config
   # Navigate to: Interface Options > SPI > Enable
   # Exit and reboot
   ```

2. **Configure Hardware**
   ```yaml
   display:
     primary_interface: "rpi_gpio"   # Use GPIO adapter
     matrix_count: 4                 # Number of 8×8 matrices
     brightness_gpio_pin: 13         # (Optional) PWM brightness control
   ```

3. **Run HIL Tests**
   ```bash
   cd /opt/weatherbox
   bash tools/hil/smoke_display_rotation.sh    # Mock tests (no hardware needed)
   
   # Then manual verification (see specs/002-weather-display/checklists/hil.md)
   ```

### Display Output Format

The weather display shows:
- **Matrix 1**: Current day weather + temperature
- **Matrix 2-4**: 3-day forecast (each matrix = 1 day)
- Each matrix displays icon for weather type and min/max temperatures

Example output:
```
[Sunny 15°C] [Rainy 12°C] [Cloudy 10°C] [Cloudy 11°C]
  (Today)    (Tomorrow)   (Day 3)       (Day 4)
```

### Logging & Diagnostics

Weather display logs are sent to systemd journal:

```bash
# View recent logs
sudo journalctl -u weatherbox-display -n 50

# Follow live
sudo journalctl -u weatherbox-display -f

# Show debug logs (if enabled)
sudo journalctl -u weatherbox-display -p debug

# Export logs
sudo journalctl -u weatherbox-display > weather-display.log
```

If forecast is unavailable, check:
- API connectivity: `ping api.metoffice.gov.uk`
- API key: Verify in `/etc/weatherbox/weather-display.yaml`
- Logs: `journalctl -u weatherbox-display`



1. **Power on device**
   - Provisioning service starts
   - Looks for stored credentials in `/etc/weatherbox/credentials.yaml`
   - If none found: starts AP `weatherbox-setup` within 30–60 seconds

2. **Connect and provision**
   - See **[specs/001-connect/quickstart.md](../specs/001-connect/quickstart.md)** for user steps
   - Credentials saved to `/etc/weatherbox/credentials.yaml` (mode 0o600)

3. **Automatic connection**
   - On next boot or reboot, device connects using saved credentials
   - If connection fails: starts AP again (automatic fallback)

## Service Management

### Start/Stop Services

```bash
# Start
sudo systemctl start weatherbox-provisioning weatherbox-display

# Stop
sudo systemctl stop weatherbox-provisioning weatherbox-display

# Restart
sudo systemctl restart weatherbox-provisioning weatherbox-display

# Disable auto-start (manual control only)
sudo systemctl disable weatherbox-provisioning weatherbox-display

# Re-enable auto-start
sudo systemctl enable weatherbox-provisioning weatherbox-display
```

### View Logs

```bash
# Recent logs (last 50 lines)
sudo journalctl -u weatherbox-provisioning -n 50

# Follow in real-time
sudo journalctl -u weatherbox-provisioning -f

# Filter by priority
sudo journalctl -u weatherbox-provisioning -p err

# Show today's logs
sudo journalctl -u weatherbox-provisioning --since today

# Export to file
sudo journalctl -u weatherbox-provisioning > /tmp/weatherbox.log
```

### Restart After Changes

```bash
# Edit config
sudo nano /etc/weatherbox/config.yaml

# Restart services for changes to take effect
sudo systemctl restart weatherbox-provisioning weatherbox-display
```

## Troubleshooting

### Service Won't Start

```bash
# Check service status
sudo systemctl status weatherbox-provisioning

# Check logs for errors
sudo journalctl -u weatherbox-provisioning -n 20

# Try manual run (for debugging)
cd /opt/weatherbox
python3 src/weatherbox/provisioning/boot.py
```

### AP Doesn't Appear

```bash
# Verify hostapd/dnsmasq are installed
sudo apt install -y hostapd dnsmasq

# Check hostapd status
sudo systemctl status hostapd dnsmasq

# Restart provisioning service
sudo systemctl restart weatherbox-provisioning
```

### Credential File Permission Errors

```bash
# Check permissions
sudo ls -la /etc/weatherbox/credentials.yaml
sudo stat /etc/weatherbox/credentials.yaml

# Should show owner=root, mode=600
# If not, fix:
sudo chown root:root /etc/weatherbox/credentials.yaml
sudo chmod 600 /etc/weatherbox/credentials.yaml
```

## Updating Weatherbox

```bash
# Pull latest code
cd /opt/weatherbox
git pull origin main

# Update dependencies (if requirements.txt changed)
sudo pip3 install -r requirements.txt

# Restart services
sudo systemctl restart weatherbox-provisioning weatherbox-display
```

## Uninstallation

```bash
# Stop services
sudo systemctl stop weatherbox-provisioning weatherbox-display

# Disable from auto-start
sudo systemctl disable weatherbox-provisioning weatherbox-display

# Remove systemd units
sudo rm /etc/systemd/system/weatherbox-*.service
sudo systemctl daemon-reload

# Remove files (careful!)
sudo rm -rf /opt/weatherbox
sudo rm -rf /etc/weatherbox
sudo rm -rf /var/log/weatherbox
```

## Development & Testing

### Run Tests Locally

```bash
cd /opt/weatherbox

# Run all tests
python3 -m pytest tests/ -v

# Run specific test file
python3 -m pytest tests/unit/test_wifi_adapter.py -v

# Run with coverage
python3 -m pytest tests/ --cov=src/weatherbox
```

### Manual Testing

```bash
# Test Wi-Fi scanning (provisioning)
python3 -c "from src.weatherbox.wifi.adapter import WifiAdapter; print('OK')"

# Test credential storage
python3 -c "from src.weatherbox.credentials.store import CredentialStore; print('OK')"

# Start Flask app manually
cd /opt/weatherbox
python3 src/weatherbox/provisioning/app.py
# Then visit http://localhost:8080
```

## Hardware Integration

### LED Matrices (Optional)

If using 8×8 RGB LED matrices:

1. **Connect to GPIO/SPI**
   - Follow your matrix manufacturer's wiring guide
   - Typically: GND, 5V, CLK, MOSI, MISO, CS pins

2. **Install rpi-rgb-led-matrix library** (optional)
   ```bash
   git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
   cd rpi-rgb-led-matrix
   make -C bindings/python
   sudo pip3 install bindings/python/
   ```

3. **Configure in `/etc/weatherbox/weather-display.yaml`**
   ```yaml
   display:
     primary_interface: "rpi_gpio"
     matrix_count: 4
   ```

4. **Run HIL smoke tests** (see specs/002-weather-display/checklists/hil.md)

## Support

- **Documentation**: See `specs/*/quickstart.md` for user guides
- **Research**: See `specs/*/research.md` for technical decisions
- **Tests**: See `tests/` directory for validation examples
- **Issues**: Check logs with `journalctl` first, then consult documentation

---

**Last Updated**: 2026-02-28  
**Version**: 1.0
