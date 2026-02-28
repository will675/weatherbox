# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11 (target Pi OS / Debian-derived images)
**Primary Dependencies**: `flask` (captive UI), `requests` (HTTP), optional `python-networkmanager` or `nmcli` wrapper; test deps: `pytest`.
**Storage**: Local file-based YAML config (`config.yaml`) with credentials stored in a restricted file (`/etc/weatherbox/credentials.yaml`) — optional symmetric encryption using libsodium if hardware/keyring available.
**Testing**: `pytest` for unit and integration; use test doubles / mocks for NetworkManager and display adapters.
**Target Platform**: Raspberry Pi OS (Linux ARMv7/ARM64) — Pi 3/4 supported.
**Project Type**: Long-running system service/daemon with a small web UI for provisioning.
**Performance Goals**: Low CPU usage for provisioning service; connection attempts within 30s for success cases; provisioning UI reachable within 60s on boot for virgin devices.
**Constraints**: Limited CPU/memory on Pi models; headless device (no local display other than LED matrices); network stack varies across OS flavors (NetworkManager vs wpa_supplicant).
**Scale/Scope**: Single-device provisioning and ongoing background services; integration + HIL testing targeting attached hardware.

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
│   ├── wifi/
│   │   ├── adapter.py              # WifiAdapter interface
│   │   ├── nm_adapter.py           # NetworkManager implementation
│   │   └── wpa_adapter.py          # wpa_supplicant implementation
│   ├── provisioning/
│   │   ├── app.py                  # Flask captive portal app
│   │   ├── boot.py                 # Boot orchestration (connect attempts + AP fallback)
│   │   ├── ap_manager.py           # AP bring-up wrapper
│   │   └── static/
│   │       └── index.html          # Captive UI form
│   ├── credentials/
│   │   └── store.py                # Credential save/load with file permissions
│   ├── logging.py                  # Logging configuration
│   └── led8x8icons.py              # Bitmap definitions (existing)

tests/
├── unit/
│   ├── test_wifi_adapter.py
│   ├── test_credential_store.py
│   └── test_ap_manager.py
├── integration/
│   └── test_provision_flow.py
└── hil/
    └── smoke_provision.sh          # Hardware-in-loop smoke test
```

**Structure Decision**: Single-project layout with Wi-Fi stack, provisioning portal, and credential management in modular subdirectories under `src/weatherbox/`. Test structure mirrors source modules. HIL tests in separate directory.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
