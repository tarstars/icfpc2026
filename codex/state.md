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
- Implemented a generated 16-stage streaming Sort pipeline, passed all 7
  public cases locally, and submitted it successfully for 25/25 server cases.
- Preserved Sort variants in a machine-readable catalogue and submitted the
  geometry-only 92×92 successor successfully for 25/25 server cases and a
  38,830,462.08 server score.
- Implemented and preserved a radix-packed 89×89 History Lesson solution; it
  passed 1/1 live at score 7,921 and tied rank 7 at the recorded snapshot.
- Corrected the local judge to honor footprint-only scoring.
- Matched local backtick pairing to the stricter server parser after preserving
  the initial rejected candidate and its load error.
- Implemented a 38×41 Packet Reassembly ring candidate that passes all six
  public cases at local score 12,232,076.67.

## Blockers

- None for API access.

## Next steps

1. Support Claude with live problem retrieval, submission, and result polling.
2. Preserve and submit the Packet Reassembly candidate only when explicitly
   selected, then optimize its geometry against the live result.
