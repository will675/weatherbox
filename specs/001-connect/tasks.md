```markdown
# Tasks: Wi‑Fi provisioning (specs/001-connect)

**Feature**: Wi‑Fi provisioning (Connection Portal)

## Phase 1: Setup
- [x] T001 [P] Create `requirements.txt` with `flask`, `requests`, `python-networkmanager` (optional), and `pynacl` at `requirements.txt`
- [x] T002 Create example configuration file `config.yaml.example` with keys: `ap_ssid`, `ap_mode`, `credential_file_path`, `service_user` at `config.yaml.example`
- [x] T003 Create systemd unit template for the provisioning service at `packaging/systemd/weatherbox-provisioning.service`

## Phase 2: Foundational
- [x] T004 Create Wi‑Fi adapter interface `WifiAdapter` (methods: `scan()`, `connect(ssid,password)`, `status()`) at `src/weatherbox/wifi/adapter.py`
- [x] T005 [P] Implement NetworkManager adapter at `src/weatherbox/wifi/nm_adapter.py` that implements `WifiAdapter` (use `python-networkmanager` or `nmcli` fallback)
- [x] T006 [P] Implement wpa_supplicant adapter at `src/weatherbox/wifi/wpa_adapter.py` that implements `WifiAdapter` (shell out to `wpa_cli`/`wpa_supplicant`)
- [x] T007 Create credential storage helper functions (`save_credentials`, `load_credentials`, `secure_file_permissions`) at `src/weatherbox/credentials/store.py`
- [x] T008 Create logging configuration and a provisioning logger at `src/weatherbox/logging.py`

## Phase 3: [US1] Wi‑Fi provisioning & persistent connection
- [ ] T009 [US1] Implement boot orchestration `boot_provision()` that: reads stored credentials, attempts up to 3 connects (with backoff), and falls back to AP mode on failure at `src/weatherbox/provisioning/boot.py`
- [ ] T010 [US1] [P] Implement AP manager to bring up an access point (NetworkManager/hostapd wrappers) at `src/weatherbox/provisioning/ap_manager.py`
- [ ] T011 [US1] [P] Scaffold captive portal Flask app with endpoints `/scan` (returns SSIDs) and `/provision` (accepts credentials) at `src/weatherbox/provisioning/app.py` and static files at `src/weatherbox/provisioning/static/index.html`
- [ ] T012 [US1] Implement client-side validation for the provisioning form (non-empty, length limits) and server-side CSRF protections in `src/weatherbox/provisioning/static/index.html` and `src/weatherbox/provisioning/app.py`
- [ ] T013 [US1] Store provisioned credentials via the credential helper to a secure path (default `/etc/weatherbox/credentials.yaml`) and ensure file mode `0600` at `src/weatherbox/credentials/store.py` (usage: invoked by `app.py`)
- [ ] T014 [US1] Add observable events/logs for connection attempts, provisioning submissions, and failures at `src/weatherbox/logging.py`

## Phase 4: Tests & Integration
- [ ] T015 [US1] [P] Add unit tests for adapter interface and adapters at `tests/unit/test_wifi_adapter.py`
- [ ] T016 [US1] Add integration test script that simulates a fresh-boot provisioning flow using test doubles at `tests/integration/test_provision_flow.py`
- [ ] T017 [US1] Add HIL checklist and a smoke test script for AP + captive UI availability at `specs/001-connect/checklists/hil.md` and `tools/hil/smoke_provision.sh`

## Final Phase: Polish & Cross-cutting
- [ ] T018 Create `specs/001-connect/quickstart.md` with steps: flash image, first-boot behaviour, provisioning flow, and recovery instructions at `specs/001-connect/quickstart.md`
- [ ] T019 Document credential storage choices and how to enable optional encryption at `specs/001-connect/research.md` (update existing file)
- [ ] T020 [P] Create packaging and install instructions (how to enable systemd unit) at `packaging/README.md`

## Dependencies
- Order: Phase1 → Phase2 → Phase3 (US1) → Phase4 → Final
- Parallelizable tasks: any marked with `[P]` can be implemented concurrently (e.g., adapters, unit tests, frontend scaffold).

## Parallel execution examples
- NetworkManager adapter (`T005`) and wpa_supplicant adapter (`T006`) can proceed in parallel.
- Frontend scaffold (`T011`) and credential helper (`T007`) can be developed in parallel.

## Independent test criteria (per story)
- US1: Fresh device boots → AP + captive UI available within 60s; entering credentials causes device to connect on next boot. Test scripts: `tests/integration/test_provision_flow.py` and HIL smoke script at `tools/hil/smoke_provision.sh`.

## MVP suggestion
- Minimal deliverable: `T004`, `T007`, `T009`, `T011`, `T013`, `T015` (adapter interface, credential store, boot flow, captive UI, secure storage, unit tests).

```
