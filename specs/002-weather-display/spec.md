```markdown
# Feature Specification: Weather fetch and 8×8 display

**Feature Branch**: `002-weather-display`
**Created**: 2026-02-22
**Status**: Draft
**Input**: Fetch Met Office forecasts and render day/night summaries on four 8×8 LED matrices.

## User Scenarios & Testing

### User Story - Forecast fetch and display (Priority: P1)

As an end user, I want the device to show today's and the next three days' summary forecasts on four 8×8 LED matrices so I can read current and upcoming weather at a glance.

**Independent Test**: With network connected, configure a known location in the config file, run the service and verify the four matrices show: current-day summary (max or min temp depending on time) and three subsequent days' max temps and icons.

**Acceptance Scenarios**:
1. Given current local time before 18:00, When forecast retrieved, Then matrix 1 shows today's maximum temperature and the most common daytime weather type; matrices 2–4 show each of the next 3 days' maximum temperature and most common daytime weather type.
2. Given current local time at or after 18:00, When forecast retrieved, Then matrix 1 shows today's minimum temperature and the most common night weather type; matrices 2–4 as above.
3. Given forecast lookup failure, When network/API is unreachable, Then all four matrices display the defined error symbol and the service follows the retry/backoff schedule.

---

## Edge Cases
- Partial network connectivity (DNS failures) → treat as lookup failure and follow retry schedule.
- Invalid/missing config location → fall back to a device-level default location and log a warning; surface error on matrix and record diagnostics.

## Requirements

### Functional Requirements
- **FR-WX-005**: The device MUST fetch the Met Office forecast for the configured location: today's forecast and at least the next 3 days.
- **FR-WX-006**: For the current day, if local time < 18:00, display today's maximum temperature and most common daytime weather type; otherwise display today's minimum and most common night type.
- **FR-WX-007**: For next 3 days, each matrix MUST display that day's maximum temperature and most common daytime weather type.
- **FR-WX-008**: Weather types returned by the Met Office MUST be mapped to a predefined icon set; mapping MUST be configurable in `config/icons.yaml`.
- **FR-WX-009**: Update cadence: 06:00–23:00 every 5 minutes; 23:00–06:00 hourly.
- **FR-WX-010**: On forecast lookup failure, display an error symbol and follow retry schedule.

### Non‑functional Requirements
- **NFR-WX-001 (Resilience)**: Retry/backoff schedule: every 1 min for 5 attempts; every 5 min for 12 attempts; then every 10 min until restored.
- **NFR-WX-003 (Performance)**: Keep sustained CPU usage under target budgets on Pi 3/4.
- **NFR-WX-005 (Safety)**: Brightness caps, night mode, and ambient adaptation supported.

## Implementation Notes
- Icon mapping: `config/icons.yaml` mapping Met Office strings to icon IDs; include documented fallback icon.
- Display driver: adapter layer so HIL tests can inject a frame capture implementation instead of writing to GPIO.
- Config path: `config.yaml` at repo root; include `config.yaml.example` with expected keys.

## Success Criteria
- **SC-WX-003**: Forecast update cadence matches configured windows with logs showing schedule.
- **SC-WX-004**: On simulated API/network failure, error symbol appears and retry schedule executes as specified.

```
