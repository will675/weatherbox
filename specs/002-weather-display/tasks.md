# Tasks: Weather fetch and display (specs/002-weather-display)

**Feature**: Weather fetch and 8×8 display

## Phase 1: Setup
- [x] T001 [P] Create `requirements.txt` with `requests`, `apscheduler`, `pytz`, `pyyaml`, `rpi-rgb-led-matrix` (or mock), and test deps: `pytest`, `freezegun` at `requirements.txt`
- [x] T002 Create example configuration file `config.yaml.example` with keys: `met_office_location_code`, `api_key` (optional), `update_window_day`, `update_window_night`, `brightness_cap`, `icons_config_path` at `config.yaml.example`
- [x] T003 Create sample icon mapping file `config/icons.yaml.example` with Met Office weather types mapped to icon IDs from `led8x8icons.py` at `config/icons.yaml.example`
- [x] T004 Create systemd unit template for the display service at `packaging/systemd/weatherbox-display.service`

## Phase 2: Foundational
- [x] T005 Create display adapter interface `DisplayAdapter` (methods: `render_frame(matrix_index, bitmap)`) at `src/weatherbox/display/adapter.py`
- [ ] T006 [P] Implement rpi-rgb-led-matrix adapter at `src/weatherbox/display/rpi_adapter.py` using the hardware library
- [x] T007 [P] Implement frame-capture test adapter at `src/weatherbox/display/frame_capture.py` for unit/integration testing
- [x] T008 Create retry/backoff scheduler `RetryScheduler` (exponential backoff: 1 min ×5; 5 min ×12; 10 min thereafter) at `src/weatherbox/weather/retry_scheduler.py`
- [x] T009 Create update window scheduler that enforces 5-min daytime (06:00–23:00) and hourly night updates at `src/weatherbox/weather/retry_scheduler.py` (extend existing class)
- [x] T010 [P] Create Met Office API client and response parser at `src/weatherbox/weather/metoffice_adapter.py` handling 3-hourly periods and aggregation
- [x] T011 [P] Create forecast aggregator to compute daily summaries: max/min temps, most common day/night weather type at `src/weatherbox/weather/forecast_parser.py`
- [x] T012 Create icon mapping loader and validator at `src/weatherbox/icons/loader.py` with fallback icon logic
- [x] T013 Create logging configuration for display service at `src/weatherbox/logging.py` with structured logs for API errors, render events, and diagnostics

## Phase 3: [US1] Forecast fetch and display
- [ ] T014 [US1] [P] Implement brightness controller with caps and night mode (after 22:00) at `src/weatherbox/brightness/controller.py`
- [ ] T015 [US1] [P] Scaffold optional ambient brightness sensor adapter at `src/weatherbox/brightness/sensor_adapter.py`
- [ ] T016 [US1] Render current day (matrix 1): show max temp + weather type if before 18:00; min temp + night weather if at/after 18:00 at `src/weatherbox/display_service.py` (rendering logic)
- [ ] T017 [US1] Render next 3 days (matrices 2–4): each shows max temp + most common daytime weather type at `src/weatherbox/display_service.py` (rendering logic, continued)
- [ ] T018 [US1] Implement main service loop that: fetches forecast, applies retry schedule, renders to display, and logs events at `src/weatherbox/display_service.py` (main)
- [ ] T019 [US1] Display error state on all matrices when API lookup fails; verify error symbol from `led8x8icons.py` is available at `src/weatherbox/display_service.py` (error handling)
- [ ] T020 [US1] Add diagnostic capture (frame snapshot + API response dump) on errors to facilitate debugging at `src/weatherbox/display_service.py` (logging)

## Phase 4: Tests & Integration
- [ ] T021 [US1] [P] Add unit tests for forecast parser (aggregation logic, day/night rules) at `tests/unit/test_forecast_parser.py`
- [ ] T022 [US1] [P] Add unit tests for retry scheduler (backoff state machine, update window transitions) at `tests/unit/test_retry_scheduler.py`
- [ ] T023 [US1] [P] Add unit tests for brightness controller (caps, night mode transitions) at `tests/unit/test_brightness_controller.py`
- [ ] T024 [US1] Add integration test: fetch + parse + render cycle with stubbed API, verify frame output at `tests/integration/test_forecast_fetch_and_render.py`
- [ ] T025 [US1] Add integration test: simulate API failure, verify retry schedule executes and error symbol appears on display at `tests/integration/test_forecast_fetch_and_render.py` (continued)
- [ ] T026 [US1] Add integration test: verify update cadence (5-min daytime, hourly night) using mocked time at `tests/integration/test_update_schedule.py`
- [ ] T027 [US1] Add HIL checklist and smoke test script for display rotation (run on Pi with matrices attached) at `specs/002-weather-display/checklists/hil.md` and `tools/hil/hil_display_rotation.sh`

## Final Phase: Polish & Cross-cutting
- [ ] T028 Create `specs/002-weather-display/quickstart.md` with steps: configure location, API key, icon mapping; deploy service; verify output at `specs/002-weather-display/quickstart.md`
- [ ] T029 Document Met Office API integration, retry schedule, and brightness tuning at `specs/002-weather-display/research.md` (update existing file if needed)
- [ ] T030 [P] Document icon mapping format and how to extend/customize at `config/icons.yaml.example` (comments/README)
- [ ] T031 [P] Create packaging and install instructions (systemd integration, config placement) at `packaging/README.md`

## Dependencies
- Order: Phase1 → Phase2 → Phase3 (US1) → Phase4 → Final
- Parallelizable tasks: any marked with `[P]` can be implemented concurrently (e.g., adapters, parsers, unit tests, sensors).

## Parallel execution examples
- Display adapters (`T006`, `T007`) can proceed in parallel.
- Weather adapters (`T010`, `T011`) can proceed in parallel.
- Brightness components (`T014`, `T015`) can proceed in parallel.
- Unit tests (`T021`, `T022`, `T023`) and integration tests (`T024`, `T025`) can develop in parallel.

## Independent test criteria (per story)
- US1: With network configured and location set in config, fetched forecast renders on matrices within 2s; day/night logic applies based on local time; API failures trigger error symbol and retry schedule. Test scripts: `tests/integration/test_forecast_fetch_and_render.py`, `tests/integration/test_update_schedule.py`, HIL smoke script at `tools/hil/hil_display_rotation.sh`.

## MVP suggestion
- Minimal deliverable: `T001`, `T005`, `T008`, `T010`, `T012`, `T016`, `T017`, `T018`, `T024` (setup, adapters, scheduler, API client, icon loader, rendering, main loop, integration test).
