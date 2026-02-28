# Quickstart: Wi-Fi Provisioning

Get your Weatherbox device connected to Wi-Fi without SSH.

## Prerequisites

- Raspberry Pi (any model) with Raspbian OS installed
- USB power adapter
- 2.4GHz Wi-Fi network available
- Any device with a web browser (laptop, tablet, phone)

## Installation

### 1. Flash the Image

If you haven't already:
```bash
# On your computer, using Raspberry Pi Imager or dd:
sudo dd if=weatherbox-os.img of=/dev/sdX bs=4M conv=fsync
# Replace /dev/sdX with your SD card device (e.g., /dev/sdb)
```

### 2. Deploy the Provisioning Service

SSH into your Pi (or attach keyboard/monitor):
```bash
ssh pi@raspberrypi.local
# or: ssh pi@<pi-ip-address>
```

Then:
```bash
# Install dependencies
sudo apt update
sudo apt install -y python3-flask python3-requests network-manager dnsmasq hostapd

# Copy files to device
scp -r weatherbox/ pi@raspberrypi.local:~/src/

# Enable systemd service
sudo systemctl enable weatherbox-provisioning
sudo systemctl start weatherbox-provisioning
```

## First Boot Provisioning Flow

### Scenario A: Fresh Device (No Stored Credentials)

1. **Power on the device**
   - Device boots and runs the provisioning service
   - Access point `weatherbox-setup` will appear within 30–60 seconds
   - **Note**: This requires hostapd/dnsmasq to be installed

2. **Connect to the AP**
   - On your laptop/phone, open Wi-Fi networks
   - Connect to `weatherbox-setup` (open network, no password)
   - Device receives IP address in `192.168.4.x` range

3. **Open the Captive Portal**
   - Browser may auto-launch captive portal, or manually visit:
     ```
     http://192.168.4.1:8080
     ```
   - You should see the Weatherbox Wi-Fi setup form

4. **Scan for Networks**
   - Click **📡 Scan for Networks**
   - Wait 5–10 seconds for list to appear
   - You'll see all visible Wi-Fi networks with signal strength and security type

5. **Select and Provision**
   - Click on your home Wi-Fi network (e.g., "MyHomeNetwork")
   - SSID field auto-populates
   - Enter your Wi-Fi password
   - Observe password strength indicator
   - Click **✓ Connect**
   - Should see "Credentials saved successfully"

6. **Verify Connection**
   - Device now connects to your home network
   - Provisioning AP disappears
   - Device continues boot sequence and joins your network

### Scenario B: Device with Stored Credentials

1. **Power on the device**
   - Device attempts to connect using stored credentials
   - If successful: device joins your network (no provisioning needed)
   - If failed: device starts AP after 60 seconds

2. **To Re-provision**
   - Clear stored credentials:
     ```bash
     sudo rm /etc/weatherbox/credentials.yaml
     sudo systemctl restart weatherbox-provisioning
     ```
   - Follow Scenario A

## Verification

### Verify Device is Connected

**Option 1**: Check router's client list
- Open your router's admin panel
- Look for "weatherbox" or "raspberrypi" in connected devices
- Note the assigned IP address

**Option 2**: SSH to device
```bash
ssh pi@weatherbox.local
# or: ssh pi@<assigned-ip>
```

**Option 3**: Ping the device
```bash
ping weatherbox.local
# or: ping <ip-address>
```

### Check Provisioning Logs

```bash
# View recent logs
journalctl -u weatherbox-provisioning -n 20

# Follow logs in real-time
journalctl -u weatherbox-provisioning -f

# Filter for errors only
journalctl -u weatherbox-provisioning | grep -i error
```

## Troubleshooting

### AP Does Not Appear After Boot

**Possible Cause**: hostapd/dnsmasq not installed or misconfigured

**Solution**:
```bash
# Verify packages are installed
sudo apt install -y hostapd dnsmasq

# Check hostapd status
sudo systemctl status hostapd
sudo systemctl status dnsmasq

# Restart provisioning service
sudo systemctl restart weatherbox-provisioning
```

### Cannot Connect to AP

**Possible Cause**: AP SSID or mode misconfigured

**Solution**:
1. Check configuration:
   ```bash
   cat /etc/weatherbox/config.yaml | grep ap_
   ```

2. Verify interface is up:
   ```bash
   sudo ip link show wlan0
   # Should show "UP"
   ```

3. Check DHCP server:
   ```bash
   sudo journalctl -u dnsmasq -n 10
   ```

### Captive Portal Not Loading

**Possible Cause**: Flask app not running or port blocked

**Solution**:
```bash
# Check Flask process
sudo ps aux | grep python | grep flask

# Verify port 8080 is listening
sudo netstat -tuln | grep 8080

# Try manual curl
curl http://192.168.4.1:8080

# Check Flask logs
journalctl -u weatherbox-provisioning | tail -20
```

### Password Validation Errors

**"Password must be at least 8 characters"**
- Wi-Fi passwords must be 8–63 characters
- If your password is shorter, temporarily change your Wi-Fi password or use a guest network

**"Network name must be 32 characters or less"**
- SSID must not exceed 32 characters
- Choose or rename your Wi-Fi network

### Device Does Not Connect After Provisioning

**Possible Cause**: Credentials not saved, or incorrect password entered

**Solution**:
```bash
# Check if credentials file exists
sudo ls -la /etc/weatherbox/credentials.yaml

# Verify permissions (should be 0o600)
sudo stat /etc/weatherbox/credentials.yaml

# View stored credentials (password will be visible)
sudo cat /etc/weatherbox/credentials.yaml

# Clear and re-provision if incorrect
sudo rm /etc/weatherbox/credentials.yaml
sudo systemctl restart weatherbox-provisioning
```

## Recovery

### Reset to Factory / Clear Credentials

```bash
sudo rm /etc/weatherbox/credentials.yaml
sudo systemctl restart weatherbox-provisioning
```

Device will boot into AP mode again and allow re-provisioning.

### Manual Network Configuration (Advanced)

If provisioning doesn't work, configure Wi-Fi via SSH:

```bash
# Using nmcli (NetworkManager)
sudo nmcli device wifi connect "SSID" password "PASSWORD"

# Using wpa_cli (wpa_supplicant)
sudo wpa_cli add_network
sudo wpa_cli set_network 0 ssid '"SSID"'
sudo wpa_cli set_network 0 psk '"PASSWORD"'
sudo wpa_cli enable_network 0
```

## Next Steps

Once your device is connected to Wi-Fi:

1. **Set up Weather Display** (if installed)
   - Configure Met Office location code
   - Start the display service
   - Verify weather forecast renders on 8×8 matrices

2. **Access via Network**
   - SSH: `ssh pi@weatherbox.local`
   - Check logs: `journalctl -u weatherbox-provisioning`
   - Deploy updates without re-provisioning

3. **Automate at Boot**
   - Service automatically starts on device power-on
   - Device connects to stored network automatically
   - No manual intervention needed on subsequent boots

## Support

For issues or questions:

1. **Check logs first**:
   ```bash
   journalctl -u weatherbox-provisioning -n 50
   ```

2. **Review this quickstart** for your specific scenario

3. **Manual testing**:
   - Test Wi-Fi credentials manually with nmcli/wpa_cli
   - Test Flask app with curl from device
   - Verify permissions on credential files

---

**Last Updated**: 2026-02-28  
**Version**: 1.0
