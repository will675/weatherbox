```markdown
# Feature Specification: Wi‑Fi provisioning (Connection Portal)

**Feature Branch**: `001-connect`
**Created**: 2026-02-22
**Status**: Draft
**Input**: Provide an access-point + captive web UI for Wi‑Fi provisioning, plus resilient attempt-to-connect behaviour using stored credentials.

## User Scenarios & Testing

### User Story - Wi‑Fi provisioning & persistent connection (Priority: P1)

As an installer/owner, I want the device to automatically connect to a stored Wi‑Fi network if available, and fall back to an access point with a captive web UI to provision Wi‑Fi if no working connection exists, so the device can be networked without needing physical access to the Pi's OS.

**Independent Test**: Boot a virgin SD image without stored credentials → device starts AP and serves captive UI listing SSIDs; enter SSID+password → device connects and reports success to the UI. With stored credentials, boot device and verify it attempts up to 3 connection attempts, and only starts AP if connection attempts fail.

**Acceptance Scenarios**:
1. Given no stored Wi‑Fi credentials, When device boots, Then it hosts a secure access point (SSID configurable) and serves a captive web UI listing scanned SSIDs and an input for password.
2. Given stored credentials, When device boots, Then it attempts to connect up to 3 times and, on success, continues to normal operation and does not host AP.
3. Given stored credentials that fail, When retry attempts are exhausted, Then the device starts the AP and captive UI for reprovisioning.
4. When user provisions credentials via the UI, Then credentials are stored securely (file permissions / encrypted store) and used on next boot.

---

## Edge Cases
- Repeated failed provisioning attempts (wrong password) → rate-limit captive UI attempts and require physical reset after N failed provision attempts (documented manual recovery).
- Partial network connectivity (DNS failures) should be detected and treated as lookup failure for upstream services.

## Requirements

### Functional Requirements
- **FR-CONN-001**: Device MUST attempt to connect to stored Wi‑Fi credentials on boot. It MUST attempt up to 3 connection attempts before failing over to AP mode.
- **FR-CONN-002**: If no stored credentials or connection attempts fail, device MUST host a Wi‑Fi access point with a captive web UI listing scanned SSIDs and allowing password entry.
- **FR-CONN-003**: The provisioning UI MUST validate basic password constraints client-side (non-empty, length limits) and post credentials to the device securely.
- **FR-CONN-004**: Stored credentials MUST be stored with least privilege (file permissions) and preferably encrypted at rest (document implementation choice).

### Non‑functional Requirements
- **NFR-CONN-SEC**: Device MUST not expose stored credentials via the provisioning UI or logs. AP behaviour (open vs WPA2) MUST be documented and configurable.
- **NFR-CONN-OBS**: Device MUST provide logs for connection attempts, provisioning events, and diagnostics captures to facilitate testing.

## Implementation Notes
- Config file path: `config.yaml` at repository root on device; provisioning secrets stored with least privilege or encrypted store.
- Wi‑Fi stack: prefer an abstraction layer wrapped around NetworkManager / wpa_supplicant so test doubles can be used in CI.
- Captive UI: serve a minimal UI that lists SSIDs and posts credentials to a local endpoint; CSRF protections and HTTPS/local-only constraints should be considered.

## Success Criteria
- **SC-CONN-001**: Device with no stored credentials boots and is reachable via the AP captive UI within 60s and shows at least 5 scanned SSIDs.
- **SC-CONN-002**: Device with valid stored credentials connects within 30s in >95% of cold‑boot tests (n=20) on target hardware.

## Open Questions
1. Provisioning AP security model: open AP + captive portal, WPA2‑PSK with default printed password, or ephemeral key distribution? (Choose preferred approach.)
2. Credentials storage encryption: use OS keyring/hardware store, file permissions only, or local encryption with device key?

```
