# Research: Weather fetch and display (branch: 001-connect)

## Decisions & Rationale

- Decision: **Met Office API integration** — use the Met Office DataPoint API (or open-source alternative if no API key) to fetch site-specific forecasts. Implement a thin adapter to parse 3-hourly periods and aggregate to daily summaries.
  - Rationale: Met Office provides authoritative UK forecasts; DataPoint API is well-documented and widely used. Parsing periods and selecting "most common weather type" requires filtering by period type (day vs night) and aggregating.
  - Alternatives considered: OpenWeatherMap (broader geographic coverage but may require credentials), local YAML fallback for testing (not used in production).

- Decision: **Retry/backoff implementation** — exponential backoff encoded as: 1 min × 5 attempts; 5 min × 12 attempts; 10 min thereafter. Use `apscheduler` or similar to manage scheduled retries and update windows (5 min daytime, hourly night).
  - Rationale: aggressive early retries (1 min) catch transient failures; slower backoff (5–10 min) reduces load on API and device when connectivity is degraded. Scheduled updates respect time windows and can be cancelled if connectivity is restored earlier.
  - Alternatives considered: fixed interval retries (simpler but less responsive), fully random backoff (may not converge quickly).

- Decision: **Icon mapping** — store in `config/icons.yaml` mapping canonical Met Office weather type strings (e.g., "Partly cloudy", "Heavy rain") to icon bitmap IDs defined in `src/weatherbox/led8x8icons.py`. Include a documented fallback icon for unmapped types.
  - Rationale: decoupling icon logic from display code allows easy configuration and testing; fallback ensures partial failures don't break the display entirely.

- Decision: **Display driver abstraction** — implement a thin `DisplayAdapter` interface (methods: `render_frame(matrix_index, bitmap)`) wrapping the rpi-rgb-led-matrix library. In CI tests, inject a frame-capture adapter that serializes bitmaps instead of writing GPIO.
  - Rationale: enables testing without hardware; allows future support for other matrix drivers.

- Decision: **Brightness and safety** — cap LED brightness in software and support optional ambient brightness sensor input to reduce brightness automatically at night. Implement a "night mode" that further reduces brightness after 22:00.
  - Rationale: protects hardware from overheating and extends display lifespan; safety requirement from spec.

## Libraries & Tools (notes for later phases)

- HTTP client: `requests` with timeout and retry logic.
- Scheduling: `apscheduler` for managing timed updates and backoff retries.
- Time mocking in tests: `freezegun` to simulate different times of day.
- Display: `rpi-rgb-led-matrix` (Python bindings to the mature C++ library) or alternative LED matrix library.
- Logging: Python `logging` module with structured logs for diagnostics.

## Testing Considerations

- Unit tests: mock Met Office API responses; validate aggregation logic (most common type selection, day/night rules); test retry schedule state machine.
- Integration: run forecast fetch + render cycle with stubbed API; validate frame output matches expected icon sequence.
- HIL: boot on a Pi with attached four matrices; trigger API failures and verify retry schedule + error symbol display.

## Open Items (carried forward)

- Met Office API key / rate limits: must be provided before Phase 1 implementation begins (impacts retry schedule tuning).
- Ambient brightness sensor integration: optional enhancement; design should allow plugging in a sensor driver if available.
