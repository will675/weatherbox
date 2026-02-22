```markdown
# Research: Wi‑Fi provisioning (branch: 001-connect)

## Decisions & Rationale

- Decision: **Provisioning AP security model** — use an **open AP + captive portal bound to local IP** as the default, with an **optional WPA2-PSK mode** configurable by image builders.
  - Rationale: open AP + captive portal is the simplest UX for end users (no printed password required). It avoids typing long default passphrases and reduces on-device configuration. Security mitigations: captive portal will only accept configuration requests to the device's local IP, UI elements and endpoints will not echo secrets, requests are rate-limited, and the AP SSID is configurable. Offer WPA2 mode as opt-in for more security-sensitive deployments.
  - Alternatives considered: WPA2-PSK with a default printed password (more secure but worse UX); ephemeral key distribution (complex; requires additional tooling). Chosen option balances UX and security for consumer installs.

- Decision: **Credentials storage** — store credentials in a filesystem-owned file with least privileges (mode 600, owned by `root` or service user) and **prefer using OS keyring/hardware-backed store if available**. Optionally support symmetric encryption (libsodium secretbox) if a device key or TPM is available.
  - Rationale: file-permissions-only is universally available and simple to implement/test; using OS keyring or hardware-backed storage increases security where available. Provide configuration to enable encryption for deployments that can provision a device key.
  - Alternatives considered: enforced OS keyring only (not universally available on minimal Pi images), storing in plaintext (rejected).

- Decision: **Wi‑Fi stack abstraction** — implement a small abstraction layer over the system Wi‑Fi manager. Prefer using **NetworkManager** via `python-networkmanager` when present; fallback to `wpa_supplicant`/`wpa_cli` or `nmcli` invocations on systems without NetworkManager.
  - Rationale: NetworkManager simplifies scans, connection attempts and status queries for many Linux distros. A thin adapter supports test doubles in CI and allows deployment flexibility.

## Libraries & Tools (notes for later phases)

- Captive UI: `Flask` (small, well-supported), consider `Flask-Limiter` for rate-limiting and `itsdangerous`/CSRF protections.
- HTTP client: `requests` for any upstream calls from the provisioning component.
- Encryption (optional): `pynacl` (libsodium) for secretbox symmetric encryption if device keying is selected.
- System integration: `python-networkmanager` or shelling out to `nmcli`/`wpa_cli` as adapter implementations.

## Testing Considerations

- Unit tests: mock the Wi‑Fi adapter interface; validate credential storage behaviour; validate captive UI validation and CSRF protections.
- Integration: run on a Pi image (HIL) to validate AP bringing-up and captive web UI reachability within 60s.

## Open Items (carried forward)

- Met Office API key and rate limits: not applicable to this feature — defer to `002-weather-display` planning.

```
