# Implementation Plan: Weather fetch and 8×8 LED display

**Branch**: `001-connect` | **Date**: 2026-02-22 | **Spec**: `specs/002-weather-display/spec.md`
**Input**: Feature specification from `/specs/002-weather-display/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Fetch daily Met Office forecasts for a configured location and render 4-day summaries on four 8×8 LED matrices: matrix 1 shows current day (max/min temp depending on time of day) and weather type; matrices 2–4 show next 3 days' max temps and weather. Implement exponential backoff retry schedule (1 min × 5; 5 min × 12; 10 min thereafter); update cadence is 5 minutes daytime (06:00–23:00) and hourly at night. Include brightness caps and optional ambient sensor support for safety.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11 (target Pi OS / Debian-derived images)
**Primary Dependencies**: `requests` (Met Office API), `pillow` (image/icon generation), `rpi-rgb-led-matrix` (display driver) or similar mature LED matrix lib; test deps: `pytest`, `freezegun` (time mocking).
**Storage**: Local YAML config (`config.yaml`, `config/icons.yaml`) and optional JSON/YAML logs for diagnostics.
**Testing**: `pytest` for unit and integration; use test doubles / frame capture adapters for display driver in CI.
**Target Platform**: Raspberry Pi OS (Linux ARMv7/ARM64) — Pi 3/4 supported.
**Project Type**: Long-running system service/daemon with scheduled update loop and hardware output.
**Performance Goals**: Forecast fetch + render cycle < 2s at nominal bandwidth; sustained CPU usage <60% on Pi 3; forecast update cadence adherence (5-min updates 06:00–23:00, hourly otherwise).
**Constraints**: Limited CPU/memory on Pi; GPIO/SPI access for LED matrices; network latency and API rate limits; optional ambient brightness sensor input.
**Scale/Scope**: Single device; 4 LED matrices; daily forecast data for 4 days; retry schedule up to 10 min backoff.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

[Gates determined based on constitution file]

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── weatherbox/
│   ├── weather/
│   │   ├── metoffice_adapter.py    # Met Office API client
│   │   ├── forecast_parser.py      # Parse + aggregate forecast periods
│   │   └── retry_scheduler.py      # Backoff retry logic + update windows
│   ├── display/
│   │   ├── adapter.py              # Display driver abstraction
│   │   ├── rpi_adapter.py          # rpi-rgb-led-matrix wrapper
│   │   └── frame_capture.py        # Test-mode frame capture
│   ├── icons/
│   │   ├── icons.yaml              # Weather type → bitmap ID mapping (config)
│   │   └── loader.py               # Load and validate icon mapping
│   ├── brightness/
│   │   ├── controller.py           # Brightness limits + night mode
│   │   └── sensor_adapter.py       # Optional ambient sensor
│   ├── display_service.py          # Main service loop
│   └── led8x8icons.py              # Bitmap definitions (existing)

tests/
├── unit/
│   ├── test_metoffice_parser.py
│   ├── test_retry_scheduler.py
│   └── test_brightness_controller.py
├── integration/
│   ├── test_forecast_fetch_and_render.py
│   └── test_update_schedule.py
└── hil/
    └── hil_display_rotation.sh     # Hardware-in-loop smoke test
```

**Structure Decision**: Single-project layout with weather fetch, display rendering, and scheduling in modular subdirectories under `src/weatherbox/`. Test structure mirrors source modules. HIL tests in separate directory.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
