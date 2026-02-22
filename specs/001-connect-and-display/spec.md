```markdown
# Feature Specification: Wi‑Fi provisioning + Met Office weather display

**Feature Branch**: `001-connect-and-display`
**Created**: 2026-02-22
**Status**: Draft
**Input**: Build an application to run on a Raspberry Pi that provides Wi‑Fi provisioning (AP + captive web UI) and a weather-display driver that fetches forecasts from the Met Office API and renders day/night summaries on four 8x8 LED matrices.

## User Scenarios & Testing (mandatory)

### User Story 1 - Wi‑Fi provisioning & persistent connection (Priority: P1)

As an installer/owner, I want the device to automatically connect to a stored Wi‑Fi network if available, and fall back to an access point with a captive web UI to provision Wi‑Fi if no working connection exists, so the device can be networked without needing physical access to the Pi's OS.

**Why this priority**: Without network connectivity the device cannot fetch weather data or receive remote updates.

**Independent Test**: Boot a virgin SD image without stored credentials → device starts AP and serves captive UI listing SSIDs; enter SSID+password → device connects and reports success to the UI. With stored credentials, boot device and verify it attempts up to 3 connection attempts, and only starts AP if connection attempts fail.

**Acceptance Scenarios**:
1. Given no stored Wi‑Fi credentials, When device boots, Then it hosts a secure access point (SSID configurable) and serves a captive web UI listing scanned SSIDs and an input for password.
2. Given stored credentials, When device boots, Then it attempts to connect up to 3 times and, on success, continues to normal operation and does not host AP.
3. Given stored credentials that fail, When retry attempts are exhausted, Then the device starts the AP and captive UI for reprovisioning.
4. When user provisions credentials via the UI, Then credentials are stored securely (file permissions / encrypted store) and used on next boot.

---

### User Story 2 - Forecast fetch and display (Priority: P1)

As an end user, I want the device to show today's and the next three days' summary forecasts on four 8×8 LED matrices so I can read current and upcoming weather at a glance.

**Why this priority**: This is the core product function.

**Independent Test**: With network connected, configure a known location in the config file, run the service and verify the four matrices show: current-day summary (max or min temp depending on time) and three subsequent days' max temps and icons.

**Acceptance Scenarios**:
1. Given current local time before 18:00, When forecast retrieved, Then matrix 1 shows today's maximum temperature and the most common daytime weather type; matrices 2–4 show each of the next 3 days' maximum temperature and most common daytime weather type.
2. Given current local time at or after 18:00, When forecast retrieved, Then matrix 1 shows today's minimum temperature and the most common night weather type; matrices 2–4 as above (daytime max + most common daytime type).
3. Given forecast lookup failure, When network/API is unreachable, Then all four matrices display the defined error symbol and the service follows the retry/backoff schedule described in Non‑functional requirements.

---

## Edge Cases
- Partial network connectivity (DNS failures) → treat as lookup failure and follow retry schedule.
- Invalid/missing config location → fall back to a device-level default location and log an observable warning; surface a clear error in the UI (or on matrix) and record a diagnostics artifact.
- Repeated failed provisioning attempts (wrong password) → rate-limit captive UI attempts and require physical reset after N failed provision attempts (documented manual recovery).
- LED matrix failure or disconnected chain → surface an error on the remaining matrices and include the condition in diagnostics.

## Requirements (mandatory)

### Functional Requirements
- **FR-001**: Device MUST attempt to connect to stored Wi‑Fi credentials on boot. It MUST attempt up to 3 connection attempts before failing over to AP mode.
- **FR-002**: If no stored credentials or connection attempts fail, device MUST host a Wi‑Fi access point with a captive web UI listing scanned SSIDs and allowing password entry.
- **FR-003**: The provisioning UI MUST validate basic password constraints client-side (non-empty, length limits) and post credentials to the device securely (HTTPS or local-only form with CSRF protections when applicable).
- **FR-004**: Stored credentials MUST be stored with least privilege (file permissions) and preferably encrypted at rest (document implementation choice).
- **FR-005**: The device MUST fetch the Met Office forecast for the configured location: today's forecast and at least the next 3 days.
- **FR-006**: For the current day, if local time < 18:00, the device MUST display today's maximum temperature and the most common daytime weather type on matrix 1; if local time >= 18:00, show today's minimum temperature and most common night weather type on matrix 1.
- **FR-007**: For next 3 days, each subsequent matrix MUST display that day's maximum temperature and most common daytime weather type.
- **FR-008**: Weather types returned by the Met Office MUST be mapped to a predefined icon set; mapping MUST be configurable in a file (e.g., `config/icons.yaml`) and documented.
- **FR-009**: Update cadence: between 06:00 and 23:00 local time, forecasts MUST refresh every 5 minutes; between 23:00 and 06:00 refresh MUST be once per hour.
- **FR-010**: On forecast/API lookup failure, display an error symbol on all matrices and follow the retry schedule defined in Non‑functional Requirements.

### Non‑functional Requirements
- **NFR-001 (Resilience)**: Error retry/backoff schedule for forecast lookup: try every 1 minute for 5 minutes (5 attempts), then every 5 minutes for 60 minutes (12 attempts), then every 10 minutes until service is restored. All retries must be cancellable if connectivity is restored earlier.
- **NFR-002 (Security)**: Device MUST not expose stored credentials via the provisioning UI or logs. Access point should be configurable (SSID name) and protected by a strong default passphrase for provisioning sessions or use an open AP with a captive portal that only accepts connections to the local IP (document the chosen approach).
- **NFR-003 (Performance)**: Rendering and per-frame processing MUST not exceed the device budgets; target is to keep sustained CPU usage for the display process under 60% on Raspberry Pi 3/4 models under normal workload.
- **NFR-004 (Observability)**: Device MUST provide logs for connection attempts, provisioning events, API errors, and diagnostics captures (frame snapshots) to facilitate HIL testing.
- **NFR-005 (Safety)**: Brightness caps MUST be enforced to prevent overheating; night mode and ambient adaptation MUST be supported.

## Key Entities
- Wi‑Fi credentials (SSID, password, security type, last‑seen timestamp)
- Config (location id, icons mapping, update windows, display brightness limits)
- Forecast bundle (date, day/night max/min temps, list of weather type occurrences)
- Icon map (Met Office weather type → icon index)

## Success Criteria (mandatory)
- **SC-001**: Device with no stored credentials boots and is reachable via the AP captive UI within 60s and shows at least 5 scanned SSIDs.
- **SC-002**: Device with valid stored credentials connects within 30s in >95% of cold‑boot tests (n=20) on target hardware.
- **SC-003**: Forecast display update cadence matches configured windows (5‑minute updates between 06:00–23:00, hourly otherwise) for a 24‑hour run with logs demonstrating schedule.
- **SC-004**: On simulated API/network failure, the error symbol appears on all matrices within the retry window and the retry schedule executes as specified.
- **SC-005**: Icons shown for at least 90% of forecast types in a mapping test (mapping file covers returned types or has a documented fallback icon).

## Test Plan (high level)
- Unit tests: parsing Met Office responses, mapping logic, config validation, retry scheduler.
- Integration tests: Wi‑Fi connection logic (mocked system calls), captive UI endpoints, end‑to‑end forecast fetch (stubbed API), display driver API (simulated matrix frames).
- Hardware‑in‑the‑loop (HIL): boot a Pi with attached four 8×8 matrices and run full stack: provisioning flow, normal operation, simulated API outage, thermal/brightness checks, frame capture comparisons using pixel tolerance thresholds.
- Smoke tests: power‑cycle behaviour, provisioning, and recovery.

## Assumptions
- The Met Office API provides a forecast API that returns per‑period weather type and temperatures for at least current day + 3 days for the specified location.
- The hardware wiring for four chained 8×8 matrices and driver library (e.g., rpi-rgb-led-matrix or equivalent) is available and exposes per‑matrix frame writes.
- Device has writable persistent storage for config and credentials (SD card) and a method for secure storage (file permissions or lightweight encryption).

## Open Questions / NEEDS CLARIFICATION (max 3)
1. Provisioning AP security model: prefer (A) open AP + captive HTTPS portal bound to local IP, (B) WPA2‑PSK AP with a strong default password printed on device, or (C) ephemeral key distribution. Which approach is preferred? (Impacts security and UX.)
2. Credentials storage encryption: (A) use OS keyring/hardware-backed store if available, (B) use file permissions only, (C) implement lightweight local encryption with a device key – which is acceptable?
3. Met Office API authentication/limits: do we have an API key and rate limits documented? If so, supply them; otherwise we will design with conservative rate budgets and error handling.

## Implementation Notes
- Config file path: `config.yaml` at repository root on device; `config.yaml.example` will contain the expected keys (location id, update windows, brightness, icons mapping file path).
- Icon mapping: `config/icons.yaml` — this maps canonical Met Office type strings to one of the predefined icon IDs.
- Wi‑Fi stack: prefer NetworkManager or systemd‑networkd wrappers where available; provide an abstraction layer to allow test doubles in CI.
- Display driver: provide an adapter layer so HIL tests can inject a frame capture implementation instead of writing to physical GPIO in CI.

## Deliverables
- `spec.md` (this file)
- `plan.md` (for follow‑up `/speckit.plan`) — will define chosen stack and file layout
- `tasks.md` (generated by `/speckit.tasks`) — actionable tasks
- HIL test scripts and a diagnostics capture utility (proposed)

## Readiness
This spec is complete enough to start `/speckit.plan` after the three clarification questions above are answered. The plan will select concrete libraries (NetworkManager vs direct wpa_supplicant, rpi matrix driver choice) and produce the implementation tasks.

``` 
