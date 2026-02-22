# Project Constitution — IoT (Raspberry Pi + LED matrices)

Purpose: A concise, actionable set of principles and checks to guide engineering decisions for this IoT project (Raspberry Pi devices driving LED matrices). This document focuses on code quality & security, testing standards, user experience consistency, and performance requirements suitable for constrained hardware.

## Contract (short)
- Inputs: code changes (PRs), hardware changes, firmware updates, feature requests.
- Outputs: reliable firmware/software for Raspberry Pi devices that control LED matrices, with secure deployment, tested behaviour, consistent UX on displays, and measured performance within hardware budgets.
- Error modes: device-bricking updates, regressions in networking or display output, overheating, security exposure, battery/power issues, flaky hardware-dependent tests.
- Success criteria: PRs merge only after automated checks and required reviews; device images pass hardware integration tests; security checks and safe rollback paths exist for OTA updates.

## Overarching Principles
- Automate what you can (linters, tests, CI), but validate hardware flows with reproducible hardware tests.
- Prioritise safety and security: devices are deployed in the field and may be physically accessible.
- Optimise for clarity and maintainability; embedded/IoT code must be understandable by other engineers who may service devices.
- Keep the runtime footprint predictable and bounded; favour deterministic behaviour on low-power hardware.

## 1) Code Quality & Security

Principles:
- Code must be readable, well-documented, and testable. Prefer small modules and clear public APIs.
- Security is part of quality: design to minimize attack surface and protect secrets.

Rules & tooling (recommended):
- Use a formatter and linter suited for the language (black + flake8/mypy for Python, gofmt/golangci-lint for Go, ESLint/Prettier for JS).
- Require type checks / static analysis where available (mypy, TypeScript strict, etc.).
- No credentials or secrets in source. Use environment variables, config files excluded from VCS, or encrypted secret stores.
- All network endpoints and firmware updates must be authenticated and, where possible, signed.
- Run dependency vulnerability checks in CI (e.g., Dependabot, GitHub Dependabot alerts, or Snyk).

IoT-specific security rules:
- Run services as non-root. Drop capabilities where possible.
- Disable SSH password authentication; use key-based auth and consider ephemeral keys for provisioning.
- Encrypt sensitive local data (keys, tokens) and prefer hardware-backed storage (TPM, secure element) if available.
- Limit open ports and outbound access; use a firewall or iptables rules where practical.
- Implement fail-safe/rollback for OTA updates: keep the last known-good image and automatic rollback on boot failures.
- Log minimally and avoid exposing private info in logs.

Checklist for PR authors (security-focused):
- No secrets committed. All new secrets go to the secrets manager or encrypted store.
- Any network auth or update mechanism has documented authentication and signing.
- Privilege reduction verified (service runs as dedicated user).

## 2) Testing Standards (including hardware testing)

Principles:
- Tests should be fast, deterministic where possible, and include hardware-in-the-loop (HIL) for display/output-critical features.

Test categories & practices:
- Unit tests: logic-only tests that run in CI fast and without hardware.
- Integration tests: simulated hardware via mocks or test doubles; run in CI for functional contracts.
- Hardware-in-the-loop (HIL): automated tests that exercise the Pi + LED matrix (boot, display output, power cycling, sensors). Run on dedicated test benches or nightly CI runners with attached devices.
- End-to-end: for critical user journeys (display message, update firmware, network commissioning), maintain a small stable E2E suite that runs in a controlled test lab or on release gates.

Test data & determinism:
- Use deterministic fixtures and time-freezing for time-dependent logic.
- For HIL visual checks, capture images/frames and run pixel-tolerance comparisons rather than brittle visual diffs.

Flakiness & quarantine:
- Any flaky test must be annotated and either fixed or quarantined; persistent flakiness blocks merges for that area until addressed.

CI gating:
- PRs must pass unit and integration tests before merging. HIL tests may run in separate jobs and must pass for release branches or when changing hardware-related code.

Examples of acceptance criteria:
- A change to the display driver must include unit tests (logic), integration tests (driver API), and a HIL test plan or evidence showing device output matches expectations.

## 3) User Experience (UX) Consistency for LED Matrices

Principles:
- Provide consistent visual language across LED matrices: consistent brightness, colour profile, animation timing, and error indicators.
- Consider ambient conditions: brightness adaptation, night modes, and thermal constraints.

Design rules & measurable criteria:
- Brightness caps: define maximum allowed brightness per hardware revision to avoid overheating and excessive power draw.
- Colour palettes and gamma: define and document device colour profile and palette set; share as tokens/config.
- Animation frame budgets: set target FPS (e.g., 30 FPS max) and maximum per-frame CPU/GPU budget to avoid dropping frames or overheating.
- Error/maintenance UI: define a standard error pattern (colour/animation) that signals connectivity, update, or hardware failure; ensure messages are actionable.

Accessibility & physical safety:
- Use safe maximum brightness and avoid harmful flashing frequencies (adhere to guidelines to reduce photosensitive seizure risk).

Checklist for UI/display PRs:
- Include captured frames or a short recording demonstrating the change on target hardware.
- Verify brightness behaviour at operating extremes and document expected thermal effects.
- Accessibility / safety review for animations (frequency, contrast, brightness).

## 4) Performance & Resource Budgets

Principles:
- Define measurable budgets for latency, CPU, memory, power, and thermal usage. Measure rather than guess.
- Prioritise user-visible latency (e.g., display update latency) and reliability over micro-optimisations that complicate code.

Suggested budgets (adjust per hardware):
- Display update latency: per-frame processing should keep stable FPS (example target: 30 FPS for animations; 60 FPS only if hardware tested).
- CPU: avoid >60% sustained CPU utilization on Raspberry Pi 3/4 models for display drivers; measure under expected workload.
- Memory: keep process RSS predictable and within available RAM minus OS/services (e.g., reserve 100-200MB for OS on Pi 4 depending on image).
- Startup: service should be operational within a defined boot budget (e.g., < 30s to ready state) unless documented otherwise.

Measurement & tooling:
- Add microbenchmarks for critical rendering and network paths. Run these in CI or nightly runners and record metrics.
- Use simple tracing and profiling (py-spy, perf, simple logging of frame times) rather than heavy profilers on-device.

Regression policy:
- Treat regressions that exceed budgets as release blockers unless a mitigations plan and owner sign-off exist.

## Deployment, OTA & Recovery

- OTA updates must be signed and atomic where possible. Keep a fallback partition with the previous image.
- Implement health checks and watchdogs. If a device fails to become healthy after an update, automatically roll back.
- Document the manual recovery steps (serial console, SD reimage) and provide tooling to capture diagnostics before reimaging.

## PR Checklist (copyable)
- [ ] Linted & formatted
- [ ] Static analysis / types checked
- [ ] Unit tests added/updated
- [ ] Integration tests or mocks covering hardware API changes
- [ ] HIL test plan or evidence for display/driver changes (screenshots/frames)
- [ ] Security review: secrets, auth, runtime privileges
- [ ] Performance notes / benchmarks if change affects frame processing or networking
- [ ] Linked issue/ticket and migration notes (if applicable)

## Enforcement & Governance
- Place this file at `.github/CONSTITUTION.md` and link it from PR templates and onboarding material.
- CI: require `lint` and `test:unit` for PR merges. Require `test:integration` and HIL passes for release branches or changes touching hardware drivers.
- Security: add dependency vulnerability scans and require high-severity issues to be triaged before releases.
- Appoint owners for hardware, security, and releases in `CODEOWNERS`.
- Schedule periodic audits for security, tests, and power/thermal performance (quarterly or on major releases).

## Exceptions & escalation
- Document any exceptions to these rules in the PR with rationale and a remediation plan (example: temporary increased brightness for a demo must have a rollback plan and safety sign-off).

## Next steps & integration suggestions
- Add a PR template referencing this constitution and including the PR checklist.
- Create GitHub Actions jobs: `lint`, `test:unit`, `test:integration`, and a `hil` job for test-lab runners.
- Add a small diagnostics script that can be run on-device to capture state: CPU, memory, thermal, recent logs, and a frame capture.

---
Last updated: 2026-02-22
