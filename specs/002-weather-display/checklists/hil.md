# Hardware-in-the-Loop (HIL) Checklist: Weather Display (002-weather-display)

This checklist is for manual verification of the weather display feature running on actual Raspberry Pi hardware with attached LED matrices.

**Prerequisites:**
- Raspberry Pi 3B+ or later
- 4× chained 8×8 RGB LED matrices (via rpi-rgb-led-matrix library)
- GPIO pins accessible (Hat connector or jumper wires)
- Wi-Fi connection (from 001-connect feature)
- Internet connectivity for Met Office API
- Python 3.8+ with weatherbox installed

## Verification Steps

### Setup & Configuration

- [ ] **HIL-001** Verify Pi is booted and connected to Wi-Fi
  - [ ] Check Wi-Fi provisioning from 001-connect works
  - [ ] Confirm Internet access: `ping 8.8.8.8`
  - [ ] Verify stable connection (>30 seconds)

- [ ] **HIL-002** Verify LED matrices are physically connected
  - [ ] Check GPIO pins connected to Hat or matrix board
  - [ ] Verify power supply to matrices (check LED glow)
  - [ ] Confirm all 4 matrices receiving power
  - [ ] No loose connections or short circuits

- [ ] **HIL-003** Verify configuration files are in place
  - [ ] `/etc/weatherbox/config.yaml` exists
  - [ ] `/etc/weatherbox/icons.yaml` exists
  - [ ] `/etc/weatherbox/weather-display.yaml` exists
  - [ ] Met Office API key configured (if required)

- [ ] **HIL-004** Verify systemd service is installed
  - [ ] Check systemd unit: `systemctl cat weatherbox-display`
  - [ ] Service file at `/etc/systemd/system/weatherbox-display.service`
  - [ ] Correct permissions and ownership

### Hardware Display Tests

- [ ] **HIL-005** Test display hardware direct rendering
  - [ ] Run: `python -c "from weatherbox.display.rpi_adapter import RpiAdapter; a = RpiAdapter(); a.initialize(); print('Display ready')" 2>&1 | grep -q "ready" && echo PASS || echo FAIL`
  - [ ] Display should show no errors (or mock mode if library unavailable)
  - [ ] Note: May require GPIO access / sudo

- [ ] **HIL-006** Test clear/blank display
  - Command: `systemctl stop weatherbox-display && (sudo python3 -c "from weatherbox.display.rpi_adapter import RpiAdapter; a = RpiAdapter(); a.initialize(); a.clear_all()" 2>/dev/null || echo "Mock mode") && systemctl start weatherbox-display`
  - [ ] All LED matrices turn off / go blank
  - [ ] No partial pixels or artifacts
  - [ ] Restore weather display after test

### Service Runtime Tests

- [ ] **HIL-007** Test service starts successfully
  - Command: `systemctl start weatherbox-display && sleep 2 && systemctl is-active weatherbox-display`
  - [ ] Service transitions to `active (running)`
  - [ ] No startup errors in logs: `journalctl -u weatherbox-display -n 20`

- [ ] **HIL-008** Test display shows initial forecast
  - [ ] Wait 10-15 seconds after service start
  - [ ] LED matrices display weather icons
  - [ ] Can identify at least 1 matrix shows data (not blank)
  - [ ] No error symbols (X pattern) visible unless API fails (expected)

- [ ] **HIL-009** Test API updates trigger re-render
  - [ ] Observe display for 1-2 update cycles (5 min daytime, 1 hour night)
  - [ ] Confirm display content updates after each interval
  - [ ] No hanging or frozen displays
  - [ ] Timestamps in logs show fetch events: `journalctl -u weatherbox-display -f | grep -i "fetch\|update"`

### Feature Tests

- [ ] **HIL-010** Test current day rendering (Matrix 0)
  - [ ] Matrix 0 displays today's forecast
  - [ ] If before 18:00: shows high temp + daytime weather icon
  - [ ] If after 18:00: shows low temp + night weather icon
  - [ ] Format visible (number pattern recognizable as temperature)

- [ ] **HIL-011** Test 3-day forecast rendering (Matrices 1-3)
  - [ ] Matrix 1 shows tomorrow's forecast
  - [ ] Matrix 2 shows day +2 forecast
  - [ ] Matrix 3 shows day +3 forecast
  - [ ] Each matrix shows unique weather icon
  - [ ] Temperature values distinguish between days

- [ ] **HIL-012** Test daytime update interval (5 minutes)
  - Observed between 06:00–23:00:
  - [ ] Check logs: `journalctl -u weatherbox-display | grep "updated\|rendered" | tail -10`
  - [ ] Confirm updates occur ~5 minutes apart (within ±1 min drift)
  - [ ] Display content refreshes with each update

- [ ] **HIL-013** Test night update interval (60 minutes)
  - Observed between 23:00–06:00 OR use time travel if available:
  - [ ] Check logs for update times
  - [ ] Confirm updates occur ~60 minutes apart
  - [ ] Verify display only refreshes hourly (not every 5 min)

- [ ] **HIL-014** Test brightness control
  - [ ] Observe display brightness during day vs night
  - [ ] Day brightness noticeably brighter than night
  - [ ] No excessive brightness causing LED strain
  - [ ] No flashing or flickering

- [ ] **HIL-015** Test brightness night mode (after 22:00)
  - [ ] After 22:00, display dims to night brightness
  - [ ] Night brightness cap prevents overheating
  - [ ] Transition smooth, no sudden changes

### Error Handling & Recovery

- [ ] **HIL-016** Test API failure handling
  - [ ] Stop Internet (unplug Ethernet or disable Wi-Fi)
  - [ ] Wait for API timeout (~10 sec)
  - [ ] Verify error symbol displays (X pattern on all matrices)
  - [ ] Check logs for API error: `journalctl -u weatherbox-display | grep -i "error\|fail"`

- [ ] **HIL-017** Test retry schedule on API failure
  - [ ] With Internet stopped, observe display for 10+ minutes
  - [ ] Confirm retry attempts logged (1 min, 5 min intervals)
  - [ ] Display continues retrying without crashing
  - [ ] No excessive CPU/GPU usage

- [ ] **HIL-018** Test recovery after API failure
  - [ ] Restore Internet connectivity
  - [ ] Wait for next retry attempt (should be within 5 minutes)
  - [ ] Verify weather display re-appears after recovery
  - [ ] Check logs for successful fetch: `journalctl -u weatherbox-display | grep -i "success\|fetched"`

- [ ] **HIL-019** Test graceful shutdown
  - Command: `systemctl stop weatherbox-display`
  - [ ] Service stops within 5 seconds
  - [ ] No errors in logs
  - [ ] Display clears or remains in last state (not corrupted)
  - [ ] No zombie processes: `ps aux | grep weatherbox`

### Logging & Diagnostics

- [ ] **HIL-020** Verify structured logging
  - Command: `journalctl -u weatherbox-display -n 50 | head -20`
  - [ ] Logs include timestamps
  - [ ] Logs include log levels (INFO, WARNING, ERROR)
  - [ ] Logs include meaningful event descriptions
  - [ ] No truncated or corrupted log lines

- [ ] **HIL-021** Check error diagnostics saved
  - [ ] After an API failure, check `/var/log/weatherbox/` or configured diagnostics dir
  - [ ] Error snapshots exist (JSON files with timestamps)
  - [ ] Snapshots include API response and error message
  - [ ] Can identify root cause from diagnostics

### Performance & Stability

- [ ] **HIL-022** Test memory usage
  - Command: `ps aux | grep weatherbox-display`
  - [ ] Process memory (RSS) < 100 MB (healthy Python process)
  - [ ] No memory leak over 10+ minutes of operation
  - [ ] System remains responsive

- [ ] **HIL-023** Test CPU usage
  - [ ] Display refresh does not spike CPU beyond 20%
  - [ ] Service idle between updates (minimal CPU)
  - [ ] No runaway threads or locks

- [ ] **HIL-024** Test long-term stability (30+ minutes)
  - [ ] Leave display running for 30+ minutes
  - [ ] Verify no crashes or restarts: `systemctl status weatherbox-display`
  - [ ] Display continues updating on schedule
  - [ ] Logs show consistent operation

### Environmental Tests (Optional)

- [ ] **HIL-025** Test with varying lighting conditions (if ambient sensor installed)
  - [ ] Bright room: verify brightness adjusts down
  - [ ] Dark room: verify brightness adjusts up
  - [ ] Gradual transitions work smoothly

- [ ] **HIL-026** Test with network interruptions
  - [ ] Brief Wi-Fi disconnection (5-10 seconds)
  - [ ] Verify service recovers without restart
  - [ ] Longer outage (>5 min): verify error handling
  - [ ] No catastrophic failures

## Cleanup & Next Steps

After completing all tests:

- [ ] **HIL-027** Document any issues found
  - [ ] Log unique symptoms or failures
  - [ ] Include timestamps and error messages
  - [ ] Create GitHub issues for bugs

- [ ] **HIL-028** Restore normal operation
  - [ ] Ensure Wi-Fi and Internet are active
  - [ ] Restart service: `systemctl restart weatherbox-display`
  - [ ] Confirm display shows weather again

## Success Criteria

**All tests must pass for HIL verification to be complete:**
- Display renders correctly on all 4 matrices
- Updates occur on correct schedule (5 min / 60 min)
- API failures are handled gracefully with retries
- Performance is stable over extended runtime
- Logs are clear and diagnostic

**If any test fails:** Follow the troubleshooting steps in `/specs/002-weather-display/research.md` or contact the development team.

---

**Test Date:** _______________
**Tester:** _______________
**Hardware:** Pi Model: _____________ OS: _____________ Python: _____________
**Result:** ☐ PASS  ☐ FAIL  ☐ PARTIAL
