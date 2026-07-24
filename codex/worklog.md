# Codex Worklog

## 2026-07-24

- Initialized the shared contest workspace and Codex handoff structure.
- Adapted external-storage and YT policy from neighboring `troll_farm` and
  `math_through_eml` projects.
- Corrected persistent `medium_data` mounting with a UUID-based, boot-safe
  `fstab` entry.
- Provisioned all five external-backed roots and validated writes through
  their repository symlinks.
- Installed and initialized Git LFS 3.0.2; verified project attribute routing.
- Imported the team credentials into the ignored `.env`, completed the normal
  browser/CAPTCHA login, and saved the bearer key without logging it.
- Added and live-validated the `icfpc-api` problem, clock, submission, wait,
  and guarded submit commands; documented them in `docs/api-tools.md`.
