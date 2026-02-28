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

## First Boot

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
