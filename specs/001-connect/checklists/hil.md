# Hardware-in-the-Loop (HIL) - Wi-Fi Provisioning Smoke Test

This document describes the manual hardware tests for the Wi-Fi provisioning feature on real Raspberry Pi hardware.

## Prerequisites

- [ ] Raspberry Pi with Raspbian OS installed
- [ ] Development laptop on same local network
- [ ] SSH access to Pi configured
- [ ] weatherbox provisioning service installed and enabled
- [ ] All Phase 3 implementation code deployed to device

## Test Environment Setup

- [ ] Device has no stored Wi-Fi credentials (`/etc/weatherbox/credentials.yaml` does not exist)
- [ ] Device is powered on and boots to console
- [ ] Device Wi-Fi hardware is functional (can detect SSID)
- [ ] dnsmasq and hostapd packages installed on device
- [ ] Flask dependencies installed (`pip install -r requirements.txt`)

## Test Scenarios

### Scenario 1: Fresh Boot Creates AP

**Objective**: Device boots without credentials and starts access point.

- [ ] Power on device
- [ ] Wait 30 seconds for boot completion
- [ ] From laptop, scan available Wi-Fi networks
- [ ] Verify `weatherbox-setup` SSID appears (within 60s of boot)
- [ ] Connect to `weatherbox-setup` (open network)
- [ ] Verify IP address assigned in 192.168.4.0/24 range
- [ ] Open browser to http://192.168.4.1:8080
- [ ] Verify captive portal loads (see form with scan button)

**Pass Criteria**: AP is online and accessible within 60s of fresh boot

---

### Scenario 2: Network Scan from Portal

**Objective**: User can scan for available networks from captive portal.

- **Starting State**: Connected to `weatherbox-setup` AP from Scenario 1
- [ ] On captive portal page, click "📡 Scan for Networks" button
- [ ] Wait for scan to complete (~5-10 seconds)
- [ ] Verify list of available networks appears (at least one should be visible)
- [ ] Verify network names (SSIDs) are displayed correctly
- [ ] Verify signal strength (%) is shown for each network
- [ ] Verify security type is shown (WPA2, WPA, Open, etc.)
- [ ] Check browser console for JavaScript errors (F12 → Console tab)

**Pass Criteria**: Scan completes without errors; networks are accurately listed with signal and security info

---

### Scenario 3: Provision New Credentials

**Objective**: User can enter and save Wi-Fi credentials via portal.

- **Starting State**: On captive portal with network scan results visible
- [ ] Click on your Wi-Fi network (e.g., "YourHomeNetwork")
- [ ] Verify SSID field auto-populates with selected network name
- [ ] Enter Wi-Fi password in the password field
- [ ] Observe password strength indicator (should show appropriate strength)
- [ ] Click "✓ Connect" button
- [ ] Wait for response (should show success message or error)
- [ ] Verify success message appears: "Credentials saved successfully" or similar

**Pass Criteria**: Credentials are accepted; success message is shown

---

### Scenario 4: Device Connects on Next Boot

**Objective**: After provisioning, device connects to Wi-Fi on reboot.

- **Starting State**: Credentials have been saved via Scenario 3
- [ ] Power off device (or SSH: `sudo shutdown -r now` for soft reboot)
- [ ] Wait 60 seconds for device to fully boot
- [ ] From your home network router, check connected devices
- [ ] Verify device appears in connected devices list
- [ ] Alternatively, SSH to Pi on your home network (get IP from router or use `ping weatherbox.local`)
- [ ] Verify `/etc/weatherbox/credentials.yaml` exists and is readable (by service user)

**Pass Criteria**: Device connects to provisioned network automatically on next boot

---

### Scenario 5: Credential Storage Security

**Objective**: Verify credentials are stored securely.

- **Starting State**: Device has provisioned credentials
- [ ] SSH into device: `ssh pi@<device-ip>`
- [ ] Check credential file: `ls -l /etc/weatherbox/credentials.yaml`
- [ ] Verify file mode is `-rw-------` (0o600 = owner read/write only)
- [ ] Verify owner is the service user (e.g., `root` or `weatherboxsvc`)
- [ ] Attempt to read as unprivileged user (should be denied):
  ```bash
  sudo -u nobody cat /etc/weatherbox/credentials.yaml
  ```
- [ ] Verify access denied error

**Pass Criteria**: File permissions are 0o600; unauthorized users cannot read credentials

---

### Scenario 6: CSRF Protection

**Objective**: Verify CSRF tokens are validated.

- **Starting State**: Connected to provisioning AP
- [ ] On captive portal, open developer tools (F12)
- [ ] Go to Network tab; clear history
- [ ] Click "Scan for Networks"
- [ ] Inspect the POST request to `/api/scan`
- [ ] Verify `csrf_token` field is present in request body
- [ ] Manually modify the CSRF token in developer tools (simulate CSRF attack):
  - Open Console tab
  - Run: `document.getElementById('csrf_token').value = 'invalid-token'`
- [ ] Click scan button again
- [ ] Verify request fails (403 Forbidden response)
- [ ] Check browser console for error message

**Pass Criteria**: Invalid CSRF tokens are rejected with 403; error message is displayed

---

### Scenario 7: Connection with Wrong Credentials

**Objective**: Verify graceful handling of invalid credentials.

- **Starting State**: Fresh boot with AP active
- [ ] Connect to `weatherbox-setup` AP
- [ ] Open captive portal (http://192.168.4.1:8080)
- [ ] Select a Wi-Fi network from scan results
- [ ] Enter an incorrect password for that network
- [ ] Click "✓ Connect"
- [ ] Observe response (should reject or indicate error)
- [ ] Verify no credentials are saved
- [ ] Unplug network cable from router (simulate network unavailable)
- [ ] Click scan button again
- [ ] Verify graceful error message or timeout (not a crash)

**Pass Criteria**: Invalid credentials rejected; app handles network errors gracefully

---

### Scenario 8: Credential Update/Change

**Objective**: User can update stored credentials with new Wi-Fi network.

- **Starting State**: Device is on home network (from previous provisioning)
- [ ] Switch to 5GHz band of router (or different SSID)
- [ ] Device should disconnect
- [ ] Device should enter AP mode automatically
- [ ] Connect to `weatherbox-setup` AP again
- [ ] Scan networks and select the 5GHz SSID
- [ ] Enter password for new network
- [ ] Click "✓ Connect"
- [ ] Wait 30 seconds for device to reconnect
- [ ] Verify device now connects to new network on next scan

**Pass Criteria**: Credentials can be updated; device switches to new network

---

### Scenario 9: Logging and Observability

**Objective**: Verify provisioning events are logged correctly.

- **Starting State**: Device has completed provisioning
- [ ] SSH into device
- [ ] Check provisioning logs:
  ```bash
  journalctl -u weatherbox-provisioning -n 50
  ```
- [ ] Verify log entries for:
  - Service startup
  - Credential loading attempt
  - Connection attempts with timestamps
  - AP startup (if credentials failed)
  - Network scan requests
  - Credential save operations
- [ ] Verify log level is appropriate (INFO for normal, WARN for issues)
- [ ] Verify no ERROR or CRITICAL logs for successful flow

**Pass Criteria**: All provisioning events are logged; timestamps are accurate; no spurious errors

---

### Scenario 10: Silent Recovery (Optional - Advanced)

**Objective**: Device automatically recovers if network drops.

- **Starting State**: Device connected to home Wi-Fi
- [ ] Unplug Pi from network
- [ ] Wait 30 seconds
- [ ] Verify `weatherbox-setup` AP appears
- [ ] Connected devices lose internet (expected)
- [ ] Connect to `weatherbox-setup` AP
- [ ] Verify captive portal is accessible
- [ ] Plug network back in; provisioning service should detect active connection
- [ ] Check logs for recovery event

**Pass Criteria**: Device automatically falls back to AP when network drops

---

## Test Execution Notes

- Run scenarios sequentially; many depend on previous state
- Between scenarios, you may need to clear credentials:
  ```bash
  sudo rm /etc/weatherbox/credentials.yaml
  sudo systemctl restart weatherbox-provisioning
  ```
- Monitor systemd journal during tests for real-time log output:
  ```bash
  journalctl -u weatherbox-provisioning -f
  ```
- Use browser Developer Tools (F12) to inspect network requests and JavaScript errors

## Pass/Fail Determination

**PASS**: All 9 required scenarios (1-9) pass without errors

**FAIL**: Any of scenarios 1-9 fail; device crashes; credentials not saved; security violations detected

## Regression Testing

After any code changes, re-run all 10 scenarios to ensure no regressions.

---

**Last Updated**: 2026-02-24  
**Test Lead**: [Your Name]  
**Device Model**: [Pi Model]  
**Raspbian Version**: [Version]
