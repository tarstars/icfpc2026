# Codex State

Updated: 2026-07-24

## Objective

Provide safe, reusable contest API access while Claude develops littleman
solutions.

## Completed

- Established shared repository layout and policies.
- Established Codex handoff files.
- Added a fail-closed external-storage preflight.
- Provisioned and validated all logical bulk roots on `medium_data`.
- Added a stable, boot-safe UUID entry for `medium_data` to `/etc/fstab`.
- Configured common large artifact formats for Git LFS.
- Retrieved the team bearer key through the normal CAPTCHA-protected browser
  login and stored all credentials only in the ignored, mode-0600 `.env`.
- Added a `uv`-managed API client with public problem/clock reads,
  authenticated submission reads and waits, and explicitly confirmed
  submission creation.
- Added shared API tool descriptions and tests.

## Blockers

- None for API access.

## Next steps

1. Support Claude with live problem retrieval and result polling.
2. Create contest submissions only when the exact problem ID and locally
   judged program are intentionally selected.
